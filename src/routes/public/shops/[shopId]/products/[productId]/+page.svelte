<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { getPublicShopById } from '$lib/apis/shops';
	import { getPublicProductById as getPublicProduct } from '$lib/apis/products';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { cart } from '$lib/stores/cart';
	import { toast } from 'svelte-sonner';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let product = null;
	let shop = null;
	let loading = true;
	let selectedImageIndex = 0;

	$: productImageUrls = product?.image_urls && Array.isArray(product.image_urls)
		? product.image_urls
		: product?.image_url
			? [product.image_url]
			: [];

	$: currentImage = productImageUrls[selectedImageIndex]
		? productImageUrls[selectedImageIndex].startsWith('http')
			? productImageUrls[selectedImageIndex]
			: `${WEBUI_API_BASE_URL}/files/${productImageUrls[selectedImageIndex]}/content`
		: null;

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const loadData = async () => {
		loading = true;
		try {
			const shopId = $page.params.shopId;
			const productId = $page.params.productId;

			const [shopRes, productRes] = await Promise.all([
				getPublicShopById(shopId),
				getPublicProduct(productId)
			]);

			if (shopRes) {
				shop = shopRes;
			}
			if (productRes) {
				product = productRes;
			}
		} catch (error) {
			console.error('Error loading data:', error);
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>{product ? product.name : 'Product'} • {$i18n ? $i18n.t('Product') : 'Product'}</title>
	<meta name="description" content={product?.description || 'Découvrez ce produit'} />
	{#if product}
		<meta property="og:title" content={product.name} />
		<meta property="og:description" content={product.description || ''} />
		{#if currentImage}
			<meta property="og:image" content={currentImage} />
		{/if}
		<meta property="og:type" content="product" />
		{#if product.price}
			<meta property="product:price:amount" content={product.price.toString()} />
			<meta property="product:price:currency" content={product.currency || 'EUR'} />
		{/if}
	{/if}
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center min-h-screen">
		<Loader />
	</div>
{:else if product}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
			<div class="mb-4">
				<a
					href={shop ? `/public/shops/${shop.id}` : '/public/shops'}
					class="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
				>
					← {$i18n ? $i18n.t('Back to shop') : 'Back to shop'}
				</a>
			</div>

			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-0">
					<div class="relative">
						{#if currentImage}
							<img
								src={currentImage}
								alt={product.name}
								class="w-full h-full min-h-[500px] object-cover"
							/>
						{:else}
							<div class="w-full h-full min-h-[500px] bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
							<span class="text-white text-lg font-medium">{$i18n ? $i18n.t('No Image') : 'No Image'}</span>
						</div>
						{/if}

						{#if productImageUrls.length > 1}
							<div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex gap-2">
								{#each productImageUrls as url, idx}
									<button
										on:click={() => {
											selectedImageIndex = idx;
										}}
										class="w-16 h-16 rounded-lg overflow-hidden border-2 {selectedImageIndex === idx
											? 'border-blue-500'
											: 'border-gray-300 dark:border-gray-600'}"
									>
										<img
											src={url.startsWith('http') ? url : `${WEBUI_API_BASE_URL}/files/${url}/content`}
											alt="Thumbnail {idx + 1}"
											class="w-full h-full object-cover"
										/>
									</button>
								{/each}
							</div>
						{/if}
					</div>

					<div class="p-8 flex flex-col">
						<div class="flex-1">
							<h1 class="text-4xl font-bold mb-4 text-gray-900 dark:text-gray-100">
								{product.name}
							</h1>

							<div class="mb-6">
								<span class="text-3xl font-bold bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
									{formatPrice(product.price, product.currency)}
								</span>
							</div>

							{#if product.description}
								<div class="mb-6">
									<h2 class="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">
										{$i18n ? $i18n.t('Description') : 'Description'}
									</h2>
									<p class="text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-line">
										{product.description}
									</p>
								</div>
							{/if}

							<div class="flex flex-wrap gap-2 mb-6">
								{#if product.category}
									<span class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm font-medium">
										{product.category}
									</span>
								{/if}
								{#if product.currency}
									<span class="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-sm font-medium">
										{product.currency}
									</span>
								{/if}
								{#if product.stock !== undefined}
									<span
										class="px-3 py-1 rounded-full text-sm font-medium {product.stock > 0
											? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
											: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'}"
									>
										{product.stock > 0
											? `${product.stock} ${$i18n ? $i18n.t('in stock') : 'in stock'}`
											: ($i18n ? $i18n.t('Out of stock') : 'Out of stock')}
									</span>
								{/if}
							</div>
						</div>

						<div class="mt-6">
							<button
								on:click={() => {
									if (product) {
										cart.addItem({
											product_id: product.id,
											shop_id: product.shop_id,
											name: product.name,
											price: product.price,
											currency: product.currency || 'EUR',
											image_url: productImageUrls[0] || product.image_url,
											quantity: 1
										});
										toast.success($i18n ? $i18n.t('Product added to cart') : 'Product added to cart');
									}
								}}
								class="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold"
							>
								{$i18n ? $i18n.t('Add to Cart') : 'Add to Cart'}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="flex items-center justify-center min-h-screen">
		<div class="text-center">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
				{$i18n ? $i18n.t('Product not found') : 'Product not found'}
			</h1>
			<a href="/public/shops" class="text-blue-600 hover:text-blue-800">
				{$i18n ? $i18n.t('Back to shops') : 'Back to shops'}
			</a>
		</div>
	</div>
{/if}
