/**
 * OpenAI Realtime API Wrapper
 * Documentation: https://platform.openai.com/docs/guides/realtime
 */

export interface OpenAIRealtimeConfig {
	apiKey: string;
	model?: string;
	voice?: string;
	instructions?: string;
	baseUrl?: string;
}

export interface OpenAIRealtimeCallbacks {
	onAudioInput?: (audioData: ArrayBuffer) => void;
	onAudioOutput?: (audioData: ArrayBuffer) => void;
	onTextOutput?: (text: string) => void;
	onTranscript?: (text: string) => void;
	onError?: (error: Error) => void;
	onClose?: () => void;
	onOpen?: () => void;
}

export class OpenAIRealtimeClient {
	private ws: WebSocket | null = null;
	private config: OpenAIRealtimeConfig;
	private callbacks: OpenAIRealtimeCallbacks;
	private audioContext: AudioContext | null = null;
	private mediaStream: MediaStream | null = null;
	private audioWorkletNode: AudioWorkletNode | null = null;
	private isConnected = false;

	constructor(config: OpenAIRealtimeConfig, callbacks: OpenAIRealtimeCallbacks) {
		this.config = {
			model: 'gpt-realtime',
			voice: 'alloy',
			baseUrl: 'wss://api.openai.com/v1',
			...config
		};
		this.callbacks = callbacks;
	}

	async connect(ephemeralKey?: string): Promise<void> {
		return new Promise((resolve, reject) => {
			try {
				// OpenAI Realtime API requires ephemeral keys for browser connections
				// The ephemeral key is used as client_secret parameter in the WebSocket URL
				if (!ephemeralKey || !ephemeralKey.trim()) {
					reject(new Error('Ephemeral key is required for OpenAI Realtime API in browser'));
					return;
				}

				// Validate API key is configured
				if (!this.config.apiKey || !this.config.apiKey.trim()) {
					reject(new Error('OpenAI API key is required'));
					return;
				}

				const url = `${this.config.baseUrl}/realtime?model=${this.config.model}&client_secret=${encodeURIComponent(ephemeralKey.trim())}`;
				this.ws = new WebSocket(url);

				this.ws.onopen = () => {
					this.isConnected = true;
					
					// Send Authorization header via first message (if supported)
					// Or initialize session
					this.ws?.send(JSON.stringify({
						type: 'session.update',
						session: {
							type: 'realtime',
							model: this.config.model,
							instructions: this.config.instructions || 'You are a helpful assistant.',
							audio: {
								output: {
									voice: this.config.voice || 'alloy'
								}
							},
							input_audio_format: 'pcm16',
							output_audio_format: 'pcm16',
							turn_detection: {
								type: 'server_vad',
								threshold: 0.5,
								prefix_padding_ms: 300,
								silence_duration_ms: 500
							},
							tools: [],
							tool_choice: 'auto'
						}
					}));

					this.callbacks.onOpen?.();
					resolve();
				};

				this.ws.onmessage = (event) => {
					try {
						const data = JSON.parse(event.data);
						this.handleMessage(data);
					} catch (error) {
						console.error('Error parsing WebSocket message:', error);
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
		switch (data.type) {
			case 'response.output_text.delta':
				if (data.delta) {
					this.callbacks.onTextOutput?.(data.delta);
				}
				break;

			case 'response.output_audio.delta':
				if (data.delta) {
					// Decode base64 audio to ArrayBuffer
					const audioData = this.base64ToArrayBuffer(data.delta);
					this.callbacks.onAudioOutput?.(audioData);
				}
				break;

			case 'response.output_audio_transcript.delta':
				if (data.delta) {
					this.callbacks.onTranscript?.(data.delta);
				}
				break;

			case 'response.audio_transcript.done':
				if (data.transcript) {
					this.callbacks.onTranscript?.(data.transcript);
				}
				break;

			case 'error':
				this.callbacks.onError?.(new Error(data.error?.message || 'Unknown error'));
				break;
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
				this.audioContext = new AudioContext({ sampleRate: 24000 });
			}
			
			// Wait for AudioContext to be ready
			if (this.audioContext.state === 'suspended') {
				await this.audioContext.resume();
			}
			
			if (!this.audioContext) {
				throw new Error('AudioContext is not available');
			}
			
			// Create audio worklet for processing
			try {
				await this.audioContext.audioWorklet.addModule(
					new URL('/audio-processor.js', import.meta.url)
				);
			} catch (workletError) {
				// Fallback to ScriptProcessorNode if AudioWorklet not available
				console.warn('AudioWorklet not available, using ScriptProcessorNode:', workletError);
			}

			const source = this.audioContext.createMediaStreamSource(stream);
			const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

			processor.onaudioprocess = (e) => {
				if (!this.isConnected || !this.ws) return;

				const inputData = e.inputBuffer.getChannelData(0);
				const pcm16 = this.float32ToPCM16(inputData);
				
				// Convert to base64
				const base64Audio = btoa(
					String.fromCharCode(...new Uint8Array(pcm16.buffer))
				);
				
				// Send audio to WebSocket
				this.ws.send(JSON.stringify({
					type: 'input_audio_buffer.append',
					audio: base64Audio
				}));
			};

			source.connect(processor);
			processor.connect(this.audioContext.destination);
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

	private async setupScriptProcessor(): Promise<void> {
		// Fallback implementation
		return Promise.resolve();
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
		if (!this.isConnected || !this.ws) return;

		this.ws.send(JSON.stringify({
			type: 'conversation.item.create',
			item: {
				type: 'message',
				role: 'user',
				content: [
					{
						type: 'input_text',
						text: text
					}
				]
			}
		}));
	}

	interrupt(): void {
		if (!this.isConnected || !this.ws) return;

		this.ws.send(JSON.stringify({
			type: 'response.audio_interrupt'
		}));
	}

	disconnect(): void {
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}

		if (this.audioContext) {
			this.audioContext.close();
			this.audioContext = null;
		}

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
