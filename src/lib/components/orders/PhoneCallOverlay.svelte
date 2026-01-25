<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { settings, models } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { OpenAIRealtimeClient } from '$lib/apis/realtime/openai';
	import { GeminiLiveClient } from '$lib/apis/realtime/gemini';
	import { createRealtimeClientSecret, getOpenAIKeys } from '$lib/apis/openai';
	import { getGeminiKey } from '$lib/apis/gemini';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let order: any;
	export let deliveryPerson: any | null = null;
	export let callType: 'customer' | 'delivery_person';
	export let phoneNumber: string;
	export let onClose: () => void;
	export let onCallEnd: () => void;

	let calling = false;
	let inCall = false;
	let callEnded = false;
	let callDuration = 0;
	let callDurationInterval: any = null;

	let loading = false;
	let assistantSpeaking = false;

	let audioStream: MediaStream | null = null;
	let realtimeClient: OpenAIRealtimeClient | GeminiLiveClient | null = null;

	let rmsLevel = 0;
	const VISUALIZER_BUFFER_LENGTH = 300;
	let visualizerData = Array(VISUALIZER_BUFFER_LENGTH).fill(0);

	// Provider selection
	type Provider = 'openai' | 'gemini';
	let selectedProvider: Provider = 'openai';
	let availableProviders: Provider[] = ['openai', 'gemini'];

	// Get API keys from settings
	const getAPIKey = async (provider: Provider): Promise<string | null> => {
		const token = typeof window !== 'undefined' ? localStorage.token : '';
		
		if (provider === 'openai') {
			// Priority 1: Direct connections from settings
			const directConnections = $settings?.directConnections;
			if (directConnections?.OPENAI_API_KEYS?.[0]) {
				return directConnections.OPENAI_API_KEYS[0];
			}
			
			// Priority 2: Get from backend API (user's configured keys)
			if (token) {
				try {
					const keys = await getOpenAIKeys(token);
					if (keys && keys.length > 0 && keys[0]) {
						return keys[0];
					}
				} catch (error) {
					console.warn('Failed to get OpenAI keys from backend:', error);
				}
			}
			
			// Priority 3: Fallback to localStorage
			return localStorage.getItem('openai_api_key') || null;
		} else if (provider === 'gemini') {
			// Priority 1: Direct connections from settings
			const directConnections = $settings?.directConnections;
			if (directConnections?.GEMINI_API_KEY) {
				return directConnections.GEMINI_API_KEY;
			}
			
			// Priority 2: Get from backend API (user's configured keys)
			if (token) {
				try {
					const key = await getGeminiKey(token);
					if (key) {
						return key;
					}
				} catch (error) {
					console.warn('Failed to get Gemini key from backend:', error);
				}
			}
			
			// Priority 3: Fallback to localStorage
			return localStorage.getItem('gemini_api_key') || null;
		}
		return null;
	};

	// Build system instructions
	const getSystemInstructions = (): string => {
		const orderInfo = order ? `
Order ID: ${order.id}
Status: ${order.status}
Customer: ${order.customer_name} (${order.customer_email})
Items: ${order.items.map((i: any) => `${i.name} x${i.quantity}`).join(', ')}
Total: ${order.total} ${order.currency}
` : '';

		const deliveryPersonInfo = deliveryPerson ? `
Delivery Person: ${deliveryPerson.name}
Phone: ${deliveryPerson.phone}
Vehicle: ${deliveryPerson.vehicle_type || 'N/A'}
` : '';

		return `You are a helpful assistant making a phone call for order management.

${callType === 'customer' ? `
You are calling the customer about their order. Be professional, friendly, and helpful.
You can:
- Ask for clarification on order details
- Confirm delivery information
- Answer questions about the order
- Help resolve any issues
` : `
You are calling the delivery person assigned to deliver this order. Be professional and clear.
You can:
- Provide delivery instructions
- Confirm delivery details
- Answer questions about the order
- Coordinate delivery timing
`}

ORDER INFORMATION:
${orderInfo}

${deliveryPersonInfo}

IMPORTANT:
- Keep responses concise and natural for phone conversation
- Speak clearly and professionally
- If you need to ask questions, ask one at a time
- Be helpful and solution-oriented`;
	};

	// Audio visualization
	const setupAudioVisualization = (stream: MediaStream) => {
		const audioContext = new AudioContext();
		const source = audioContext.createMediaStreamSource(stream);
		const analyser = audioContext.createAnalyser();
		analyser.fftSize = 2048;
		source.connect(analyser);

		const dataArray = new Uint8Array(analyser.frequencyBinCount);

		const updateVisualizer = () => {
			if (!inCall) return;

			analyser.getByteFrequencyData(dataArray);
			const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
			rmsLevel = average / 255;

			// Update visualizer data
			visualizerData.shift();
			visualizerData.push(Math.min(1, rmsLevel * 2));

			requestAnimationFrame(updateVisualizer);
		};

		updateVisualizer();
	};

	const startCall = async () => {
		calling = true;
		loading = true;

		try {
			// Get API key
			const apiKey = await getAPIKey(selectedProvider);
			if (!apiKey) {
				const providerName = selectedProvider === 'openai' ? 'OpenAI' : 'Google Gemini';
				toast.error(
					$i18n.t('API key not found for {provider}. Please configure your API key in Settings > Connections.', {
						provider: providerName
					})
				);
				calling = false;
				loading = false;
				return;
			}

			// Get audio stream
			audioStream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: true,
					noiseSuppression: true,
					autoGainControl: true,
					sampleRate: selectedProvider === 'gemini' ? 16000 : 24000
				}
			});

			// Setup audio visualization
			setupAudioVisualization(audioStream);

			// Initialize realtime client based on provider
			if (selectedProvider === 'openai') {
				// Validate API key before proceeding
				if (!apiKey || !apiKey.trim()) {
					toast.error($i18n.t('OpenAI API key is required. Please configure it in Settings > Connections.'));
					calling = false;
					loading = false;
					return;
				}

				// Get ephemeral key for secure client-side connection
				let ephemeralKey: string | undefined;
				try {
					const token = typeof window !== 'undefined' ? localStorage.token : '';
					const secretResponse = await createRealtimeClientSecret(token, {
						session: {
							type: 'realtime',
							model: 'gpt-realtime',
							instructions: getSystemInstructions(),
							audio: {
								output: {
									voice: 'alloy'
								}
							}
						}
					});
					
					if (!secretResponse || !secretResponse.value || !secretResponse.value.trim()) {
						throw new Error('Invalid ephemeral key received from server');
					}
					
					ephemeralKey = secretResponse.value.trim();
				} catch (error: any) {
					console.error('Failed to get ephemeral key:', error);
					toast.error($i18n.t('Failed to initialize call. Please check your API key.') + (error.message ? `: ${error.message}` : ''));
					calling = false;
					loading = false;
					return;
				}

				realtimeClient = new OpenAIRealtimeClient(
					{
						apiKey: apiKey.trim(),
						model: 'gpt-realtime',
						voice: 'alloy',
						instructions: getSystemInstructions()
					},
					{
						onOpen: () => {
							console.log('OpenAI Realtime connected');
							calling = false;
							inCall = true;
							loading = false;

							// Start call duration counter
							callDurationInterval = setInterval(() => {
								callDuration++;
							}, 1000);
						},
						onAudioOutput: (audioData: ArrayBuffer) => {
							assistantSpeaking = true;
							(realtimeClient as OpenAIRealtimeClient).playAudioOutput(audioData);
						},
						onTextOutput: (text: string) => {
							console.log('AI:', text);
						},
						onTranscript: (text: string) => {
							console.log('User:', text);
						},
						onError: (error: Error) => {
							console.error('OpenAI Realtime error:', error);
							toast.error($i18n.t('Call error: ') + error.message);
							endCall();
						},
						onClose: () => {
							console.log('OpenAI Realtime disconnected');
							endCall();
						}
					}
				);

				// Connect first, then start audio input
				await realtimeClient.connect(ephemeralKey);
				
				// Ensure audio stream is still valid before starting input
				if (audioStream && audioStream.active) {
					await realtimeClient.startAudioInput(audioStream);
				} else {
					throw new Error('Audio stream is not available');
				}
			} else if (selectedProvider === 'gemini') {
				// Validate API key before creating client
				if (!apiKey || !apiKey.trim()) {
					toast.error($i18n.t('Gemini API key is required. Please configure it in Settings > Connections.'));
					calling = false;
					loading = false;
					return;
				}
				
				realtimeClient = new GeminiLiveClient(
					{
						apiKey: apiKey.trim(),
						model: 'gemini-2.5-flash-native-audio-preview-12-2025',
						systemInstruction: getSystemInstructions()
					},
					{
						onOpen: () => {
							console.log('Gemini Live connected');
							calling = false;
							inCall = true;
							loading = false;

							// Start call duration counter
							callDurationInterval = setInterval(() => {
								callDuration++;
							}, 1000);
						},
						onAudioOutput: (audioData: ArrayBuffer) => {
							assistantSpeaking = true;
							(realtimeClient as GeminiLiveClient).playAudioOutput(audioData);
						},
						onTextOutput: (text: string) => {
							console.log('AI:', text);
						},
						onInterrupted: () => {
							assistantSpeaking = false;
							console.log('User interrupted AI');
						},
						onError: (error: Error) => {
							console.error('Gemini Live error:', error);
							toast.error($i18n.t('Call error: ') + error.message);
							endCall();
						},
						onClose: () => {
							console.log('Gemini Live disconnected');
							endCall();
						}
					}
				);

				// Connect first, then start audio input
				await realtimeClient.connect();
				
				// Ensure audio stream is still valid before starting input
				if (audioStream && audioStream.active) {
					await realtimeClient.startAudioInput(audioStream);
				} else {
					throw new Error('Audio stream is not available');
				}
			}
		} catch (error: any) {
			console.error('Error starting call:', error);
			toast.error($i18n.t('Failed to start call: ') + (error.message || error));
			calling = false;
			loading = false;
		}
	};

	const endCall = async () => {
		callEnded = true;
		inCall = false;
		assistantSpeaking = false;

		if (realtimeClient) {
			realtimeClient.disconnect();
			realtimeClient = null;
		}

		if (audioStream) {
			audioStream.getTracks().forEach(track => track.stop());
			audioStream = null;
		}

		if (callDurationInterval) {
			clearInterval(callDurationInterval);
			callDurationInterval = null;
		}

		if (onCallEnd) {
			onCallEnd();
		}
	};

	const formatDuration = (seconds: number) => {
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	};

	onMount(async () => {
		// Check which providers are available
		const openaiKey = await getAPIKey('openai');
		const geminiKey = await getAPIKey('gemini');

		// Filter available providers
		availableProviders = [];
		if (openaiKey) availableProviders.push('openai');
		if (geminiKey) availableProviders.push('gemini');

		if (availableProviders.length === 0) {
			toast.error(
				$i18n.t('No API keys configured. Please configure OpenAI or Gemini API key in Settings > Connections.')
			);
		} else {
			// Set default provider
			selectedProvider = availableProviders[0] || 'openai';
		}
	});
</script>

<div class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center">
	<div class="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
		<div class="flex items-center justify-between mb-6">
			<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
				{$i18n.t('Phone Call')}
			</h2>
			<button
				class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
				on:click={endCall}
			>
				<XMark className="w-5 h-5" />
			</button>
		</div>

		<!-- Provider Selection (before call starts) -->
		{#if !inCall && !callEnded}
			<div class="mb-6">
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Provider')}
				</label>
				<select
					bind:value={selectedProvider}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					disabled={calling || loading}
				>
					{#each availableProviders as provider}
						<option value={provider}>
							{provider === 'openai' ? 'OpenAI Realtime' : 'Google Gemini Live'}
						</option>
					{/each}
				</select>
			</div>
		{/if}

		<div class="text-center mb-6">
			<div class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
				{callType === 'customer' 
					? $i18n.t('Calling Customer')
					: $i18n.t('Calling Delivery Person')}
			</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{phoneNumber}
			</div>
			{#if inCall}
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-2">
					{formatDuration(callDuration)}
				</div>
			{/if}
		</div>

		<!-- Audio Visualizer -->
		{#if inCall}
			<div class="flex items-center justify-center gap-1 h-12 mb-6">
				{#each visualizerData as level}
					<div
						class="w-1 bg-blue-500 rounded-full transition-all"
						style="height: {level * 100}%"
					></div>
				{/each}
			</div>
		{/if}

		<!-- Status -->
		<div class="text-center mb-6">
			{#if calling || loading}
				<div class="flex items-center justify-center gap-2 text-gray-600 dark:text-gray-400">
					<Spinner className="w-5 h-5" />
					<span>{$i18n.t('Connecting...')}</span>
				</div>
			{:else if inCall}
				<div class="flex items-center justify-center gap-2">
					<div class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
					<span class="text-green-600 dark:text-green-400 font-medium">
						{$i18n.t('Call in progress')}
					</span>
				</div>
			{:else if callEnded}
				<div class="text-gray-600 dark:text-gray-400">
					{$i18n.t('Call ended')}
				</div>
			{/if}
		</div>

		<!-- Controls -->
		<div class="flex justify-center gap-4">
			{#if inCall}
				<button
					class="px-6 py-3 bg-red-500 text-white rounded-full hover:bg-red-600 transition font-medium"
					on:click={endCall}
				>
					{$i18n.t('End Call')}
				</button>
			{:else if !callEnded}
				<button
					class="px-6 py-3 bg-green-500 text-white rounded-full hover:bg-green-600 transition font-medium"
					on:click={startCall}
					disabled={calling || loading}
				>
					{$i18n.t('Start Call')}
				</button>
			{/if}
		</div>
	</div>
</div>
