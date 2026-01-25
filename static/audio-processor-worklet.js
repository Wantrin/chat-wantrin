/**
 * AudioWorklet processor for converting audio to PCM16 and sending to WebSocket
 * Used by Gemini Live and OpenAI Realtime clients
 */

class AudioProcessorWorklet extends AudioWorkletProcessor {
	constructor() {
		super();
		this.bufferSize = 4096;
		this.buffer = new Float32Array(this.bufferSize);
		this.bufferIndex = 0;
	}

	process(inputs, outputs, parameters) {
		const input = inputs[0];
		
		if (input && input.length > 0) {
			const inputChannel = input[0];
			
			// Copy input samples to buffer
			for (let i = 0; i < inputChannel.length; i++) {
				this.buffer[this.bufferIndex++] = inputChannel[i];
				
				// When buffer is full, send it
				if (this.bufferIndex >= this.bufferSize) {
					// Convert Float32 to Int16 PCM
					const pcm16 = new Int16Array(this.bufferSize);
					for (let j = 0; j < this.bufferSize; j++) {
						const s = Math.max(-1, Math.min(1, this.buffer[j]));
						pcm16[j] = s < 0 ? s * 0x8000 : s * 0x7FFF;
					}
					
					// Send to main thread
					this.port.postMessage({
						type: 'audio',
						data: pcm16.buffer
					});
					
					this.bufferIndex = 0;
				}
			}
		}
		
		return true; // Keep processor alive
	}
}

registerProcessor('audio-processor-worklet', AudioProcessorWorklet);
