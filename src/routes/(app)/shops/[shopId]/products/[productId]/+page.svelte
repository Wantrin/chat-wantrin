<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getProductById } from '$lib/apis/products';
	import { user, showSidebar } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ImageCarousel from '$lib/components/common/ImageCarousel.svelte';

	const i18n = getContext('i18n');

	let product: any = null;
	let loading = true;

	const formatPrice = (price: number, currency: string = 'EUR') =>
		new Intl.NumberFormat('fr-FR', { style: 'currency', currency: currency || 'EUR' }).format(price);

	const toDisplayUrl = (u: string) => (u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`);

	$: imageUrls = (() => {
		if (product?.image_urls) {
			let urls = product.image_urls;
			if (typeof urls === 'string') {
				try {
					urls = JSON.parse(urls);
				} catch (e) {
					return [];
				}
			}
			if (Array.isArray(urls)) {
				return urls
					.filter(url => url && typeof url === 'string' && url.trim() !== '')
					.map(url => toDisplayUrl(url));
			}
		}
		return [];
	})();

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
	<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full overflow-y-auto">
		<div class="max-w-6xl mx-auto p-6 w-full">
		<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-0">
				<div class="p-4 bg-gray-100 dark:bg-gray-900">
					<div class="w-full h-full min-h-[500px]">
						<ImageCarousel
							images={imageUrls}
							showThumbnails={true}
							showIndicators={true}
							showArrows={true}
							autoPlay={false}
						/>
					</div>
				</div>

				<div class="p-8 flex flex-col justify-between">
					<div>
						<h1 class="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
							{product.name}
						</h1>
						{#if product.description}
							<p class="text-gray-600 dark:text-gray-400 mb-6 text-lg leading-relaxed">{product.description}</p>
						{/if}

						<div class="mb-6">
							<span class="text-4xl font-bold bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
								{formatPrice(product.price, product.currency)}
							</span>
						</div>

				{#if product.stock !== undefined}
					<div class="mb-6">
						<span
							class="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold {product.stock > 0
								? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
								: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'}"
						>
							{product.stock > 0 ? `${product.stock} ${$i18n.t('in stock')}` : $i18n.t('Out of stock')}
						</span>
					</div>
				{/if}

				<div class="mb-6 flex gap-2 flex-wrap">
					{#if product.category}
						<span class="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm font-medium">
							{product.category}
						</span>
					{/if}
					{#if product.currency}
						<span class="px-4 py-2 bg-gradient-to-r from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 text-green-700 dark:text-green-400 rounded-full text-sm font-medium">
							{product.currency}
						</span>
					{/if}
				</div>

				<div class="mb-6">
					<a href="/shops/{product.shop_id}" class="inline-flex items-center gap-2 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors">
						<span>{$i18n.t('View Shop')}</span>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</a>
				</div>
					</div>
					{#if $user && ($user.id === product.user_id || $user.role === 'admin')}
						<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
							<button
								on:click={() => goto(`/shops/${product.shop_id}/products/${product.id}/edit`)}
								class="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5"
							>
								{$i18n.t('Edit Product')}
							</button>
						</div>
					{/if}
				</div>
			</div>
		</div>
		</div>
	</div>
{/if}

