<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { getOrderById, updateOrderById, getOrderStatusHistory, type OrderStatusHistory } from '$lib/apis/orders';
	import { getDeliveryPersonsByShopId, type DeliveryPerson } from '$lib/apis/delivery_persons';
	import { getAllUsers } from '$lib/apis/users';
	import { showSidebar } from '$lib/stores';
	import Loader from '$lib/components/common/Loader.svelte';

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
				// Reload status history
				statusHistory = await getOrderStatusHistory(token, order.id);
				toast.success($i18n ? $i18n.t('Order updated successfully') : 'Order updated successfully');
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
	</div>
{/if}
