<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { settings, config, user, audioQueue } from '$lib/stores';
	import { copyToClipboard, removeAllDetails } from '$lib/utils';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Name from '$lib/components/chat/Messages/Name.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Skeleton from '$lib/components/chat/Messages/Skeleton.svelte';
	
	const i18n = getContext('i18n');
	
	export let message;
	export let idx;
	export let onEdit;
	export let onDelete;
	export let onRegenerate;
	export let onContinue;
	export let isLastMessage = false;
	
	let edit = false;
	let editedContent = '';
	let textAreaElement: HTMLTextAreaElement;
	let speaking = false;
	let loadingSpeech = false;
	let rating = message.rating || null;
	
	const copyMessage = async () => {
		const res = await copyToClipboard(message.content);
		if (res) {
			toast.success($i18n.t('Copied to clipboard'));
		}
	};
	
	const editMessage = async () => {
		edit = true;
		editedContent = message.content;
		await tick();
		if (textAreaElement) {
			textAreaElement.focus();
			textAreaElement.style.height = '';
			textAreaElement.style.height = `${textAreaElement.scrollHeight}px`;
		}
	};
	
	const saveEdit = async () => {
		if (onEdit) {
			onEdit(idx, editedContent);
		}
		edit = false;
		await tick();
	};
	
	const cancelEdit = () => {
		edit = false;
		editedContent = '';
	};
	
	const stopAudio = () => {
		try {
			speechSynthesis.cancel();
			$audioQueue?.stop();
		} catch {}
		if (speaking) {
			speaking = false;
		}
	};
	
	const speak = async () => {
		if (!(message?.content ?? '').trim().length) {
			toast.info($i18n.t('No content to speak'));
			return;
		}
		
		speaking = true;
		const content = removeAllDetails(message.content);
		
		// Use browser TTS by default
		let voices = [];
		const getVoicesLoop = setInterval(() => {
			voices = speechSynthesis.getVoices();
			if (voices.length > 0) {
				clearInterval(getVoicesLoop);
				const speech = new SpeechSynthesisUtterance(content);
				speech.rate = $settings?.audio?.tts?.playbackRate ?? 1;
				speech.onend = () => {
					speaking = false;
				};
				speech.onerror = () => {
					speaking = false;
				};
				speechSynthesis.speak(speech);
			}
		}, 100);
		
		// Fallback: try OpenAI TTS if configured
		if ($config?.audio?.tts?.engine && $config.audio.tts.engine !== '') {
			loadingSpeech = true;
			try {
				const url = await synthesizeOpenAISpeech(
					localStorage.token,
					content,
					$settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice
				);
				if (url && speaking && $audioQueue) {
					$audioQueue.enqueue(url);
				}
			} catch (error) {
				console.error(error);
				// Fallback to browser TTS if OpenAI TTS fails
			} finally {
				loadingSpeech = false;
			}
		}
	};
	
	const handleRating = (value: number) => {
		rating = rating === value ? null : value;
		message.rating = rating;
		// Could save rating to backend if needed
	};
</script>

<div class="flex flex-col gap-1 group">
	<div class="flex items-center justify-between pt-1">
		<Name role={message.role} />
	</div>

	<div class="flex-1">
		{#if edit}
			<div class="w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 mb-2">
				<div class="max-h-96 overflow-auto">
					<textarea
						bind:this={textAreaElement}
						bind:value={editedContent}
						class="bg-transparent outline-hidden w-full resize-none"
						on:input={(e) => {
							e.target.style.height = '';
							e.target.style.height = `${e.target.scrollHeight}px`;
						}}
						on:keydown={(e) => {
							if (e.key === 'Escape') {
								cancelEdit();
							}
							const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
							const isEnterPressed = e.key === 'Enter';
							if (isCmdOrCtrlPressed && isEnterPressed) {
								saveEdit();
							}
						}}
					></textarea>
				</div>
				<div class="mt-2 mb-1 flex justify-between text-sm font-medium">
					<button
						class="px-3.5 py-1.5 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
						on:click={saveEdit}
					>
						{$i18n.t('Save')}
					</button>
					<button
						class="px-3.5 py-1.5 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
						on:click={cancelEdit}
					>
						{$i18n.t('Cancel')}
					</button>
				</div>
			</div>
		{:else if message.role === 'assistant' && !message.done}
			<Skeleton size="sm" />
		{:else}
			<div class="w-full">
				<div class="flex {($settings?.chatBubble ?? true) ? 'justify-end pb-1' : 'w-full'}">
					<div
						class="max-w-full {($settings?.chatBubble ?? true)
							? 'bg-gray-900 dark:bg-white text-gray-100 dark:text-gray-800 rounded-3xl px-5 py-3'
							: 'bg-transparent'}"
					>
						<Markdown id={`task-message-${idx}`} content={message.content || ''} />
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if !edit}
		<div class="flex justify-start overflow-x-auto text-gray-600 dark:text-gray-500 mt-0.5">
			<div class="flex items-center gap-1 {isLastMessage || ($settings?.highContrastMode ?? false) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity">
			{#if message.role === 'assistant' && message.done}
				<!-- Edit -->
				<Tooltip content={$i18n.t('Edit')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
						on:click={editMessage}
					>
						<Pencil className="w-4 h-4" strokeWidth="2.3" />
					</button>
				</Tooltip>
				
				<!-- Copy -->
				<Tooltip content={$i18n.t('Copy')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
						on:click={copyMessage}
					>
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
						</svg>
					</button>
				</Tooltip>
				
				<!-- Read Aloud -->
				{#if $user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true)}
					<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
						<button
							class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
							on:click={() => {
								if (!loadingSpeech) {
									if (speaking) {
										stopAudio();
									} else {
										speak();
									}
								}
							}}
						>
							{#if loadingSpeech}
								<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
									<circle class="animate-pulse" cx="4" cy="12" r="3" />
									<circle class="animate-pulse" cx="12" cy="12" r="3" style="animation-delay: 0.2s" />
									<circle class="animate-pulse" cx="20" cy="12" r="3" style="animation-delay: 0.4s" />
								</svg>
							{:else if speaking}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor" class="w-4 h-4">
									<path stroke-linecap="round" stroke-linejoin="round" d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor" class="w-4 h-4">
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" />
								</svg>
							{/if}
						</button>
					</Tooltip>
				{/if}
				
				<!-- Info -->
				<Tooltip content={$i18n.t('Information')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
						</svg>
					</button>
				</Tooltip>
				
				<!-- Thumbs Up -->
				<Tooltip content={$i18n.t('Good Response')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition {rating === 1 ? 'bg-gray-100 dark:bg-gray-800' : ''}"
						on:click={() => handleRating(1)}
					>
						<svg stroke="currentColor" fill="none" stroke-width="2.3" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
							<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
						</svg>
					</button>
				</Tooltip>
				
				<!-- Thumbs Down -->
				<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition {rating === -1 ? 'bg-gray-100 dark:bg-gray-800' : ''}"
						on:click={() => handleRating(-1)}
					>
						<svg stroke="currentColor" fill="none" stroke-width="2.3" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4">
							<path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
						</svg>
					</button>
				</Tooltip>
				
				<!-- Continue Response (Play) -->
				{#if isLastMessage && onContinue}
					<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
						<button
							class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
							on:click={() => onContinue()}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" />
							</svg>
						</button>
					</Tooltip>
				{/if}
				
				<!-- Regenerate -->
				{#if onRegenerate}
					<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
						<button
							class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
							on:click={() => onRegenerate(idx)}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
							</svg>
						</button>
					</Tooltip>
				{/if}
			{:else if message.role === 'user'}
				<!-- Edit -->
				<Tooltip content={$i18n.t('Edit')} placement="bottom">
					<button
						class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
						on:click={editMessage}
					>
						<Pencil className="w-4 h-4" strokeWidth="2.3" />
					</button>
				</Tooltip>
				
				<!-- Delete -->
				{#if onDelete}
					<Tooltip content={$i18n.t('Delete')} placement="bottom">
						<button
							class="p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
							on:click={() => onDelete(idx)}
						>
							<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.3" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
							</svg>
						</button>
					</Tooltip>
				{/if}
			{/if}
			</div>
		</div>
	{/if}
</div>
