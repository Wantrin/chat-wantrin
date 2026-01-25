<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { getOrderById, updateOrderById, getOrderStatusHistory, type OrderStatusHistory } from '$lib/apis/orders';
	import { getDeliveryPersonsByShopId, type DeliveryPerson } from '$lib/apis/delivery_persons';
	import { getAllUsers } from '$lib/apis/users';
	import { showSidebar, models, settings, user, config, socket } from '$lib/stores';
	import Loader from '$lib/components/common/Loader.svelte';
	import { chatCompletion } from '$lib/apis/openai';
	import { splitStream, convertMessagesToHistory, convertHistoryToMessages } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Messages from '$lib/components/chat/Messages.svelte';
	import { v4 as uuidv4 } from 'uuid';
	import { onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let order = null;
	let loading = true;
	let updating = false;
	let selectedStatus = '';
	let trackingNumber = '';
	let carrier = '';
	let trackingUrl = '';
	let estimatedDeliveryDate = '';
	let statusHistory: OrderStatusHistory[] = [];
	let showTrackingForm = false;
	
	// Assignment variables
	let selectedUserId = '';
	let selectedDeliveryPersonId = '';
	let users: any[] = [];
	let deliveryPersons: DeliveryPerson[] = [];
	let loadingUsers = false;
	let loadingDeliveryPersons = false;
	
	// AI Chat variables
	let showAIAssistant = false;
	let messages: any[] = [];
	let history = { messages: {}, currentId: null };
	let currentMessage = '';
	let generatingResponse = false;
	let stopGeneration = false;
	let selectedModelId = '';
	let selectedModels = [];
	
	$: if (selectedModelId) {
		selectedModels = [selectedModelId];
	}

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const formatDate = (timestamp: number) => {
		return new Date(timestamp / 1000000).toLocaleDateString('fr-FR', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const getStatusColor = (status: string) => {
		switch (status) {
			case 'pending':
				return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
			case 'confirmed':
				return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
			case 'processing':
				return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
			case 'shipped':
				return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400';
			case 'delivered':
				return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
			case 'cancelled':
				return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
		}
	};

	const getStatusLabel = (status: string) => {
		const labels = {
			pending: $i18n ? $i18n.t('Pending') : 'Pending',
			confirmed: $i18n ? $i18n.t('Confirmed') : 'Confirmed',
			processing: $i18n ? $i18n.t('Processing') : 'Processing',
			shipped: $i18n ? $i18n.t('Shipped') : 'Shipped',
			delivered: $i18n ? $i18n.t('Delivered') : 'Delivered',
			cancelled: $i18n ? $i18n.t('Cancelled') : 'Cancelled'
		};
		return labels[status] || status;
	};

	const loadData = async () => {
		loading = true;
		try {
			const shopId = $page.params.shopId;
			const orderId = $page.params.orderId;
			const token = typeof window !== 'undefined' ? localStorage.token : '';

			const [shopRes, orderRes] = await Promise.all([
				getShopById(token, shopId),
				getOrderById(token, orderId)
			]);

			if (shopRes) {
				shop = shopRes;
			}
			if (orderRes) {
				order = orderRes;
				selectedStatus = order.status;
				trackingNumber = order.tracking_number || '';
				carrier = order.carrier || '';
				trackingUrl = order.tracking_url || '';
				selectedUserId = order.assigned_user_id || '';
				selectedDeliveryPersonId = order.assigned_delivery_person_id || '';
				if (order.estimated_delivery_date) {
					const date = new Date(order.estimated_delivery_date / 1000000);
					estimatedDeliveryDate = date.toISOString().split('T')[0];
				}
				
				// Load chat messages from meta if they exist
				if (order.meta && order.meta.chatMessages && Array.isArray(order.meta.chatMessages)) {
					messages = order.meta.chatMessages.map(msg => ({
						...msg,
						done: msg.done !== undefined ? msg.done : true
					}));
					// Convert to history format
					history = convertMessagesToHistory(messages);
				} else {
					messages = [];
					history = { messages: {}, currentId: null };
				}
				
				// Load status history
				try {
					statusHistory = await getOrderStatusHistory(token, orderRes.id);
				} catch (error) {
					console.error('Error loading status history:', error);
					statusHistory = [];
				}
				
				// Load users and delivery persons
				loadUsers();
				loadDeliveryPersons();
				
				// Auto-respond if order is newly created (pending status and no chat messages)
				// This triggers when the order is first opened after client submission
				if (order.status === 'pending' && Object.keys(history.messages).length === 0) {
					// Use default model for automatic summary
					selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
					selectedModels = selectedModelId ? [selectedModelId] : [];
					
					// Wait a bit for the UI to render, then auto-open chat and respond
					setTimeout(async () => {
						if (!showAIAssistant) {
							await initializeAIChat();
						}
					}, 500);
				}
			}
		} catch (error) {
			console.error('Error loading data:', error);
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const updateStatus = async () => {
		if (!order || selectedStatus === order.status) return;

		const oldStatus = order.status;
		updating = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const updated = await updateOrderById(token, order.id, {
				status: selectedStatus
			});

			if (updated) {
				order = updated;
				// Reload status history
				statusHistory = await getOrderStatusHistory(token, order.id);
				toast.success($i18n ? $i18n.t('Order updated successfully') : 'Order updated successfully');
				
				// Automatically respond with AI when status changes
				// This includes: new pending orders, or status changes to processing/confirmed
				const shouldAutoRespond = 
					(selectedStatus === 'pending' && Object.keys(history.messages).length === 0) || // New order
					((selectedStatus === 'processing' || selectedStatus === 'confirmed') && oldStatus !== selectedStatus); // Status changed
				
				if (shouldAutoRespond) {
					// Open AI assistant if not already open
					if (!showAIAssistant) {
						await initializeAIChat();
					}
					
					// Use default model for automatic summaries
					selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
					selectedModels = selectedModelId ? [selectedModelId] : [];
					
					// Generate automatic response
					if (selectedStatus === 'pending' && Object.keys(history.messages).length === 0) {
						// New order - request initial summary with complete order info
						const completeOrderInfo = getCompleteOrderInfo(order);
						const notesWarning = order.notes 
							? ($i18n 
								? `\n\n⚠️ ATTENTION: Cette commande contient des notes importantes. Assure-toi de les lire attentivement et de mettre en évidence toute erreur, correction ou demande spéciale mentionnée dans les notes.`
								: `\n\n⚠️ ATTENTION: This order contains important notes. Make sure to read them carefully and highlight any errors, corrections, or special requests mentioned in the notes.`)
							: '';
						currentMessage = $i18n 
							? `Une nouvelle commande vient d'être soumise par le client. Voici toutes les informations de la commande:\n\n${completeOrderInfo}\n\nFais-moi un résumé complet de cette commande et vérifie qu'elle est correcte.${notesWarning}`
							: `A new order has just been submitted by the client. Here is all the order information:\n\n${completeOrderInfo}\n\nGive me a complete summary of this order and verify that it is correct.${notesWarning}`;
						await generateAIChatResponse();
					} else if ((selectedStatus === 'processing' || selectedStatus === 'confirmed') && oldStatus !== selectedStatus) {
						// Status changed - request updated summary with complete order info
						const messagesList = convertHistoryToMessages(history);
						const completeOrderInfo = getCompleteOrderInfo(order);
						const notesWarning = order.notes 
							? ($i18n 
								? `\n\n⚠️ ATTENTION: Cette commande contient des notes importantes. Assure-toi de les lire attentivement et de mettre en évidence toute erreur, correction ou demande spéciale mentionnée dans les notes.`
								: `\n\n⚠️ ATTENTION: This order contains important notes. Make sure to read them carefully and highlight any errors, corrections, or special requests mentioned in the notes.`)
							: '';
						if (messagesList.length === 0 || (messagesList.length === 1 && messagesList[0].role === 'assistant' && !messagesList[0].done)) {
							currentMessage = $i18n 
								? `La commande vient de passer au statut "${getStatusLabel(selectedStatus)}". Voici toutes les informations actuelles de la commande:\n\n${completeOrderInfo}\n\nFais-moi un résumé complet de cette commande et vérifie qu'elle est correcte.${notesWarning}`
								: `The order has just been updated to "${getStatusLabel(selectedStatus)}" status. Here is all the current order information:\n\n${completeOrderInfo}\n\nGive me a complete summary of this order and verify that it is correct.${notesWarning}`;
							await generateAIChatResponse();
						} else {
							currentMessage = $i18n
								? `La commande vient de passer au statut "${getStatusLabel(selectedStatus)}". Voici toutes les informations actuelles de la commande:\n\n${completeOrderInfo}\n\nPeux-tu me donner un résumé de l'état actuel de la commande ?${notesWarning}`
								: `The order has just been updated to "${getStatusLabel(selectedStatus)}" status. Here is all the current order information:\n\n${completeOrderInfo}\n\nCan you give me a summary of the current order status?${notesWarning}`;
							await generateAIChatResponse();
						}
					}
				}
			}
		} catch (error) {
			console.error('Error updating order:', error);
			toast.error(`${error}`);
		} finally {
			updating = false;
		}
	};

	const loadUsers = async () => {
		loadingUsers = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const usersRes = await getAllUsers(token);
			if (usersRes && usersRes.items) {
				users = usersRes.items;
			}
		} catch (error) {
			console.error('Error loading users:', error);
			users = [];
		} finally {
			loadingUsers = false;
		}
	};

	const loadDeliveryPersons = async () => {
		if (!shop) return;
		loadingDeliveryPersons = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const deliveryPersonsRes = await getDeliveryPersonsByShopId(token, shop.id, false);
			if (deliveryPersonsRes) {
				deliveryPersons = deliveryPersonsRes;
			}
		} catch (error) {
			console.error('Error loading delivery persons:', error);
			deliveryPersons = [];
		} finally {
			loadingDeliveryPersons = false;
		}
	};

	const updateTracking = async () => {
		if (!order) return;

		updating = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const updates: any = {
				tracking_number: trackingNumber || undefined,
				carrier: carrier || undefined,
				tracking_url: trackingUrl || undefined
			};
			
			if (estimatedDeliveryDate) {
				updates.estimated_delivery_date = new Date(estimatedDeliveryDate).getTime() * 1000000;
			}
			
			const updated = await updateOrderById(token, order.id, updates);

			if (updated) {
				order = updated;
				showTrackingForm = false;
				toast.success($i18n ? $i18n.t('Tracking information updated successfully') : 'Tracking information updated successfully');
			}
		} catch (error) {
			console.error('Error updating tracking:', error);
			toast.error(`${error}`);
		} finally {
			updating = false;
		}
	};

	const updateAssignments = async () => {
		if (!order) return;

		updating = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const updated = await updateOrderById(token, order.id, {
				assigned_user_id: selectedUserId || undefined,
				assigned_delivery_person_id: selectedDeliveryPersonId || undefined
			});

			if (updated) {
				order = updated;
				toast.success($i18n ? $i18n.t('Assignments updated successfully') : 'Assignments updated successfully');
			}
		} catch (error) {
			console.error('Error updating assignments:', error);
			toast.error(`${error}`);
		} finally {
			updating = false;
		}
	};


	// Helper function to generate complete order information string
	const getCompleteOrderInfo = (order) => {
		const itemsSummary = order.items.map(item => 
			`- ${item.name} x${item.quantity} (${item.price} ${item.currency} each) - Total: ${item.price * item.quantity} ${item.currency}`
		).join('\n');
		
		const shippingAddressStr = [
			order.shipping_address.street,
			`${order.shipping_address.postal_code} ${order.shipping_address.city}`,
			order.shipping_address.state,
			order.shipping_address.country
		].filter(Boolean).join(', ');

		return `Order ID: ${order.id}
Status: ${order.status}
Customer Name: ${order.customer_name}
Customer Email: ${order.customer_email}
${order.customer_phone ? `Customer Phone: ${order.customer_phone}` : ''}

ITEMS ORDERED:
${itemsSummary}

SHIPPING ADDRESS:
${shippingAddressStr}

FINANCIAL DETAILS:
- Subtotal: ${order.subtotal} ${order.currency}
- Shipping Cost: ${order.shipping_cost} ${order.currency}
- Total: ${order.total} ${order.currency}

${order.tracking_number ? `TRACKING NUMBER: ${order.tracking_number}` : ''}
${order.carrier ? `CARRIER: ${order.carrier}` : ''}
${order.tracking_url ? `TRACKING URL: ${order.tracking_url}` : ''}
${order.assigned_user_id ? `ASSIGNED USER ID: ${order.assigned_user_id}` : ''}
${order.assigned_delivery_person_id ? `ASSIGNED DELIVERY PERSON ID: ${order.assigned_delivery_person_id}` : ''}
${order.notes ? `⚠️ NOTES (IMPORTANT - READ CAREFULLY): ${order.notes}` : ''}
${order.created_at ? `CREATED AT: ${formatDate(order.created_at)}` : ''}
${order.updated_at ? `UPDATED AT: ${formatDate(order.updated_at)}` : ''}
${order.shipped_at ? `SHIPPED AT: ${formatDate(order.shipped_at)}` : ''}
${order.delivered_at ? `DELIVERED AT: ${formatDate(order.delivered_at)}` : ''}
${order.estimated_delivery_date ? `ESTIMATED DELIVERY: ${formatDate(order.estimated_delivery_date)}` : ''}`;
	};

	const initializeAIChat = async () => {
		if (!order) return;

		// Always use default model for automatic summaries
		selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
		if (!selectedModelId) {
			toast.error($i18n ? $i18n.t('No model available') : 'No model available');
			return;
		}
		selectedModels = selectedModelId ? [selectedModelId] : [];

		showAIAssistant = true;
		
		// If messages already exist (from database), just display them
		if (Object.keys(history.messages).length > 0) {
			// Load existing messages
			await tick();
		} else {
			// No messages exist, generate initial summary with complete order context
			const completeOrderInfo = getCompleteOrderInfo(order);
			const notesWarning = order.notes 
				? ($i18n 
					? `\n\n⚠️ ATTENTION: Cette commande contient des notes importantes. Assure-toi de les lire attentivement et de mettre en évidence toute erreur, correction ou demande spéciale mentionnée dans les notes.`
					: `\n\n⚠️ ATTENTION: This order contains important notes. Make sure to read them carefully and highlight any errors, corrections, or special requests mentioned in the notes.`)
				: '';
			currentMessage = $i18n 
				? `Voici les informations de la commande que j'ai dans mon système:\n\n${completeOrderInfo}\n\nFais-moi un résumé complet de cette commande et vérifie qu'elle est correcte.${notesWarning}`
				: `Here is the complete order information I have in my system:\n\n${completeOrderInfo}\n\nGive me a complete summary of this order and verify that it is correct.${notesWarning}`;
			await generateAIChatResponse();
		}
	};

	let scrollTimeout = null;
	const scrollToBottom = () => {
		// Debounce scroll to avoid too many calls during streaming
		if (scrollTimeout) {
			clearTimeout(scrollTimeout);
		}
		scrollTimeout = setTimeout(() => {
			const element = document.getElementById('messages-container');
			if (element) {
				element.scrollTop = element.scrollHeight;
			}
		}, 50);
	};

	const saveChatMessages = async () => {
		if (!order) return;
		
		// Convert history back to messages array for storage
		messages = convertHistoryToMessages(history);
		
		// Save chat messages in meta without showing toast
		const orderMeta = {
			...(order.meta || {}),
			chatMessages: messages.length > 0 ? messages : undefined
		};
		
		const token = typeof window !== 'undefined' ? localStorage.token : '';
		await updateOrderById(token, order.id, {
			meta: orderMeta
		}).catch((error) => {
			console.error('Failed to save chat messages:', error);
		});
	};

	const generateAIChatResponse = async () => {
		if (!order) return;
		
		// Use default model if not explicitly selected
		if (!selectedModelId) {
			selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
			selectedModels = selectedModelId ? [selectedModelId] : [];
		}

		const model = $models.find((m) => m.id === selectedModelId);
		if (!model) {
			toast.error($i18n ? $i18n.t('No model available') : 'No model available');
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
			
			// Scroll to show the new message immediately
			const element = document.getElementById('messages-container');
			if (element) {
				element.scrollTop = element.scrollHeight;
			}
			
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
		
		// Scroll to show the new message immediately
		const element = document.getElementById('messages-container');
		if (element) {
			element.scrollTop = element.scrollHeight;
		}

		generatingResponse = true;
		stopGeneration = false;

		// Build complete order information using helper function
		const itemsSummary = order.items.map(item => 
			`- ${item.name} x${item.quantity} (${item.price} ${item.currency} each) - Total: ${item.price * item.quantity} ${item.currency}`
		).join('\n');
		
		const shippingAddressStr = [
			order.shipping_address.street,
			`${order.shipping_address.postal_code} ${order.shipping_address.city}`,
			order.shipping_address.state,
			order.shipping_address.country
		].filter(Boolean).join(', ');

		// Check if web search is enabled
		const modelSupportsWebSearch = model?.info?.meta?.capabilities?.web_search !== false;
		const webSearchEnabled = $config?.features?.enable_web_search &&
			($user?.role === 'admin' || ($user?.permissions?.features?.web_search ?? true)) &&
			modelSupportsWebSearch;
		
		// Build complete order information with all details
		const orderInfo = `=== COMPLETE ORDER INFORMATION (YOU HAVE ACCESS TO ALL OF THIS) ===
Order ID: ${order.id}
Status: ${order.status}
Customer Name: ${order.customer_name}
Customer Email: ${order.customer_email}
${order.customer_phone ? `Customer Phone: ${order.customer_phone}` : ''}

ITEMS ORDERED:
${itemsSummary}

SHIPPING ADDRESS:
${shippingAddressStr}

FINANCIAL DETAILS:
- Subtotal: ${order.subtotal} ${order.currency}
- Shipping Cost: ${order.shipping_cost} ${order.currency}
- Total: ${order.total} ${order.currency}

${order.tracking_number ? `TRACKING NUMBER: ${order.tracking_number}` : ''}
${order.carrier ? `CARRIER: ${order.carrier}` : ''}
${order.tracking_url ? `TRACKING URL: ${order.tracking_url}` : ''}
${order.assigned_user_id ? `ASSIGNED USER ID: ${order.assigned_user_id}` : ''}
${order.assigned_delivery_person_id ? `ASSIGNED DELIVERY PERSON ID: ${order.assigned_delivery_person_id}` : ''}
${order.notes ? `⚠️ NOTES (IMPORTANT - READ CAREFULLY): ${order.notes}` : ''}
${order.created_at ? `CREATED AT: ${formatDate(order.created_at)}` : ''}
${order.updated_at ? `UPDATED AT: ${formatDate(order.updated_at)}` : ''}
${order.shipped_at ? `SHIPPED AT: ${formatDate(order.shipped_at)}` : ''}
${order.delivered_at ? `DELIVERED AT: ${formatDate(order.delivered_at)}` : ''}
${order.estimated_delivery_date ? `ESTIMATED DELIVERY: ${formatDate(order.estimated_delivery_date)}` : ''}
=== END OF ORDER INFORMATION ===`;

		const systemPrompt = `You are a helpful assistant with access to order data. You can see the complete order information below. Use this information to answer questions.

${orderInfo}

YOUR ROLE: You are an assistant helping an agent review order information. You have complete access to the order data shown above.

CRITICAL INSTRUCTIONS:
1. You have the order information above - use it to answer questions
2. When asked about the order, provide details from the information above
3. If asked about products, items, customer, or shipping - use the data above
4. Do NOT say you cannot help - you can help by using the information above
5. Do NOT ask for information - you already have it in the data above
6. Be helpful and provide complete information from the order data above
7. If the user mentions "${order.items[0]?.name || 'a product'}" or any item, you can see it in the order data above
8. **PAY SPECIAL ATTENTION TO NOTES** - If there are notes in the order, they may contain important information like errors, corrections, special requests, or customer concerns. Always highlight these prominently in your summary.
9. **DETECT ERRORS AND ISSUES** - If notes mention errors (like wrong quantities, wrong items, mistakes), highlight them clearly and suggest what action should be taken.
10. **PRIORITIZE IMPORTANT INFORMATION** - Put critical information (errors, corrections, urgent requests) at the top or in a clearly marked section.

EXAMPLE RESPONSE when asked about the order:
"Based on the order information I have access to:

**Order #${order.id.slice(0, 8)}**
- **Status:** ${order.status}
- **Customer:** ${order.customer_name} (${order.customer_email})${order.customer_phone ? ` - ${order.customer_phone}` : ''}
- **Items:**
${order.items.map(i => `  - ${i.name} x${i.quantity} - ${i.price * i.quantity} ${i.currency}`).join('\n')}
- **Shipping:** ${shippingAddressStr}
- **Total:** ${order.total} ${order.currency}
${order.tracking_number ? `- **Tracking:** ${order.tracking_number}${order.carrier ? ` (${order.carrier})` : ''}` : ''}
${order.notes ? `- **Notes:** ${order.notes}` : ''}

[Add any observations or recommendations]"

${order.notes ? `⚠️ IMPORTANT: This order has notes that may contain important information, errors, or special requests. Always read and highlight the notes prominently in your response. If the notes mention any errors or corrections needed, make sure to:
- Clearly state what the error or issue is
- Explain what needs to be corrected
- Suggest the appropriate action to take
- Put this information in a prominent position in your summary` : ''}

IMPORTANT: The order data above contains all the information. When the user asks about "${order.items[0]?.name || 'products'}" or the order, use the data above. You have this information - do not ask for it.

You can:
- Summarize the order using the data above
- Answer questions about items, customer, shipping, totals
- Provide recommendations based on the order data
- Highlight errors, corrections, or special requests mentioned in notes
${webSearchEnabled ? '- Search for additional shipping information if needed' : ''}

Remember: Always check and highlight the notes if they exist, especially if they mention errors or corrections needed.`;

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
						if (history.messages[responseMessageId]) {
							history.messages[responseMessageId].done = true;
							history = history;
						}
						generatingResponse = false;
						break;
					}

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								if (line === 'data: [DONE]') {
									if (history.messages[responseMessageId]) {
										history.messages[responseMessageId].done = true;
										history = history;
									}
									generatingResponse = false;
									
									// Save messages after AI response is complete
									await saveChatMessages();
									
									// Scroll to bottom immediately when done
									await tick();
									const element = document.getElementById('messages-container');
									if (element) {
										element.scrollTop = element.scrollHeight;
									}
								} else if (line.startsWith('data: ')) {
									let data = JSON.parse(line.replace(/^data: /, ''));

									if (data.choices && data.choices.length > 0) {
										const choice = data.choices[0];
										if (choice.delta && choice.delta.content) {
											if (history.messages[responseMessageId]) {
												history.messages[responseMessageId].content += choice.delta.content;
												history = history;
												
												// Scroll to bottom during streaming (debounced)
												scrollToBottom();
											}
										}
									}
								}
							}
						}
					} catch (error) {
						console.error('Error parsing stream:', error);
					}
				}
			}
		} catch (error) {
			console.error('Error generating response:', error);
			toast.error($i18n ? $i18n.t('Failed to generate response') : 'Failed to generate response');
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

	const handleOrderEvent = async (orderData: any) => {
		// Check if this event is for the current order
		if (!order || orderData.id !== order.id) return;
		
		const oldStatus = order.status;
		const newStatus = orderData.status;
		
		// Update order data
		order = orderData;
		selectedStatus = newStatus;
		
		// Auto-respond for new orders (pending status) or status changes to processing/confirmed
		const shouldAutoRespond = 
			(newStatus === 'pending' && Object.keys(history.messages).length === 0) || // New order submitted by client
			((newStatus === 'processing' || newStatus === 'confirmed') && oldStatus !== newStatus); // Status changed
		
		if (shouldAutoRespond) {
			// Use default model for automatic summaries
			selectedModelId = $settings?.default_model || ($models.length > 0 ? $models[0].id : '');
			selectedModels = selectedModelId ? [selectedModelId] : [];
			
			// Open AI assistant if not already open
			if (!showAIAssistant) {
				await initializeAIChat();
			}
			
			// Generate automatic response with complete order info
			if (newStatus === 'pending' && Object.keys(history.messages).length === 0) {
				// New order - request initial summary with complete order info
				const completeOrderInfo = getCompleteOrderInfo(order);
				const notesWarning = order.notes 
					? ($i18n 
						? `\n\n⚠️ ATTENTION: Cette commande contient des notes importantes. Assure-toi de les lire attentivement et de mettre en évidence toute erreur, correction ou demande spéciale mentionnée dans les notes.`
						: `\n\n⚠️ ATTENTION: This order contains important notes. Make sure to read them carefully and highlight any errors, corrections, or special requests mentioned in the notes.`)
					: '';
				currentMessage = $i18n 
					? `Une nouvelle commande vient d'être soumise par le client. Voici toutes les informations de la commande:\n\n${completeOrderInfo}\n\nFais-moi un résumé complet de cette commande et vérifie qu'elle est correcte.${notesWarning}`
					: `A new order has just been submitted by the client. Here is all the order information:\n\n${completeOrderInfo}\n\nGive me a complete summary of this order and verify that it is correct.${notesWarning}`;
				await generateAIChatResponse();
			} else if ((newStatus === 'processing' || newStatus === 'confirmed') && oldStatus !== newStatus) {
				// Status changed - request updated summary with complete order info
				const messagesList = convertHistoryToMessages(history);
				const completeOrderInfo = getCompleteOrderInfo(order);
				const notesWarning = order.notes 
					? ($i18n 
						? `\n\n⚠️ ATTENTION: Cette commande contient des notes importantes. Assure-toi de les lire attentivement et de mettre en évidence toute erreur, correction ou demande spéciale mentionnée dans les notes.`
						: `\n\n⚠️ ATTENTION: This order contains important notes. Make sure to read them carefully and highlight any errors, corrections, or special requests mentioned in the notes.`)
					: '';
				if (messagesList.length === 0 || (messagesList.length === 1 && messagesList[0].role === 'assistant' && !messagesList[0].done)) {
					currentMessage = $i18n 
						? `La commande vient de passer au statut "${getStatusLabel(newStatus)}". Voici toutes les informations actuelles de la commande:\n\n${completeOrderInfo}\n\nFais-moi un résumé complet de cette commande et vérifie qu'elle est correcte.${notesWarning}`
						: `The order has just been updated to "${getStatusLabel(newStatus)}" status. Here is all the current order information:\n\n${completeOrderInfo}\n\nGive me a complete summary of this order and verify that it is correct.${notesWarning}`;
					await generateAIChatResponse();
				} else {
					currentMessage = $i18n
						? `La commande vient de passer au statut "${getStatusLabel(newStatus)}". Voici toutes les informations actuelles de la commande:\n\n${completeOrderInfo}\n\nPeux-tu me donner un résumé de l'état actuel de la commande ?${notesWarning}`
						: `The order has just been updated to "${getStatusLabel(newStatus)}" status. Here is all the current order information:\n\n${completeOrderInfo}\n\nCan you give me a summary of the current order status?${notesWarning}`;
					await generateAIChatResponse();
				}
			}
		}
	};

	onMount(async () => {
		await loadData();
		
		// Listen for order events via socket
		if ($socket && order) {
			$socket.on('order-events', handleOrderEvent);
			// Join the shop room to receive order events
			$socket.emit('join', `shop:${order.shop_id}`);
		}
		
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

	onDestroy(() => {
		// Clean up socket listener
		if ($socket) {
			$socket.off('order-events', handleOrderEvent);
		}
	});
</script>

<svelte:head>
	<title>{order ? `Order #${order.id.slice(0, 8)}` : 'Order'} • {$i18n ? $i18n.t('Order Details') : 'Order Details'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<Loader />
	</div>
{:else if shop && order}
	<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full">
		<div class="px-5 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{$i18n ? $i18n.t('Order Details') : 'Order Details'} - #{order.id.slice(0, 8)}
				</h1>
			</div>
			<a
				href="/shops/{shop.id}/orders"
				class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
			>
				← {$i18n ? $i18n.t('Back to Orders') : 'Back to Orders'}
			</a>
		</div>

		<div class="flex-1 flex overflow-hidden">
			<!-- Order Information panel -->
			<div class="{showAIAssistant ? 'w-1/2 border-r border-gray-200 dark:border-gray-700' : 'flex-1'} flex flex-col overflow-hidden">
				<div class="flex-1 overflow-auto p-5">
					<div class="max-w-4xl mx-auto space-y-6">
				<!-- Status Update Section -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Update Status') : 'Update Status'}
					</h2>
					<div class="flex items-center gap-4">
						<select
							bind:value={selectedStatus}
							disabled={updating}
							class="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
						>
							<option value="pending">{$i18n ? $i18n.t('Pending') : 'Pending'}</option>
							<option value="confirmed">{$i18n ? $i18n.t('Confirmed') : 'Confirmed'}</option>
							<option value="processing">{$i18n ? $i18n.t('Processing') : 'Processing'}</option>
							<option value="shipped">{$i18n ? $i18n.t('Shipped') : 'Shipped'}</option>
							<option value="delivered">{$i18n ? $i18n.t('Delivered') : 'Delivered'}</option>
							<option value="cancelled">{$i18n ? $i18n.t('Cancelled') : 'Cancelled'}</option>
						</select>
						<button
							on:click={updateStatus}
							disabled={updating || selectedStatus === order.status}
							class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{updating
								? ($i18n ? $i18n.t('Updating...') : 'Updating...')
								: ($i18n ? $i18n.t('Update') : 'Update')}
						</button>
					</div>
					<div class="mt-4">
						<span
							class="inline-block px-3 py-1 rounded-full text-sm font-medium {getStatusColor(order.status)}"
						>
							{getStatusLabel(order.status)}
						</span>
					</div>
				</div>

				<!-- Delivery Tracking Section -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
					<div class="flex items-center justify-between mb-4">
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
							{$i18n ? $i18n.t('Delivery Tracking') : 'Delivery Tracking'}
						</h2>
						<button
							on:click={() => {
								showTrackingForm = !showTrackingForm;
							}}
							class="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
						>
							{showTrackingForm
								? ($i18n ? $i18n.t('Cancel') : 'Cancel')
								: ($i18n ? $i18n.t('Edit Tracking') : 'Edit Tracking')}
						</button>
					</div>

					{#if showTrackingForm}
						<div class="space-y-4">
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n ? $i18n.t('Tracking Number') : 'Tracking Number'}
								</label>
								<input
									type="text"
									bind:value={trackingNumber}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									placeholder="1234567890"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n ? $i18n.t('Carrier') : 'Carrier'}
								</label>
								<input
									type="text"
									bind:value={carrier}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									placeholder="Colissimo, Chronopost, DHL, etc."
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n ? $i18n.t('Tracking URL') : 'Tracking URL'}
								</label>
								<input
									type="url"
									bind:value={trackingUrl}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									placeholder="https://..."
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									{$i18n ? $i18n.t('Estimated Delivery Date') : 'Estimated Delivery Date'}
								</label>
								<input
									type="date"
									bind:value={estimatedDeliveryDate}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								/>
							</div>
							<button
								on:click={updateTracking}
								disabled={updating}
								class="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{updating
									? ($i18n ? $i18n.t('Saving...') : 'Saving...')
									: ($i18n ? $i18n.t('Save Tracking Information') : 'Save Tracking Information')}
							</button>
						</div>
					{:else}
						<div class="space-y-3">
							{#if order.tracking_number}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Tracking Number') : 'Tracking Number'}:</strong>
									<span class="ml-2 text-gray-600 dark:text-gray-400 font-mono">{order.tracking_number}</span>
								</div>
							{/if}
							{#if order.carrier}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Carrier') : 'Carrier'}:</strong>
									<span class="ml-2 text-gray-600 dark:text-gray-400">{order.carrier}</span>
								</div>
							{/if}
							{#if order.tracking_url}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Tracking URL') : 'Tracking URL'}:</strong>
									<a
										href={order.tracking_url}
										target="_blank"
										rel="noopener noreferrer"
										class="ml-2 text-blue-600 dark:text-blue-400 hover:underline"
									>
										{$i18n ? $i18n.t('Track Package') : 'Track Package'}
									</a>
								</div>
							{/if}
							{#if order.shipped_at}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Shipped At') : 'Shipped At'}:</strong>
									<span class="ml-2 text-gray-600 dark:text-gray-400">{formatDate(order.shipped_at)}</span>
								</div>
							{/if}
							{#if order.estimated_delivery_date}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Estimated Delivery') : 'Estimated Delivery'}:</strong>
									<span class="ml-2 text-gray-600 dark:text-gray-400">{formatDate(order.estimated_delivery_date)}</span>
								</div>
							{/if}
							{#if order.delivered_at}
								<div>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Delivered At') : 'Delivered At'}:</strong>
									<span class="ml-2 text-gray-600 dark:text-gray-400">{formatDate(order.delivered_at)}</span>
								</div>
							{/if}
							{#if !order.tracking_number && !order.carrier && !order.tracking_url}
								<p class="text-gray-500 dark:text-gray-400 text-sm">
									{$i18n ? $i18n.t('No tracking information available') : 'No tracking information available'}
								</p>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Delivery Assignment Section -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Delivery Assignment') : 'Delivery Assignment'}
					</h2>
					<div class="space-y-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n ? $i18n.t('Assigned User') : 'Assigned User'}
								<span class="text-xs text-gray-500 dark:text-gray-400 ml-1">
									({$i18n ? $i18n.t('User managing this delivery') : 'User managing this delivery'})
								</span>
							</label>
							<select
								bind:value={selectedUserId}
								disabled={updating || loadingUsers}
								class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
							>
								<option value="">{$i18n ? $i18n.t('No user assigned') : 'No user assigned'}</option>
								{#if loadingUsers}
									<option disabled>{$i18n ? $i18n.t('Loading users...') : 'Loading users...'}</option>
								{:else}
									{#each users as user}
										<option value={user.id}>
											{user.name || user.email} {user.role === 'admin' ? '(Admin)' : ''}
										</option>
									{/each}
								{/if}
							</select>
							{#if order.assigned_user_id}
								<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									{$i18n ? $i18n.t('Currently assigned') : 'Currently assigned'}: {users.find(u => u.id === order.assigned_user_id)?.name || users.find(u => u.id === order.assigned_user_id)?.email || order.assigned_user_id}
								</p>
							{/if}
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n ? $i18n.t('Assigned Delivery Person') : 'Assigned Delivery Person'}
								<span class="text-xs text-gray-500 dark:text-gray-400 ml-1">
									({$i18n ? $i18n.t('Person delivering this order') : 'Person delivering this order'})
								</span>
							</label>
							<select
								bind:value={selectedDeliveryPersonId}
								disabled={updating || loadingDeliveryPersons}
								class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
							>
								<option value="">{$i18n ? $i18n.t('No delivery person assigned') : 'No delivery person assigned'}</option>
								{#if loadingDeliveryPersons}
									<option disabled>{$i18n ? $i18n.t('Loading delivery persons...') : 'Loading delivery persons...'}</option>
								{:else}
									{#each deliveryPersons as dp}
										<option value={dp.id}>
											{dp.name} {dp.vehicle_type ? `(${dp.vehicle_type})` : ''} {!dp.is_active ? ' - ' + ($i18n ? $i18n.t('Inactive') : 'Inactive') : ''}
										</option>
									{/each}
								{/if}
							</select>
							{#if order.assigned_delivery_person_id}
								<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
									{$i18n ? $i18n.t('Currently assigned') : 'Currently assigned'}: {deliveryPersons.find(dp => dp.id === order.assigned_delivery_person_id)?.name || order.assigned_delivery_person_id}
								</p>
							{/if}
						</div>

						<button
							on:click={updateAssignments}
							disabled={updating || (selectedUserId === (order?.assigned_user_id || '') && selectedDeliveryPersonId === (order?.assigned_delivery_person_id || ''))}
							class="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{updating
								? ($i18n ? $i18n.t('Saving...') : 'Saving...')
								: ($i18n ? $i18n.t('Update Assignments') : 'Update Assignments')}
						</button>
					</div>
				</div>

				<!-- Status History -->
				{#if statusHistory.length > 0}
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n ? $i18n.t('Status History') : 'Status History'}
						</h2>
						<div class="space-y-3">
							{#each statusHistory as history}
								<div class="flex items-start gap-3 pb-3 border-b border-gray-200 dark:border-gray-700 last:border-0">
									<div class="flex-1">
										<div class="flex items-center gap-2 mb-1">
											<span class="px-2 py-1 rounded text-xs font-medium {getStatusColor(history.status)}">
												{getStatusLabel(history.status)}
											</span>
											<span class="text-xs text-gray-500 dark:text-gray-400">
												{formatDate(history.created_at)}
											</span>
										</div>
										{#if history.notes}
											<p class="text-sm text-gray-600 dark:text-gray-400">{history.notes}</p>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Order Information -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n ? $i18n.t('Customer Information') : 'Customer Information'}
						</h3>
						<div class="space-y-2 text-gray-600 dark:text-gray-400">
							<p>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Name') : 'Name'}:</strong> {order.customer_name}
							</p>
							<p>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Email') : 'Email'}:</strong> {order.customer_email}
							</p>
							{#if order.customer_phone}
								<p>
									<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Phone') : 'Phone'}:</strong> {order.customer_phone}
								</p>
							{/if}
						</div>
					</div>

					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n ? $i18n.t('Shipping Address') : 'Shipping Address'}
						</h3>
						<div class="space-y-1 text-gray-600 dark:text-gray-400">
							<p>{order.shipping_address.street}</p>
							<p>
								{order.shipping_address.postal_code} {order.shipping_address.city}
							</p>
							{#if order.shipping_address.state}
								<p>{order.shipping_address.state}</p>
							{/if}
							<p>{order.shipping_address.country}</p>
						</div>
					</div>
				</div>

				<!-- Order Items -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Order Items') : 'Order Items'}
					</h3>
					<div class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each order.items as item}
							<div class="py-4 flex justify-between items-center">
								<div>
									<p class="font-medium text-gray-900 dark:text-gray-100">{item.name}</p>
									<p class="text-sm text-gray-600 dark:text-gray-400">
										{$i18n ? $i18n.t('Quantity') : 'Quantity'}: {item.quantity}
									</p>
								</div>
								<p class="font-semibold text-gray-900 dark:text-gray-100">
									{formatPrice(item.price * item.quantity, item.currency)}
								</p>
							</div>
						{/each}
					</div>

					<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700 space-y-2">
						<div class="flex justify-between text-gray-600 dark:text-gray-400">
							<span>{$i18n ? $i18n.t('Subtotal') : 'Subtotal'}</span>
							<span>{formatPrice(order.subtotal, order.currency)}</span>
						</div>
						<div class="flex justify-between text-gray-600 dark:text-gray-400">
							<span>{$i18n ? $i18n.t('Shipping') : 'Shipping'}</span>
							<span>{formatPrice(order.shipping_cost, order.currency)}</span>
						</div>
						<div
							class="flex justify-between text-lg font-bold text-gray-900 dark:text-gray-100 pt-2 border-t border-gray-200 dark:border-gray-700"
						>
							<span>{$i18n ? $i18n.t('Total') : 'Total'}</span>
							<span>{formatPrice(order.total, order.currency)}</span>
						</div>
					</div>
				</div>

				<!-- Order Notes -->
				{#if order.notes}
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
							{$i18n ? $i18n.t('Order Notes') : 'Order Notes'}
						</h3>
						<p class="text-gray-600 dark:text-gray-400 whitespace-pre-line">{order.notes}</p>
					</div>
				{/if}

				<!-- Order Metadata -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Order Information') : 'Order Information'}
					</h3>
					<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
						<p>
							<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Order ID') : 'Order ID'}:</strong> {order.id}
						</p>
						<p>
							<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Created At') : 'Created At'}:</strong> {formatDate(order.created_at)}
						</p>
						<p>
							<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Updated At') : 'Updated At'}:</strong> {formatDate(order.updated_at)}
						</p>
					</div>
				</div>
					</div>
				</div>
				{#if !showAIAssistant}
					<div class="px-5 pb-4 border-t border-gray-200 dark:border-gray-700 pt-4">
						<button
							class="w-full px-4 py-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition disabled:opacity-50"
							on:click={initializeAIChat}
							disabled={!order}
						>
							{$i18n ? $i18n.t('Open AI Assistant') : 'Open AI Assistant'}
						</button>
					</div>
				{/if}
			</div>

			<!-- AI Chat panel (visible when showAIAssistant is true) -->
			{#if showAIAssistant}
				<div class="w-1/2 flex flex-col overflow-hidden">
					<div class="flex-1 overflow-auto" id="messages-container">
						<Messages
							className="h-full flex pt-4 pb-8"
							chatId={order?.id || ''}
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
									placeholder={$i18n ? $i18n.t('Send a Message') : 'Send a Message'}
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
									{$i18n ? $i18n.t('Stop') : 'Stop'}
								</button>
							{/if}
							<button
								class="px-4 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-3xl hover:bg-gray-300 dark:hover:bg-gray-600 transition flex-shrink-0"
								on:click={() => {
									showAIAssistant = false;
								}}
								title={$i18n ? $i18n.t('Close AI Assistant') : 'Close AI Assistant'}
							>
								<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
