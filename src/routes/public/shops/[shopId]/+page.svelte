<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { getPublicShopById } from '$lib/apis/shops';
	import { searchPublicProducts } from '$lib/apis/products';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ProductCardPublic from '$lib/components/products/ProductCardPublic.svelte';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let products = [];
	let loading = true;
	let productsLoading = false;
	let pageNum = 1;
	let total = 0;
	let allLoaded = false;

	$: imageUrl = shop?.image_url
		? shop.image_url.startsWith('http')
			? shop.image_url
			: `${WEBUI_API_BASE_URL}/files/${shop.image_url}/content`
		: null;

	const loadShop = async () => {
		loading = true;
		try {
			const shopId = $page.params.shopId;
			const res = await getPublicShopById(shopId);
			if (res) {
				shop = res;
				await loadProducts();
			}
		} catch (error) {
			console.error('Error loading shop:', error);
		} finally {
			loading = false;
		}
	};

	const loadProducts = async () => {
		if (!shop) return;
		productsLoading = true;
		try {
			const res = await searchPublicProducts(null, null, null, shop.id, null, null, pageNum);
			if (res) {
				if (pageNum === 1) {
					products = res.items || [];
				} else {
					products = [...products, ...(res.items || [])];
				}
				total = res.total || 0;
				if (products.length >= total) {
					allLoaded = true;
				}
			}
		} catch (error) {
			console.error('Error loading products:', error);
		} finally {
			productsLoading = false;
		}
	};

	const loadMore = () => {
		if (!productsLoading && !allLoaded) {
			pageNum += 1;
			loadProducts();
		}
	};

	onMount(() => {
		loadShop();
	});
</script>

<svelte:head>
	<title>{shop ? shop.name : 'Shop'} • {$i18n ? $i18n.t('Public Shop') : 'Public Shop'}</title>
	<meta name="description" content={shop?.description || 'Découvrez les produits de ce magasin'} />
	{#if shop}
		<meta property="og:title" content={shop.name} />
		<meta property="og:description" content={shop.description || ''} />
		{#if imageUrl}
			<meta property="og:image" content={imageUrl} />
		{/if}
		<meta property="og:type" content="website" />
	{/if}
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<Loader />
	</div>
{:else if shop}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700 mb-8">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-0">
					<div class="relative overflow-hidden">
						{#if imageUrl}
							<img
								src={imageUrl}
								alt={shop.name}
								class="w-full h-full min-h-[400px] object-cover"
							/>
						{:else}
							<div class="w-full h-full min-h-[400px] bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
							<span class="text-white text-lg font-medium">{$i18n ? $i18n.t('No Image') : 'No Image'}</span>
						</div>
						{/if}
						<div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
					</div>
					<div class="p-8 flex flex-col justify-between">
						<div>
							<h1 class="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
								{shop.name}
							</h1>
							{#if shop.description}
								<p class="text-gray-600 dark:text-gray-400 mb-6 text-lg leading-relaxed">{shop.description}</p>
							{/if}
						</div>
					</div>
				</div>
			</div>

			<div class="mb-6">
				<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
					{$i18n ? $i18n.t('Products') : 'Products'} ({total})
				</h2>
			</div>

			{#if productsLoading && products.length === 0}
				<div class="flex justify-center items-center py-20">
					<Loader />
				</div>
			{:else if products.length === 0}
				<div class="text-center py-20">
					<p class="text-gray-500 dark:text-gray-400 text-lg">
						{$i18n ? $i18n.t('No products found') : 'No products found'}
					</p>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
					{#each products as product (product.id)}
						<ProductCardPublic item={product} publicRoute={true} />
					{/each}
				</div>

				{#if !allLoaded}
					<div class="text-center">
						<button
							on:click={loadMore}
							disabled={productsLoading}
							class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
						>
							{productsLoading ? ($i18n ? $i18n.t('Loading...') : 'Loading...') : ($i18n ? $i18n.t('Load More') : 'Load More')}
						</button>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n ? $i18n.t('Shop not found') : 'Shop not found'}
			</h1>
			<a href="/public/shops" class="text-blue-600 hover:text-blue-800">
				{$i18n ? $i18n.t('Back to shops') : 'Back to shops'}
			</a>
		</div>
	</div>
{/if}
