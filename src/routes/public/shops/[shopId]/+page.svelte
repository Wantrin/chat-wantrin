<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getContext } from 'svelte';
	import { tick } from 'svelte';
	import { page } from '$app/stores';
	import { getPublicShopById } from '$lib/apis/shops';
	import { searchPublicProducts } from '$lib/apis/products';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { currentShopName } from '$lib/stores/currentShop';
	import { currentShopImage } from '$lib/stores/currentShopImage';
	import { shopColors } from '$lib/stores/shopColors';
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

	$: primaryColor = shop?.primary_color || '#3B82F6'; // Default blue
	$: secondaryColor = shop?.secondary_color || '#F97316'; // Default orange
	$: primaryColorLight = shop?.primary_color ? `${shop.primary_color}20` : '#3B82F620';
	$: secondaryColorLight = shop?.secondary_color ? `${shop.secondary_color}20` : '#F9731620';

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
				// Set shop name in store for Header and Footer
				if (res.name) {
					currentShopName.set(res.name);
				}
				// Set shop image in store for Header
				if (res.image_url) {
					currentShopImage.set(res.image_url);
				} else {
					currentShopImage.set(null);
				}
				// Set shop colors in store
				shopColors.set({
					primary: res.primary_color || null,
					secondary: res.secondary_color || null
				});
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
			console.log('Loading products for shop:', shop.id, shop.name);
			const res = await searchPublicProducts(null, null, null, shop.id, null, null, pageNum);
			console.log('Products response for shop:', res);
			if (res) {
				if (pageNum === 1) {
					products = res.items || [];
				} else {
					products = [...products, ...(res.items || [])];
				}
				total = res.total || 0;
				console.log(`Loaded ${products.length} products for shop, total: ${total}`);
				if (products.length >= total) {
					allLoaded = true;
				}
			} else {
				console.warn('No response from searchPublicProducts for shop');
				products = [];
				total = 0;
			}
		} catch (error) {
			console.error('Error loading products:', error);
			products = [];
			total = 0;
		} finally {
			productsLoading = false;
		}
	};

	const loadMore = async () => {
		if (!productsLoading && !allLoaded) {
			const previousProductsCount = products.length;
			pageNum += 1;
			await loadProducts();
			
			// Scroll to the newly loaded products
			await tick();
			if (products.length > previousProductsCount) {
				const newProductsStart = document.querySelector(`[data-product-index="${previousProductsCount}"]`);
				if (newProductsStart) {
					newProductsStart.scrollIntoView({ behavior: 'smooth', block: 'start' });
				} else {
					// Fallback: scroll to bottom
					window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
				}
			}
		}
	};

	const scrollToTop = () => {
		window.scrollTo({ top: 0, behavior: 'smooth' });
	};

	let showScrollToTop = false;

	const handleScroll = () => {
		showScrollToTop = window.scrollY > 300;
	};

	onMount(() => {
		loadShop();
		if (typeof window !== 'undefined') {
			window.addEventListener('scroll', handleScroll);
		}
	});

	onDestroy(() => {
		// Clear shop name, image and colors when leaving the page
		currentShopName.set(null);
		currentShopImage.set(null);
		shopColors.set({ primary: null, secondary: null });
		if (typeof window !== 'undefined') {
			window.removeEventListener('scroll', handleScroll);
		}
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
	<div class="flex items-center justify-center min-h-[60vh]">
		<Loader />
	</div>
{:else if shop}
	<!-- Hero Section -->
	<div
		class="dark:from-gray-900 dark:via-gray-800 dark:to-gray-900"
		style="background: linear-gradient(135deg, {primaryColorLight} 0%, white 50%, {secondaryColorLight} 100%);"
	>
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
			<!-- Breadcrumb -->
			<nav class="mb-4" aria-label="Breadcrumb">
				<ol class="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
					<li>
						<a
							href="/public/shops"
							class="transition-colors"
							style="color: inherit; --hover-color: {primaryColor};"
							on:mouseenter={(e) => {
								e.currentTarget.style.color = primaryColor;
							}}
							on:mouseleave={(e) => {
								e.currentTarget.style.color = 'inherit';
							}}
						>
							{$i18n ? $i18n.t('Shops') : 'Shops'}
						</a>
					</li>
					<li>
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
					</li>
					<li class="text-gray-900 dark:text-gray-100 font-medium">{shop.name}</li>
				</ol>
			</nav>

		</div>
	</div>

	<!-- Products Section -->
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<div class="mb-8">
			<div class="flex items-center justify-between">
				<h2 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
					{$i18n ? $i18n.t('Products') : 'Products'}
					<span class="text-lg font-normal text-gray-500 dark:text-gray-400 ml-2">({total})</span>
				</h2>
			</div>
		</div>

		{#if productsLoading && products.length === 0}
			<div class="flex justify-center items-center py-20">
				<Loader />
			</div>
			{:else if products.length === 0}
				<div class="text-center py-20">
					<svg
						class="mx-auto h-24 w-24 text-gray-400 dark:text-gray-600 mb-4"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
						/>
					</svg>
					<p class="text-gray-500 dark:text-gray-400 text-lg mb-2">
						{$i18n ? $i18n.t('No products found') : 'No products found'}
					</p>
					<p class="text-gray-400 dark:text-gray-500 text-sm mb-4 max-w-md mx-auto">
						{$i18n
							? $i18n.t('This shop does not have any public products yet. Products must have access_control set to null to be visible publicly.')
							: 'This shop does not have any public products yet. Products must have access_control set to null to be visible publicly.'}
					</p>
					<a
						href="/public/shops"
						class="inline-flex items-center text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
					>
						{$i18n ? $i18n.t('Browse other shops') : 'Browse other shops'}
						<svg class="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</a>
				</div>
			{:else}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12">
					{#each products as product, index (product.id)}
						<div data-product-index={index}>
							<ProductCardPublic item={product} publicRoute={true} />
						</div>
					{/each}
				</div>

			{#if !allLoaded}
				<div class="text-center">
					<button
						on:click={loadMore}
						disabled={productsLoading}
						class="inline-flex items-center px-8 py-3 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all"
						style="background-color: {primaryColor};"
						on:mouseenter={(e) => {
							if (!productsLoading) {
								e.currentTarget.style.opacity = '0.9';
							}
						}}
						on:mouseleave={(e) => {
							e.currentTarget.style.opacity = '1';
						}}
					>
						{#if productsLoading}
							<svg
								class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
							>
								<circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
								></circle>
								<path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
								></path>
							</svg>
						{/if}
						{productsLoading
							? ($i18n ? $i18n.t('Loading...') : 'Loading...')
							: ($i18n ? $i18n.t('Load More Products') : 'Load More Products')}
					</button>
				</div>
			{/if}
		{/if}
	</div>

	<!-- Scroll to Top Button -->
	{#if showScrollToTop}
		<button
			on:click={scrollToTop}
			class="fixed bottom-8 right-8 z-50 p-4 text-white rounded-full shadow-lg transition-all transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2"
			style="background-color: {primaryColor}; --hover-opacity: 0.9;"
			on:mouseenter={(e) => {
				e.currentTarget.style.opacity = '0.9';
			}}
			on:mouseleave={(e) => {
				e.currentTarget.style.opacity = '1';
			}}
			aria-label="Scroll to top"
		>
			<svg
				class="w-6 h-6"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M5 10l7-7m0 0l7 7m-7-7v18"
				/>
			</svg>
		</button>
	{/if}
{:else}
	<div class="flex items-center justify-center min-h-[60vh]">
		<div class="text-center">
			<svg
				class="mx-auto h-24 w-24 text-gray-400 dark:text-gray-600 mb-4"
				fill="none"
				viewBox="0 0 24 24"
				stroke="currentColor"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n ? $i18n.t('Shop not found') : 'Shop not found'}
			</h1>
			<p class="text-gray-500 dark:text-gray-400 mb-6">
				{$i18n
					? $i18n.t('The shop you are looking for does not exist or has been removed.')
					: 'The shop you are looking for does not exist or has been removed.'}
			</p>
			<a
				href="/public/shops"
				class="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
			>
				{$i18n ? $i18n.t('Back to shops') : 'Back to shops'}
				<svg class="w-4 h-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5l7 7-7 7"
					/>
				</svg>
			</a>
		</div>
	</div>
{/if}
