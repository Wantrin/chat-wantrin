<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getProductById, updateProductById } from '$lib/apis/products';
	import { searchShops } from '$lib/apis/shops';
	import { uploadFile } from '$lib/apis/files';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let product = null;
	let name = '';
	let description = '';
	let price = 0;
	let image_urls: string[] = [];
	let imageFiles: File[] = [];
	let imageFileIds: string[] = [];
	let imagePreviews: string[] = [];
	let uploadingImages = false;
	let stock = 0;
	let category = '';
	let currency = '';
	let shop_id = '';
	let shops = [];
	let loading = false;
	let loadingProduct = true;
	let loadingShops = true;

	const toDisplayUrl = (u: string) => (u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`);

	const handleImagesUpload = async (event: Event) => {
		const target = event.target as HTMLInputElement;
		const files = Array.from(target.files ?? []);
		if (files.length === 0) return;

		if (files.some((f) => !f.type.startsWith('image/'))) {
			toast.error($i18n.t('Please upload image files only'));
			return;
		}

		imageFiles = files;
		imagePreviews = files.map((f) => URL.createObjectURL(f));

		uploadingImages = true;
		try {
			const uploaded = await Promise.all(
				files.map((f) => uploadFile(localStorage.token, f, null, false))
			);
			imageFileIds = uploaded.filter(Boolean).map((u) => u.id);
			toast.success($i18n.t('Images uploaded successfully'));
		} catch (error) {
			toast.error(`${error}`);
			imageFileIds = [];
			imageFiles = [];
			imagePreviews = [];
		} finally {
			uploadingImages = false;
		}
	};

	const handleSubmit = async () => {
		if (!name || price <= 0 || !shop_id || (imageFileIds.length === 0 && image_urls.length === 0)) {
			toast.error($i18n.t('Please fill in all required fields'));
			return;
		}

		loading = true;
		try {
			const res = await updateProductById(localStorage.token, $page.params.id, {
				name,
				description: description || null,
				price,
				image_urls: imageFileIds.length > 0 ? imageFileIds : image_urls,
				stock,
				category: category || null,
				currency: currency || null,
				shop_id: shop_id
			});

			if (res) {
				toast.success($i18n.t('Product updated successfully'));
				goto(`/shops/${res.shop_id}/products/${res.id}`);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/products');
			return;
		}

		try {
			const res = await getProductById(localStorage.token, $page.params.id);
			if (res) {
				product = res;
				if ($user.id !== res.user_id && $user.role !== 'admin') {
					toast.error($i18n.t('You do not have permission to edit this product'));
					goto(`/shops/${res.shop_id}/products/${res.id}`);
					return;
				}
				name = res.name;
				description = res.description || '';
				price = res.price;
				image_urls = Array.isArray(res.image_urls)
					? res.image_urls
					: res.image_url
						? [res.image_url]
						: [];
				imagePreviews = image_urls.map((u) => toDisplayUrl(u));
				stock = res.stock || 0;
				category = res.category || '';
				currency = res.currency || '';
				shop_id = res.shop_id || '';

				// Charger les shops de l'utilisateur
				try {
					const shopsRes = await searchShops(localStorage.token, null, 'created', null, null, null, 1);
					if (shopsRes && shopsRes.items) {
						shops = shopsRes.items;
					}
				} catch (error) {
					console.error('Error loading shops:', error);
				} finally {
					loadingShops = false;
				}
			} else {
				toast.error($i18n.t('Product not found'));
				goto('/products');
			}
		} catch (error) {
			toast.error(`${error}`);
			goto('/products');
		} finally {
			loadingProduct = false;
		}
	});
</script>

{#if loadingProduct}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if product}
	<div class="max-w-3xl mx-auto p-6">
		<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
			<h1 class="text-3xl font-bold mb-8 bg-gradient-to-r from-orange-600 to-orange-600 dark:from-orange-400 dark:to-orange-400 bg-clip-text text-transparent">
				{$i18n.t('Edit Product')}
			</h1>

			<form
				on:submit|preventDefault={handleSubmit}
				class="space-y-6"
			>
				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
						{$i18n.t('Product Name')} <span class="text-red-500">*</span>
					</label>
					<input
						type="text"
						bind:value={name}
						required
						placeholder={$i18n.t('Enter product name')}
						class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md"
					/>
				</div>

				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Description')}</label>
					<textarea
						bind:value={description}
						rows="4"
						placeholder={$i18n.t('Enter product description')}
						class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md resize-none"
					></textarea>
				</div>

				<div class="grid grid-cols-2 gap-6">
					<div>
						<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
							{$i18n.t('Price')} <span class="text-red-500">*</span>
						</label>
						<input
							type="number"
							bind:value={price}
							min="0"
							step="0.01"
							required
							placeholder="0.00"
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md"
						/>
					</div>

					<div>
						<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Stock')}</label>
						<input
							type="number"
							bind:value={stock}
							min="0"
							placeholder="0"
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md"
						/>
					</div>
				</div>

				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Product Images')}</label>
					<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-6 hover:border-orange-400 dark:hover:border-orange-500 transition-colors">
						<input
							type="file"
							accept="image/*"
							multiple
							on:change={handleImagesUpload}
							disabled={uploadingImages}
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-gradient-to-r file:from-orange-500 file:to-orange-500 file:text-white hover:file:from-orange-600 hover:file:to-orange-600 transition-all shadow-sm hover:shadow-md cursor-pointer"
						/>
						{#if uploadingImages}
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{$i18n.t('Uploading images...')}</p>
						{/if}
						{#if imagePreviews.length > 0}
							<div class="mt-4 grid grid-cols-3 gap-3">
								{#each imagePreviews as p (p)}
									<div class="relative group">
										<img src={p} alt="preview" class="w-full h-32 object-cover rounded-xl shadow-md group-hover:shadow-xl transition-all" />
										<div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 rounded-xl transition-colors"></div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>

				<div class="grid grid-cols-2 gap-6">
					<div>
						<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Category')}</label>
						<select
							bind:value={category}
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md font-medium"
						>
						<option value="">{$i18n.t('Select a category')}</option>
						<option value="electronics">{$i18n.t('Electronics')}</option>
						<option value="clothing">{$i18n.t('Clothing')}</option>
						<option value="food">{$i18n.t('Food')}</option>
						<option value="books">{$i18n.t('Books')}</option>
						<option value="other">{$i18n.t('Other')}</option>
					</select>
				</div>

					<div>
						<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Currency')}</label>
						<select
							bind:value={currency}
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md font-medium"
						>
							<option value="">{$i18n.t('Select a currency')}</option>
							<option value="EUR">EUR (€)</option>
							<option value="USD">USD ($)</option>
							<option value="GBP">GBP (£)</option>
							<option value="JPY">JPY (¥)</option>
							<option value="CNY">CNY (¥)</option>
							<option value="INR">INR (₹)</option>
							<option value="CAD">CAD ($)</option>
							<option value="AUD">AUD ($)</option>
							<option value="CHF">CHF (Fr)</option>
							<option value="SEK">SEK (kr)</option>
							<option value="NOK">NOK (kr)</option>
							<option value="DKK">DKK (kr)</option>
							<option value="PLN">PLN (zł)</option>
							<option value="RUB">RUB (₽)</option>
							<option value="BRL">BRL (R$)</option>
							<option value="MXN">MXN ($)</option>
							<option value="ZAR">ZAR (R)</option>
							<option value="KRW">KRW (₩)</option>
							<option value="SGD">SGD ($)</option>
							<option value="HKD">HKD ($)</option>
							<option value="NZD">NZD ($)</option>
							<option value="XOF">XOF (CFA)</option>
						</select>
					</div>
				</div>

				{#if loadingShops}
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading shops...')}</div>
				{:else if shops.length > 0}
					<div>
						<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
							{$i18n.t('Shop')} <span class="text-red-500">*</span>
						</label>
						<select
							bind:value={shop_id}
							required
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md font-medium"
						>
							<option value="">{$i18n.t('Select a shop')}</option>
							{#each shops as shop (shop.id)}
								<option value={shop.id}>{shop.name}</option>
							{/each}
						</select>
					</div>
				{/if}

				<div class="flex gap-4 pt-4">
					<button
						type="submit"
						disabled={loading}
						class="flex-1 px-6 py-3 bg-gradient-to-r from-orange-600 to-orange-600 hover:from-orange-700 hover:to-orange-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none disabled:shadow-lg"
					>
						{loading ? $i18n.t('Updating...') : $i18n.t('Update Product')}
					</button>
					<button
						type="button"
						on:click={() => goto(`/shops/${product.shop_id}/products/${product.id}`)}
						class="px-6 py-3 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg font-semibold border-2 border-gray-200 dark:border-gray-600"
					>
						{$i18n.t('Cancel')}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
