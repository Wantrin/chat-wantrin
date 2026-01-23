<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { cart } from '$lib/stores/cart';
	import { shopColors } from '$lib/stores/shopColors';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	$: primaryColor = $shopColors.primary || '#3B82F6'; // Default blue
	$: secondaryColor = $shopColors.secondary || '#F97316'; // Default orange

	let cartItems = [];
	let loading = false;

	$: cartItems = $cart.items;
	$: total = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
	$: currency = cartItems.length > 0 ? cartItems[0].currency : 'EUR';

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const updateQuantity = (productId: string, quantity: number) => {
		cart.updateQuantity(productId, quantity);
	};

	const removeItem = (productId: string) => {
		cart.removeItem(productId);
	};

	const proceedToCheckout = () => {
		if (cartItems.length === 0) return;
		// Group items by shop_id
		const shops = new Map();
		cartItems.forEach((item) => {
			if (!shops.has(item.shop_id)) {
				shops.set(item.shop_id, []);
			}
			shops.get(item.shop_id).push(item);
		});

		// For now, we'll handle one shop at a time
		// In the future, we could create multiple orders
		const firstShop = Array.from(shops.keys())[0];
		goto(`/public/checkout?shop_id=${firstShop}`);
	};

	$: imageUrl = (url) => {
		if (!url) return null;
		return url.startsWith('http') ? url : `${WEBUI_API_BASE_URL}/files/${url}/content`;
	};
</script>

<svelte:head>
	<title>Panier • {$i18n ? $i18n.t('Cart') : 'Cart'}</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-8">
			{$i18n ? $i18n.t('Shopping Cart') : 'Shopping Cart'}
		</h1>

		{#if cartItems.length === 0}
			<div class="text-center py-20">
				<svg
					class="mx-auto h-24 w-24 text-gray-400 mb-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
					/>
				</svg>
				<p class="text-gray-500 dark:text-gray-400 text-lg mb-4">
					{$i18n ? $i18n.t('Your cart is empty') : 'Your cart is empty'}
				</p>
				<a
					href="/public/shops"
					class="inline-block px-6 py-3 text-white rounded-lg transition"
					style="background-color: {primaryColor};"
					on:mouseenter={(e) => {
						e.currentTarget.style.opacity = '0.9';
					}}
					on:mouseleave={(e) => {
						e.currentTarget.style.opacity = '1';
					}}
				>
					{$i18n ? $i18n.t('Continue Shopping') : 'Continue Shopping'}
				</a>
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
				<div class="lg:col-span-2">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
						<div class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each cartItems as item (item.product_id)}
								<div class="p-6 flex items-center gap-4">
									{#if imageUrl(item.image_url)}
										<img
											src={imageUrl(item.image_url)}
											alt={item.name}
											class="w-24 h-24 object-cover rounded-lg"
										/>
									{:else}
										<div
											class="w-24 h-24 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center"
										>
											<span class="text-gray-400 text-xs">{$i18n ? $i18n.t('No Image') : 'No Image'}</span>
										</div>
									{/if}

									<div class="flex-1">
										<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
											{item.name}
										</h3>
										<p class="text-gray-600 dark:text-gray-400">
											{formatPrice(item.price, item.currency)} × {item.quantity}
										</p>
									</div>

									<div class="flex items-center gap-4">
										<div class="flex items-center gap-2">
											<button
												on:click={() => updateQuantity(item.product_id, item.quantity - 1)}
												class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
											>
												-
											</button>
											<span class="w-12 text-center font-medium">{item.quantity}</span>
											<button
												on:click={() => updateQuantity(item.product_id, item.quantity + 1)}
												class="w-8 h-8 flex items-center justify-center border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
											>
												+
											</button>
										</div>

										<div class="text-right min-w-[100px]">
											<p class="text-lg font-bold text-gray-900 dark:text-gray-100">
												{formatPrice(item.price * item.quantity, item.currency)}
											</p>
										</div>

										<button
											on:click={() => removeItem(item.product_id)}
											class="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
											title={$i18n ? $i18n.t('Remove') : 'Remove'}
										>
											<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
												/>
											</svg>
										</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				</div>

				<div class="lg:col-span-1">
					<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 sticky top-4">
						<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-4">
							{$i18n ? $i18n.t('Order Summary') : 'Order Summary'}
						</h2>

						<div class="space-y-3 mb-6">
							<div class="flex justify-between text-gray-600 dark:text-gray-400">
								<span>{$i18n ? $i18n.t('Subtotal') : 'Subtotal'}</span>
								<span>{formatPrice(total, currency)}</span>
							</div>
							<div class="flex justify-between text-gray-600 dark:text-gray-400">
								<span>{$i18n ? $i18n.t('Shipping') : 'Shipping'}</span>
								<span>{$i18n ? $i18n.t('Calculated at checkout') : 'Calculated at checkout'}</span>
							</div>
							<div class="border-t border-gray-200 dark:border-gray-700 pt-3 flex justify-between text-lg font-bold text-gray-900 dark:text-gray-100">
								<span>{$i18n ? $i18n.t('Total') : 'Total'}</span>
								<span>{formatPrice(total, currency)}</span>
							</div>
						</div>

						<button
							on:click={proceedToCheckout}
							class="w-full px-6 py-3 text-white rounded-lg transition font-semibold"
							style="background-color: {primaryColor};"
							on:mouseenter={(e) => {
								e.currentTarget.style.opacity = '0.9';
							}}
							on:mouseleave={(e) => {
								e.currentTarget.style.opacity = '1';
							}}
						>
							{$i18n ? $i18n.t('Proceed to Checkout') : 'Proceed to Checkout'}
						</button>

						<a
							href="/public/shops"
							class="block text-center mt-4 transition-colors"
							style="color: {primaryColor};"
							on:mouseenter={(e) => {
								e.currentTarget.style.opacity = '0.8';
							}}
							on:mouseleave={(e) => {
								e.currentTarget.style.opacity = '1';
							}}
						>
							{$i18n ? $i18n.t('Continue Shopping') : 'Continue Shopping'}
						</a>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
