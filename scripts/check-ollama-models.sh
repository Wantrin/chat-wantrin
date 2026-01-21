#!/bin/bash
# Script de diagnostic pour vérifier la connexion Ollama et les modèles disponibles

OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"

echo "=== Diagnostic Ollama ==="
echo "URL Ollama: $OLLAMA_BASE_URL"

# Construire l'URL de l'API
if [[ "$OLLAMA_BASE_URL" =~ /api$ ]]; then
    OLLAMA_API_URL="$OLLAMA_BASE_URL"
else
    OLLAMA_API_URL="${OLLAMA_BASE_URL}/api"
fi

echo "URL API: $OLLAMA_API_URL"
echo ""

# Test de connexion
echo "1. Test de connexion à Ollama..."
if curl -s -f "${OLLAMA_API_URL}/tags" > /dev/null 2>&1; then
    echo "✓ Ollama est accessible"
else
    echo "✗ Ollama n'est pas accessible"
    echo "  Vérifiez que le conteneur Ollama est démarré: docker ps | grep ollama"
    exit 1
fi

# Liste des modèles
echo ""
echo "2. Modèles disponibles dans Ollama:"
MODELS_JSON=$(curl -s "${OLLAMA_API_URL}/tags" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$MODELS_JSON" ]; then
    echo "$MODELS_JSON" | python3 -m json.tool 2>/dev/null || echo "$MODELS_JSON"
    
    MODEL_COUNT=$(echo "$MODELS_JSON" | grep -o '"name"' | wc -l)
    echo ""
    echo "Nombre de modèles: $MODEL_COUNT"
    
    if [ "$MODEL_COUNT" -eq 0 ]; then
        echo ""
        echo "⚠ Aucun modèle trouvé dans Ollama"
        echo "Pour télécharger Gemma 3, exécutez:"
        echo "  docker exec ollama ollama pull gemma3"
        echo "Ou pour Gemma 2:"
        echo "  docker exec ollama ollama pull gemma2"
    else
        echo ""
        echo "Modèles trouvés:"
        echo "$MODELS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | while read model; do
            echo "  - $model"
        done
    fi
else
    echo "✗ Impossible de récupérer la liste des modèles"
    exit 1
fi

# Vérifier Gemma
echo ""
echo "3. Vérification de Gemma:"
if echo "$MODELS_JSON" | grep -qiE "gemma3|gemma2"; then
    GEMMA_MODEL=$(echo "$MODELS_JSON" | grep -o '"name":"[^"]*gemma[^"]*"' | sed 's/"name":"//g' | sed 's/"//g' | head -1)
    echo "✓ Gemma trouvé: $GEMMA_MODEL"
else
    echo "✗ Gemma n'est pas installé"
    echo ""
    echo "Pour télécharger Gemma 3:"
    echo "  docker exec ollama ollama pull gemma3"
    echo ""
    echo "Pour télécharger Gemma 2:"
    echo "  docker exec ollama ollama pull gemma2"
fi

echo ""
echo "=== Fin du diagnostic ==="
