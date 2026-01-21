# Dépannage : Aucun modèle trouvé (No models found)

## Problème
L'application affiche "no models found" ou "no result found" même après avoir configuré Gemma 3.

## Solutions

### 1. Vérifier que Ollama est démarré

```bash
docker ps | grep ollama
```

Si le conteneur n'est pas en cours d'exécution :
```bash
docker-compose up -d ollama
```

### 2. Vérifier la connexion à Ollama

Testez depuis le conteneur open-webui :
```bash
docker exec open-webui curl -s http://ollama:11434/api/tags
```

Vous devriez voir une réponse JSON avec la liste des modèles (même si elle est vide).

### 3. Vérifier les modèles installés dans Ollama

```bash
docker exec ollama ollama list
```

Si aucun modèle n'est listé, vous devez les télécharger manuellement.

### 4. Télécharger Gemma 3 manuellement

```bash
# Télécharger Gemma 3
docker exec ollama ollama pull gemma3

# Ou si gemma3 n'est pas disponible, essayer gemma2
docker exec ollama ollama pull gemma2

# Vérifier après téléchargement
docker exec ollama ollama list
```

### 5. Vérifier la configuration de l'URL Ollama

Dans `docker-compose.yaml`, assurez-vous que :
```yaml
environment:
  - 'OLLAMA_BASE_URL=http://ollama:11434'
```

### 6. Utiliser le script de diagnostic

Un script de diagnostic est disponible :
```bash
docker exec open-webui bash /app/scripts/check-ollama-models.sh
```

Ou depuis l'hôte (si le script est monté) :
```bash
docker exec -e OLLAMA_BASE_URL=http://ollama:11434 open-webui bash scripts/check-ollama-models.sh
```

### 7. Vérifier les logs

```bash
# Logs Ollama
docker logs ollama

# Logs Open WebUI
docker logs open-webui | grep -i ollama
docker logs open-webui | grep -i gemma
```

### 8. Redémarrer les services

```bash
docker-compose down
docker-compose up -d
```

Attendez quelques secondes puis vérifiez :
```bash
docker exec ollama ollama list
```

### 9. Vérifier dans l'interface Open WebUI

1. Connectez-vous à l'interface Open WebUI
2. Allez dans **Settings** → **Models**
3. Cliquez sur **Refresh** pour forcer le rafraîchissement de la liste des modèles

### 10. Vérifier la configuration par défaut

Dans `backend/open_webui/config.py`, la ligne suivante doit être présente :
```python
DEFAULT_MODELS = PersistentConfig(
    "DEFAULT_MODELS", "ui.default_models", os.environ.get("DEFAULT_MODELS", "gemma3")
)
```

## Modèles Ollama disponibles

Pour voir tous les modèles disponibles dans Ollama :
```bash
docker exec ollama ollama list
```

Pour télécharger d'autres modèles populaires :
```bash
# Llama 3
docker exec ollama ollama pull llama3

# Mistral
docker exec ollama ollama pull mistral

# CodeLlama
docker exec ollama ollama pull codellama
```

## Problèmes courants

### Ollama redémarre en boucle

Si Ollama redémarre constamment, vérifiez les logs :
```bash
docker logs ollama
```

Causes possibles :
- Problème de permissions sur le volume
- Espace disque insuffisant
- Problème de mémoire

### Timeout lors du téléchargement

Si le téléchargement de Gemma 3 prend trop de temps ou échoue :
1. Vérifiez votre connexion internet
2. Vérifiez l'espace disque disponible
3. Téléchargez une version plus petite :
   ```bash
   docker exec ollama ollama pull gemma2:2b  # Version 2B (plus petite)
   ```

### Modèles non visibles dans l'interface

Si les modèles sont installés dans Ollama mais n'apparaissent pas dans Open WebUI :
1. Rafraîchissez la page
2. Allez dans Settings → Models et cliquez sur Refresh
3. Vérifiez les logs d'Open WebUI pour des erreurs de connexion

## Support

Si le problème persiste :
1. Collectez les logs : `docker logs ollama > ollama.log` et `docker logs open-webui > webui.log`
2. Vérifiez la configuration : `docker-compose config`
3. Vérifiez les ressources système : `docker stats`
