<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { WEBUI_NAME, user, models, settings, config } from '$lib/stores';
	import {
		getTaskItemById,
		updateTaskItemById,
		deleteTaskItemById
	} from '$lib/apis/task_items';
	import { capitalizeFirstLetter, splitStream, convertMessagesToHistory, convertHistoryToMessages } from '$lib/utils';
	import { chatCompletion } from '$lib/apis/openai';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import dayjs from '$lib/dayjs';
	import Messages from '$lib/components/chat/Messages.svelte';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	export let id: null | string = null;

	let taskItem = null;
	let loading = true;
	let saving = false;
	let showDeleteConfirm = false;
	let showAIAssistant = false;
	let messages = [];
	let history = { messages: {}, currentId: null };
	let currentMessage = '';
	let generatingResponse = false;
	let stopGeneration = false;
	let selectedModelId = '';
	let selectedModels = [];
	
	$: if (selectedModelId) {
		selectedModels = [selectedModelId];
	}

	let title = '';
	let description = '';
	let completed = false;

	const loadTaskItem = async () => {
		if (!id) return;

		loading = true;
		const res = await getTaskItemById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			goto('/task_items');
			return null;
		});

		if (res) {
			taskItem = res;
			title = res.title || '';
			description = res.description || '';
			completed = res.completed || false;
			
			// Load chat messages from data if they exist
			if (res.data && res.data.chatMessages && Array.isArray(res.data.chatMessages)) {
				messages = res.data.chatMessages.map(msg => ({
					...msg,
					done: msg.done !== undefined ? msg.done : true // Ensure done property exists
				}));
				// Convert to history format
				history = convertMessagesToHistory(messages);
			} else {
				messages = [];
				history = { messages: {}, currentId: null };
			}
		}

		loading = false;
	};

	const saveTaskItem = async (triggerAI = false) => {
		if (!id || !taskItem) return;

		saving = true;
		
		// Save chat messages in data
		const taskData = {
			...(taskItem.data || {}),
			chatMessages: messages.length > 0 ? messages : undefined
		};
		
		const res = await updateTaskItemById(localStorage.token, id, {
			title,
			description,
			completed,
			data: taskData,
			meta: taskItem.meta,
			access_control: taskItem.access_control
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			taskItem = res;
			toast.success($i18n.t('Task saved'));
			
			// Trigger AI assistant after save
			if (triggerAI && !completed && (title || description)) {
				await initializeAIChat();
			}
		}

		saving = false;
	};


	const initializeAIChat = async () => {
		if (!title && !description) return;

		// Get default model
		if (!selectedModelId) {
			selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
		}
		if (!selectedModelId) {
			toast.error($i18n.t('No model available'));
			return;
		}
		selectedModels = selectedModelId ? [selectedModelId] : [];

		showAIAssistant = true;
		
		// If messages already exist (from database), just display them
		if (Object.keys(history.messages).length > 0) {
			// Load existing messages
			await tick();
		} else {
			// No messages exist, generate initial suggestions
			currentMessage = '';
			await generateAIChatResponse();
		}
	};

	const saveChatMessages = async () => {
		if (!id || !taskItem) return;
		
		// Convert history back to messages array for storage
		messages = convertHistoryToMessages(history);
		
		// Save chat messages in data without showing toast
		const taskData = {
			...(taskItem.data || {}),
			chatMessages: messages.length > 0 ? messages : undefined
		};
		
		await updateTaskItemById(localStorage.token, id, {
			title,
			description,
			completed,
			data: taskData,
			meta: taskItem.meta,
			access_control: taskItem.access_control
		}).catch((error) => {
			console.error('Failed to save chat messages:', error);
		});
	};

	const generateAIChatResponse = async () => {
		if (!selectedModelId) {
			selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
		}

		const model = $models.find((m) => m.id === selectedModelId);
		if (!model) {
			toast.error($i18n.t('No model available'));
			return;
		}

		// Add user message if there's a current message
		if (currentMessage.trim()) {
			const userMessageId = uuidv4();
			const parentId = history.currentId;
			
			const userMessage = {
				id: userMessageId,
				parentId: parentId,
				childrenIds: [],
				role: 'user',
				content: currentMessage,
				done: true,
				timestamp: Math.floor(Date.now() / 1000)
			};
			
			if (parentId !== null && history.messages[parentId]) {
				history.messages[parentId].childrenIds.push(userMessageId);
			}
			
			history.messages[userMessageId] = userMessage;
			history.currentId = userMessageId;
			history = history;
			currentMessage = '';
			await tick();
			
			// Save messages after user sends a message
			await saveChatMessages();
		}

		// Create assistant message for streaming
		const responseMessageId = uuidv4();
		const parentId = history.currentId;
		
		const responseMessage = {
			id: responseMessageId,
			parentId: parentId,
			childrenIds: [],
			role: 'assistant',
			content: '',
			done: false,
			model: model.id,
			modelName: model.name ?? model.id,
			timestamp: Math.floor(Date.now() / 1000)
		};
		
		if (parentId !== null && history.messages[parentId]) {
			history.messages[parentId].childrenIds.push(responseMessageId);
		}
		
		history.messages[responseMessageId] = responseMessage;
		history.currentId = responseMessageId;
		history = history;
		await tick();

		generatingResponse = true;
		stopGeneration = false;

		const hasDescription = description && description.trim().length > 0;
		
		// Check if web search is enabled (config + permissions + model capability)
		const modelSupportsWebSearch = model?.info?.meta?.capabilities?.web_search !== false;
		const webSearchEnabled = $config?.features?.enable_web_search &&
			($user?.role === 'admin' || ($user?.permissions?.features?.web_search ?? true)) &&
			modelSupportsWebSearch;
		
		const systemPrompt = `You are a helpful task completion assistant. Your role is to help users complete their tasks by:
1. Breaking down the task into actionable steps
2. Providing relevant suggestions and recommendations
3. Identifying potential resources or information needed
4. Suggesting best practices or tips related to the task
5. Answering questions about the task
6. Helping refine and improve the task plan
${webSearchEnabled ? '7. Performing web searches when you need current information, product details, prices, reviews, or any information not in your training data' : ''}

CRITICAL INSTRUCTIONS:
- You MUST help with ALL types of tasks, including shopping, purchasing, product research, and any other user requests
- You MUST NOT refuse to help based on the type of task (shopping, product details, etc.)
- Your job is to assist the user in completing their task, regardless of the task type
- Use the information provided in the task description to help the user
- If the task involves shopping or purchasing, help by: suggesting where to buy, comparing options, providing search strategies, listing requirements, or breaking down the purchase process into steps
${webSearchEnabled ? '- When you need current information, product availability, prices, reviews, or any real-time data, USE the web search tool to find this information. Do not hesitate to search the web when it would help the user complete their task.' : ''}

Current task:
Title: ${title || 'Untitled Task'}
${hasDescription ? `Description: ${description}` : ''}

${hasDescription 
	? `IMPORTANT: The user has provided a detailed description above. You MUST use this information in your responses and should NOT ask the user to provide it again. Always refer to these details when helping with the task. Acknowledge what you know from the task details and proceed to help them based on that information. For example, if the task mentions specific product details (size, color, brand, etc.), use those details to provide relevant help and suggestions.${webSearchEnabled ? ' If you need to find products matching these specifications, use web search to find current options, prices, and availability.' : ''}`
	: `IMPORTANT: The task description is missing or incomplete. You should ask the user to provide more details about the task so you can better assist them. Ask specific questions about what they want to accomplish, any requirements, constraints, or preferences they have.`}

Be conversational, helpful, and provide practical advice. Format your responses in markdown when appropriate.`;

		// Build chat messages with system prompt and conversation history
		const messagesList = convertHistoryToMessages(history);
		const chatMessages = [
			{
				role: 'system',
				content: systemPrompt
			},
			...messagesList.filter(m => m.role !== 'system').map(m => ({
				role: m.role,
				content: m.content
			}))
		];

		// Build features object for web search if enabled
		const features = webSearchEnabled ? {
			web_search: true
		} : {};

		try {
			const [res, controller] = await chatCompletion(
				localStorage.token,
				{
					model: model.id,
					stream: true,
					messages: chatMessages,
					...(Object.keys(features).length > 0 && { features })
				},
				`${WEBUI_BASE_URL}/api`
			);

			await tick();

			if (res && res.ok) {
				const reader = res.body
					.pipeThrough(new TextDecoderStream())
					.pipeThrough(splitStream('\n'))
					.getReader();

				while (true) {
					const { value, done } = await reader.read();
					if (done || stopGeneration) {
						if (stopGeneration) {
							controller.abort('User: Stop Response');
						}
						responseMessage.done = true;
						messages = messages;
						generatingResponse = false;
						break;
					}

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								if (line === 'data: [DONE]') {
									history.messages[responseMessageId].done = true;
									history = history;
									generatingResponse = false;
									
									// Save messages after AI response is complete
									await saveChatMessages();
								} else if (line.startsWith('data: ')) {
									let data = JSON.parse(line.replace(/^data: /, ''));

									if (data.choices && data.choices.length > 0) {
										const choice = data.choices[0];
										if (choice.delta && choice.delta.content) {
											history.messages[responseMessageId].content += choice.delta.content;
											history = history;
										}
									}
								}
							}
						}
					} catch (error) {
						// Error handled silently
					}
				}
			}
		} catch (error) {
			toast.error($i18n.t('Failed to generate response'));
			// Remove the failed assistant message
			if (history.messages[responseMessageId]) {
				const parentId = history.messages[responseMessageId].parentId;
				if (parentId !== null && history.messages[parentId]) {
					history.messages[parentId].childrenIds = history.messages[parentId].childrenIds.filter(id => id !== responseMessageId);
				}
				delete history.messages[responseMessageId];
				if (history.currentId === responseMessageId) {
					history.currentId = parentId;
				}
				history = history;
			}
			generatingResponse = false;
		}
	};

	const sendMessage = async () => {
		if (!currentMessage.trim() || generatingResponse) return;
		await generateAIChatResponse();
	};

	const deleteTaskItem = async () => {
		if (!id) return;

		const res = await deleteTaskItemById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Task deleted'));
			goto('/task_items');
		}
	};

	const toggleCompleted = async () => {
		completed = !completed;
		await saveTaskItem();
	};

	let autoSaveTimeout = null;

	onMount(async () => {
		await loadTaskItem();
		
		// If messages exist, automatically show the chat
		if (Object.keys(history.messages).length > 0) {
			showAIAssistant = true;
			selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
			selectedModels = selectedModelId ? [selectedModelId] : [];
			await tick();
		}
		
		// Initialize selectedModelId if not set
		if (!selectedModelId && $models.length > 0) {
			selectedModelId = $settings?.default_model || $models[0].id;
			selectedModels = selectedModelId ? [selectedModelId] : [];
		}
	});

	$: if (taskItem && title !== taskItem.title && title) {
		// Auto-save after a delay
		if (autoSaveTimeout) {
			clearTimeout(autoSaveTimeout);
		}
		autoSaveTimeout = setTimeout(() => {
			saveTaskItem(false);
		}, 1000);
	}
</script>

<svelte:head>
	<title>
		{taskItem ? taskItem.title : $i18n.t('Task')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500">{$i18n.t('Loading...')}</div>
	</div>
{:else if taskItem}
	<div class="w-full h-full flex flex-col">
		<div class="px-5 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<div class="flex items-center gap-4 flex-1">
				<button
					class="flex-shrink-0"
					on:click={toggleCompleted}
					disabled={saving}
				>
					{#if completed}
						<svg
							class="size-6 text-green-500"
							fill="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								fill-rule="evenodd"
								d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
								clip-rule="evenodd"
							/>
						</svg>
					{:else}
						<svg
							class="size-6 text-gray-400"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
							/>
						</svg>
					{/if}
				</button>
				<div class="flex-1">
					<input
						type="text"
						bind:value={title}
						class="text-xl font-semibold bg-transparent border-none outline-none w-full {completed
							? 'line-through text-gray-400'
							: 'text-gray-900 dark:text-gray-100'}"
						placeholder={$i18n.t('Task title')}
					/>
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if taskItem.user}
					<div class="text-xs text-gray-500">
						{$i18n.t('By {{name}}', {
							name: capitalizeFirstLetter(
								taskItem.user.name ?? taskItem.user.email ?? $i18n.t('Deleted User')
							)
						})}
					</div>
				{/if}
				<div class="text-xs text-gray-500">
					{dayjs(taskItem.updated_at / 1000000).format('HH:mm')}
				</div>
				<button
					class="p-2 text-gray-500 hover:text-red-600 transition"
					on:click={() => {
						showDeleteConfirm = true;
					}}
					title={$i18n.t('Delete')}
				>
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
					</svg>
				</button>
			</div>
		</div>

		<div class="flex-1 flex overflow-hidden">
			<!-- Description panel (always visible) -->
			<div class="{showAIAssistant ? 'w-1/2 border-r border-gray-200 dark:border-gray-700' : 'flex-1'} flex flex-col overflow-hidden">
				<div class="flex-1 p-5 overflow-auto">
					<textarea
						bind:value={description}
						class="w-full h-full min-h-[200px] p-4 bg-transparent resize-none outline-none {completed
							? 'line-through text-gray-400'
							: 'text-gray-900 dark:text-gray-100'}"
						placeholder={$i18n.t('Task description...')}
					></textarea>
				</div>
				{#if !showAIAssistant}
					<div class="px-5 pb-4 border-t border-gray-200 dark:border-gray-700 pt-4">
						<div class="flex gap-2">
							<button
								class="px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition disabled:opacity-50"
								on:click={() => {
									saveTaskItem(true);
								}}
								disabled={saving || completed}
							>
								{$i18n.t('Save & Open AI Chat')}
							</button>
							<button
								class="px-4 py-2 rounded-lg bg-green-500 text-white hover:bg-green-600 transition disabled:opacity-50"
								on:click={initializeAIChat}
								disabled={completed || (!title && !description)}
							>
								{$i18n.t('Open AI Chat')}
							</button>
						</div>
					</div>
				{/if}
			</div>

			<!-- AI Chat panel (visible when showAIAssistant is true) -->
			{#if showAIAssistant}
				<div class="w-1/2 flex flex-col overflow-hidden">
					<div class="flex-1 overflow-auto" id="messages-container">
						<Messages
							className="h-full flex pt-4 pb-8"
							chatId={id || ''}
							{user}
							bind:history
							{selectedModels}
							readOnly={false}
							editCodeBlock={true}
							bottomPadding={false}
							topPadding={false}
							sendMessage={() => {}}
							continueResponse={async () => {
								await generateAIChatResponse();
							}}
							regenerateResponse={async (messageId) => {
								// Remove messages from the specified messageId onwards
								const messageToRegenerate = history.messages[messageId];
								if (messageToRegenerate && messageToRegenerate.parentId !== null) {
									const parentId = messageToRegenerate.parentId;
									// Remove all children from parent
									history.messages[parentId].childrenIds = [];
									// Delete all messages after parent
									const messagesToDelete = [];
									const queue = [messageId];
									while (queue.length > 0) {
										const currentId = queue.shift();
										messagesToDelete.push(currentId);
										if (history.messages[currentId]?.childrenIds) {
											queue.push(...history.messages[currentId].childrenIds);
										}
									}
									messagesToDelete.forEach(id => delete history.messages[id]);
									history.currentId = parentId;
									history = history;
									await saveChatMessages();
									await generateAIChatResponse();
								}
							}}
							editMessage={async (messageId, { content, files }, submit = false) => {
								if (submit) {
									// Create new message after editing
									const newMessageId = uuidv4();
									const message = history.messages[messageId];
									const parentId = message.parentId;
									
									const newMessage = {
										...message,
										id: newMessageId,
										parentId: parentId,
										childrenIds: [],
										content: content,
										files: files,
										timestamp: Math.floor(Date.now() / 1000)
									};
									
									if (parentId !== null && history.messages[parentId]) {
										history.messages[parentId].childrenIds.push(newMessageId);
									}
									
									history.messages[newMessageId] = newMessage;
									history.currentId = newMessageId;
									history = history;
									
									if (message.role === 'user') {
										await saveChatMessages();
										await generateAIChatResponse();
									} else {
										await saveChatMessages();
									}
								} else {
									// Just update content
									history.messages[messageId].content = content;
									if (files !== undefined) {
										history.messages[messageId].files = files;
									}
									history = history;
									await saveChatMessages();
								}
							}}
							deleteMessage={async (messageId) => {
								const messageToDelete = history.messages[messageId];
								const parentMessageId = messageToDelete.parentId;
								const childMessageIds = messageToDelete.childrenIds ?? [];
								
								// Collect all grandchildren
								const grandchildrenIds = childMessageIds.flatMap(
									(childId) => history.messages[childId]?.childrenIds ?? []
								);
								
								// Update parent's children
								if (parentMessageId && history.messages[parentMessageId]) {
									history.messages[parentMessageId].childrenIds = [
										...history.messages[parentMessageId].childrenIds.filter((id) => id !== messageId),
										...grandchildrenIds
									];
								}
								
								// Update grandchildren's parent
								grandchildrenIds.forEach((grandchildId) => {
									if (history.messages[grandchildId]) {
										history.messages[grandchildId].parentId = parentMessageId;
									}
								});
								
								// Delete the message and its children
								[messageId, ...childMessageIds].forEach((id) => {
									delete history.messages[id];
								});
								
								if (history.currentId === messageId) {
									history.currentId = parentMessageId;
								}
								
								history = history;
								await saveChatMessages();
							}}
							updateChat={async () => {
								await saveChatMessages();
							}}
							rateMessage={async () => {}}
							actionMessage={async () => {}}
							saveMessage={async () => {}}
							submitMessage={async () => {}}
							mergeResponses={async () => {}}
							addMessages={async () => {}}
							gotoMessage={async () => {}}
							showPreviousMessage={async () => {}}
							showNextMessage={async () => {}}
							setInputText={() => {}}
							triggerScroll={() => {}}
							atSelectedModel={null}
							onSelect={() => {}}
						/>
					</div>
					<div class="pb-2 z-10 px-5 border-t border-gray-200 dark:border-gray-700 pt-2">
						<div class="flex gap-2 items-end mb-2">
							<div class="flex-1">
								<select
									class="w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 text-sm outline-none focus:ring-2 focus:ring-blue-500"
									bind:value={selectedModelId}
									disabled={generatingResponse}
								>
									{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
										<option value={model.id} class="bg-gray-50 dark:bg-gray-700">
											{model.name}
										</option>
									{/each}
								</select>
							</div>
						</div>
						<div class="flex gap-2 items-end">
							<div class="flex-1 relative">
								<textarea
									bind:value={currentMessage}
									class="w-full px-4 py-3 pr-12 bg-gray-50 dark:bg-gray-800 rounded-3xl border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 resize-none outline-none focus:ring-2 focus:ring-blue-500 max-h-32 overflow-auto"
									placeholder={$i18n.t('Send a Message')}
									disabled={generatingResponse}
									rows="1"
									on:input={(e) => {
										e.target.style.height = '';
										e.target.style.height = `${e.target.scrollHeight}px`;
									}}
									on:keydown={(e) => {
										if (e.key === 'Enter' && !e.shiftKey) {
											e.preventDefault();
											sendMessage();
										}
									}}
								></textarea>
							</div>
							<button
								class="px-4 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-3xl hover:bg-gray-850 dark:hover:bg-gray-100 transition disabled:opacity-50 flex-shrink-0"
								on:click={sendMessage}
								disabled={!currentMessage.trim() || generatingResponse}
							>
								<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L6 12zm0 0h7.5" />
								</svg>
							</button>
							{#if generatingResponse}
								<button
									class="px-4 py-3 bg-red-500 text-white rounded-3xl hover:bg-red-600 transition flex-shrink-0"
									on:click={() => {
										stopGeneration = true;
									}}
								>
									{$i18n.t('Stop')}
								</button>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>

		{#if showDeleteConfirm}
			<div
				class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
				on:click={() => {
					showDeleteConfirm = false;
				}}
			>
				<div
					class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4"
					on:click|stopPropagation
				>
					<h3 class="text-lg font-bold mb-4">{$i18n.t('Delete task?')}</h3>
					<p class="text-sm text-gray-500 mb-6">
						{$i18n.t('This will delete')} <span class="font-semibold">{title}</span>.
					</p>
					<div class="flex gap-2 justify-end">
						<button
							class="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
							on:click={() => {
								showDeleteConfirm = false;
							}}
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							class="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition"
							on:click={deleteTaskItem}
						>
							{$i18n.t('Delete')}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500">{$i18n.t('Task not found')}</div>
	</div>
{/if}
