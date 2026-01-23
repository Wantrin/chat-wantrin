<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { user, showSidebar } from '$lib/stores';
	import { shopColors } from '$lib/stores/shopColors';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ShareShopModal from '$lib/components/shops/ShareShopModal.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let loading = true;
	let showShareModal = false;

	$: primaryColor = shop?.primary_color || '#3B82F6'; // Default blue
	$: secondaryColor = shop?.secondary_color || '#F97316'; // Default orange

	$: shopIdentifier = shop ? (shop.url || shop.id) : null;

	$: imageUrl = shop?.image_url
		? shop.image_url.startsWith('http')
			? shop.image_url
			: `${WEBUI_API_BASE_URL}/files/${shop.image_url}/content`
		: null;

	onMount(async () => {
		try {
			const shopId = $page.params.shopId;
			const res = await getShopById(localStorage.token, shopId);
			if (res) {
				shop = res;
				// Set shop colors
				shopColors.set({
					primary: res.primary_color || null,
					secondary: res.secondary_color || null
				});
			} else {
				toast.error($i18n.t('Shop not found'));
				goto('/shops');
			}
		} catch (error) {
			toast.error(`${error}`);
			goto('/shops');
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if shop}
	<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full overflow-y-auto">
		<div class="max-w-6xl mx-auto p-6 w-full">
		<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-0">
				<div class="relative overflow-hidden">
					{#if imageUrl}
						<img
							src={imageUrl}
							alt={shop.name}
							class="w-full h-full min-h-[400px] object-cover"
						/>
					{:else}
						<div
							class="w-full h-full min-h-[400px] flex items-center justify-center"
							style="background: linear-gradient(135deg, {primaryColor} 0%, {secondaryColor} 50%, {primaryColor} 100%);"
						>
							<span class="text-white text-lg font-medium">{$i18n.t('No Image')}</span>
						</div>
					{/if}
					<div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
				</div>
				<div class="p-8 flex flex-col justify-between">
					<div>
						<h1
							class="text-4xl font-bold mb-4 bg-clip-text text-transparent"
							style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%); -webkit-background-clip: text; background-clip: text;"
						>
							{shop.name}
						</h1>
						{#if shop.description}
							<p class="text-gray-600 dark:text-gray-400 mb-6 text-lg leading-relaxed">{shop.description}</p>
						{/if}
					</div>
					{#if $user && ($user.id === shop.user_id || $user.role === 'admin')}
						<div class="mt-6 flex gap-3 flex-wrap">
							<button
								on:click={() => goto(`/shops/${shopIdentifier}/edit`)}
								class="px-6 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
								style="background: linear-gradient(to right, {primaryColor} 0%, {primaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
							>
								{$i18n.t('Edit Shop')}
							</button>
							<button
								on:click={() => goto(`/shops/${shopIdentifier}/products/create`)}
								class="px-6 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
								style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
							>
								{$i18n.t('Add Product')}
							</button>
							<button
								on:click={() => goto(`/shops/${shopIdentifier}/products`)}
								class="px-6 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
								style="background: linear-gradient(to right, {secondaryColor} 0%, {secondaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
							>
								{$i18n.t('View Products')}
							</button>
							<button
								on:click={() => goto(`/shops/${shopIdentifier}/orders`)}
								class="px-6 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
								style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%); opacity: 0.8;"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '0.8';
								}}
							>
								{$i18n.t('View Orders')}
							</button>
							<button
								on:click={() => {
									showShareModal = true;
								}}
								class="px-6 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5 flex items-center gap-2"
								style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
							>
								<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
								</svg>
								{$i18n.t('Share Shop')}
							</button>
						</div>
					{:else}
						<div class="mt-6">
							<button
								on:click={() => goto(`/shops/${shopIdentifier}/products`)}
								class="px-8 py-3 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
								style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
							>
								{$i18n.t('View Products')}
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
		</div>
	</div>

	<ShareShopModal bind:show={showShareModal} {shop} />
{/if}
