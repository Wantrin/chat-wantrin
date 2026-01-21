<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { createNewProduct, deleteProductById, getProducts, searchProducts } from '$lib/apis/products';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ProductCard from './ProductCard.svelte';
	import Loader from '../common/Loader.svelte';

	export let viewOption: string | null = null;
	export let shopId: string | null = null;

	let loaded = false;

	let selectedProduct = null;
	let showDeleteConfirm = false;

	let items = null;
	let total = null;

	let query = '';
	let category = '';

	let sortKey = null;

	let page = 1;

	let itemsLoading = false;
	let allItemsLoaded = false;

	const deleteProductHandler = async (id) => {
		const res = await deleteProductById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			init();
		}
	};

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
	};

	const init = async () => {
		itemsLoading = true;
		reset();

		try {
			const res = await searchProducts(
				localStorage.token,
				query || null,
				category || null,
				shopId || null,
				viewOption !== undefined ? viewOption : null,
				null,
				sortKey || null,
				null,
				page
			);

			if (res) {
				items = res.items || [];
				total = res.total || 0;

				if (items.length >= total) {
					allItemsLoaded = true;
				}
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			itemsLoading = false;
		}
	};

	const loadMore = async () => {
		if (itemsLoading || allItemsLoaded) return;

		itemsLoading = true;
		page += 1;

		try {
			const res = await searchProducts(
				localStorage.token,
				query || null,
				category || null,
				shopId || null,
				viewOption !== undefined ? viewOption : null,
				null,
				sortKey || null,
				null,
				page
			);

			if (res && res.items) {
				items = [...items, ...res.items];
				if (items.length >= total) {
					allItemsLoaded = true;
				}
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			itemsLoading = false;
		}
	};

	$: if (loaded) {
		init();
	}

	$: if (query !== undefined || category !== undefined || sortKey !== undefined || viewOption !== undefined) {
		if (loaded) {
			init();
		}
	}

	onMount(() => {
		loaded = true;
	});
</script>

<div class="flex flex-col h-full w-full">
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center gap-2 flex-1">
			<div class="relative flex-1 max-w-md">
				<Search class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
				<input
					type="text"
					placeholder={$i18n.t('Search products...')}
					class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
					bind:value={query}
				/>
			</div>
			<select
				class="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
				bind:value={category}
			>
				<option value="">{$i18n.t('All Categories')}</option>
				<option value="electronics">{$i18n.t('Electronics')}</option>
				<option value="clothing">{$i18n.t('Clothing')}</option>
				<option value="food">{$i18n.t('Food')}</option>
				<option value="books">{$i18n.t('Books')}</option>
				<option value="other">{$i18n.t('Other')}</option>
			</select>
			<select
				class="px-4 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
				bind:value={sortKey}
			>
				<option value="">{$i18n.t('Sort by')}</option>
				<option value="name">{$i18n.t('Name')}</option>
				<option value="price">{$i18n.t('Price')}</option>
				<option value="updated_at">{$i18n.t('Recently Updated')}</option>
			</select>
		</div>
		{#if $user && (showCreateButton || (!shopId && viewOption === null))}
			<Tooltip content={$i18n.t('Add Product')}>
				<button
					class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
					on:click={() => {
						if (shopId) {
							goto(`/shops/${shopId}/products/create`);
						} else {
							goto('/products/create');
						}
					}}
				>
					<Plus class="w-5 h-5" />
					<span>{$i18n.t('Add Product')}</span>
				</button>
			</Tooltip>
		{/if}
	</div>

	<div class="flex-1 overflow-y-auto p-4">
		{#if itemsLoading && items === null}
			<div class="flex items-center justify-center h-full">
				<Loader />
			</div>
		{:else if items && items.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
				{#each items as item (item.id)}
					<ProductCard
						{item}
						on:delete={(e) => {
							selectedProduct = e.detail;
							showDeleteConfirm = true;
						}}
					/>
				{/each}
			</div>
			{#if !allItemsLoaded}
				<div class="flex justify-center mt-4">
					<button
						class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
						on:click={loadMore}
						disabled={itemsLoading}
					>
						{#if itemsLoading}
							<Spinner class="w-4 h-4" />
						{:else}
							{$i18n.t('Load More')}
						{/if}
					</button>
				</div>
			{/if}
		{:else if items && items.length === 0}
			<div class="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
				<p class="text-lg">{$i18n.t('No products found')}</p>
			</div>
		{/if}
	</div>

	<DeleteConfirmDialog
		open={showDeleteConfirm}
		title={$i18n.t('Delete Product')}
		message={$i18n.t('Are you sure you want to delete this product?')}
		on:confirm={() => {
			if (selectedProduct) {
				deleteProductHandler(selectedProduct.id);
				showDeleteConfirm = false;
				selectedProduct = null;
			}
		}}
		on:cancel={() => {
			showDeleteConfirm = false;
			selectedProduct = null;
		}}
	/>
</div>
