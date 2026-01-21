# Script PowerShell pour réinitialiser la base de données

Write-Host "🗑️  Réinitialisation de la base de données..." -ForegroundColor Yellow

# Vérifier si Docker est utilisé
$dockerRunning = docker ps 2>$null | Select-String "open-webui"

if ($dockerRunning) {
    Write-Host "📦 Container Docker détecté" -ForegroundColor Cyan
    Write-Host "Arrêt des containers..."
    docker-compose down
    
    Write-Host "Suppression du volume de données..."
    $volume = docker volume ls -q | Select-String "open-webui"
    if ($volume) {
        docker volume rm $volume
        Write-Host "✅ Volume supprimé" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Volume non trouvé" -ForegroundColor Yellow
    }
    
    Write-Host "✅ Base de données réinitialisée" -ForegroundColor Green
    Write-Host "Pour redémarrer: docker-compose up" -ForegroundColor Cyan
} else {
    Write-Host "💻 Mode local détecté" -ForegroundColor Cyan
    
    $dbPath = "backend\data\webui.db"
    if (Test-Path $dbPath) {
        Write-Host "Suppression de $dbPath..."
        Remove-Item $dbPath -Force
        Write-Host "✅ Base de données supprimée" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Fichier $dbPath non trouvé" -ForegroundColor Yellow
    }
    
    $oldDbPath = "backend\data\ollama.db"
    if (Test-Path $oldDbPath) {
        Write-Host "Suppression de $oldDbPath (ancien format)..."
        Remove-Item $oldDbPath -Force
    }
}

Write-Host ""
Write-Host "✅ Réinitialisation terminée!" -ForegroundColor Green
Write-Host "La base de données sera recréée au prochain démarrage." -ForegroundColor Cyan
