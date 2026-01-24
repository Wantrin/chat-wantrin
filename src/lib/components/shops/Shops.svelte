<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { createNewShop, deleteShopById, getShops, searchShops } from '$lib/apis/shops';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ShopCard from './ShopCard.svelte';
	import Loader from '../common/Loader.svelte';

	export let viewOption: string | null = null;

	let loaded = false;

	let selectedShop = null;
	let showDeleteConfirm = false;

	let items = null;
	let total = null;

	let query = '';

	let sortKey = null;

	let page = 1;

	let itemsLoading = false;
	let allItemsLoaded = false;
	
	// Track recent error messages to prevent duplicates
	const recentErrors = new Set<string>();
	const clearErrorAfter = (errorKey: string, delay: number = 2000) => {
		setTimeout(() => {
			recentErrors.delete(errorKey);
		}, delay);
	};

	const showErrorOnce = (error: any) => {
		const errorMessage = `${error}`;
		const errorKey = errorMessage.substring(0, 50); // Use first 50 chars as key
		
		// Only show error if we haven't shown it recently
		if (!recentErrors.has(errorKey)) {
			recentErrors.add(errorKey);
			clearErrorAfter(errorKey);
			
			// Only show error if it's not a 401 (unauthorized) - those are handled by auth flow
			if (!errorMessage.includes('401') && !errorMessage.includes('Unauthorized')) {
				toast.error(errorMessage);
			}
		}
	};

	const deleteShopHandler = async (id) => {
		const res = await deleteShopById(localStorage.token, id).catch((error) => {
			showErrorOnce(error);
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
		// Prevent multiple simultaneous calls
		if (itemsLoading) {
			return;
		}
		
		itemsLoading = true;
		reset();

		try {
			const res = await searchShops(
				localStorage.token,
				query || null,
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
			showErrorOnce(error);
		} finally {
			itemsLoading = false;
		}
	};

	const loadMore = async () => {
		if (itemsLoading || allItemsLoaded) return;

		itemsLoading = true;
		page += 1;

		try {
			const res = await searchShops(
				localStorage.token,
				query || null,
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
			showErrorOnce(error);
		} finally {
			itemsLoading = false;
		}
	};

	let initTimeout: ReturnType<typeof setTimeout> | null = null;

	// Unified reactive statement to prevent duplicate calls
	// Watch all relevant variables to trigger init when any change
	$: if (loaded && (query !== undefined || sortKey !== undefined || viewOption !== undefined)) {
		// Debounce init calls to prevent duplicate API requests
		if (initTimeout) {
			clearTimeout(initTimeout);
		}
		initTimeout = setTimeout(() => {
			init();
		}, 150);
	}

	onMount(() => {
		loaded = true;
	});
</script>

<div class="flex flex-col h-full w-full bg-gradient-to-br from-blue-50 via-orange-50 to-blue-50 dark:from-gray-900 dark:via-orange-900/20 dark:to-gray-800">
	<div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm gap-4">
		<div class="flex items-center gap-3 flex-1">
			<div class="relative flex-1 max-w-md">
				<input
					type="text"
					placeholder={$i18n.t('Search shops...')}
					class="w-full pl-12 pr-4 py-3 h-[48px] border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md"
					bind:value={query}
				/>
				<div class="absolute left-4 top-1/2 transform -translate-y-1/2 pointer-events-none z-10">
					<Search class="w-5 h-5 text-gray-400 dark:text-gray-500" />
				</div>
			</div>
			<select
				class="px-5 py-3 h-[48px] border-2 border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all shadow-sm hover:shadow-md font-medium min-w-[150px]"
				bind:value={sortKey}
			>
				<option value="">{$i18n.t('Sort by')}</option>
				<option value="name">{$i18n.t('Name')}</option>
				<option value="updated_at">{$i18n.t('Recently Updated')}</option>
			</select>
		</div>
		{#if $user}
			<Tooltip content={$i18n.t('Add Shop')}>
				<button
					class="flex items-center justify-center gap-2 px-6 h-[48px] bg-gradient-to-r from-blue-600 to-orange-600 hover:from-blue-700 hover:to-orange-700 text-white rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl font-semibold transform hover:-translate-y-0.5 whitespace-nowrap"
					on:click={() => goto('/shop/create')}
				>
					<Plus class="w-5 h-5" />
					<span>{$i18n.t('Add Shop')}</span>
				</button>
			</Tooltip>
		{/if}
	</div>

	<div class="flex-1 overflow-y-auto p-6">
		{#if itemsLoading && items === null}
			<div class="flex items-center justify-center h-full">
				<Loader />
			</div>
		{:else if items && items.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
				{#each items as item (item.id)}
					<ShopCard
						{item}
						on:delete={(e) => {
							selectedShop = e.detail;
							showDeleteConfirm = true;
						}}
					/>
				{/each}
			</div>
			{#if !allItemsLoaded}
				<div class="flex justify-center mt-8">
					<button
						class="px-6 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-300 shadow-md hover:shadow-lg font-medium border-2 border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600"
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
			<div class="flex flex-col items-center justify-center h-full">
				<div class="text-center p-8 bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700">
					<svg class="w-16 h-16 mx-auto text-gray-400 dark:text-gray-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
					</svg>
					<p class="text-xl font-semibold text-gray-600 dark:text-gray-400">{$i18n.t('No shops found')}</p>
				</div>
			</div>
		{/if}
	</div>

	<DeleteConfirmDialog
		open={showDeleteConfirm}
		title={$i18n.t('Delete Shop')}
		message={$i18n.t('Are you sure you want to delete this shop?')}
		on:confirm={() => {
			if (selectedShop) {
				deleteShopHandler(selectedShop.id);
				showDeleteConfirm = false;
				selectedShop = null;
			}
		}}
		on:cancel={() => {
			showDeleteConfirm = false;
			selectedShop = null;
		}}
	/>
</div>
