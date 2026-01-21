#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

# Add conditional Playwright browser installation
if [[ "${WEB_LOADER_ENGINE,,}" == "playwright" ]]; then
    if [[ -z "${PLAYWRIGHT_WS_URL}" ]]; then
        echo "Installing Playwright browsers..."
        playwright install chromium
        playwright install-deps chromium
    fi

    python -c "import nltk; nltk.download('punkt_tab')"
fi

if [ -n "${WEBUI_SECRET_KEY_FILE}" ]; then
    KEY_FILE="${WEBUI_SECRET_KEY_FILE}"
else
    KEY_FILE=".webui_secret_key"
fi

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"
if test "$WEBUI_SECRET_KEY $WEBUI_JWT_SECRET_KEY" = " "; then
  echo "Loading WEBUI_SECRET_KEY from file, not provided as an environment variable."

  if ! [ -e "$KEY_FILE" ]; then
    echo "Generating WEBUI_SECRET_KEY"
    # Generate a random value to use as a WEBUI_SECRET_KEY in case the user didn't provide one.
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi

  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

if [[ "${USE_OLLAMA_DOCKER,,}" == "true" ]]; then
    echo "USE_OLLAMA is set to true, starting ollama serve."
    ollama serve &
fi

# Pré-télécharger Gemma 3 si Ollama est disponible (en arrière-plan pour ne pas bloquer le démarrage)
if [ -n "${OLLAMA_BASE_URL}" ]; then
    (
        OLLAMA_URL="${OLLAMA_BASE_URL}"
        # S'assurer que l'URL se termine par /api ou ajouter le port si nécessaire
        if [[ ! "$OLLAMA_URL" =~ :[0-9]+ ]]; then
            OLLAMA_URL="${OLLAMA_URL}:11434"
        fi
        if [[ "$OLLAMA_URL" =~ /api$ ]]; then
            OLLAMA_API_URL="${OLLAMA_URL}"
        else
            OLLAMA_API_URL="${OLLAMA_URL}/api"
        fi
        
        echo "Attente d'Ollama pour télécharger Gemma 3..."
        MAX_RETRIES=60
        RETRY_COUNT=0
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if curl -s -f "${OLLAMA_API_URL}/tags" > /dev/null 2>&1; then
                echo "Ollama est prêt, vérification de Gemma 3..."
                # Vérifier si gemma3 ou gemma2 est déjà installé
                MODELS_JSON=$(curl -s "${OLLAMA_API_URL}/tags" 2>/dev/null || echo "{}")
                MODELS=$(echo "$MODELS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' || echo "")
                
                if echo "$MODELS" | grep -qiE "gemma3|gemma2"; then
                    echo "Gemma est déjà installé: $(echo "$MODELS" | grep -iE "gemma3|gemma2" | head -1)"
                else
                    echo "Téléchargement de Gemma 3..."
                    curl -X POST "${OLLAMA_API_URL}/pull" \
                        -H "Content-Type: application/json" \
                        -d '{"name": "gemma3"}' 2>&1 | grep -v "^$" || {
                        echo "Tentative avec Gemma 2..."
                        curl -X POST "${OLLAMA_API_URL}/pull" \
                            -H "Content-Type: application/json" \
                            -d '{"name": "gemma2"}' 2>&1 | grep -v "^$" || echo "Impossible de télécharger Gemma automatiquement"
                    }
                fi
                break
            fi
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
                echo "Attente d'Ollama... ($RETRY_COUNT/$MAX_RETRIES)"
            fi
            sleep 2
        done
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "Avertissement: Ollama n'est pas disponible après $MAX_RETRIES tentatives. Les modèles devront être téléchargés manuellement."
        fi
    ) &
fi

if [[ "${USE_CUDA_DOCKER,,}" == "true" ]]; then
  echo "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# Check if SPACE_ID is set, if so, configure for space
if [ -n "$SPACE_ID" ]; then
  echo "Configuring for HuggingFace Space deployment"
  if [ -n "$ADMIN_USER_EMAIL" ] && [ -n "$ADMIN_USER_PASSWORD" ]; then
    echo "Admin user configured, creating"
    WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' &
    webui_pid=$!
    echo "Waiting for webui to start..."
    while ! curl -s "http://localhost:${PORT}/health" > /dev/null; do
      sleep 1
    done
    echo "Creating admin user..."
    curl \
      -X POST "http://localhost:${PORT}/api/v1/auths/signup" \
      -H "accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{ \"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\" }"
    echo "Shutting down webui..."
    kill $webui_pid
  fi

  export WEBUI_URL=${SPACE_HOST}
fi

PYTHON_CMD=$(command -v python3 || command -v python)
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

# If script is called with arguments, use them; otherwise use default workers
if [ "$#" -gt 0 ]; then
    ARGS=("$@")
else
    ARGS=(--workers "$UVICORN_WORKERS")
fi

# Run uvicorn
WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec "$PYTHON_CMD" -m uvicorn open_webui.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --forwarded-allow-ips '*' \
    "${ARGS[@]}"