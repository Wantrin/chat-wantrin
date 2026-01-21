#!/bin/bash
# Script d'initialisation pour télécharger les modèles Ollama au démarrage

set -e

OLLAMA_HOST="${OLLAMA_BASE_URL:-http://ollama:11434}"
MAX_RETRIES=30
RETRY_DELAY=2

echo "En attente du service Ollama..."

# Attendre que Ollama soit prêt
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
        echo "Ollama est prêt!"
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "Erreur: Ollama n'est pas disponible après ${MAX_RETRIES} tentatives"
        exit 1
    fi
    echo "Tentative $i/$MAX_RETRIES: En attente d'Ollama..."
    sleep $RETRY_DELAY
done

# Télécharger Gemma 3 si pas déjà présent
echo "Vérification de la présence de Gemma 3..."
MODELS=$(curl -s "${OLLAMA_HOST}/api/tags" | jq -r '.models[].name' 2>/dev/null || echo "")

if echo "$MODELS" | grep -q "gemma3"; then
    echo "Gemma 3 est déjà installé"
else
    echo "Téléchargement de Gemma 3..."
    curl -X POST "${OLLAMA_HOST}/api/pull" \
        -H "Content-Type: application/json" \
        -d '{"name": "gemma3"}' || {
        echo "Avertissement: Impossible de télécharger gemma3, essayons gemma2..."
        curl -X POST "${OLLAMA_HOST}/api/pull" \
            -H "Content-Type: application/json" \
            -d '{"name": "gemma2"}' || echo "Avertissement: Impossible de télécharger gemma2"
    }
fi

echo "Initialisation terminée!"
