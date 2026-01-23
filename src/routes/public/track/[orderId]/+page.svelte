<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { getOrderById, getOrderStatusHistory, type OrderStatusHistory } from '$lib/apis/orders';
	import { getPublicShopById } from '$lib/apis/shops';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let order = null;
	let shop = null;
	let statusHistory: OrderStatusHistory[] = [];
	let loading = true;

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

	const getStatusIcon = (status: string) => {
		switch (status) {
			case 'delivered':
				return 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'shipped':
				return 'M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z';
			case 'processing':
				return 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'confirmed':
				return 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z';
			default:
				return 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z';
		}
	};

	const loadData = async () => {
		loading = true;
		try {
			const orderId = $page.params.orderId;
			const token = typeof window !== 'undefined' ? localStorage.token || null : null;

			const orderRes = await getOrderById(token, orderId);
			if (orderRes) {
				order = orderRes;
				if (order.shop_id) {
					const shopRes = await getPublicShopById(order.shop_id);
					if (shopRes) {
						shop = shopRes;
					}
				}

				// Load status history if authenticated
				if (token) {
					try {
						statusHistory = await getOrderStatusHistory(token, orderId);
					} catch (error) {
						console.error('Error loading status history:', error);
						statusHistory = [];
					}
				}
			}
		} catch (error) {
			console.error('Error loading data:', error);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>{order ? `Track Order #${order.id.slice(0, 8)}` : 'Track Order'} • {$i18n ? $i18n.t('Track Your Order') : 'Track Your Order'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<Loader />
	</div>
{:else if order}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div class="text-center mb-8">
				<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
					{$i18n ? $i18n.t('Track Your Order') : 'Track Your Order'}
				</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{$i18n ? $i18n.t('Order Number') : 'Order Number'}: <span class="font-mono">#{order.id.slice(0, 8)}</span>
				</p>
			</div>

			<!-- Current Status -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
						{$i18n ? $i18n.t('Current Status') : 'Current Status'}
					</h2>
					<span
						class="px-4 py-2 rounded-full text-sm font-medium {getStatusColor(order.status)}"
					>
						{getStatusLabel(order.status)}
					</span>
				</div>
			</div>

			<!-- Tracking Information -->
			{#if order.tracking_number || order.carrier || order.tracking_url}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Tracking Information') : 'Tracking Information'}
					</h3>
					<div class="space-y-3">
						{#if order.tracking_number}
							<div>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Tracking Number') : 'Tracking Number'}:</strong>
								<span class="ml-2 text-gray-600 dark:text-gray-400 font-mono text-lg">{order.tracking_number}</span>
							</div>
						{/if}
						{#if order.carrier}
							<div>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Carrier') : 'Carrier'}:</strong>
								<span class="ml-2 text-gray-600 dark:text-gray-400">{order.carrier}</span>
							</div>
						{/if}
						{#if order.tracking_url}
							<a
								href={order.tracking_url}
								target="_blank"
								rel="noopener noreferrer"
								class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
							>
								<svg
									class="w-4 h-4"
									fill="none"
									viewBox="0 0 24 24"
									stroke-width="1.5"
									stroke="currentColor"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
									/>
								</svg>
								{$i18n ? $i18n.t('Track Package') : 'Track Package'}
							</a>
						{/if}
						{#if order.shipped_at}
							<div class="pt-2 border-t border-gray-200 dark:border-gray-700">
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Shipped On') : 'Shipped On'}:</strong>
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
								<strong class="text-green-700 dark:text-green-400">{$i18n ? $i18n.t('Delivered On') : 'Delivered On'}:</strong>
								<span class="ml-2 text-gray-600 dark:text-gray-400">{formatDate(order.delivered_at)}</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Status History Timeline -->
			{#if statusHistory.length > 0}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-6">
						{$i18n ? $i18n.t('Order Timeline') : 'Order Timeline'}
					</h3>
					<div class="relative">
						<div class="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700"></div>
						<div class="space-y-6">
							{#each statusHistory as history, index}
								<div class="relative flex items-start gap-4">
									<div class="relative z-10 flex-shrink-0">
										<div class="flex items-center justify-center w-8 h-8 rounded-full {history.status === 'delivered'
											? 'bg-green-500'
											: history.status === 'shipped'
												? 'bg-indigo-500'
												: 'bg-gray-400'}">
											<svg
												class="w-5 h-5 text-white"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
												stroke="currentColor"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d={getStatusIcon(history.status)}
												/>
											</svg>
										</div>
									</div>
									<div class="flex-1 min-w-0 pb-6">
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
				</div>
			{/if}

			<!-- Order Summary -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
					{$i18n ? $i18n.t('Order Summary') : 'Order Summary'}
				</h3>
				<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
					<p>
						<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Order Date') : 'Order Date'}:</strong> {formatDate(order.created_at)}
					</p>
					{#if shop}
						<p>
							<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Shop') : 'Shop'}:</strong> {shop.name}
						</p>
					{/if}
					<p>
						<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Total') : 'Total'}:</strong> {new Intl.NumberFormat('fr-FR', {
							style: 'currency',
							currency: order.currency || 'EUR'
						}).format(order.total)}
					</p>
				</div>
			</div>

			<div class="text-center">
				<a
					href="/public/orders/{order.id}"
					class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold"
				>
					{$i18n ? $i18n.t('View Full Order Details') : 'View Full Order Details'}
				</a>
			</div>
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n ? $i18n.t('Order not found') : 'Order not found'}
			</h1>
			<a href="/public/shops" class="text-blue-600 hover:text-blue-800">
				{$i18n ? $i18n.t('Back to shops') : 'Back to shops'}
			</a>
		</div>
	</div>
{/if}
