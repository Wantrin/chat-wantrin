<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { getOrdersByShopId } from '$lib/apis/orders';
	import { showSidebar } from '$lib/stores';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let orders = [];
	let loading = true;
	let statusFilter = 'all';
	let searchQuery = '';

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const formatDate = (timestamp: number) => {
		return new Date(timestamp / 1000000).toLocaleDateString('fr-FR', {
			year: 'numeric',
			month: 'short',
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
			const shopId = $page.params.shopId?.trim();
			if (!shopId) {
				toast.error($i18n ? $i18n.t('Invalid shop ID') : 'Invalid shop ID');
				goto('/shops');
				return;
			}
			const token = typeof window !== 'undefined' ? localStorage.token : '';

			// First, try to load the shop
			try {
				const shopRes = await getShopById(token, shopId);
				if (shopRes) {
					shop = shopRes;
				} else {
					toast.error($i18n ? $i18n.t('Shop not found') : 'Shop not found');
					goto('/shops');
					return;
				}
			} catch (shopError: any) {
				console.error('Error loading shop:', shopError);
				const errorMsg = shopError?.detail || shopError?.message || shopError || 'Shop not found';
				toast.error(errorMsg);
				goto('/shops');
				return;
			}

			// Then, try to load orders
			try {
				const ordersRes = await getOrdersByShopId(token, shopId);
				if (ordersRes && Array.isArray(ordersRes)) {
					orders = ordersRes;
				} else {
					orders = [];
				}
			} catch (ordersError: any) {
				console.error('Error loading orders:', ordersError);
				// Don't redirect if orders fail, just show empty list
				const errorMsg = ordersError?.detail || ordersError?.message || ordersError;
				if (errorMsg && errorMsg !== 'Shop not found') {
					toast.error(errorMsg);
				}
				orders = [];
			}
		} catch (error: any) {
			console.error('Error loading data:', error);
			const errorMsg = error?.detail || error?.message || error || 'An error occurred';
			toast.error(errorMsg);
		} finally {
			loading = false;
		}
	};

	$: filteredOrders = orders.filter((order) => {
		const matchesStatus = statusFilter === 'all' || order.status === statusFilter;
		const matchesSearch =
			!searchQuery ||
			order.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			order.customer_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
			order.id.toLowerCase().includes(searchQuery.toLowerCase());
		return matchesStatus && matchesSearch;
	});

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>{shop ? `${shop.name} - Orders` : 'Orders'} • {$i18n ? $i18n.t('Orders') : 'Orders'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<Loader />
	</div>
{:else if shop}
	<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full">
		<div class="px-5 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{$i18n ? $i18n.t('Orders') : 'Orders'} - {shop.name}
				</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					{filteredOrders.length} {$i18n ? $i18n.t('order(s)') : 'order(s)'}
				</p>
			</div>
			<a
				href="/shops/{shop.id}"
				class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
			>
				← {$i18n ? $i18n.t('Back to Shop') : 'Back to Shop'}
			</a>
		</div>

		<div class="flex-1 overflow-auto p-5">
			<div class="mb-6 flex flex-col sm:flex-row gap-4">
				<div class="flex-1">
					<input
						type="text"
						bind:value={searchQuery}
						placeholder={$i18n ? $i18n.t('Search orders...') : 'Search orders...'}
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					/>
				</div>
				<select
					bind:value={statusFilter}
					class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
				>
					<option value="all">{$i18n ? $i18n.t('All Status') : 'All Status'}</option>
					<option value="pending">{$i18n ? $i18n.t('Pending') : 'Pending'}</option>
					<option value="confirmed">{$i18n ? $i18n.t('Confirmed') : 'Confirmed'}</option>
					<option value="processing">{$i18n ? $i18n.t('Processing') : 'Processing'}</option>
					<option value="shipped">{$i18n ? $i18n.t('Shipped') : 'Shipped'}</option>
					<option value="delivered">{$i18n ? $i18n.t('Delivered') : 'Delivered'}</option>
					<option value="cancelled">{$i18n ? $i18n.t('Cancelled') : 'Cancelled'}</option>
				</select>
			</div>

			{#if filteredOrders.length === 0}
				<div class="text-center py-20">
					<p class="text-gray-500 dark:text-gray-400 text-lg">
						{$i18n ? $i18n.t('No orders found') : 'No orders found'}
					</p>
				</div>
			{:else}
				<div class="space-y-4">
					{#each filteredOrders as order (order.id)}
						<div
							class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition cursor-pointer"
							on:click={() => goto(`/shops/${shop.id}/orders/${order.id}`)}
						>
							<div class="flex items-start justify-between">
								<div class="flex-1">
									<div class="flex items-center gap-4 mb-2">
										<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
											{$i18n ? $i18n.t('Order') : 'Order'} #{order.id.slice(0, 8)}
										</h3>
										<span
											class="px-3 py-1 rounded-full text-sm font-medium {getStatusColor(order.status)}"
										>
											{getStatusLabel(order.status)}
										</span>
									</div>
									<div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400">
										<div>
											<p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
												{$i18n ? $i18n.t('Customer') : 'Customer'}
											</p>
											<p>{order.customer_name}</p>
											<p>{order.customer_email}</p>
										</div>
										<div>
											<p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
												{$i18n ? $i18n.t('Date') : 'Date'}
											</p>
											<p>{formatDate(order.created_at)}</p>
										</div>
										<div>
											<p class="font-medium text-gray-900 dark:text-gray-100 mb-1">
												{$i18n ? $i18n.t('Total') : 'Total'}
											</p>
											<p class="text-lg font-bold text-gray-900 dark:text-gray-100">
												{formatPrice(order.total, order.currency)}
											</p>
										</div>
									</div>
									<div class="mt-4">
										<p class="text-sm text-gray-600 dark:text-gray-400">
											{order.items.length} {$i18n ? $i18n.t('item(s)') : 'item(s)'}
										</p>
									</div>
								</div>
								<div class="ml-4">
									<svg
										class="w-5 h-5 text-gray-400"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 5l7 7-7 7"
										/>
									</svg>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
