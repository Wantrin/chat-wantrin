<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import DropdownOptions from '../common/DropdownOptions.svelte';

	let i18n;
	try {
		i18n = getContext('i18n');
	} catch (e) {
		console.error('i18n context is not available in ProductCard component:', e);
		// Create a dummy store-like object to prevent errors
		i18n = {
			subscribe: (fn) => {
				fn({ t: (key) => key });
				return () => {};
			}
		};
	}
	const dispatch = createEventDispatcher();

	export let item;

	let showMenu = false;

	const formatPrice = (price: number, currency: string = 'EUR') => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	};

	const toDisplayUrl = (u: string | null | undefined) => {
		if (!u) return null;
		return u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`;
	};

	$: imageUrls = (() => {
		// Use image_urls (array)
		if (item?.image_urls) {
			// Handle case where image_urls might be a JSON string (SQLite)
			let urls = item.image_urls;
			if (typeof urls === 'string') {
				try {
					urls = JSON.parse(urls);
				} catch (e) {
					console.warn('Failed to parse image_urls as JSON:', e);
					urls = null;
				}
			}
			
			if (Array.isArray(urls)) {
				const filtered = urls.filter(url => url && typeof url === 'string' && url.trim() !== '');
				if (filtered.length > 0) return filtered;
			}
		}
		return [];
	})();

	$: coverUrl = imageUrls.length > 0 ? toDisplayUrl(imageUrls[0]) : null;
</script>

<div
	class="group bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600 hover:-translate-y-1"
	role="button"
	tabindex="0"
	on:click={() => {
		if (item.shop_id) {
			goto(`/shops/${item.shop_id}/products/${item.id}`);
		} else {
			goto(`/products/${item.id}`);
		}
	}}
	on:keydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			if (item.shop_id) {
				goto(`/shops/${item.shop_id}/products/${item.id}`);
			} else {
				goto(`/products/${item.id}`);
			}
		}
	}}
>
	<div class="relative overflow-hidden">
		{#if coverUrl}
			<img
				src={coverUrl}
				alt={item.name}
				class="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-110"
			/>
		{:else}
			<div class="w-full h-48 bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
				<span class="text-white text-sm font-medium">{$i18n ? $i18n.t('No Image') : 'No Image'}</span>
			</div>
		{/if}
		<div class="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
	</div>
	<div class="p-5">
		<div class="flex items-start justify-between mb-3">
			<h3 class="text-lg font-bold text-gray-900 dark:text-gray-100 line-clamp-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
				{item.name}
			</h3>
			{#if $user && ($user.id === item.user_id || $user.role === 'admin')}
				<div class="relative z-10">
					<Tooltip content={$i18n ? $i18n.t('Options') : 'Options'}>
						<button
							class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors backdrop-blur-sm bg-white/50 dark:bg-gray-800/50"
							on:click|stopPropagation={(e) => {
								showMenu = !showMenu;
							}}
						>
							<EllipsisHorizontal class="w-5 h-5 text-gray-600 dark:text-gray-300" />
						</button>
					</Tooltip>
					{#if showMenu}
						<DropdownOptions
							options={[
								{
									label: $i18n ? $i18n.t('Edit') : 'Edit',
									action: () => {
										goto(`/shops/${item.shop_id}/products/${item.id}/edit`);
										showMenu = false;
									}
								},
								{
									label: $i18n ? $i18n.t('Delete') : 'Delete',
									action: () => {
										showMenu = false;
										dispatch('delete', item);
									}
								}
							]}
							on:close={() => {
								showMenu = false;
							}}
						/>
					{/if}
				</div>
			{/if}
		</div>
		{#if item.description}
			<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-4 leading-relaxed">
				{item.description}
			</p>
		{/if}
		<div class="flex items-center justify-between mb-3 pb-3 border-b border-gray-100 dark:border-gray-700">
			<span class="text-2xl font-bold bg-gradient-to-r from-blue-600 to-orange-600 dark:from-blue-400 dark:to-orange-400 bg-clip-text text-transparent">
				{formatPrice(item.price, item.currency)}
			</span>
			{#if item.stock !== undefined}
				<span
					class="text-xs font-semibold px-2.5 py-1 rounded-full {item.stock > 0
						? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
						: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'}"
				>
					{item.stock > 0 ? `${item.stock} ${$i18n ? $i18n.t('in stock') : 'in stock'}` : ($i18n ? $i18n.t('Out of stock') : 'Out of stock')}
				</span>
			{/if}
		</div>
		<div class="flex items-center justify-between">
			<div class="flex gap-2 flex-wrap">
				{#if item.category}
					<span class="text-xs font-medium px-2.5 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
						{item.category}
					</span>
				{/if}
				{#if item.currency}
					<span class="text-xs font-medium px-2.5 py-1 bg-gradient-to-r from-green-100 to-emerald-100 dark:from-green-900/30 dark:to-emerald-900/30 text-green-700 dark:text-green-400 rounded-full">
						{item.currency}
					</span>
				{/if}
			</div>
			<span class="text-xs font-medium text-orange-600 dark:text-orange-400 opacity-0 group-hover:opacity-100 transition-opacity">
				{$i18n ? $i18n.t('View') : 'View'} →
			</span>
		</div>
	</div>
</div>
