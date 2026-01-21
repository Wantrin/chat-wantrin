# Commandes PowerShell pour Docker et Ollama

## Commandes de base

### Vérifier les conteneurs
```powershell
docker ps
```

### Vérifier les modèles Ollama
```powershell
docker exec ollama ollama list
```

### Télécharger un modèle
```powershell
docker exec ollama ollama pull gemma3
```

### Voir les logs (équivalent de grep)
```powershell
# Logs Open WebUI avec recherche
docker logs open-webui 2>&1 | Select-String -Pattern "gemma" -CaseSensitive:$false

# Logs Ollama avec recherche
docker logs ollama 2>&1 | Select-String -Pattern "model|pull" -CaseSensitive:$false

# Dernières lignes des logs
docker logs open-webui --tail 50
docker logs ollama --tail 50
```

### Redémarrer les services
```powershell
docker-compose restart open-webui
docker-compose restart ollama
```

### Arrêter et redémarrer
```powershell
docker-compose down
docker-compose up -d
```

## Commandes de diagnostic

### Vérifier la connexion à Ollama
```powershell
docker exec open-webui curl -s http://ollama:11434/api/tags
```

### Vérifier les modèles disponibles via API
```powershell
docker exec open-webui curl -s http://ollama:11434/api/tags | ConvertFrom-Json | Select-Object -ExpandProperty models
```

### Tester Ollama depuis le conteneur
```powershell
docker exec ollama ollama run gemma3 "Bonjour, comment ça va?"
```

## Commandes utiles

### Suivre les logs en temps réel
```powershell
docker logs -f open-webui
docker logs -f ollama
```

### Voir l'utilisation des ressources
```powershell
docker stats
```

### Nettoyer les conteneurs arrêtés
```powershell
docker container prune
```

### Nettoyer les images non utilisées
```powershell
docker image prune
```

## Exemples de recherche dans les logs

```powershell
# Rechercher "gemma" dans les logs
docker logs open-webui 2>&1 | Select-String "gemma"

# Rechercher les erreurs
docker logs open-webui 2>&1 | Select-String -Pattern "error|Error|ERROR" -CaseSensitive:$false

# Rechercher les warnings
docker logs open-webui 2>&1 | Select-String -Pattern "warn|Warn|WARNING" -CaseSensitive:$false

# Rechercher plusieurs termes
docker logs open-webui 2>&1 | Select-String -Pattern "gemma|ollama|model" -CaseSensitive:$false
```
