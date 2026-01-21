# Configuration Docker pour Gemma 3

## Vue d'ensemble

Cette configuration permet de pré-télécharger automatiquement le modèle Gemma 3 lors du démarrage du conteneur Ollama dans Docker.

## Configuration

### docker-compose.yaml

Le service `ollama` a été configuré pour :
1. Démarrer le serveur Ollama en arrière-plan
2. Attendre 5 secondes que le serveur soit prêt
3. Télécharger automatiquement Gemma 3 (ou Gemma 2 en fallback)
4. Maintenir le processus en cours d'exécution

```yaml
ollama:
  entrypoint: ["/bin/sh", "-c"]
  command: "ollama serve & sleep 5 && (ollama pull gemma3 || ollama pull gemma2 || echo 'Modèle Gemma non disponible') && wait"
```

### Configuration par défaut

Le modèle Gemma 3 est également configuré comme modèle par défaut dans `backend/open_webui/config.py` :

```python
DEFAULT_MODELS = PersistentConfig(
    "DEFAULT_MODELS", "ui.default_models", os.environ.get("DEFAULT_MODELS", "gemma3")
)
```

## Utilisation

### Démarrage avec Docker Compose

```bash
docker-compose up -d
```

Le modèle Gemma 3 sera automatiquement téléchargé lors du premier démarrage du conteneur Ollama.

### Vérification

Pour vérifier que Gemma 3 est bien installé :

```bash
docker exec ollama ollama list
```

Vous devriez voir `gemma3` (ou `gemma2`) dans la liste.

### Téléchargement manuel

Si le téléchargement automatique échoue, vous pouvez télécharger manuellement :

```bash
docker exec ollama ollama pull gemma3
```

Ou pour Gemma 2 :

```bash
docker exec ollama ollama pull gemma2
```

## Notes importantes

1. **Nom du modèle** : Le nom exact peut varier selon la version d'Ollama. Si `gemma3` n'est pas disponible, le système essaiera `gemma2`.

2. **Taille du modèle** : Gemma 3 est disponible en plusieurs tailles (1B, 4B, 12B, 27B). Par défaut, Ollama télécharge la version recommandée. Pour spécifier une taille :

   ```bash
   docker exec ollama ollama pull gemma3:2b  # Version 2B
   docker exec ollama ollama pull gemma3:4b  # Version 4B
   ```

3. **Espace disque** : Assurez-vous d'avoir suffisamment d'espace disque. Les modèles peuvent être volumineux (plusieurs GB).

4. **Premier démarrage** : Le premier démarrage peut prendre du temps car le modèle doit être téléchargé.

## Personnalisation

### Variable d'environnement

Vous pouvez modifier le modèle par défaut via la variable d'environnement :

```yaml
environment:
  - 'DEFAULT_MODELS=gemma3:4b'
```

### Script d'initialisation alternatif

Un script d'initialisation est disponible dans `scripts/docker-init-ollama.sh` pour une configuration plus avancée.

## Dépannage

### Le modèle ne se télécharge pas

1. Vérifiez les logs du conteneur Ollama :
   ```bash
   docker logs ollama
   ```

2. Vérifiez la connectivité réseau :
   ```bash
   docker exec ollama curl -s http://localhost:11434/api/tags
   ```

3. Téléchargez manuellement le modèle (voir section "Téléchargement manuel")

### Le modèle n'apparaît pas dans Open WebUI

1. Vérifiez que le modèle est bien installé dans Ollama
2. Redémarrez Open WebUI pour rafraîchir la liste des modèles
3. Vérifiez la configuration `DEFAULT_MODELS` dans l'interface admin
