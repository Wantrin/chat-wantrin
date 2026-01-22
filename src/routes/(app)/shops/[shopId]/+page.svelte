<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import { user } from '$lib/stores';
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
	<div class="max-w-4xl mx-auto p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				{#if imageUrl}
					<img
						src={imageUrl}
						alt={shop.name}
						class="w-full rounded-lg"
					/>
				{:else}
					<div class="w-full h-96 bg-gray-200 dark:bg-gray-700 flex items-center justify-center rounded-lg">
						<span class="text-gray-400 dark:text-gray-500">{$i18n.t('No Image')}</span>
					</div>
				{/if}
			</div>
			<div>
				<h1 class="text-3xl font-bold mb-4">{shop.name}</h1>
				{#if shop.description}
					<p class="text-gray-600 dark:text-gray-400 mb-4">{shop.description}</p>
				{/if}
				{#if $user && ($user.id === shop.user_id || $user.role === 'admin')}
					<div class="mt-6 flex gap-4 flex-wrap">
						<button
							on:click={() => goto(`/shops/${shop.id}/edit`)}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
						>
							{$i18n.t('Edit Shop')}
						</button>
						<button
							on:click={() => goto(`/shops/${shop.id}/products/create`)}
							class="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition"
						>
							{$i18n.t('Add Product')}
						</button>
						<button
							on:click={() => goto(`/shops/${shop.id}/products`)}
							class="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
						>
							{$i18n.t('View Products')}
						</button>
					</div>
				{:else}
					<div class="mt-6">
						<button
							on:click={() => goto(`/shops/${shop.id}/products`)}
							class="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
						>
							{$i18n.t('View Products')}
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
