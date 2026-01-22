<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { cart } from '$lib/stores/cart';
	import { createNewOrder } from '$lib/apis/orders';
	import { getPublicShopById } from '$lib/apis/shops';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let cartItems = [];
	let loading = false;
	let submitting = false;

	// Form fields
	let customerName = '';
	let customerEmail = '';
	let customerPhone = '';
	let street = '';
	let city = '';
	let postalCode = '';
	let country = 'France';
	let state = '';
	let shippingCost = 0;
	let notes = '';

	$: shopId = $page.url.searchParams.get('shop_id');
	$: filteredItems = shopId
		? cartItems.filter((item) => item.shop_id === shopId)
		: cartItems;
	$: subtotal = filteredItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
	$: total = subtotal + shippingCost;
	$: currency = filteredItems.length > 0 ? filteredItems[0].currency : 'EUR';

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const loadShop = async () => {
		if (!shopId) {
			toast.error($i18n ? $i18n.t('Shop ID is required') : 'Shop ID is required');
			goto('/public/cart');
			return;
		}

		loading = true;
		try {
			const res = await getPublicShopById(shopId);
			if (res) {
				shop = res;
			} else {
				toast.error($i18n ? $i18n.t('Shop not found') : 'Shop not found');
				goto('/public/cart');
			}
		} catch (error) {
			console.error('Error loading shop:', error);
			toast.error(`${error}`);
			goto('/public/cart');
		} finally {
			loading = false;
		}
	};

	const submitOrder = async () => {
		if (!shopId || filteredItems.length === 0) {
			toast.error($i18n ? $i18n.t('Invalid order') : 'Invalid order');
			return;
		}

		// Validation
		if (!customerName.trim()) {
			toast.error($i18n ? $i18n.t('Name is required') : 'Name is required');
			return;
		}
		if (!customerEmail.trim() || !customerEmail.includes('@')) {
			toast.error($i18n ? $i18n.t('Valid email is required') : 'Valid email is required');
			return;
		}
		if (!street.trim() || !city.trim() || !postalCode.trim() || !country.trim()) {
			toast.error($i18n ? $i18n.t('Complete shipping address is required') : 'Complete shipping address is required');
			return;
		}

		submitting = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token || null : null;

			const orderData = {
				shop_id: shopId,
				customer_name: customerName.trim(),
				customer_email: customerEmail.trim(),
				customer_phone: customerPhone.trim() || undefined,
				shipping_address: {
					street: street.trim(),
					city: city.trim(),
					postal_code: postalCode.trim(),
					country: country.trim(),
					state: state.trim() || undefined
				},
				items: filteredItems.map((item) => ({
					product_id: item.product_id,
					name: item.name,
					price: item.price,
					quantity: item.quantity,
					currency: item.currency
				})),
				shipping_cost: shippingCost,
				notes: notes.trim() || undefined
			};

			const order = await createNewOrder(token || '', orderData);

			if (order) {
				// Remove ordered items from cart
				filteredItems.forEach((item) => {
					cart.removeItem(item.product_id);
				});

				toast.success($i18n ? $i18n.t('Order placed successfully!') : 'Order placed successfully!');
				goto(`/public/orders/${order.id}`);
			}
		} catch (error) {
			console.error('Error creating order:', error);
			toast.error(`${error}`);
		} finally {
			submitting = false;
		}
	};

	onMount(() => {
		cart.subscribe((c) => {
			cartItems = c.items;
		});

		if (cartItems.length === 0) {
			toast.error($i18n ? $i18n.t('Your cart is empty') : 'Your cart is empty');
			goto('/public/cart');
			return;
		}

		loadShop();
	});
</script>

<svelte:head>
	<title>Checkout • {$i18n ? $i18n.t('Checkout') : 'Checkout'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<Loader />
	</div>
{:else if shop && filteredItems.length > 0}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-8">
				{$i18n ? $i18n.t('Checkout') : 'Checkout'}
			</h1>

			<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
				<div class="lg:col-span-2">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
						<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
							{$i18n ? $i18n.t('Shipping Information') : 'Shipping Information'}
						</h2>

						<div class="space-y-4">
							<div>
								<label
									for="name"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									{$i18n ? $i18n.t('Full Name') : 'Full Name'} *
								</label>
								<input
									id="name"
									type="text"
									bind:value={customerName}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									required
								/>
							</div>

							<div>
								<label
									for="email"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									{$i18n ? $i18n.t('Email') : 'Email'} *
								</label>
								<input
									id="email"
									type="email"
									bind:value={customerEmail}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									required
								/>
							</div>

							<div>
								<label
									for="phone"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									{$i18n ? $i18n.t('Phone') : 'Phone'}
								</label>
								<input
									id="phone"
									type="tel"
									bind:value={customerPhone}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								/>
							</div>

							<div>
								<label
									for="street"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									{$i18n ? $i18n.t('Street Address') : 'Street Address'} *
								</label>
								<input
									id="street"
									type="text"
									bind:value={street}
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									required
								/>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div>
									<label
										for="city"
										class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
									>
										{$i18n ? $i18n.t('City') : 'City'} *
									</label>
									<input
										id="city"
										type="text"
										bind:value={city}
										class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
										required
									/>
								</div>

								<div>
									<label
										for="postalCode"
										class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
									>
										{$i18n ? $i18n.t('Postal Code') : 'Postal Code'} *
									</label>
									<input
										id="postalCode"
										type="text"
										bind:value={postalCode}
										class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
										required
									/>
								</div>
							</div>

							<div class="grid grid-cols-2 gap-4">
								<div>
									<label
										for="country"
										class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
									>
										{$i18n ? $i18n.t('Country') : 'Country'} *
									</label>
									<input
										id="country"
										type="text"
										bind:value={country}
										class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
										required
									/>
								</div>

								<div>
									<label
										for="state"
										class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
									>
										{$i18n ? $i18n.t('State/Province') : 'State/Province'}
									</label>
									<input
										id="state"
										type="text"
										bind:value={state}
										class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
									/>
								</div>
							</div>

							<div>
								<label
									for="notes"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
								>
									{$i18n ? $i18n.t('Order Notes') : 'Order Notes'}
								</label>
								<textarea
									id="notes"
									bind:value={notes}
									rows="3"
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								></textarea>
							</div>
						</div>
					</div>
				</div>

				<div class="lg:col-span-1">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 sticky top-4">
						<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n ? $i18n.t('Order Summary') : 'Order Summary'}
						</h2>

						<div class="space-y-3 mb-6">
							{#each filteredItems as item}
								<div class="flex justify-between text-sm">
									<span class="text-gray-600 dark:text-gray-400">
										{item.name} × {item.quantity}
									</span>
									<span class="font-medium text-gray-900 dark:text-gray-100">
										{formatPrice(item.price * item.quantity, item.currency)}
									</span>
								</div>
							{/each}

							<div class="border-t border-gray-200 dark:border-gray-700 pt-3 space-y-2">
								<div class="flex justify-between text-gray-600 dark:text-gray-400">
									<span>{$i18n ? $i18n.t('Subtotal') : 'Subtotal'}</span>
									<span>{formatPrice(subtotal, currency)}</span>
								</div>
								<div class="flex justify-between text-gray-600 dark:text-gray-400">
									<span>{$i18n ? $i18n.t('Shipping') : 'Shipping'}</span>
									<span>{formatPrice(shippingCost, currency)}</span>
								</div>
								<div
									class="flex justify-between text-lg font-bold text-gray-900 dark:text-gray-100 pt-2 border-t border-gray-200 dark:border-gray-700"
								>
									<span>{$i18n ? $i18n.t('Total') : 'Total'}</span>
									<span>{formatPrice(total, currency)}</span>
								</div>
							</div>
						</div>

						<button
							on:click={submitOrder}
							disabled={submitting}
							class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
						>
							{submitting
								? ($i18n ? $i18n.t('Placing Order...') : 'Placing Order...')
								: ($i18n ? $i18n.t('Place Order') : 'Place Order')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
