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
	<div class="max-w-2xl mx-auto p-6">
		<h1 class="text-2xl font-bold mb-6">{$i18n.t('Edit Product')}</h1>

		<form
			on:submit|preventDefault={handleSubmit}
			class="space-y-4"
		>
			<div>
				<label class="block text-sm font-medium mb-2">
					{$i18n.t('Product Name')} <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					bind:value={name}
					required
					placeholder={$i18n.t('Enter product name')}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
				/>
			</div>

			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('Description')}</label>
				<textarea
					bind:value={description}
					rows="4"
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
				></textarea>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div>
					<label class="block text-sm font-medium mb-2">
						{$i18n.t('Price')} <span class="text-red-500">*</span>
					</label>
					<input
						type="number"
						bind:value={price}
						min="0"
						step="0.01"
						required
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium mb-2">{$i18n.t('Stock')}</label>
					<input
						type="number"
						bind:value={stock}
						min="0"
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
					/>
				</div>
			</div>

			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('Product Images')}</label>
				<input
					type="file"
					accept="image/*"
					multiple
					on:change={handleImagesUpload}
					disabled={uploadingImages}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-gray-800 dark:file:text-gray-300"
				/>
				{#if uploadingImages}
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{$i18n.t('Uploading images...')}</p>
				{/if}
				{#if imagePreviews.length > 0}
					<div class="mt-3 grid grid-cols-3 gap-2">
						{#each imagePreviews as p (p)}
							<img src={p} alt="preview" class="w-full h-24 object-cover rounded-lg" />
						{/each}
					</div>
				{/if}
			</div>

			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('Category')}</label>
				<select
					bind:value={category}
					class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
				>
					<option value="">{$i18n.t('Select a category')}</option>
					<option value="electronics">{$i18n.t('Electronics')}</option>
					<option value="clothing">{$i18n.t('Clothing')}</option>
					<option value="food">{$i18n.t('Food')}</option>
					<option value="books">{$i18n.t('Books')}</option>
					<option value="other">{$i18n.t('Other')}</option>
				</select>
			</div>

			<div class="flex gap-4">
				<button
					type="submit"
					disabled={loading}
					class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{loading ? $i18n.t('Updating...') : $i18n.t('Update Product')}
				</button>
				<button
					type="button"
					on:click={() => goto(`/shops/${product.shop_id}/products/${product.id}`)}
					class="px-6 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition"
				>
					{$i18n.t('Cancel')}
				</button>
			</div>
		</form>
	</div>
{/if}
