<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME } from '$lib/stores';
	import { currentShopName } from '$lib/stores/currentShop';
	import { currentShopImage } from '$lib/stores/currentShopImage';
	import { shopColors } from '$lib/stores/shopColors';
	import CartIcon from '$lib/components/cart/CartIcon.svelte';
	import { cart } from '$lib/stores/cart';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	$: displayName = $currentShopName || $WEBUI_NAME || 'Shop';
	$: primaryColor = $shopColors.primary || '#3B82F6'; // Default blue
	$: secondaryColor = $shopColors.secondary || '#F97316'; // Default orange
	$: shopImageUrl = $currentShopImage
		? $currentShopImage.startsWith('http')
			? $currentShopImage
			: `${WEBUI_API_BASE_URL}/files/${$currentShopImage}/content`
		: null;

	let searchQuery = '';
	let mobileMenuOpen = false;
	let itemCount = 0;

	cart.subscribe((c) => {
		itemCount = c.items.reduce((sum, item) => sum + item.quantity, 0);
	});

	const handleSearch = () => {
		if (searchQuery.trim()) {
			goto(`/public/shops?search=${encodeURIComponent(searchQuery.trim())}`);
		}
	};

	const handleKeyPress = (e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			handleSearch();
		}
	};
</script>

<header
	class="border-b fixed top-0 left-0 right-0 z-50 shadow-sm"
	style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%); border-color: rgba(0, 0, 0, 0.1);"
>
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
		<!-- Top Bar -->
		<div class="flex items-center justify-between h-16">
			<!-- Logo -->
			<div class="flex items-center">
				<a href="/public/shops" class="flex items-center space-x-2">
					{#if shopImageUrl}
						<img
							src={shopImageUrl}
							alt={displayName}
							class="w-10 h-10 rounded-lg object-cover border-2 border-white/30"
						/>
					{:else}
						<div
							class="w-10 h-10 rounded-lg flex items-center justify-center"
							style="background: rgba(255, 255, 255, 0.2); backdrop-filter: blur(10px);"
						>
							<span class="text-white font-bold text-lg">{displayName.charAt(0).toUpperCase()}</span>
						</div>
					{/if}
					<span class="text-xl font-bold text-white">
						{displayName}
					</span>
				</a>
			</div>

			<!-- Desktop Navigation -->
			<nav class="hidden md:flex items-center space-x-8">
				<a
					href="/public/shops"
					class="text-white font-medium transition-colors {($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')
						? ''
						: ''}"
					style="color: {($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')
						? '#FFFFFF'
						: 'rgba(255, 255, 255, 0.9)'};"
					on:mouseenter={(e) => {
						e.currentTarget.style.color = '#FFFFFF';
						e.currentTarget.style.textDecoration = 'underline';
					}}
					on:mouseleave={(e) => {
						if (($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')) {
							e.currentTarget.style.color = '#FFFFFF';
						} else {
							e.currentTarget.style.color = 'rgba(255, 255, 255, 0.9)';
						}
						e.currentTarget.style.textDecoration = 'none';
					}}
				>
					{$i18n ? $i18n.t('Shops') : 'Shops'}
				</a>
				<a
					href="/public/cart"
					class="text-white font-medium transition-colors {$page.url.pathname === '/public/cart'
						? ''
						: ''}"
					style="color: {$page.url.pathname === '/public/cart'
						? '#FFFFFF'
						: 'rgba(255, 255, 255, 0.9)'};"
					on:mouseenter={(e) => {
						e.currentTarget.style.color = '#FFFFFF';
						e.currentTarget.style.textDecoration = 'underline';
					}}
					on:mouseleave={(e) => {
						if ($page.url.pathname === '/public/cart') {
							e.currentTarget.style.color = '#FFFFFF';
						} else {
							e.currentTarget.style.color = 'rgba(255, 255, 255, 0.9)';
						}
						e.currentTarget.style.textDecoration = 'none';
					}}
				>
					{$i18n ? $i18n.t('Cart') : 'Cart'}
					{#if itemCount > 0}
						<span
							class="ml-1 text-xs text-white px-2 py-0.5 rounded-full"
							style="background-color: rgba(255, 255, 255, 0.3); backdrop-filter: blur(10px);"
						>
							{itemCount}
						</span>
					{/if}
				</a>
			</nav>

			<!-- Search Bar (Desktop) -->
			<div class="hidden lg:flex items-center flex-1 max-w-md mx-8">
				<div class="relative w-full">
					<input
						type="text"
						bind:value={searchQuery}
						on:keypress={handleKeyPress}
						placeholder={$i18n ? $i18n.t('Search products...') : 'Search products...'}
						class="w-full px-4 py-2 pl-10 pr-4 text-sm text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:border-transparent transition-all"
						style="background-color: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.3); --focus-ring-color: {primaryColor};"
						on:focus={(e) => {
							e.currentTarget.style.borderColor = '#FFFFFF';
							e.currentTarget.style.boxShadow = `0 0 0 2px rgba(255, 255, 255, 0.5)`;
							e.currentTarget.style.backgroundColor = '#FFFFFF';
						}}
						on:blur={(e) => {
							e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)';
							e.currentTarget.style.boxShadow = '';
							e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
						}}
					/>
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<svg
							class="h-5 w-5 text-gray-400"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
							/>
						</svg>
					</div>
					<button
						on:click={handleSearch}
						class="absolute inset-y-0 right-0 pr-3 flex items-center transition-colors"
						style="color: {primaryColor};"
						on:mouseenter={(e) => {
							e.currentTarget.style.opacity = '0.9';
						}}
						on:mouseleave={(e) => {
							e.currentTarget.style.opacity = '1';
						}}
					>
						<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 7l5 5m0 0l-5 5m5-5H6"
							/>
						</svg>
					</button>
				</div>
			</div>

			<!-- Right Actions -->
			<div class="flex items-center space-x-4">
				<!-- Cart Icon -->
				<div class="hidden md:block">
					<CartIcon />
				</div>

				<!-- Mobile Menu Button -->
				<button
					on:click={() => (mobileMenuOpen = !mobileMenuOpen)}
					class="md:hidden p-2 rounded-md text-white hover:bg-white/20 transition-colors"
					aria-label="Toggle menu"
				>
					{#if mobileMenuOpen}
						<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					{:else}
						<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 6h16M4 12h16M4 18h16"
							/>
						</svg>
					{/if}
				</button>
			</div>
		</div>

		<!-- Mobile Menu -->
		{#if mobileMenuOpen}
			<div class="md:hidden border-t border-white/20 py-4">
				<div class="space-y-4">
					<!-- Mobile Search -->
					<div class="relative">
						<input
							type="text"
							bind:value={searchQuery}
							on:keypress={handleKeyPress}
							placeholder={$i18n ? $i18n.t('Search products...') : 'Search products...'}
							class="w-full px-4 py-2 pl-10 pr-4 text-sm text-gray-900 rounded-lg focus:outline-none focus:ring-2 transition-all"
							style="background-color: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.3);"
							on:focus={(e) => {
								e.currentTarget.style.borderColor = '#FFFFFF';
								e.currentTarget.style.boxShadow = `0 0 0 2px rgba(255, 255, 255, 0.5)`;
								e.currentTarget.style.backgroundColor = '#FFFFFF';
							}}
							on:blur={(e) => {
								e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)';
								e.currentTarget.style.boxShadow = '';
								e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
							}}
						/>
						<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
							<svg
								class="h-5 w-5 text-gray-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
								/>
							</svg>
						</div>
					</div>

					<!-- Mobile Navigation -->
					<nav class="flex flex-col space-y-3">
						<a
							href="/public/shops"
							class="text-white font-medium px-2 py-1 rounded transition-colors {($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')
								? ''
								: ''}"
							style="color: {($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')
								? '#FFFFFF'
								: 'rgba(255, 255, 255, 0.9)'}; background-color: {($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')
								? 'rgba(255, 255, 255, 0.2)'
								: 'transparent'};"
							on:click={() => (mobileMenuOpen = false)}
							on:mouseenter={(e) => {
								e.currentTarget.style.color = '#FFFFFF';
								e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
							}}
							on:mouseleave={(e) => {
								if (($page.url.pathname === '/public/shops' || $page.url.pathname.startsWith('/public/shops/')) && !$page.url.pathname.includes('/products/')) {
									e.currentTarget.style.color = '#FFFFFF';
									e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
								} else {
									e.currentTarget.style.color = 'rgba(255, 255, 255, 0.9)';
									e.currentTarget.style.backgroundColor = 'transparent';
								}
							}}
						>
							{$i18n ? $i18n.t('Shops') : 'Shops'}
						</a>
						<a
							href="/public/cart"
							class="text-white font-medium px-2 py-1 rounded transition-colors flex items-center justify-between {$page.url.pathname === '/public/cart'
								? ''
								: ''}"
							style="color: {$page.url.pathname === '/public/cart'
								? '#FFFFFF'
								: 'rgba(255, 255, 255, 0.9)'}; background-color: {$page.url.pathname === '/public/cart'
								? 'rgba(255, 255, 255, 0.2)'
								: 'transparent'};"
							on:click={() => (mobileMenuOpen = false)}
							on:mouseenter={(e) => {
								e.currentTarget.style.color = '#FFFFFF';
								e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
							}}
							on:mouseleave={(e) => {
								if ($page.url.pathname === '/public/cart') {
									e.currentTarget.style.color = '#FFFFFF';
									e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
								} else {
									e.currentTarget.style.color = 'rgba(255, 255, 255, 0.9)';
									e.currentTarget.style.backgroundColor = 'transparent';
								}
							}}
						>
							<span>{$i18n ? $i18n.t('Cart') : 'Cart'}</span>
							{#if itemCount > 0}
								<span
									class="text-xs text-white px-2 py-0.5 rounded-full"
									style="background-color: rgba(255, 255, 255, 0.3); backdrop-filter: blur(10px);"
								>
									{itemCount}
								</span>
							{/if}
						</a>
					</nav>
				</div>
			</div>
		{/if}
	</div>
</header>
