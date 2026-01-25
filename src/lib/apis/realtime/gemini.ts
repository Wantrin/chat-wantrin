/**
 * Google Gemini Live API Wrapper
 * Documentation: https://ai.google.dev/gemini-api/docs/live
 */

export interface GeminiLiveConfig {
	apiKey: string;
	model?: string;
	systemInstruction?: string;
	baseUrl?: string;
}

export interface GeminiLiveCallbacks {
	onAudioOutput?: (audioData: ArrayBuffer) => void;
	onTextOutput?: (text: string) => void;
	onError?: (error: Error) => void;
	onClose?: () => void;
	onOpen?: () => void;
	onInterrupted?: () => void;
}

export class GeminiLiveClient {
	private ws: WebSocket | null = null;
	private config: GeminiLiveConfig;
	private callbacks: GeminiLiveCallbacks;
	private audioContext: AudioContext | null = null;
	private mediaStream: MediaStream | null = null;
	private audioWorkletNode: AudioWorkletNode | null = null;
	private scriptProcessor: ScriptProcessorNode | null = null;
	private isConnected = false;
	private messageQueue: any[] = [];

	constructor(config: GeminiLiveConfig, callbacks: GeminiLiveCallbacks) {
		this.config = {
			model: 'gemini-2.5-flash-native-audio-preview-12-2025',
			baseUrl: 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent',
			...config
		};
		this.callbacks = callbacks;
	}

	async connect(): Promise<void> {
		return new Promise((resolve, reject) => {
			try {
				// Validate API key
				if (!this.config.apiKey || !this.config.apiKey.trim()) {
					reject(new Error('Gemini API key is required'));
					return;
				}
				
				// Gemini Live API WebSocket endpoint
				// Format: wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=API_KEY
				const wsUrl = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=${encodeURIComponent(this.config.apiKey.trim())}`;
				
				this.ws = new WebSocket(wsUrl);
				
				// Configure WebSocket to handle text messages (JSON) by default
				// Gemini Live sends JSON text messages, not binary
				this.ws.binaryType = 'arraybuffer';

				this.ws.onopen = () => {
					this.isConnected = true;
					
					// Send initial setup message
					this.ws?.send(JSON.stringify({
						setup: {
							model: `models/${this.config.model}`,
							generation_config: {
								response_modalities: ['AUDIO'],
								speech_config: {
									voice_config: {
										prebuilt_voice_config: {
											voice_name: 'Aoede' // Default voice
										}
									}
								}
							},
							system_instruction: {
								parts: [
									{
										text: this.config.systemInstruction || 'You are a helpful assistant.'
									}
								]
							}
						}
					}));

					// Process queued messages
					while (this.messageQueue.length > 0) {
						const message = this.messageQueue.shift();
						this.ws?.send(JSON.stringify(message));
					}

					this.callbacks.onOpen?.();
					resolve();
				};

				this.ws.onmessage = async (event) => {
					try {
						let messageData: any;
						
						// Handle Blob messages (binary audio data)
						if (event.data instanceof Blob) {
							const arrayBuffer = await event.data.arrayBuffer();
							// Gemini Live may send audio as binary in some cases
							// Try to convert to text first, if that fails, treat as binary audio
							try {
								const text = await event.data.text();
								messageData = JSON.parse(text);
							} catch {
								// If text conversion fails, treat as binary audio
								this.callbacks.onAudioOutput?.(arrayBuffer);
								return;
							}
						} else if (event.data instanceof ArrayBuffer) {
							// Handle ArrayBuffer directly
							const textDecoder = new TextDecoder();
							const text = textDecoder.decode(event.data);
							messageData = JSON.parse(text);
						} else if (typeof event.data === 'string') {
							// Handle text messages (JSON)
							messageData = JSON.parse(event.data);
						} else {
							console.warn('Unexpected message type:', typeof event.data, event.data);
							return;
						}
						
						// Process the parsed message
						if (messageData) {
							this.handleMessage(messageData);
						}
					} catch (error) {
						console.error('Error parsing WebSocket message:', error, event.data);
					}
				};

				this.ws.onerror = (error) => {
					this.callbacks.onError?.(new Error('WebSocket error'));
					reject(error);
				};

				this.ws.onclose = () => {
					this.isConnected = false;
					this.callbacks.onClose?.();
				};
			} catch (error) {
				reject(error);
			}
		});
	}

	private handleMessage(data: any) {
		// Handle server content
		if (data.serverContent) {
			// Check for interruption
			if (data.serverContent.interrupted) {
				this.callbacks.onInterrupted?.();
				return;
			}

			// Handle model turn (response)
			if (data.serverContent.modelTurn) {
				const parts = data.serverContent.modelTurn.parts || [];
				
				for (const part of parts) {
					// Audio output
					if (part.inlineData && part.inlineData.data) {
						const audioData = this.base64ToArrayBuffer(part.inlineData.data);
						this.callbacks.onAudioOutput?.(audioData);
					}

					// Text output
					if (part.text) {
						this.callbacks.onTextOutput?.(part.text);
					}
				}
			}
		}
	}

	private base64ToArrayBuffer(base64: string): ArrayBuffer {
		const binaryString = atob(base64);
		const bytes = new Uint8Array(binaryString.length);
		for (let i = 0; i < binaryString.length; i++) {
			bytes[i] = binaryString.charCodeAt(i);
		}
		return bytes.buffer;
	}

	async startAudioInput(stream: MediaStream): Promise<void> {
		if (!stream) {
			throw new Error('MediaStream is required');
		}
		
		this.mediaStream = stream;
		
		try {
			// Create AudioContext if it doesn't exist
			if (!this.audioContext || this.audioContext.state === 'closed') {
				this.audioContext = new AudioContext({ sampleRate: 16000 });
			}
			
			// Wait for AudioContext to be ready
			if (this.audioContext.state === 'suspended') {
				await this.audioContext.resume();
			}
			
			if (!this.audioContext) {
				throw new Error('AudioContext is not available');
			}
			
			const source = this.audioContext.createMediaStreamSource(stream);
			let useAudioWorklet = false;
			
			// Try to use AudioWorklet (modern, non-deprecated)
			try {
				// Create AudioWorklet processor
				// AudioWorklet files must be in static folder for SvelteKit
				await this.audioContext.audioWorklet.addModule('/audio-processor-worklet.js');
				
				const workletNode = new AudioWorkletNode(this.audioContext, 'audio-processor-worklet');
				
				workletNode.port.onmessage = (event) => {
					if (event.data.type === 'audio' && this.isConnected && this.ws) {
						const pcm16Array = new Int16Array(event.data.data);
						const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcm16Array.buffer)));
						
						// Send audio to WebSocket
						const message = {
							realtimeInput: {
								mediaChunks: [
									{
										mimeType: 'audio/pcm',
										data: base64Audio
									}
								]
							}
						};

						if (this.isConnected) {
							this.ws.send(JSON.stringify(message));
						} else {
							this.messageQueue.push(message);
						}
					}
				};
				
				this.audioWorkletNode = workletNode;
				source.connect(workletNode);
				useAudioWorklet = true;
			} catch (workletError) {
				// Fallback to ScriptProcessorNode if AudioWorklet not available
				console.warn('AudioWorklet not available, using ScriptProcessorNode (deprecated):', workletError);
				
				const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

				processor.onaudioprocess = (e) => {
					if (!this.isConnected || !this.ws) return;

					const inputData = e.inputBuffer.getChannelData(0);
					const pcm16 = this.float32ToPCM16(inputData);
					const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcm16)));
					
					// Send audio to WebSocket
					const message = {
						realtimeInput: {
							mediaChunks: [
								{
									mimeType: 'audio/pcm',
									data: base64Audio
								}
							]
						}
					};

					if (this.isConnected) {
						this.ws.send(JSON.stringify(message));
					} else {
						this.messageQueue.push(message);
					}
				};

				source.connect(this.scriptProcessor);
				this.scriptProcessor.connect(this.audioContext.destination);
			}
		} catch (error) {
			console.error('Error setting up audio input:', error);
			throw error;
		}
	}

	private float32ToPCM16(float32Array: Float32Array): Int16Array {
		const int16Array = new Int16Array(float32Array.length);
		for (let i = 0; i < float32Array.length; i++) {
			const s = Math.max(-1, Math.min(1, float32Array[i]));
			int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
		}
		return int16Array;
	}

	playAudioOutput(audioData: ArrayBuffer): void {
		if (!this.audioContext || this.audioContext.state === 'closed') {
			this.audioContext = new AudioContext({ sampleRate: 24000 });
		}

		// Ensure AudioContext is running
		if (this.audioContext.state === 'suspended') {
			this.audioContext.resume().catch(err => {
				console.error('Error resuming AudioContext:', err);
			});
		}

		if (!this.audioContext) {
			console.error('AudioContext is not available for playback');
			return;
		}

		this.audioContext.decodeAudioData(audioData.slice(0))
			.then((audioBuffer) => {
				if (!this.audioContext) {
					console.error('AudioContext was closed during decode');
					return;
				}
				const source = this.audioContext!.createBufferSource();
				source.buffer = audioBuffer;
				source.connect(this.audioContext!.destination);
				source.start();
			})
			.catch((error) => {
				console.error('Error playing audio:', error);
			});
	}

	sendText(text: string): void {
		if (!this.isConnected || !this.ws) {
			this.messageQueue.push({
				realtimeInput: {
					text: text
				}
			});
			return;
		}

		this.ws.send(JSON.stringify({
			realtimeInput: {
				text: text
			}
		}));
	}

	disconnect(): void {
		// Clean up WebSocket
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}

		// Clean up audio processing nodes
		if (this.audioWorkletNode) {
			try {
				this.audioWorkletNode.disconnect();
				this.audioWorkletNode = null;
			} catch (e) {
				console.warn('Error disconnecting AudioWorklet:', e);
			}
		}
		
		if (this.scriptProcessor) {
			try {
				this.scriptProcessor.disconnect();
				this.scriptProcessor = null;
			} catch (e) {
				console.warn('Error disconnecting ScriptProcessor:', e);
			}
		}
		
		// Clean up AudioContext
		if (this.audioContext && this.audioContext.state !== 'closed') {
			try {
				this.audioContext.close();
			} catch (e) {
				console.warn('Error closing AudioContext:', e);
			}
		}
		this.audioContext = null;

		// Clean up MediaStream
		if (this.mediaStream) {
			this.mediaStream.getTracks().forEach(track => track.stop());
			this.mediaStream = null;
		}

		this.isConnected = false;
	}

	get connected(): boolean {
		return this.isConnected;
	}
}
