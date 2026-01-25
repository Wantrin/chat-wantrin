<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();

	import { getOllamaConfig, updateOllamaConfig } from '$lib/apis/ollama';
	import { getOpenAIConfig, updateOpenAIConfig, getOpenAIModels } from '$lib/apis/openai';
	import { getGeminiConfig, updateGeminiConfig } from '$lib/apis/gemini';
	import { getTwilioConfig, updateTwilioConfig } from '$lib/apis/twilio';
	import { getModels as _getModels, getBackendConfig } from '$lib/apis';
	import { getConnectionsConfig, setConnectionsConfig } from '$lib/apis/configs';

	import { config, models, settings, user } from '$lib/stores';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	import OpenAIConnection from './Connections/OpenAIConnection.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import OllamaConnection from './Connections/OllamaConnection.svelte';
	import GeminiConnection from './Connections/GeminiConnection.svelte';
	import TwilioConnection from './Connections/TwilioConnection.svelte';

	const i18n = getContext('i18n');

	const getModels = async () => {
		const models = await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null),
			false,
			true
		);
		return models;
	};

	// External
	let OLLAMA_BASE_URLS = [''];
	let OLLAMA_API_CONFIGS = {};

	let OPENAI_API_KEYS = [''];
	let OPENAI_API_BASE_URLS = [''];
	let OPENAI_API_CONFIGS = {};

	let GEMINI_API_KEY: string | undefined = undefined;
	let GEMINI_API_BASE_URL = 'https://generativelanguage.googleapis.com';

	let TWILIO_ACCOUNT_SID = '';
	let TWILIO_AUTH_TOKEN = '';
	let TWILIO_PHONE_NUMBER = '';
	let ENABLE_TWILIO = false;

	let ENABLE_OPENAI_API: null | boolean = null;
	let ENABLE_OLLAMA_API: null | boolean = null;

	let connectionsConfig = null;

	let pipelineUrls = {};
	let showAddOpenAIConnectionModal = false;
	let showAddOllamaConnectionModal = false;

	const updateOpenAIHandler = async (showToast: boolean = true) => {
		if (ENABLE_OPENAI_API !== null) {
			// Remove trailing slashes
			OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			// Check if API KEYS length is same than API URLS length
			if (OPENAI_API_KEYS.length !== OPENAI_API_BASE_URLS.length) {
				// if there are more keys than urls, remove the extra keys
				if (OPENAI_API_KEYS.length > OPENAI_API_BASE_URLS.length) {
					OPENAI_API_KEYS = OPENAI_API_KEYS.slice(0, OPENAI_API_BASE_URLS.length);
				}

				// if there are more urls than keys, add empty keys
				if (OPENAI_API_KEYS.length < OPENAI_API_BASE_URLS.length) {
					const diff = OPENAI_API_BASE_URLS.length - OPENAI_API_KEYS.length;
					for (let i = 0; i < diff; i++) {
						OPENAI_API_KEYS.push('');
					}
				}
			}

			const res = await updateOpenAIConfig(localStorage.token, {
				ENABLE_OPENAI_API: ENABLE_OPENAI_API,
				OPENAI_API_BASE_URLS: OPENAI_API_BASE_URLS,
				OPENAI_API_KEYS: OPENAI_API_KEYS,
				OPENAI_API_CONFIGS: OPENAI_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				if (showToast) {
					toast.success($i18n.t('OpenAI API settings updated'));
				}
				await models.set(await getModels());
				return true;
			}
		}
		return false;
	};

	const updateOllamaHandler = async () => {
		if (ENABLE_OLLAMA_API !== null) {
			// Remove trailing slashes
			OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.map((url) => url.replace(/\/$/, ''));

			const res = await updateOllamaConfig(localStorage.token, {
				ENABLE_OLLAMA_API: ENABLE_OLLAMA_API,
				OLLAMA_BASE_URLS: OLLAMA_BASE_URLS,
				OLLAMA_API_CONFIGS: OLLAMA_API_CONFIGS
			}).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('Ollama API settings updated'));
				await models.set(await getModels());
			}
		}
	};

	const updateGeminiHandler = async (showToast: boolean = true) => {
		// Remove trailing slashes
		const baseUrl = GEMINI_API_BASE_URL.replace(/\/$/, '');

		const res = await updateGeminiConfig(localStorage.token, {
			GEMINI_API_KEY: GEMINI_API_KEY,
			GEMINI_API_BASE_URL: baseUrl
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Reload the Gemini config to ensure we have the latest value
			try {
				const updatedConfig = await getGeminiConfig(localStorage.token);
				if (updatedConfig && typeof updatedConfig === 'object') {
					GEMINI_API_KEY = updatedConfig.GEMINI_API_KEY || '';
					GEMINI_API_BASE_URL = updatedConfig.GEMINI_API_BASE_URL || 'https://generativelanguage.googleapis.com';
				}
			} catch (error) {
				console.warn('Failed to reload Gemini config:', error);
			}
			
			// Update settings store with the new Gemini API key for directConnections
			if ($settings) {
				settings.set({
					...$settings,
					directConnections: {
						...($settings.directConnections || {}),
						GEMINI_API_KEY: GEMINI_API_KEY || ''
					}
				});
			}
			
			// Reload config to ensure everything is in sync
			await config.set(await getBackendConfig());
			
			if (showToast) {
				toast.success($i18n.t('Gemini API settings updated'));
			}
			return true;
		}
		return false;
	};

	const updateTwilioHandler = async (showToast: boolean = true) => {
		const res = await updateTwilioConfig(localStorage.token, {
			TWILIO_ACCOUNT_SID: TWILIO_ACCOUNT_SID,
			TWILIO_AUTH_TOKEN: TWILIO_AUTH_TOKEN,
			TWILIO_PHONE_NUMBER: TWILIO_PHONE_NUMBER,
			ENABLE_TWILIO: ENABLE_TWILIO
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Reload the Twilio config to ensure we have the latest value
			try {
				const updatedConfig = await getTwilioConfig(localStorage.token);
				if (updatedConfig && typeof updatedConfig === 'object') {
					TWILIO_ACCOUNT_SID = updatedConfig.TWILIO_ACCOUNT_SID || '';
					TWILIO_AUTH_TOKEN = updatedConfig.TWILIO_AUTH_TOKEN || '';
					TWILIO_PHONE_NUMBER = updatedConfig.TWILIO_PHONE_NUMBER || '';
					ENABLE_TWILIO = updatedConfig.ENABLE_TWILIO || false;
				}
			} catch (error) {
				console.warn('Failed to reload Twilio config:', error);
			}
			
			// Reload config to ensure everything is in sync
			await config.set(await getBackendConfig());
			
			if (showToast) {
				toast.success($i18n.t('Twilio settings updated'));
			}
			return true;
		}
		return false;
	};

	const updateConnectionsHandler = async () => {
		const res = await setConnectionsConfig(localStorage.token, connectionsConfig).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t('Connections settings updated'));
			await models.set(await getModels());
			await config.set(await getBackendConfig());
		}
	};

	const addOpenAIConnectionHandler = async (connection) => {
		OPENAI_API_BASE_URLS = [...OPENAI_API_BASE_URLS, connection.url];
		OPENAI_API_KEYS = [...OPENAI_API_KEYS, connection.key];
		OPENAI_API_CONFIGS[OPENAI_API_BASE_URLS.length - 1] = connection.config;

		await updateOpenAIHandler();
	};

	const addOllamaConnectionHandler = async (connection) => {
		OLLAMA_BASE_URLS = [...OLLAMA_BASE_URLS, connection.url];
		OLLAMA_API_CONFIGS[OLLAMA_BASE_URLS.length - 1] = {
			...connection.config,
			key: connection.key
		};

		await updateOllamaHandler();
	};

	onMount(async () => {
		if ($user?.role === 'admin') {
			let ollamaConfig = {};
			let openaiConfig = {};
			let geminiConfig = {};

			let twilioConfig: any = {};
			
			await Promise.all([
				(async () => {
					try {
						ollamaConfig = await getOllamaConfig(localStorage.token);
					} catch (error) {
						console.error('Failed to load Ollama config:', error);
						ollamaConfig = {};
					}
				})(),
				(async () => {
					try {
						openaiConfig = await getOpenAIConfig(localStorage.token);
					} catch (error) {
						console.error('Failed to load OpenAI config:', error);
						openaiConfig = {};
					}
				})(),
				(async () => {
					try {
						geminiConfig = await getGeminiConfig(localStorage.token);
						console.log('Loaded Gemini config:', geminiConfig);
					} catch (error) {
						console.error('Failed to load Gemini config:', error);
						geminiConfig = {};
					}
				})(),
				(async () => {
					try {
						twilioConfig = await getTwilioConfig(localStorage.token);
						console.log('Loaded Twilio config:', twilioConfig);
					} catch (error) {
						console.error('Failed to load Twilio config:', error);
						twilioConfig = {};
					}
				})(),
				(async () => {
					try {
						connectionsConfig = await getConnectionsConfig(localStorage.token);
					} catch (error) {
						console.error('Failed to load connections config:', error);
						connectionsConfig = null;
					}
				})()
			]);

			ENABLE_OPENAI_API = openaiConfig.ENABLE_OPENAI_API;
			ENABLE_OLLAMA_API = ollamaConfig.ENABLE_OLLAMA_API;

			OPENAI_API_BASE_URLS = openaiConfig.OPENAI_API_BASE_URLS;
			OPENAI_API_KEYS = openaiConfig.OPENAI_API_KEYS;
			OPENAI_API_CONFIGS = openaiConfig.OPENAI_API_CONFIGS;

			OLLAMA_BASE_URLS = ollamaConfig.OLLAMA_BASE_URLS;
			OLLAMA_API_CONFIGS = ollamaConfig.OLLAMA_API_CONFIGS;

			// Load Gemini config - ensure we handle null/undefined properly
			if (geminiConfig && typeof geminiConfig === 'object') {
				GEMINI_API_KEY = geminiConfig.GEMINI_API_KEY || '';
				GEMINI_API_BASE_URL = geminiConfig.GEMINI_API_BASE_URL || 'https://generativelanguage.googleapis.com';
			} else {
				GEMINI_API_KEY = '';
				GEMINI_API_BASE_URL = 'https://generativelanguage.googleapis.com';
			}
			
			console.log('Final GEMINI_API_KEY length:', GEMINI_API_KEY?.length || 0);

			// Load Twilio config
			if (twilioConfig && typeof twilioConfig === 'object') {
				TWILIO_ACCOUNT_SID = twilioConfig.TWILIO_ACCOUNT_SID || '';
				TWILIO_AUTH_TOKEN = twilioConfig.TWILIO_AUTH_TOKEN || '';
				TWILIO_PHONE_NUMBER = twilioConfig.TWILIO_PHONE_NUMBER || '';
				ENABLE_TWILIO = twilioConfig.ENABLE_TWILIO || false;
			} else {
				TWILIO_ACCOUNT_SID = '';
				TWILIO_AUTH_TOKEN = '';
				TWILIO_PHONE_NUMBER = '';
				ENABLE_TWILIO = false;
			}

			if (ENABLE_OPENAI_API) {
				// get url and idx
				for (const [idx, url] of OPENAI_API_BASE_URLS.entries()) {
					if (!OPENAI_API_CONFIGS[idx]) {
						// Legacy support, url as key
						OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[url] || {};
					}
				}

				OPENAI_API_BASE_URLS.forEach(async (url, idx) => {
					OPENAI_API_CONFIGS[idx] = OPENAI_API_CONFIGS[idx] || {};
					if (!(OPENAI_API_CONFIGS[idx]?.enable ?? true)) {
						return;
					}
					try {
						const res = await getOpenAIModels(localStorage.token, idx);
						if (res.pipelines) {
							pipelineUrls[url] = true;
						}
					} catch (error) {
						// Silently handle errors when checking for pipelines
						// The error is already logged by getOpenAIModels
						console.warn(`Failed to fetch models for connection ${idx}:`, error);
					}
				});
			}

			if (ENABLE_OLLAMA_API) {
				for (const [idx, url] of OLLAMA_BASE_URLS.entries()) {
					if (!OLLAMA_API_CONFIGS[idx]) {
						OLLAMA_API_CONFIGS[idx] = OLLAMA_API_CONFIGS[url] || {};
					}
				}
			}
		}
	});

	const submitHandler = async () => {
		// Update all configs without showing individual toasts
		const results = await Promise.all([
			updateOpenAIHandler(false),
			updateOllamaHandler(false),
			updateGeminiHandler(false),
			updateTwilioHandler(false)
		]);

		// Show a single success toast if at least one update succeeded
		if (results.some(r => r === true)) {
			toast.success($i18n.t('Settings updated successfully'));
		}

		dispatch('save');

		await config.set(await getBackendConfig());
	};
</script>

<AddConnectionModal
	bind:show={showAddOpenAIConnectionModal}
	onSubmit={addOpenAIConnectionHandler}
/>

<AddConnectionModal
	ollama
	bind:show={showAddOllamaConnectionModal}
	onSubmit={addOllamaConnectionHandler}
/>

<form class="flex flex-col h-full justify-between text-sm" on:submit|preventDefault={submitHandler}>
	<div class=" overflow-y-scroll scrollbar-hidden h-full">
		{#if ENABLE_OPENAI_API !== null && ENABLE_OLLAMA_API !== null && connectionsConfig !== null && GEMINI_API_KEY !== undefined}
			<div class="mb-3.5">
				<div class=" mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('General')}</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="my-2">
					<div class="mt-2 space-y-2">
						<div class="flex justify-between items-center text-sm">
							<div class="  font-medium">{$i18n.t('OpenAI API')}</div>

							<div class="flex items-center">
								<div class="">
									<Switch
										bind:state={ENABLE_OPENAI_API}
										on:change={async () => {
											updateOpenAIHandler();
										}}
									/>
								</div>
							</div>
						</div>

						{#if ENABLE_OPENAI_API}
							<div class="">
								<div class="flex justify-between items-center">
									<div class="font-medium text-xs">{$i18n.t('Manage OpenAI API Connections')}</div>

									<Tooltip content={$i18n.t(`Add Connection`)}>
										<button
											class="px-1"
											on:click={() => {
												showAddOpenAIConnectionModal = true;
											}}
											type="button"
										>
											<Plus />
										</button>
									</Tooltip>
								</div>

								<div class="flex flex-col gap-1.5 mt-1.5">
									{#each OPENAI_API_BASE_URLS as url, idx}
										<OpenAIConnection
											bind:url={OPENAI_API_BASE_URLS[idx]}
											bind:key={OPENAI_API_KEYS[idx]}
											bind:config={OPENAI_API_CONFIGS[idx]}
											pipeline={pipelineUrls[url] ? true : false}
											onSubmit={() => {
												updateOpenAIHandler();
											}}
											onDelete={() => {
												OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS.filter(
													(url, urlIdx) => idx !== urlIdx
												);
												OPENAI_API_KEYS = OPENAI_API_KEYS.filter((key, keyIdx) => idx !== keyIdx);

												let newConfig = {};
												OPENAI_API_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OPENAI_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OPENAI_API_CONFIGS = newConfig;
												updateOpenAIHandler();
											}}
										/>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<div class=" my-2">
					<div class="flex justify-between items-center text-sm mb-2">
						<div class="  font-medium">{$i18n.t('Ollama API')}</div>

						<div class="mt-1">
							<Switch
								bind:state={ENABLE_OLLAMA_API}
								on:change={async () => {
									updateOllamaHandler();
								}}
							/>
						</div>
					</div>

					{#if ENABLE_OLLAMA_API}
						<div class="">
							<div class="flex justify-between items-center">
								<div class="font-medium text-xs">{$i18n.t('Manage Ollama API Connections')}</div>

								<Tooltip content={$i18n.t(`Add Connection`)}>
									<button
										class="px-1"
										on:click={() => {
											showAddOllamaConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex w-full gap-1.5">
								<div class="flex-1 flex flex-col gap-1.5 mt-1.5">
									{#each OLLAMA_BASE_URLS as url, idx}
										<OllamaConnection
											bind:url={OLLAMA_BASE_URLS[idx]}
											bind:config={OLLAMA_API_CONFIGS[idx]}
											{idx}
											onSubmit={() => {
												updateOllamaHandler();
											}}
											onDelete={() => {
												OLLAMA_BASE_URLS = OLLAMA_BASE_URLS.filter((url, urlIdx) => idx !== urlIdx);

												let newConfig = {};
												OLLAMA_BASE_URLS.forEach((url, newIdx) => {
													newConfig[newIdx] =
														OLLAMA_API_CONFIGS[newIdx < idx ? newIdx : newIdx + 1];
												});
												OLLAMA_API_CONFIGS = newConfig;
											}}
										/>
									{/each}
								</div>
							</div>

							<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t('Trouble accessing Ollama?')}
								<a
									class=" text-gray-300 font-medium underline"
									href="https://github.com/open-webui/open-webui#troubleshooting"
									target="_blank"
								>
									{$i18n.t('Click here for help.')}
								</a>
							</div>
						</div>
					{/if}
				</div>

				<div class=" my-2">
					<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Google Gemini API')}</div>

					<div class="mt-2 space-y-2">
						<GeminiConnection
							bind:apiKey={GEMINI_API_KEY}
							bind:baseUrl={GEMINI_API_BASE_URL}
							onSubmit={() => {
								updateGeminiHandler();
							}}
							onDelete={() => {
								GEMINI_API_KEY = '';
								updateGeminiHandler();
							}}
						/>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('Configure your Google Gemini API key for speech-to-speech phone calls.')}
					</div>
				</div>

				<div class=" my-2">
					<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Twilio')}</div>

					<div class="mt-2 space-y-2">
						<TwilioConnection
							bind:accountSid={TWILIO_ACCOUNT_SID}
							bind:authToken={TWILIO_AUTH_TOKEN}
							bind:phoneNumber={TWILIO_PHONE_NUMBER}
							bind:enableTwilio={ENABLE_TWILIO}
							onSubmit={() => {
								updateTwilioHandler();
							}}
						/>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('Configure Twilio for phone calls and SMS. Get your credentials from https://www.twilio.com/')}
					</div>
				</div>

				<div class="my-2">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('Direct Connections')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_DIRECT_CONNECTIONS}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t(
							'Direct Connections allow users to connect to their own OpenAI compatible API endpoints.'
						)}
					</div>
				</div>

				<hr class=" border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="my-2">
					<div class="flex justify-between items-center text-sm">
						<div class=" text-xs font-medium">{$i18n.t('Cache Base Model List')}</div>

						<div class="flex items-center">
							<div class="">
								<Switch
									bind:state={connectionsConfig.ENABLE_BASE_MODELS_CACHE}
									on:change={async () => {
										updateConnectionsHandler();
									}}
								/>
							</div>
						</div>
					</div>

					<div class="mt-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t(
							'Base Model List Cache speeds up access by fetching base models only at startup or on settings save—faster, but may not show recent base model changes.'
						)}
					</div>
				</div>
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
