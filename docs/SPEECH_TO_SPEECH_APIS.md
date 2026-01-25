# APIs Speech-to-Speech: OpenAI et Gemini

## Vue d'ensemble

Ce document décrit les APIs speech-to-speech natives d'OpenAI et Google Gemini, et comment les intégrer dans le système d'appels téléphoniques.

## OpenAI Realtime API

### Caractéristiques principales

- **Modèle**: `gpt-realtime`
- **Latence**: Très faible (streaming bidirectionnel)
- **Voix**: 6 voix prédéfinies (alloy, echo, fable, onyx, nova, shimmer)
- **Interruptions**: Gestion automatique
- **Connexions**: WebSocket, WebRTC, ou SIP
- **Disponibilité**: GA depuis août 2025

### Avantages

1. **Streaming natif**: Audio entrant et sortant en temps réel via une seule connexion
2. **Agents SDK**: SDK TypeScript dédié pour les voice agents
3. **WebRTC support**: Idéal pour les applications browser
4. **SIP support**: Parfait pour l'intégration téléphonique
5. **Multimodal**: Support audio, images, et texte

### Méthodes de connexion

#### 1. WebRTC (Recommandé pour browser)
```typescript
import { RealtimeAgent, RealtimeSession } from "@openai/agents/realtime";

const agent = new RealtimeAgent({
  name: "Assistant",
  instructions: "You are a helpful assistant.",
});

const session = new RealtimeSession(agent);
await session.connect({
  apiKey: "<client-api-key>",
});
```

#### 2. WebSocket (Pour serveur)
```typescript
const ws = new WebSocket("wss://api.openai.com/v1/realtime?model=gpt-realtime", {
  headers: {
    Authorization: "Bearer " + apiKey,
  },
});

ws.on("open", () => {
  ws.send(JSON.stringify({
    type: "session.update",
    session: {
      type: "realtime",
      instructions: "Be extra nice today!",
      audio: {
        output: {
          voice: "marin",
        },
      },
    },
  }));
});
```

#### 3. SIP (Pour téléphonie)
- Support pour connexions VoIP
- Idéal pour intégration avec systèmes téléphoniques existants

### Événements clés

- `response.output_text.delta`: Texte de réponse (streaming)
- `response.output_audio.delta`: Audio de réponse (streaming)
- `response.output_audio_transcript.delta`: Transcription audio
- `conversation.item.added`: Nouvel élément de conversation
- `conversation.item.done`: Élément terminé

## Google Gemini Live API

### Caractéristiques principales

- **Modèle**: `gemini-2.5-flash-native-audio-preview-12-2025`
- **Format audio**: PCM 16-bit, 16kHz input, 24kHz output
- **Latence**: Très faible (streaming continu)
- **Connexion**: WebSocket
- **Détection vocale**: Voice Activity Detection intégrée

### Avantages

1. **Streaming continu**: Audio entrant et sortant en continu
2. **Client-to-server**: Connexion directe depuis le browser
3. **Session management**: Gestion de conversations longues
4. **Ephemeral tokens**: Authentification sécurisée côté client
5. **Tool use**: Support des function calls en temps réel

### Format audio

- **Input**: PCM 16-bit, 16kHz, mono
- **Output**: PCM 16-bit, 24kHz, mono
- **Encodage**: Base64 pour transmission

### Exemple d'utilisation (JavaScript)

```javascript
import { GoogleGenAI, Modality } from '@google/genai';

const ai = new GoogleGenAI({});

const session = await ai.live.connect({
  model: 'gemini-2.5-flash-native-audio-preview-12-2025',
  config: {
    responseModalities: [Modality.AUDIO],
    systemInstruction: "You are a helpful assistant.",
  },
  callbacks: {
    onopen: () => console.log('Connected'),
    onmessage: (message) => {
      if (message.serverContent?.modelTurn?.parts) {
        for (const part of message.serverContent.modelTurn.parts) {
          if (part.inlineData?.data) {
            // Audio data en base64
            const audioData = Buffer.from(part.inlineData.data, 'base64');
            // Jouer l'audio
          }
        }
      }
    },
  },
});

// Envoyer audio du microphone
micStream.on('data', (data) => {
  session.sendRealtimeInput({
    audio: {
      data: data.toString('base64'),
      mimeType: "audio/pcm;rate=16000"
    }
  });
});
```

### Limitations

- **Sessions audio**: 15 minutes maximum (sans compression)
- **Sessions audio-vidéo**: 2 minutes maximum
- **Connexions**: ~10 minutes de limite

## Comparaison

| Caractéristique | OpenAI Realtime | Gemini Live |
|----------------|-----------------|-------------|
| Modèle | gpt-realtime | gemini-2.5-flash-native-audio |
| Connexions | WebSocket, WebRTC, SIP | WebSocket |
| Voix | 6 prédéfinies | Native audio |
| Latence | Très faible | Très faible |
| Interruptions | Automatique | Via VAD |
| Browser SDK | Oui (Agents SDK) | Oui |
| Téléphonie | Oui (SIP) | Via partenaires |
| Coût | Payant | Payant |

## Recommandations d'intégration

### Pour les appels téléphoniques

1. **OpenAI Realtime avec SIP**: Idéal pour intégration téléphonique directe
2. **Gemini Live avec WebSocket**: Bon pour appels via browser
3. **OpenAI Realtime avec WebRTC**: Alternative moderne pour browser

### Pour le composant PhoneCallOverlay actuel

Le composant actuel utilise:
- STT (transcription) → LLM (génération) → TTS (synthèse)

Avec les APIs natives, on peut:
- **Streaming direct**: Audio → API → Audio (sans étapes intermédiaires)
- **Latence réduite**: Pas de délai entre transcription et synthèse
- **Meilleure qualité**: Préservation de l'émotion et de l'intonation

## Prochaines étapes

1. Créer un wrapper pour OpenAI Realtime API
2. Créer un wrapper pour Gemini Live API
3. Modifier PhoneCallOverlay pour utiliser ces APIs
4. Ajouter support SIP pour appels téléphoniques réels
5. Implémenter fallback vers méthode actuelle si APIs non disponibles
