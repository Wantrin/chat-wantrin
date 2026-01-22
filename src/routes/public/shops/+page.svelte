<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { searchPublicShops } from '$lib/apis/shops';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ShopCard from '$lib/components/shops/ShopCard.svelte';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shops = [];
	let loading = true;
	let query = '';
	let page = 1;
	let total = 0;
	let allLoaded = false;

	const loadShops = async () => {
		loading = true;
		try {
			const res = await searchPublicShops(query || null, null, null, page);
			if (res) {
				if (page === 1) {
					shops = res.items || [];
				} else {
					shops = [...shops, ...(res.items || [])];
				}
				total = res.total || 0;
				if (shops.length >= total) {
					allLoaded = true;
				}
			}
		} catch (error) {
			console.error('Error loading shops:', error);
		} finally {
			loading = false;
		}
	};

	const handleSearch = () => {
		page = 1;
		allLoaded = false;
		loadShops();
	};

	const loadMore = () => {
		if (!loading && !allLoaded) {
			page += 1;
			loadShops();
		}
	};

	onMount(() => {
		loadShops();
	});
</script>

<svelte:head>
	<title>Magasins publics • {$i18n ? $i18n.t('Shops') : 'Shops'}</title>
	<meta name="description" content="Découvrez nos magasins publics et leurs produits" />
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
		<div class="text-center mb-12">
			<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n ? $i18n.t('Public Shops') : 'Public Shops'}
			</h1>
			<p class="text-lg text-gray-600 dark:text-gray-400">
				{$i18n ? $i18n.t('Discover our public shops and their products') : 'Discover our public shops and their products'}
			</p>
		</div>

		<div class="mb-8">
			<div class="max-w-md mx-auto">
				<div class="relative">
					<input
						type="text"
						bind:value={query}
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								handleSearch();
							}
						}}
						placeholder={$i18n ? $i18n.t('Search shops...') : 'Search shops...'}
						class="w-full px-4 py-3 pl-10 pr-4 text-gray-700 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
					</div>
					<button
						on:click={handleSearch}
						class="absolute inset-y-0 right-0 pr-3 flex items-center text-blue-600 hover:text-blue-800"
					>
						{$i18n ? $i18n.t('Search') : 'Search'}
					</button>
				</div>
			</div>
		</div>

		{#if loading && shops.length === 0}
			<div class="flex justify-center items-center py-20">
				<Loader />
			</div>
		{:else if shops.length === 0}
			<div class="text-center py-20">
				<p class="text-gray-500 dark:text-gray-400 text-lg">
					{$i18n ? $i18n.t('No shops found') : 'No shops found'}
				</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
				{#each shops as shop (shop.id)}
					{@const identifier = shop.url || shop.id}
					<a href="/public/shops/{identifier}" class="block">
						<ShopCard item={shop} />
					</a>
				{/each}
			</div>

			{#if !allLoaded}
				<div class="text-center">
					<button
						on:click={loadMore}
						disabled={loading}
						class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
					>
						{loading ? ($i18n ? $i18n.t('Loading...') : 'Loading...') : ($i18n ? $i18n.t('Load More') : 'Load More')}
					</button>
				</div>
			{/if}
		{/if}
	</div>
</div>
