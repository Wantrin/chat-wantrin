<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { tick } from 'svelte';
	import { page } from '$app/stores';
	import { searchPublicShops } from '$lib/apis/shops';
	import { shopColors } from '$lib/stores/shopColors';
	import { currentShopName } from '$lib/stores/currentShop';
	import { currentShopImage } from '$lib/stores/currentShopImage';
	import Loader from '$lib/components/common/Loader.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	// Reset colors, name and image on main shops page
	$: shopColors.set({ primary: null, secondary: null });
	$: currentShopName.set(null);
	$: currentShopImage.set(null);
	
	$: primaryColor = '#3B82F6'; // Default blue
	$: secondaryColor = '#F97316'; // Default orange

	let showScrollToTop = false;
	let shopsContainer: HTMLElement;

	let shops: any[] = [];
	let loading = true;
	let shopsLoading = false;
	let query = '';
	let pageNum = 1;
	let total = 0;
	let allLoaded = false;
	let initializedFromUrl = false;

	$: searchParam = $page.url.searchParams.get('search') || '';
	$: if (!initializedFromUrl && searchParam) {
		query = searchParam;
	}

	const toImageUrl = (url: string | null | undefined) => {
		if (!url) return null;
		return url.startsWith('http') ? url : `${WEBUI_API_BASE_URL}/files/${url}/content`;
	};

	const loadShops = async () => {
		shopsLoading = true;
		try {
			const res = await searchPublicShops(query || null, 'updated_at', 'desc', pageNum);
			if (res) {
				if (pageNum === 1) {
					shops = res.items || [];
				} else {
					shops = [...shops, ...(res.items || [])];
				}
				total = res.total || 0;
				if (shops.length >= total) {
					allLoaded = true;
				}
			} else {
				shops = [];
				total = 0;
			}
		} catch (error) {
			console.error('Error loading shops:', error);
			shops = [];
			total = 0;
		} finally {
			shopsLoading = false;
			loading = false;
			initializedFromUrl = true;
		}
	};

	const handleSearch = () => {
		pageNum = 1;
		allLoaded = false;
		loadShops();
	};

	const loadMore = async () => {
		if (!shopsLoading && !allLoaded) {
			const previousCount = shops.length;
			pageNum += 1;
			await loadShops();
			
			// Scroll to the newly loaded shops
			await tick();
			if (shops.length > previousCount) {
				const newStart = document.querySelector(`[data-shop-index="${previousCount}"]`);
				if (newStart) {
					newStart.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

	const handleScroll = () => {
		showScrollToTop = window.scrollY > 300;
	};

	onMount(() => {
		loadShops();
		if (typeof window !== 'undefined') {
			window.addEventListener('scroll', handleScroll);
		}
		return () => {
			if (typeof window !== 'undefined') {
				window.removeEventListener('scroll', handleScroll);
			}
		};
	});
</script>

<svelte:head>
	<title>{$i18n ? $i18n.t('Shops') : 'Shops'} • {$i18n ? $i18n.t('Shop') : 'Shop'}</title>
	<meta name="description" content="Découvrez nos magasins publics" />
</svelte:head>

<!-- Shops Section -->
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
	{#if loading && shops.length === 0}
		<div class="flex justify-center items-center py-20">
			<Loader />
		</div>
	{:else if shops.length === 0}
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
				{$i18n ? $i18n.t('No shops found') : 'No shops found'}
			</p>
			{#if query}
				<p class="text-gray-400 dark:text-gray-500 text-sm mb-4">
					{$i18n
						? $i18n.t('Try a different search term')
						: 'Try a different search term'}
				</p>
				<button
					on:click={() => {
						query = '';
						handleSearch();
					}}
					class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
				>
					{$i18n ? $i18n.t('Clear search') : 'Clear search'}
				</button>
			{/if}
		</div>
	{:else}
		<!-- Shops Grid -->
		<div
			bind:this={shopsContainer}
			class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12"
		>
			{#each shops as shop, index (shop.id)}
				<div data-shop-index={index}>
					<a
						href={`/public/shops/${shop.url || shop.id}`}
						class="group block bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-md hover:shadow-xl transition-all"
					>
						<div class="relative">
							{#if toImageUrl(shop.image_url)}
								<img
									src={toImageUrl(shop.image_url)}
									alt={shop.name}
									class="w-full h-40 object-cover"
									loading="lazy"
								/>
							{:else}
								<div
									class="w-full h-40 flex items-center justify-center"
									style="background: linear-gradient(135deg, {primaryColor} 0%, {secondaryColor} 100%);"
								>
									<span class="text-white font-semibold">{shop.name?.slice(0, 1) || 'S'}</span>
								</div>
							{/if}
							<div class="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
						</div>
						<div class="p-4">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
								{shop.name}
							</h3>
							{#if shop.description}
								<p class="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
									{shop.description}
								</p>
							{/if}
							<div class="mt-3 text-sm font-medium" style="color: {primaryColor};">
								{$i18n ? $i18n.t('Open shop') : 'Open shop'} →
							</div>
						</div>
					</a>
				</div>
			{/each}
		</div>

		{#if !allLoaded}
			<div class="text-center">
				<button
					on:click={loadMore}
					disabled={shopsLoading}
					class="inline-flex items-center px-8 py-3 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all"
					style="background-color: {primaryColor};"
					on:mouseenter={(e) => {
						if (!shopsLoading) {
							e.currentTarget.style.opacity = '0.9';
						}
					}}
					on:mouseleave={(e) => {
						e.currentTarget.style.opacity = '1';
					}}
				>
					{#if shopsLoading}
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
					{shopsLoading
						? ($i18n ? $i18n.t('Loading...') : 'Loading...')
						: ($i18n ? $i18n.t('Load More Shops') : 'Load More Shops')}
				</button>
			</div>
		{/if}
	{/if}

	<!-- Scroll to Top Button -->
	{#if showScrollToTop}
		<button
			on:click={scrollToTop}
			class="fixed bottom-8 right-8 z-50 p-4 text-white rounded-full shadow-lg transition-all transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2"
			style="background-color: {primaryColor};"
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
</div>
