# Configuration Twilio pour les appels téléphoniques

## Problème actuel

Le système actuel utilise OpenAI Realtime/Gemini Live pour la conversation vocale dans le navigateur, mais **ne passe pas réellement d'appels téléphoniques**. L'interface montre "Call in progress" mais l'appel n'est pas reçu sur le téléphone du client.

## Solution : Intégration Twilio

Pour que les appels soient réellement reçus sur les téléphones, vous devez configurer Twilio.

### 1. Installation

Installez la bibliothèque Twilio :
```bash
pip install twilio
```

### 2. Configuration Twilio

1. Créez un compte sur [Twilio](https://www.twilio.com/)
2. Obtenez votre **Account SID** et **Auth Token** depuis le dashboard Twilio
3. Achetez un numéro de téléphone Twilio

### 3. Configuration dans l'application

**Option 1 : Via l'interface admin (Recommandé)**

1. Connectez-vous en tant qu'administrateur
2. Allez dans **Settings** > **Connections**
3. Trouvez la section **Twilio**
4. Activez le switch **Enable Twilio**
5. Entrez vos identifiants :
   - **Account SID** : Votre Twilio Account SID
   - **Auth Token** : Votre Twilio Auth Token
   - **Phone Number** : Votre numéro Twilio (format E.164, ex: +1234567890)
6. Les modifications sont sauvegardées automatiquement

**Option 2 : Via les variables d'environnement**

Configurez les variables d'environnement suivantes :

```bash
ENABLE_TWILIO=True
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890  # Votre numéro Twilio (format E.164)
```

### 4. Configuration des webhooks

Pour que Twilio puisse communiquer avec votre serveur, vous devez :

1. Exposer votre serveur publiquement (utilisez ngrok pour le développement)
2. Configurer les webhooks Twilio pour pointer vers :
   - Voice URL: `https://votre-serveur.com/api/v1/orders/{order_id}/twilio-voice`
   - Status Callback: `https://votre-serveur.com/api/v1/orders/{order_id}/twilio-status`

### 5. Implémentation Media Streams

**✅ Implémenté** : L'intégration complète avec Media Streams est maintenant disponible !

Le système inclut :
- **Twilio Media Streams** : Reçoit l'audio en temps réel depuis l'appel téléphonique
- **Bridge audio** : Convertit l'audio entre Twilio (mu-law 8kHz) et les APIs IA (PCM16 16kHz/24kHz)
- **Connexion bidirectionnelle** : Audio du téléphone → IA → Réponse audio → Téléphone
- **Support multi-providers** : OpenAI Realtime et Gemini Live

### 6. Architecture

```
Téléphone Client
    ↓ (mu-law 8kHz)
Twilio Media Streams (WebSocket)
    ↓
Bridge Audio (conversion mu-law ↔ PCM16, resampling)
    ↓ (PCM16 16kHz/24kHz)
OpenAI Realtime / Gemini Live (WebSocket)
    ↓ (Réponse audio)
Bridge Audio (conversion + resampling)
    ↓ (mu-law 8kHz)
Twilio Media Streams
    ↓
Téléphone Client
```

### 7. Configuration requise

Pour que Media Streams fonctionne :

1. **Serveur accessible publiquement** : Twilio doit pouvoir se connecter à votre serveur
   - En développement : Utilisez ngrok ou un tunnel similaire
   - En production : Votre serveur doit avoir une URL publique HTTPS

2. **WebSocket support** : Votre serveur doit supporter les connexions WebSocket

3. **Dépendances** :
   ```bash
   pip install twilio websockets numpy
   ```

4. **Configuration des webhooks Twilio** :
   - Voice URL doit pointer vers : `https://votre-serveur.com/api/v1/orders/{order_id}/twilio-voice`
   - Media Streams sera automatiquement activé via le TwiML retourné

### 8. Test

Une fois configuré, testez en :
1. Configurant Twilio avec vos identifiants
2. S'assurant que votre serveur est accessible publiquement (ngrok en dev)
3. Initiant un appel depuis l'interface
4. Vérifiant que :
   - L'appel est reçu sur le téléphone du client ✅
   - L'IA répond en temps réel ✅
   - La conversation est fluide ✅

### 9. Fonctionnalités SMS

En plus des appels téléphoniques, Twilio peut également envoyer des SMS :

**Envoi de SMS :**
- Envoyez des SMS aux clients ou aux livreurs depuis l'interface de commande
- Messages personnalisables avec contexte de la commande
- Suivi du statut de livraison des SMS
- Support pour l'envoi en masse (plusieurs destinataires)

**Utilisation :**
1. Ouvrez une commande
2. Cliquez sur le bouton "SMS" à côté du bouton "Call"
3. Rédigez votre message (ou utilisez le message par défaut)
4. Envoyez le SMS

**Configuration :**
Les SMS utilisent la même configuration Twilio que les appels téléphoniques :
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

**Webhooks SMS :**
Les statuts de livraison des SMS sont automatiquement mis à jour via le webhook :
- `https://votre-serveur.com/api/v1/orders/{order_id}/twilio-sms-status`

### 10. Dépannage

**Problème** : L'appel est reçu mais pas de réponse de l'IA
- Vérifiez que les clés API OpenAI/Gemini sont configurées
- Vérifiez les logs pour les erreurs de connexion WebSocket
- Assurez-vous que le serveur est accessible publiquement

**Problème** : Audio déformé ou coupé
- Vérifiez la conversion audio (mu-law ↔ PCM16)
- Vérifiez le resampling (8kHz ↔ 16kHz/24kHz)
- Augmentez les buffers si nécessaire

**Problème** : Connexion WebSocket échoue
- Vérifiez que le serveur supporte WebSocket
- Vérifiez les certificats SSL en production
- Vérifiez les firewalls et règles de sécurité
