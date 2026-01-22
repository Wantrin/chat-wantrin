<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getShopById, updateShopById } from '$lib/apis/shops';
	import { uploadFile } from '$lib/apis/files';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	let shop = null;
	let name = '';
	let description = '';
	let imageFileId: string | null = null;
	let imagePreview: string | null = null;
	let imageFile: File | null = null;
	let loading = false;
	let loadingShop = true;
	let uploadingImage = false;

	const handleImageUpload = async (event: Event) => {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;

		// Vérifier que c'est une image
		if (!file.type.startsWith('image/')) {
			toast.error($i18n.t('Please upload an image file'));
			return;
		}

		imageFile = file;
		imagePreview = URL.createObjectURL(file);

		// Uploader l'image
		uploadingImage = true;
		try {
			const uploadedFile = await uploadFile(localStorage.token, file, null, false);
			if (uploadedFile && uploadedFile.id) {
				imageFileId = uploadedFile.id;
				toast.success($i18n.t('Image uploaded successfully'));
			} else {
				toast.error($i18n.t('Failed to upload image'));
				imageFile = null;
				imagePreview = null;
			}
		} catch (error) {
			toast.error(`${error}`);
			imageFile = null;
			imagePreview = null;
		} finally {
			uploadingImage = false;
		}
	};

	const handleSubmit = async () => {
		if (!name) {
			toast.error($i18n.t('Please fill in all required fields'));
			return;
		}

		loading = true;
		try {
			const shopId = $page.params.shopId;
			const res = await updateShopById(localStorage.token, shopId, {
				name,
				description: description || null,
				image_url: imageFileId || shop.image_url || null
			});

			if (res) {
				toast.success($i18n.t('Shop updated successfully'));
				goto(`/shops/${res.id}`);
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	onMount(async () => {
		if (!$user) {
			goto('/shops');
			return;
		}

		try {
			const shopId = $page.params.shopId;
			const res = await getShopById(localStorage.token, shopId);
			if (res) {
				shop = res;
				if ($user.id !== res.user_id && $user.role !== 'admin') {
					toast.error($i18n.t('You do not have permission to edit this shop'));
					goto('/shops');
					return;
				}
				name = res.name;
				description = res.description || '';
				imageFileId = res.image_url || null;
				if (imageFileId && !imageFileId.startsWith('http')) {
					imagePreview = `${WEBUI_API_BASE_URL}/files/${imageFileId}/content`;
				} else if (imageFileId) {
					imagePreview = imageFileId;
				}
			} else {
				toast.error($i18n.t('Shop not found'));
				goto('/shops');
			}
		} catch (error) {
			toast.error(`${error}`);
			goto('/shops');
		} finally {
			loadingShop = false;
		}
	});
</script>

{#if loadingShop}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if shop}
	<div class="max-w-3xl mx-auto p-6">
		<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
			<h1 class="text-3xl font-bold mb-8 bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
				{$i18n.t('Edit Shop')}
			</h1>

			<form
				on:submit|preventDefault={handleSubmit}
				class="space-y-6"
			>
				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
						{$i18n.t('Shop Name')} <span class="text-red-500">*</span>
					</label>
					<input
						type="text"
						bind:value={name}
						required
						placeholder={$i18n.t('Enter shop name')}
						class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all shadow-sm hover:shadow-md"
					/>
				</div>

				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Description')}</label>
					<textarea
						bind:value={description}
						rows="4"
						placeholder={$i18n.t('Enter shop description')}
						class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all shadow-sm hover:shadow-md resize-none"
					></textarea>
				</div>

				<div>
					<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">{$i18n.t('Shop Image')}</label>
					<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-6 hover:border-blue-400 dark:hover:border-blue-500 transition-colors">
						<input
							type="file"
							accept="image/*"
							on:change={handleImageUpload}
							disabled={uploadingImage}
							class="w-full px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-gradient-to-r file:from-blue-500 file:to-orange-500 file:text-white hover:file:from-blue-600 hover:file:to-orange-600 transition-all shadow-sm hover:shadow-md cursor-pointer"
						/>
						{#if uploadingImage}
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{$i18n.t('Uploading image...')}</p>
						{/if}
						{#if imagePreview}
							<div class="mt-4">
								<img
									src={imagePreview}
									alt="Preview"
									class="max-w-xs max-h-48 rounded-xl object-cover shadow-lg"
								/>
							</div>
						{/if}
					</div>
				</div>

				<div class="flex gap-4 pt-4">
					<button
						type="submit"
						disabled={loading}
						class="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-orange-600 hover:from-blue-700 hover:to-orange-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none disabled:shadow-lg"
					>
						{loading ? $i18n.t('Updating...') : $i18n.t('Update Shop')}
					</button>
					<button
						type="button"
						on:click={() => goto(`/shops/${shop.id}`)}
						class="px-6 py-3 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg font-semibold border-2 border-gray-200 dark:border-gray-600"
					>
						{$i18n.t('Cancel')}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
