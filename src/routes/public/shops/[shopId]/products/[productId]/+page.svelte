<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { getPublicShopById } from '$lib/apis/shops';
	import { getPublicProductById as getPublicProduct } from '$lib/apis/products';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { currentShopName } from '$lib/stores/currentShop';
	import { currentShopImage } from '$lib/stores/currentShopImage';
	import { shopColors } from '$lib/stores/shopColors';
	import { cart } from '$lib/stores/cart';
	import { toast } from 'svelte-sonner';
	import Loader from '$lib/components/common/Loader.svelte';
	import ImageCarousel from '$lib/components/common/ImageCarousel.svelte';

	$: primaryColor = $shopColors.primary || '#3B82F6'; // Default blue
	$: secondaryColor = $shopColors.secondary || '#F97316'; // Default orange

	const i18n = getContext('i18n');

	let product = null;
	let shop = null;
	let loading = true;

	$: productImageUrls = (() => {
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
					.map(url => url.startsWith('http') ? url : `${WEBUI_API_BASE_URL}/files/${url}/content`);
			}
		}
		return [];
	})();

	$: currentImage = productImageUrls.length > 0 ? productImageUrls[0] : null;

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
				// Set shop name in store for Header and Footer
				if (shopRes.name) {
					currentShopName.set(shopRes.name);
				}
				// Set shop image in store for Header
				if (shopRes.image_url) {
					currentShopImage.set(shopRes.image_url);
				} else {
					currentShopImage.set(null);
				}
				// Set shop colors in store
				shopColors.set({
					primary: shopRes.primary_color || null,
					secondary: shopRes.secondary_color || null
				});
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

	onDestroy(() => {
		// Clear shop name, image and colors when leaving the page
		currentShopName.set(null);
		currentShopImage.set(null);
		shopColors.set({ primary: null, secondary: null });
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
					<div class="p-4">
						<div class="w-full h-full min-h-[500px]">
							<ImageCarousel
								images={productImageUrls}
								showThumbnails={true}
								showIndicators={true}
								showArrows={true}
								autoPlay={false}
								enableZoom={true}
								transitionType="fade"
							/>
						</div>
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
											image_urls: productImageUrls.length > 0 ? productImageUrls : undefined,
											quantity: 1
										});
										toast.success($i18n ? $i18n.t('Product added to cart') : 'Product added to cart');
									}
								}}
								class="w-full px-6 py-3 text-white rounded-lg transition font-semibold"
								style="background: linear-gradient(to right, {primaryColor} 0%, {secondaryColor} 100%);"
								on:mouseenter={(e) => {
									e.currentTarget.style.opacity = '0.9';
								}}
								on:mouseleave={(e) => {
									e.currentTarget.style.opacity = '1';
								}}
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
			<a
				href="/public/shops"
				class="transition-colors"
				style="color: {primaryColor};"
				on:mouseenter={(e) => {
					e.currentTarget.style.opacity = '0.8';
				}}
				on:mouseleave={(e) => {
					e.currentTarget.style.opacity = '1';
				}}
			>
				{$i18n ? $i18n.t('Back to shops') : 'Back to shops'}
			</a>
		</div>
	</div>
{/if}
