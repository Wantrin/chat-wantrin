<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { user, showSidebar } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let shop = null;
	let loading = true;

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
						<div class="w-full h-full min-h-[400px] bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
							<span class="text-white text-lg font-medium">{$i18n.t('No Image')}</span>
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
					{#if $user && ($user.id === shop.user_id || $user.role === 'admin')}
						<div class="mt-6 flex gap-3 flex-wrap">
							<button
								on:click={() => goto(`/shops/${shop.id}/edit`)}
								class="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
							>
								{$i18n.t('Edit Shop')}
							</button>
							<button
								on:click={() => goto(`/shops/${shop.id}/products/create`)}
								class="px-6 py-3 bg-gradient-to-r from-blue-500 to-orange-600 hover:from-blue-600 hover:to-orange-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
							>
								{$i18n.t('Add Product')}
							</button>
							<button
								on:click={() => goto(`/shops/${shop.id}/products`)}
								class="px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
							>
								{$i18n.t('View Products')}
							</button>
						</div>
					{:else}
						<div class="mt-6">
							<button
								on:click={() => goto(`/shops/${shop.id}/products`)}
								class="px-8 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
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
{/if}
