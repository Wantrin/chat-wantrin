<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import DropdownOptions from '../common/DropdownOptions.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let item;

	let showMenu = false;

	const formatPrice = (price: number) => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: 'EUR'
		}).format(price);
	};

	const toDisplayUrl = (u: string) => (u.startsWith('http') ? u : `${WEBUI_API_BASE_URL}/files/${u}/content`);

	$: imageUrls =
		item?.image_urls && Array.isArray(item.image_urls)
			? item.image_urls
			: item?.image_url
				? [item.image_url]
				: [];

	$: coverUrl = imageUrls.length > 0 ? toDisplayUrl(imageUrls[0]) : null;
</script>

<div
	class="bg-white dark:bg-gray-800 rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer overflow-hidden"
	role="button"
	tabindex="0"
	on:click={() => goto(`/shops/${item.shop_id}/products/${item.id}`)}
	on:keydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			goto(`/shops/${item.shop_id}/products/${item.id}`);
		}
	}}
>
	{#if coverUrl}
		<img
			src={coverUrl}
			alt={item.name}
			class="w-full h-48 object-cover"
		/>
	{:else}
		<div class="w-full h-48 bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
			<span class="text-gray-400 dark:text-gray-500">{$i18n.t('No Image')}</span>
		</div>
	{/if}
	<div class="p-4">
		<div class="flex items-start justify-between mb-2">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 line-clamp-2">
				{item.name}
			</h3>
			{#if $user && ($user.id === item.user_id || $user.role === 'admin')}
				<div class="relative">
					<Tooltip content={$i18n.t('Options')}>
						<button
							class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
							on:click|stopPropagation={(e) => {
								showMenu = !showMenu;
							}}
						>
							<EllipsisHorizontal class="w-5 h-5 text-gray-500 dark:text-gray-400" />
						</button>
					</Tooltip>
					{#if showMenu}
						<DropdownOptions
							options={[
								{
									label: $i18n.t('Edit'),
									action: () => {
										goto(`/shops/${item.shop_id}/products/${item.id}/edit`);
										showMenu = false;
									}
								},
								{
									label: $i18n.t('Delete'),
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
			<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-2">
				{item.description}
			</p>
		{/if}
		<div class="flex items-center justify-between mt-4">
			<span class="text-xl font-bold text-blue-600 dark:text-blue-400">
				{formatPrice(item.price)}
			</span>
			{#if item.stock !== undefined}
				<span
					class="text-sm {item.stock > 0
						? 'text-green-600 dark:text-green-400'
						: 'text-red-600 dark:text-red-400'}"
				>
					{item.stock > 0 ? `${item.stock} ${$i18n.t('in stock')}` : $i18n.t('Out of stock')}
				</span>
			{/if}
		</div>
		{#if item.category}
			<div class="mt-2">
				<span class="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
					{item.category}
				</span>
			</div>
		{/if}
	</div>
</div>
