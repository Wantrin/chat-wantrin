<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { getOrderById, updateOrderById } from '$lib/apis/orders';
	import { showSidebar } from '$lib/stores';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let order = null;
	let loading = true;
	let updating = false;
	let selectedStatus = '';

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

		updating = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const updated = await updateOrderById(token, order.id, {
				status: selectedStatus
			});

			if (updated) {
				order = updated;
				toast.success($i18n ? $i18n.t('Order updated successfully') : 'Order updated successfully');
			}
		} catch (error) {
			console.error('Error updating order:', error);
			toast.error(`${error}`);
		} finally {
			updating = false;
		}
	};

	onMount(() => {
		loadData();
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
	</div>
{/if}
