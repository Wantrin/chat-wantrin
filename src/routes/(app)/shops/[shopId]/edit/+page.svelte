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
	<div class="max-w-2xl mx-auto p-6">
		<h1 class="text-2xl font-bold mb-6">{$i18n.t('Edit Shop')}</h1>

		<form
			on:submit|preventDefault={handleSubmit}
			class="space-y-4"
		>
			<div>
				<label class="block text-sm font-medium mb-2">
					{$i18n.t('Shop Name')} <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					bind:value={name}
					required
					placeholder={$i18n.t('Enter shop name')}
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

			<div>
				<label class="block text-sm font-medium mb-2">{$i18n.t('Shop Image')}</label>
				<div class="space-y-2">
					<input
						type="file"
						accept="image/*"
						on:change={handleImageUpload}
						disabled={uploadingImage}
						class="w-full px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-gray-800 dark:file:text-gray-300"
					/>
					{#if uploadingImage}
						<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Uploading image...')}</p>
					{/if}
					{#if imagePreview}
						<div class="mt-2">
							<img
								src={imagePreview}
								alt="Preview"
								class="max-w-xs max-h-48 rounded-lg object-cover"
							/>
						</div>
					{/if}
				</div>
			</div>

			<div class="flex gap-4">
				<button
					type="submit"
					disabled={loading}
					class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
				>
					{loading ? $i18n.t('Updating...') : $i18n.t('Update Shop')}
				</button>
				<button
					type="button"
					on:click={() => goto(`/shops/${shop.id}`)}
					class="px-6 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition"
				>
					{$i18n.t('Cancel')}
				</button>
			</div>
		</form>
	</div>
{/if}
