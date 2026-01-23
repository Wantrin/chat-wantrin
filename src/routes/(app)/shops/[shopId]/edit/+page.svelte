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
	import ShopAccessControl from '$lib/components/shops/ShopAccessControl.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let name = '';
	let description = '';
	let url = '';
	let primaryColor = '#3B82F6'; // Default blue
	let secondaryColor = '#F97316'; // Default orange
	let imageFileId: string | null = null;
	let imagePreview: string | null = null;
	let imageFile: File | null = null;
	let isPublic = false;
	let loading = false;
	let loadingShop = true;
	let uploadingImage = false;
	let accessControl: any = null;

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

	const sanitizeUrl = (inputUrl: string): string => {
		if (!inputUrl) return '';
		// Remove spaces and convert to lowercase
		return inputUrl.replace(/\s+/g, '-').toLowerCase().replace(/[^a-z0-9-]/g, '').replace(/-+/g, '-').replace(/^-|-$/g, '');
	};

	const handleSubmit = async () => {
		if (!name) {
			toast.error($i18n.t('Please fill in all required fields'));
			return;
		}

		loading = true;
		try {
			const shopId = $page.params.shopId;
			// Always send url field, even if empty (to allow clearing it)
			const sanitizedUrl = url ? sanitizeUrl(url) : '';
			
			// is_public and access_control are now independent:
			// - is_public: controls public visibility for external clients (website)
			// - access_control: controls internal management permissions (who can manage the shop)
			const res = await updateShopById(localStorage.token, shopId, {
				name,
				description: description || null,
				image_url: imageFileId || shop.image_url || null,
				url: sanitizedUrl,  // Send empty string if cleared, not null
				primary_color: primaryColor || null,
				secondary_color: secondaryColor || null,
				is_public: isPublic,
				access_control: accessControl !== null && accessControl !== undefined ? accessControl : null
			});

			if (res) {
				// Update local shop data with response
				shop = res;
				url = res.url || '';
				primaryColor = res.primary_color || '#3B82F6';
				secondaryColor = res.secondary_color || '#F97316';
				isPublic = res.is_public ?? false;
				// Update accessControl with the response
				if (res.access_control === null) {
					accessControl = null;
				} else if (res.access_control && (res.access_control.read || res.access_control.write)) {
					accessControl = res.access_control;
				} else {
					accessControl = {
						read: { group_ids: [], user_ids: [] },
						write: { group_ids: [], user_ids: [] }
					};
				}
				toast.success($i18n.t('Shop updated successfully'));
				// Optionally redirect or stay on edit page
				// goto(`/shops/${res.id}`);
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

		// Scroll to access-control section if hash is present
		if (typeof window !== 'undefined' && window.location.hash === '#access-control') {
			setTimeout(() => {
				const element = document.getElementById('access-control');
				if (element) {
					element.scrollIntoView({ behavior: 'smooth', block: 'start' });
				}
			}, 300);
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
				url = res.url || '';
				primaryColor = res.primary_color || '#3B82F6';
				secondaryColor = res.secondary_color || '#F97316';
				imageFileId = res.image_url || null;
				isPublic = res.is_public ?? false;
				// Initialize accessControl (independent from is_public)
				if (res.access_control === null || res.access_control === undefined) {
					accessControl = null;
				} else if (res.access_control && (res.access_control.read || res.access_control.write)) {
					accessControl = res.access_control;
				} else {
					accessControl = {
						read: { group_ids: [], user_ids: [] },
						write: { group_ids: [], user_ids: [] }
					};
				}
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
			<div class="mb-6">
				<button
					on:click={() => {
						const shopId = $page.params.shopId;
						goto(`/shops/${shopId}`);
					}}
					class="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors mb-4"
				>
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
					</svg>
					<span>{$i18n.t('Back to Shop')}</span>
				</button>
			</div>
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

			<div>
				<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
					{$i18n.t('Brand Colors')} <span class="text-gray-400 text-xs">({$i18n.t('optional')})</span>
				</label>
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-xs font-medium mb-2 text-gray-600 dark:text-gray-400">
							{$i18n.t('Primary Color')}
						</label>
						<div class="flex items-center gap-2">
							<input
								type="color"
								bind:value={primaryColor}
								class="w-16 h-12 rounded-lg border-2 border-gray-300 dark:border-gray-600 cursor-pointer"
							/>
							<input
								type="text"
								bind:value={primaryColor}
								placeholder="#3B82F6"
								on:input={(e) => {
									let value = e.target.value.trim();
									// Normalize hex color: remove # if present, add it back, uppercase
									if (value) {
										value = value.replace(/^#/, '');
										// Convert 3-digit hex to 6-digit
										if (value.length === 3 && /^[0-9A-Fa-f]{3}$/.test(value)) {
											value = value.split('').map(c => c + c).join('');
										}
										// Only update if it's a valid 6-digit hex
										if (/^[0-9A-Fa-f]{6}$/.test(value)) {
											primaryColor = '#' + value.toUpperCase();
										} else if (/^[0-9A-Fa-f]{0,6}$/.test(value)) {
											// Allow partial input while typing
											primaryColor = '#' + value.toUpperCase();
										}
									} else {
										primaryColor = '#3B82F6';
									}
								}}
								on:blur={(e) => {
									// Validate and normalize on blur
									let value = e.target.value.trim().replace(/^#/, '');
									if (value.length === 3 && /^[0-9A-Fa-f]{3}$/.test(value)) {
										value = value.split('').map(c => c + c).join('');
									}
									if (/^[0-9A-Fa-f]{6}$/.test(value)) {
										primaryColor = '#' + value.toUpperCase();
									} else if (!primaryColor || !/^#[0-9A-Fa-f]{6}$/i.test(primaryColor)) {
										primaryColor = '#3B82F6';
									}
								}}
								class="flex-1 px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all"
							/>
						</div>
					</div>
					<div>
						<label class="block text-xs font-medium mb-2 text-gray-600 dark:text-gray-400">
							{$i18n.t('Secondary Color')}
						</label>
						<div class="flex items-center gap-2">
							<input
								type="color"
								bind:value={secondaryColor}
								class="w-16 h-12 rounded-lg border-2 border-gray-300 dark:border-gray-600 cursor-pointer"
							/>
							<input
								type="text"
								bind:value={secondaryColor}
								placeholder="#F97316"
								on:input={(e) => {
									let value = e.target.value.trim();
									// Normalize hex color: remove # if present, add it back, uppercase
									if (value) {
										value = value.replace(/^#/, '');
										// Convert 3-digit hex to 6-digit
										if (value.length === 3 && /^[0-9A-Fa-f]{3}$/.test(value)) {
											value = value.split('').map(c => c + c).join('');
										}
										// Only update if it's a valid 6-digit hex
										if (/^[0-9A-Fa-f]{6}$/.test(value)) {
											secondaryColor = '#' + value.toUpperCase();
										} else if (/^[0-9A-Fa-f]{0,6}$/.test(value)) {
											// Allow partial input while typing
											secondaryColor = '#' + value.toUpperCase();
										}
									} else {
										secondaryColor = '#F97316';
									}
								}}
								on:blur={(e) => {
									// Validate and normalize on blur
									let value = e.target.value.trim().replace(/^#/, '');
									if (value.length === 3 && /^[0-9A-Fa-f]{3}$/.test(value)) {
										value = value.split('').map(c => c + c).join('');
									}
									if (/^[0-9A-Fa-f]{6}$/.test(value)) {
										secondaryColor = '#' + value.toUpperCase();
									} else if (!secondaryColor || !/^#[0-9A-Fa-f]{6}$/i.test(secondaryColor)) {
										secondaryColor = '#F97316';
									}
								}}
								class="flex-1 px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all"
							/>
						</div>
					</div>
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
					{$i18n.t('These colors will be used in the shop header, footer, and buttons')}
				</p>
			</div>

			<div>
				<label class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
					{$i18n.t('Shop URL')} <span class="text-gray-400 text-xs">({$i18n.t('optional')})</span>
				</label>
				<div class="flex items-center gap-2">
					<span class="text-sm text-gray-500 dark:text-gray-400">/public/shops/</span>
					<input
						type="text"
						bind:value={url}
						placeholder={$i18n.t('my-shop-url')}
						pattern="[a-z0-9\-]+"
						on:input={(e) => {
							// Remove spaces and invalid characters in real-time
							const sanitized = sanitizeUrl(e.target.value);
							if (sanitized !== e.target.value) {
								url = sanitized;
							}
						}}
						class="flex-1 px-4 py-3 border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all shadow-sm hover:shadow-md"
					/>
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{$i18n.t('Leave empty to auto-generate from shop name. Only lowercase letters, numbers, and hyphens allowed. Spaces will be automatically converted to hyphens.')}
				</p>
			</div>

			<div>
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={isPublic}
						class="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
					/>
					<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						{$i18n.t('Make this shop public')}
					</span>
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-8">
					{$i18n.t('Public shops can be accessed by anyone via a shareable URL on the website without requiring login. This is separate from internal access control.')}
				</p>
			</div>

			<div id="access-control" class="mt-6">
				<div class="border-t border-gray-200 dark:border-gray-700 pt-6">
					<div class="block text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
						{$i18n.t('Internal Access Control')} <span class="text-gray-400 text-xs">({$i18n.t('optional')})</span>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mb-4">
						{$i18n.t('Assign specific users and groups with read or write permissions for internal shop management. This controls who can manage the shop internally, separate from public visibility.')}
					</p>
					{#if accessControl !== null}
						<ShopAccessControl
							bind:accessControl
							onChange={(ac) => {
								accessControl = ac;
							}}
						/>
					{:else}
						<button
							type="button"
							on:click={() => {
								accessControl = {
									read: { group_ids: [], user_ids: [] },
									write: { group_ids: [], user_ids: [] }
								};
							}}
							class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium"
						>
							{$i18n.t('Enable Access Control')}
						</button>
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
