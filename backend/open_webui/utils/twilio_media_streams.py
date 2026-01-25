"""
Twilio Media Streams bridge for connecting phone calls to AI services.
"""
import asyncio
import json
import logging
import base64
import struct
from typing import Optional, Dict, Callable
from fastapi import WebSocket

log = logging.getLogger(__name__)


class TwilioMediaStreamBridge:
    """
    Bridge between Twilio Media Streams and AI Realtime APIs.
    Handles audio conversion and bidirectional streaming.
    """
    
    def __init__(
        self,
        call_sid: str,
        ai_provider: str,  # 'openai' or 'gemini'
        ai_config: dict,
        on_audio_output: Optional[Callable[[bytes], None]] = None
    ):
        """
        Initialize the bridge.
        
        Args:
            call_sid: Twilio Call SID
            ai_provider: AI provider ('openai' or 'gemini')
            ai_config: Configuration for AI service
            on_audio_output: Callback for audio output to send to Twilio
        """
        self.call_sid = call_sid
        self.ai_provider = ai_provider
        self.ai_config = ai_config
        self.on_audio_output = on_audio_output
        
        self.twilio_ws: Optional[WebSocketServerProtocol] = None
        self.ai_ws = None
        self.is_connected = False
        self.audio_buffer = bytearray()
        
    async def connect_twilio(self, ws: WebSocket):
        """Connect to Twilio Media Stream."""
        self.twilio_ws = ws
        self.is_connected = True
        log.info(f"Twilio Media Stream connected for call {self.call_sid}")
        
        # Connect to AI service
        await self._connect_ai()
        
        # Start processing messages
        try:
            while True:
                message = await ws.receive_text()
                await self._handle_twilio_message(message)
        except Exception as e:
            log.info(f"Twilio Media Stream disconnected for call {self.call_sid}: {e}")
        finally:
            await self._cleanup()
    
    async def _connect_ai(self):
        """Connect to AI Realtime API."""
        try:
            if self.ai_provider == 'openai':
                await self._connect_openai()
            elif self.ai_provider == 'gemini':
                await self._connect_gemini()
            else:
                raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
        except Exception as e:
            log.exception(f"Failed to connect to AI: {e}")
            raise
    
    async def _connect_openai(self):
        """Connect to OpenAI Realtime API."""
        try:
            import websockets
            
            api_key = self.ai_config.get('api_key')
            model = self.ai_config.get('model', 'gpt-realtime')
            instructions = self.ai_config.get('instructions', 'You are a helpful assistant.')
            voice = self.ai_config.get('voice', 'alloy')
            
            # OpenAI Realtime uses WebSocket
            ws_url = f"wss://api.openai.com/v1/realtime?model={model}"
            
            # For server-side, we need to use the API key directly
            # Note: This is a simplified version - in production, use proper authentication
            headers = {
                "Authorization": f"Bearer {api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
            
            self.ai_ws = await websockets.connect(ws_url, extra_headers=headers)
            
            # Initialize session
            await self.ai_ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "type": "realtime",
                    "model": model,
                    "instructions": instructions,
                    "audio": {
                        "output": {
                            "voice": voice
                        }
                    },
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500
                    }
                }
            }))
            
            # Start receiving messages in background
            asyncio.ensure_future(self._handle_ai_messages())
            
            log.info(f"Connected to OpenAI Realtime for call {self.call_sid}")
            
        except Exception as e:
            log.exception(f"Failed to connect to OpenAI: {e}")
            raise
    
    async def _connect_gemini(self):
        """Connect to Gemini Live API."""
        try:
            import websockets
            
            api_key = self.ai_config.get('api_key')
            model = self.ai_config.get('model', 'gemini-2.5-flash-native-audio-preview-12-2025')
            system_instruction = self.ai_config.get('system_instruction', 'You are a helpful assistant.')
            
            ws_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"
            
            self.ai_ws = await websockets.connect(ws_url)
            
            # Initialize session
            await self.ai_ws.send(json.dumps({
                "setup": {
                    "model": f"models/{model}",
                    "generation_config": {
                        "response_modalities": ["AUDIO"],
                        "speech_config": {
                            "voice_config": {
                                "prebuilt_voice_config": {
                                    "voice_name": "Aoede"
                                }
                            }
                        }
                    },
                    "system_instruction": {
                        "parts": [
                            {
                                "text": system_instruction
                            }
                        ]
                    }
                }
            }))
            
            # Start receiving messages in background
            asyncio.ensure_future(self._handle_ai_messages())
            
            log.info(f"Connected to Gemini Live for call {self.call_sid}")
            
        except Exception as e:
            log.exception(f"Failed to connect to Gemini: {e}")
            raise
    
    async def _handle_twilio_message(self, message: str):
        """Handle incoming message from Twilio Media Stream."""
        try:
            data = json.loads(message)
            event_type = data.get('event')
            
            if event_type == 'media':
                # Audio data from phone call
                payload = data.get('media', {}).get('payload')
                if payload:
                    # Decode base64 mu-law audio
                    audio_bytes = base64.b64decode(payload)
                    # Convert mu-law to PCM16
                    pcm_audio = self._mulaw_to_pcm16(audio_bytes)
                    # Resample from 8kHz to 16kHz (OpenAI) or 24kHz (Gemini)
                    target_rate = 16000 if self.ai_provider == 'openai' else 24000
                    resampled = self._resample_audio(pcm_audio, 8000, target_rate)
                    # Send to AI
                    await self._send_audio_to_ai(resampled)
            
            elif event_type == 'start':
                log.info(f"Media stream started for call {self.call_sid}")
            elif event_type == 'stop':
                log.info(f"Media stream stopped for call {self.call_sid}")
                
        except Exception as e:
            log.exception(f"Error handling Twilio message: {e}")
    
    async def _handle_ai_messages(self):
        """Handle incoming messages from AI service."""
        try:
            while True:
                message = await self.ai_ws.recv()
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    # Binary message - handle if needed
                    continue
                await self._process_ai_message(data)
        except Exception as e:
            log.info(f"AI WebSocket closed for call {self.call_sid}: {e}")
        except Exception as e:
            log.exception(f"Error handling AI messages: {e}")
    
    async def _process_ai_message(self, data: dict):
        """Process message from AI service."""
        try:
            if self.ai_provider == 'openai':
                await self._process_openai_message(data)
            elif self.ai_provider == 'gemini':
                await self._process_gemini_message(data)
        except Exception as e:
            log.exception(f"Error processing AI message: {e}")
    
    async def _process_openai_message(self, data: dict):
        """Process OpenAI Realtime message."""
        event_type = data.get('type')
        
        if event_type == 'response.audio.delta':
            # Audio output from AI
            audio_base64 = data.get('delta', '')
            if audio_base64:
                audio_bytes = base64.b64decode(audio_base64)
                # Convert PCM16 to mu-law and resample to 8kHz
                resampled = self._resample_audio(audio_bytes, 24000, 8000)
                mulaw_audio = self._pcm16_to_mulaw(resampled)
                # Send to Twilio
                await self._send_audio_to_twilio(mulaw_audio)
        
        elif event_type == 'response.text.delta':
            # Text output (for logging)
            text = data.get('delta', '')
            if text:
                log.debug(f"AI text: {text}")
    
    async def _process_gemini_message(self, data: dict):
        """Process Gemini Live message."""
        if 'serverContent' in data:
            server_content = data['serverContent']
            if 'modelTurn' in server_content:
                model_turn = server_content['modelTurn']
                if 'parts' in model_turn:
                    for part in model_turn['parts']:
                        if 'inlineData' in part and part['inlineData']['mimeType'] == 'audio/pcm':
                            # Audio output from AI
                            audio_base64 = part['inlineData']['data']
                            audio_bytes = base64.b64decode(audio_base64)
                            # Convert PCM16 to mu-law and resample to 8kHz
                            resampled = self._resample_audio(audio_bytes, 24000, 8000)
                            mulaw_audio = self._pcm16_to_mulaw(resampled)
                            # Send to Twilio
                            await self._send_audio_to_twilio(mulaw_audio)
    
    async def _send_audio_to_ai(self, audio_bytes: bytes):
        """Send audio to AI service."""
        try:
            if self.ai_provider == 'openai':
                # Encode as base64
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                await self.ai_ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": audio_base64
                }))
            elif self.ai_provider == 'gemini':
                # Encode as base64
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                await self.ai_ws.send(json.dumps({
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": "audio/pcm",
                                "data": audio_base64
                            }
                        ]
                    }
                }))
        except Exception as e:
            log.exception(f"Error sending audio to AI: {e}")
    
    async def _send_audio_to_twilio(self, mulaw_audio: bytes):
        """Send audio to Twilio Media Stream."""
        try:
            if self.twilio_ws and self.is_connected:
                # Encode as base64
                audio_base64 = base64.b64encode(mulaw_audio).decode('utf-8')
                message = {
                    "event": "media",
                    "streamSid": self.call_sid,
                    "media": {
                        "payload": audio_base64
                    }
                }
                await self.twilio_ws.send_text(json.dumps(message))
        except Exception as e:
            log.exception(f"Error sending audio to Twilio: {e}")
    
    def _mulaw_to_pcm16(self, mulaw_bytes: bytes) -> bytes:
        """Convert mu-law audio to PCM16."""
        # Mu-law to linear conversion
        pcm_samples = []
        for byte in mulaw_bytes:
            # Mu-law decoding
            byte = ~byte
            sign = byte & 0x80
            exponent = (byte >> 4) & 0x07
            mantissa = byte & 0x0F
            sample = mantissa << (exponent + 3)
            if sign:
                sample = -sample
            # Scale to 16-bit
            sample = int(sample * 256)
            pcm_samples.append(sample & 0xFF)
            pcm_samples.append((sample >> 8) & 0xFF)
        return bytes(pcm_samples)
    
    def _pcm16_to_mulaw(self, pcm_bytes: bytes) -> bytes:
        """Convert PCM16 audio to mu-law."""
        # Simple linear to mu-law conversion
        mulaw_samples = []
        for i in range(0, len(pcm_bytes), 2):
            if i + 1 < len(pcm_bytes):
                sample = struct.unpack('<h', pcm_bytes[i:i+2])[0]
                # Mu-law encoding
                sign = 0x80 if sample < 0 else 0x00
                sample = abs(sample)
                if sample > 32635:
                    sample = 32635
                sample += 0x84
                exponent = 7
                exp_mask = 0x4000
                while exponent > 0 and (sample & exp_mask) == 0:
                    exponent -= 1
                    exp_mask >>= 1
                mantissa = (sample >> (exponent + 3)) & 0x0F
                mulaw_byte = ~(sign | (exponent << 4) | mantissa)
                mulaw_samples.append(mulaw_byte & 0xFF)
        return bytes(mulaw_samples)
    
    def _resample_audio(self, audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
        """
        Simple audio resampling.
        Note: This is a basic implementation. For production, use a proper resampling library like scipy or librosa.
        """
        if from_rate == to_rate:
            return audio_bytes
        
        # Simple linear interpolation resampling
        # For production, use scipy.signal.resample or librosa.resample
        try:
            import numpy as np
            # Convert bytes to numpy array
            samples = np.frombuffer(audio_bytes, dtype=np.int16)
            # Resample
            num_samples = int(len(samples) * to_rate / from_rate)
            resampled = np.interp(
                np.linspace(0, len(samples), num_samples),
                np.arange(len(samples)),
                samples
            ).astype(np.int16)
            return resampled.tobytes()
        except ImportError:
            # Fallback: simple decimation/interpolation
            ratio = to_rate / from_rate
            if ratio > 1:
                # Upsample: repeat samples
                result = bytearray()
                for i in range(0, len(audio_bytes), 2):
                    if i + 1 < len(audio_bytes):
                        sample = audio_bytes[i:i+2]
                        for _ in range(int(ratio)):
                            result.extend(sample)
                return bytes(result)
            else:
                # Downsample: skip samples
                step = int(1 / ratio)
                return audio_bytes[::step*2][:len(audio_bytes)//step*2]
    
    async def _cleanup(self):
        """Clean up connections."""
        self.is_connected = False
        if self.ai_ws:
            try:
                await self.ai_ws.close()
            except:
                pass
        log.info(f"Bridge cleaned up for call {self.call_sid}")


# Global registry for active bridges
_active_bridges: Dict[str, TwilioMediaStreamBridge] = {}


def get_bridge(call_sid: str) -> Optional[TwilioMediaStreamBridge]:
    """Get active bridge for a call."""
    return _active_bridges.get(call_sid)


def register_bridge(call_sid: str, bridge: TwilioMediaStreamBridge):
    """Register a bridge."""
    _active_bridges[call_sid] = bridge


def unregister_bridge(call_sid: str):
    """Unregister a bridge."""
    if call_sid in _active_bridges:
        del _active_bridges[call_sid]
