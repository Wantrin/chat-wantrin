#!/bin/bash
# Script pour réinitialiser la base de données

echo "🗑️  Réinitialisation de la base de données..."

# Vérifier si Docker est utilisé
if docker ps | grep -q open-webui; then
    echo "📦 Container Docker détecté"
    echo "Arrêt des containers..."
    docker-compose down
    
    echo "Suppression du volume de données..."
    docker volume rm chat-wantrin_open-webui 2>/dev/null || \
    docker volume rm $(docker volume ls -q | grep open-webui) 2>/dev/null || \
    echo "Volume non trouvé ou déjà supprimé"
    
    echo "✅ Base de données réinitialisée"
    echo "Pour redémarrer: docker-compose up"
else
    echo "💻 Mode local détecté"
    
    if [ -f "backend/data/webui.db" ]; then
        echo "Suppression de backend/data/webui.db..."
        rm backend/data/webui.db
        echo "✅ Base de données supprimée"
    else
        echo "⚠️  Fichier backend/data/webui.db non trouvé"
    fi
    
    if [ -f "backend/data/ollama.db" ]; then
        echo "Suppression de backend/data/ollama.db (ancien format)..."
        rm backend/data/ollama.db
    fi
fi

echo ""
echo "✅ Réinitialisation terminée!"
echo "La base de données sera recréée au prochain démarrage."
