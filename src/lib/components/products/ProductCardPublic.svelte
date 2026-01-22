<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { cart } from '$lib/stores/cart';
	import { toast } from 'svelte-sonner';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let item;
	export let publicRoute = true; // Use public routes by default

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const toDisplayUrl = (u: string) => (u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`);

	$: imageUrls =
		item?.image_urls && Array.isArray(item.image_urls)
			? item.image_urls
			: item?.image_url
				? [item.image_url]
				: [];

	$: coverUrl = imageUrls.length > 0 ? toDisplayUrl(imageUrls[0]) : null;

	const handleAddToCart = (e: MouseEvent) => {
		e.stopPropagation();
		if (item) {
			cart.addItem({
				product_id: item.id,
				shop_id: item.shop_id,
				name: item.name,
				price: item.price,
				currency: item.currency || 'EUR',
				image_url: imageUrls[0] || item.image_url,
				quantity: 1
			});
			toast.success($i18n ? $i18n.t('Product added to cart') : 'Product added to cart');
		}
	};

	const handleCardClick = () => {
		const route = publicRoute ? '/public' : '';
		goto(`${route}/shops/${item.shop_id}/products/${item.id}`);
	};
</script>

<div
	class="group bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-2xl transition-all duration-300 overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600 hover:-translate-y-1"
>
	<div class="relative overflow-hidden cursor-pointer" on:click={handleCardClick}>
		{#if coverUrl}
			<img
				src={coverUrl}
				alt={item.name}
				class="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-110"
			/>
		{:else}
			<div class="w-full h-48 bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
				<span class="text-white text-sm font-medium">{$i18n ? $i18n.t('No Image') : 'No Image'}</span>
			</div>
		{/if}
		<div class="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
	</div>
	<div class="p-5">
		<div class="mb-3">
			<h3 class="text-lg font-bold text-gray-900 dark:text-gray-100 line-clamp-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors cursor-pointer" on:click={handleCardClick}>
				{item.name}
			</h3>
		</div>
		{#if item.description}
			<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-4 leading-relaxed">
				{item.description}
			</p>
		{/if}
		<div class="flex items-center justify-between mb-3 pb-3 border-b border-gray-100 dark:border-gray-700">
			<span class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
				{formatPrice(item.price, item.currency)}
			</span>
			{#if item.stock !== undefined}
				<span
					class="text-xs font-semibold px-2.5 py-1 rounded-full {item.stock > 0
						? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
						: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'}"
				>
					{item.stock > 0 ? `${item.stock} ${$i18n ? $i18n.t('in stock') : 'in stock'}` : ($i18n ? $i18n.t('Out of stock') : 'Out of stock')}
				</span>
			{/if}
		</div>
		<div class="flex items-center justify-between mb-3">
			<div class="flex gap-2 flex-wrap">
				{#if item.category}
					<span class="text-xs font-medium px-2.5 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
						{item.category}
					</span>
				{/if}
				{#if item.currency}
					<span class="text-xs font-medium px-2.5 py-1 bg-gradient-to-r from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 text-green-700 dark:text-green-400 rounded-full">
						{item.currency}
					</span>
				{/if}
			</div>
		</div>
		<button
			on:click={handleAddToCart}
			disabled={item.stock !== undefined && item.stock <= 0}
			class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
		>
			<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"
				/>
			</svg>
			{$i18n ? $i18n.t('Add to Cart') : 'Add to Cart'}
		</button>
	</div>
</div>
