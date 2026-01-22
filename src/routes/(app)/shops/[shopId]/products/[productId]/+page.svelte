<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getProductById } from '$lib/apis/products';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let product: any = null;
	let loading = true;

	const formatPrice = (price: number) =>
		new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(price);

	const toDisplayUrl = (u: string) => (u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`);

	$: imageUrls =
		product?.image_urls && Array.isArray(product.image_urls)
			? product.image_urls
			: product?.image_url
				? [product.image_url]
				: [];

	$: mainImageUrl = imageUrls.length > 0 ? toDisplayUrl(imageUrls[0]) : null;

	onMount(async () => {
		try {
			const shopId = $page.params.shopId;
			const productId = $page.params.productId;
			const res = await getProductById(localStorage.token, productId);
			if (!res) {
				toast.error($i18n.t('Product not found'));
				goto(`/shops/${shopId}/products`);
				return;
			}

			// sécurité: le produit doit appartenir au shop de l'URL
			if (res.shop_id !== shopId) {
				toast.error($i18n.t('Product not found'));
				goto(`/shops/${shopId}/products`);
				return;
			}

			product = res;
		} catch (error) {
			toast.error(`${error}`);
			const shopId = $page.params.shopId;
			goto(`/shops/${shopId}/products`);
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if product}
	<div class="max-w-4xl mx-auto p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				{#if mainImageUrl}
					<img src={mainImageUrl} alt={product.name} class="w-full rounded-lg" />
				{:else}
					<div class="w-full h-96 bg-gray-200 dark:bg-gray-700 flex items-center justify-center rounded-lg">
						<span class="text-gray-400 dark:text-gray-500">{$i18n.t('No Image')}</span>
					</div>
				{/if}

				{#if imageUrls.length > 1}
					<div class="mt-3 grid grid-cols-4 gap-2">
						{#each imageUrls.slice(1) as u (u)}
							<img src={toDisplayUrl(u)} alt="thumb" class="w-full h-20 object-cover rounded-lg" />
						{/each}
					</div>
				{/if}
			</div>

			<div>
				<h1 class="text-3xl font-bold mb-4">{product.name}</h1>
				{#if product.description}
					<p class="text-gray-600 dark:text-gray-400 mb-4">{product.description}</p>
				{/if}

				<div class="mb-4">
					<span class="text-3xl font-bold text-blue-600 dark:text-blue-400">
						{formatPrice(product.price)}
					</span>
				</div>

				{#if product.stock !== undefined}
					<div class="mb-4">
						<span
							class="text-lg {product.stock > 0
								? 'text-green-600 dark:text-green-400'
								: 'text-red-600 dark:text-red-400'}"
						>
							{product.stock > 0 ? `${product.stock} ${$i18n.t('in stock')}` : $i18n.t('Out of stock')}
						</span>
					</div>
				{/if}

				{#if product.category}
					<div class="mb-4">
						<span class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
							{product.category}
						</span>
					</div>
				{/if}

				<div class="mb-4">
					<a href="/shops/{product.shop_id}" class="text-blue-600 dark:text-blue-400 hover:underline">
						{$i18n.t('View Shop')}
					</a>
				</div>

				{#if $user && ($user.id === product.user_id || $user.role === 'admin')}
					<div class="mt-6 flex gap-4">
						<button
							on:click={() => goto(`/shops/${product.shop_id}/products/${product.id}/edit`)}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
						>
							{$i18n.t('Edit Product')}
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

