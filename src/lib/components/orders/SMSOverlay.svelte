<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { sendSMS, type SMSForm } from '$lib/apis/orders';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let order: any;
	export let deliveryPerson: any | null = null;
	export let sendTo: 'customer' | 'delivery_person' | 'both' = 'customer';
	export let onClose: () => void;
	export let onSent: () => void;

	let message = '';
	let sending = false;
	let sent = false;
	let smsResponse: any = null;

	function getStatusMessage(status: string): string {
		const statusMap: Record<string, string> = {
			'pending': 'en attente',
			'confirmed': 'confirmée',
			'processing': 'en préparation',
			'shipped': 'expédiée',
			'delivered': 'livrée',
			'cancelled': 'annulée'
		};
		return statusMap[status] || status;
	}

	function getStatusLabel(status: string): string {
		const statusMap: Record<string, string> = {
			'pending': 'En attente',
			'confirmed': 'Confirmée',
			'processing': 'En préparation',
			'shipped': 'Expédiée',
			'delivered': 'Livrée',
			'cancelled': 'Annulée'
		};
		return statusMap[status] || status;
	}

	// Build default message based on order
	$: defaultMessage = sendTo === 'customer'
		? `Bonjour ${order?.customer_name || ''}, votre commande #${order?.id?.substring(0, 8) || ''} est ${getStatusMessage(order?.status || '')}. Merci pour votre confiance!`
		: sendTo === 'delivery_person'
			? `Bonjour, vous avez été assigné à la commande #${order?.id?.substring(0, 8) || ''}. Statut: ${getStatusLabel(order?.status || '')}.`
			: `Bonjour, mise à jour concernant la commande #${order?.id?.substring(0, 8) || ''}.`;

	// Initialize message with default on mount
	onMount(() => {
		if (!message.trim() && defaultMessage) {
			message = defaultMessage;
		}
	});
	
	// Update message when default changes
	$: if (!message.trim() && defaultMessage) {
		message = defaultMessage;
	}

	const sendSMSMessage = async () => {
		if (!message.trim()) {
			toast.error($i18n.t('Message cannot be empty'));
			return;
		}

		sending = true;

		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const smsForm: SMSForm = {
				message: message.trim(),
				send_to: sendTo,
				delivery_person_id: sendTo === 'delivery_person' || sendTo === 'both' ? deliveryPerson?.id : undefined,
				context: {
					order_status: order?.status,
					order_id: order?.id,
					customer_name: order?.customer_name
				}
			};

			const result = await sendSMS(token, order.id, smsForm);
			
			if (result) {
				smsResponse = result;
				
				// Check the actual status from the response
				if (result.status === 'sent' && result.message_sid) {
					sent = true;
					toast.success($i18n.t('SMS sent successfully'));
					
					if (onSent) {
						onSent();
					}
				} else {
					// SMS failed to send
					const errorMsg = result.message || $i18n.t('Failed to send SMS');
					toast.error(errorMsg);
					sending = false; // Don't show success screen
				}
			}
		} catch (error: any) {
			console.error('Error sending SMS:', error);
			let errorMessage = 'Unknown error';
			
			if (typeof error === 'string') {
				errorMessage = error;
			} else if (error?.detail) {
				errorMessage = error.detail;
			} else if (error?.message) {
				errorMessage = error.message;
			}
			
			toast.error($i18n.t('Failed to send SMS: ') + errorMessage);
			sending = false;
		} finally {
			if (!sent && !sending) {
				// Reset sending state if we're not showing success screen
				sending = false;
			}
		}
	};

	const getRecipientName = () => {
		if (sendTo === 'customer') {
			return order?.customer_name || $i18n.t('Customer');
		} else if (sendTo === 'delivery_person') {
			return deliveryPerson?.name || $i18n.t('Delivery Person');
		} else {
			return $i18n.t('Customer & Delivery Person');
		}
	};

	const getRecipientPhone = () => {
		if (sendTo === 'customer') {
			return order?.customer_phone || '';
		} else if (sendTo === 'delivery_person') {
			return deliveryPerson?.phone || '';
		} else {
			return `${order?.customer_phone || ''}, ${deliveryPerson?.phone || ''}`;
		}
	};
</script>

<div class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center">
	<div class="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
		<div class="flex items-center justify-between mb-6">
			<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
				{$i18n.t('Send SMS')}
			</h2>
			<button
				class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
				on:click={onClose}
			>
				<XMark className="w-5 h-5" />
			</button>
		</div>

		{#if !sent}
			<div class="mb-6">
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Recipient')}
				</label>
				<div class="px-4 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg text-gray-900 dark:text-gray-100">
					<div class="font-medium">{getRecipientName()}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{getRecipientPhone()}</div>
				</div>
			</div>

			<div class="mb-6">
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.t('Message')}
				</label>
				<textarea
					bind:value={message}
					placeholder={$i18n.t('Enter your message...')}
					class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none"
					rows="6"
					maxlength="1600"
					disabled={sending}
				></textarea>
				<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
					{message.length} / 1600
				</div>
			</div>

			<div class="flex justify-end gap-4">
				<button
					class="px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium"
					on:click={onClose}
					disabled={sending}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					on:click={sendSMSMessage}
					disabled={sending || !message.trim()}
				>
					{#if sending}
						<Spinner className="w-4 h-4" />
						<span>{$i18n.t('Sending...')}</span>
					{:else}
						<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L6 12zm0 0h7.5" />
						</svg>
						<span>{$i18n.t('Send SMS')}</span>
					{/if}
				</button>
			</div>
		{:else}
			<div class="text-center">
				<div class="mb-4">
					<svg class="w-16 h-16 mx-auto text-green-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
					{$i18n.t('SMS Sent Successfully')}
				</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
					{$i18n.t('Message sent to')}: {smsResponse?.sent_to?.join(', ') || getRecipientPhone()}
				</p>
				{#if smsResponse?.message_sid}
					<p class="text-xs text-gray-500 dark:text-gray-500 mb-4">
						{$i18n.t('Message ID')}: {smsResponse.message_sid.substring(0, 20)}...
					</p>
				{/if}
				<button
					class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition font-medium"
					on:click={onClose}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		{/if}
	</div>
</div>
