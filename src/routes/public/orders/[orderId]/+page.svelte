<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { getOrderById } from '$lib/apis/orders';
	import { getPublicShopById } from '$lib/apis/shops';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let order = null;
	let shop = null;
	let loading = true;

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
	<title>{order ? `Order #${order.id.slice(0, 8)}` : 'Order'} • {$i18n ? $i18n.t('Order Confirmation') : 'Order Confirmation'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<Loader />
	</div>
{:else if order}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div class="text-center mb-8">
				<div
					class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 mb-4"
				>
					<svg
						class="w-8 h-8 text-green-600 dark:text-green-400"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M5 13l4 4L19 7"
						/>
					</svg>
				</div>
				<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-2">
					{$i18n ? $i18n.t('Order Confirmed!') : 'Order Confirmed!'}
				</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{$i18n ? $i18n.t('Thank you for your order') : 'Thank you for your order'}
				</p>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
				<div class="flex justify-between items-start mb-6">
					<div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
							{$i18n ? $i18n.t('Order Number') : 'Order Number'}
						</h2>
						<p class="text-gray-600 dark:text-gray-400 font-mono">#{order.id.slice(0, 8)}</p>
					</div>
					<div class="text-right">
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
							{$i18n ? $i18n.t('Order Date') : 'Order Date'}
						</h2>
						<p class="text-gray-600 dark:text-gray-400">{formatDate(order.created_at)}</p>
					</div>
				</div>

				<div class="mb-6">
					<span
						class="inline-block px-3 py-1 rounded-full text-sm font-medium {getStatusColor(order.status)}"
					>
						{getStatusLabel(order.status)}
					</span>
				</div>

			{#if shop}
				<div class="mb-6">
					<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n ? $i18n.t('Shop') : 'Shop'}
					</h3>
					<p class="text-gray-900 dark:text-gray-100">{shop.name}</p>
				</div>
			{/if}

			<!-- Delivery Tracking Widget -->
			{#if order.status === 'shipped' || order.status === 'delivered' || order.tracking_number}
				<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg shadow-md p-6 mb-6 border border-blue-200 dark:border-blue-800">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
						<svg
							class="w-5 h-5 text-blue-600 dark:text-blue-400"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
							/>
						</svg>
						{$i18n ? $i18n.t('Track Your Order') : 'Track Your Order'}
					</h3>
					<div class="space-y-3">
						{#if order.tracking_number}
							<div>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Tracking Number') : 'Tracking Number'}:</strong>
								<span class="ml-2 text-gray-700 dark:text-gray-300 font-mono text-lg">{order.tracking_number}</span>
							</div>
						{/if}
						{#if order.carrier}
							<div>
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Carrier') : 'Carrier'}:</strong>
								<span class="ml-2 text-gray-700 dark:text-gray-300">{order.carrier}</span>
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
						{#if order.estimated_delivery_date}
							<div class="pt-2 border-t border-blue-200 dark:border-blue-800">
								<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Estimated Delivery') : 'Estimated Delivery'}:</strong>
								<span class="ml-2 text-gray-700 dark:text-gray-300">{formatDate(order.estimated_delivery_date)}</span>
							</div>
						{/if}
						{#if order.delivered_at}
							<div class="pt-2 border-t border-blue-200 dark:border-blue-800">
								<strong class="text-green-700 dark:text-green-400">{$i18n ? $i18n.t('Delivered On') : 'Delivered On'}:</strong>
								<span class="ml-2 text-gray-700 dark:text-gray-300">{formatDate(order.delivered_at)}</span>
							</div>
						{/if}
					</div>
				</div>
			{/if}
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Shipping Address') : 'Shipping Address'}
					</h3>
					<div class="text-gray-600 dark:text-gray-400 space-y-1">
						<p class="font-medium text-gray-900 dark:text-gray-100">{order.customer_name}</p>
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

				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
						{$i18n ? $i18n.t('Contact Information') : 'Contact Information'}
					</h3>
					<div class="text-gray-600 dark:text-gray-400 space-y-1">
						<p>
							<strong>{$i18n ? $i18n.t('Email') : 'Email'}:</strong> {order.customer_email}
						</p>
						{#if order.customer_phone}
							<p>
								<strong>{$i18n ? $i18n.t('Phone') : 'Phone'}:</strong> {order.customer_phone}
							</p>
						{/if}
					</div>
				</div>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
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

			{#if order.notes}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
						{$i18n ? $i18n.t('Order Notes') : 'Order Notes'}
					</h3>
					<p class="text-gray-600 dark:text-gray-400 whitespace-pre-line">{order.notes}</p>
				</div>
			{/if}

			<div class="text-center space-x-4">
				{#if order.status === 'shipped' || order.status === 'delivered' || order.tracking_number}
					<a
						href="/public/track/{order.id}"
						class="inline-block px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-semibold"
					>
						{$i18n ? $i18n.t('Track Order') : 'Track Order'}
					</a>
				{/if}
				<a
					href="/public/shops"
					class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold"
				>
					{$i18n ? $i18n.t('Continue Shopping') : 'Continue Shopping'}
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
