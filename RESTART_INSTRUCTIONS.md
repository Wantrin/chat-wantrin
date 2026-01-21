# Instructions pour redémarrer l'application

## 🐳 Avec Docker Compose (Recommandé)

### 1. Arrêter les conteneurs actuels

```powershell
docker-compose down
```

### 2. Reconstruire l'image avec les nouveaux changements

```powershell
docker-compose build --no-cache
```

Le flag `--no-cache` garantit que tous les changements sont inclus (peut prendre plus de temps).

### 3. Redémarrer les conteneurs

```powershell
docker-compose up -d
```

Ou pour voir les logs en temps réel :

```powershell
docker-compose up
```

### ⚡ Commande combinée (recommandée)

Pour tout faire en une seule commande :

```powershell
docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

### Alternative : Rebuild rapide (si vous avez fait peu de changements)

Si vous voulez juste redémarrer sans reconstruire complètement :

```powershell
docker-compose restart
```

**⚠️ Note** : Cette commande ne reconstruira PAS l'image, donc les nouveaux fichiers ne seront pas inclus. Utilisez-la seulement si vous avez juste modifié des fichiers déjà dans l'image.

---

## 💻 Mode développement (sans Docker)

### 1. Redémarrer le Backend

Ouvrez un terminal PowerShell et exécutez :

```powershell
cd backend
.\start_windows.bat
```

Ou si vous utilisez Python directement :

```powershell
cd backend
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload
```

Le flag `--reload` permet le rechargement automatique lors des modifications de code.

### 2. Redémarrer le Frontend (dans un autre terminal)

Ouvrez un **nouveau terminal PowerShell** et exécutez :

```powershell
npm run dev
```

Cela démarrera le serveur de développement Vite qui rechargera automatiquement les changements frontend.

---

## ✅ Vérification

### Avec Docker Compose

1. **Application complète** : `http://localhost:3000` (ou le port défini dans `OPEN_WEBUI_PORT`)
2. **Accéder à la boutique** : `http://localhost:3000/shop`
3. **API Backend** : `http://localhost:3000/api/v1/products/`

### Mode développement (sans Docker)

1. **Backend** : Le serveur devrait démarrer sur `http://localhost:8080`
2. **Frontend** : Le serveur devrait démarrer sur `http://localhost:5173` (ou un autre port si 5173 est occupé)
3. **Accéder à la boutique** : `http://localhost:5173/shop`
4. **API Backend** : `http://localhost:8080/api/v1/products/`

---

## 📝 Notes importantes

### Avec Docker Compose

- ⚠️ **IMPORTANT** : Vous devez **reconstruire l'image** (`docker-compose build`) pour que les nouveaux fichiers soient inclus dans le conteneur
- Les migrations Alembic s'exécutent **automatiquement** au démarrage du conteneur si `ENABLE_DB_MIGRATIONS` est activé
- Le volume `open-webui:/app/backend/data` persiste les données de la base de données
- Pour voir les logs en temps réel : `docker-compose logs -f open-webui`
- Pour voir les logs d'un conteneur spécifique : `docker-compose logs -f open-webui`

### Mode développement

- Les migrations Alembic s'exécutent **automatiquement** au démarrage du backend si `ENABLE_DB_MIGRATIONS` est activé
- Si vous voyez des erreurs de migration, vérifiez que la variable d'environnement `ENABLE_DB_MIGRATIONS=true` est définie
- Le frontend en mode développement (`npm run dev`) rechargera automatiquement les changements
- Le backend avec `--reload` rechargera automatiquement les changements Python

---

## 🔧 Si les changements n'apparaissent toujours pas

1. **Vider le cache du navigateur** : `Ctrl + Shift + R` (ou `Cmd + Shift + R` sur Mac)
2. **Vérifier la console du navigateur** (F12) pour les erreurs
3. **Vérifier les logs du backend** :
   - Docker : `docker-compose logs -f open-webui`
   - Mode dev : Vérifier le terminal où le backend tourne
4. **S'assurer que les conteneurs/serveurs sont bien démarrés**
5. **Vérifier que la migration a bien été exécutée** : Les logs devraient montrer "Running migrations"

---

## 🚀 Commandes utiles Docker Compose

```powershell
# Voir les logs en temps réel
docker-compose logs -f open-webui

# Arrêter les conteneurs
docker-compose down

# Redémarrer un conteneur spécifique
docker-compose restart open-webui

# Reconstruire seulement le service open-webui
docker-compose build open-webui

# Voir l'état des conteneurs
docker-compose ps
```
