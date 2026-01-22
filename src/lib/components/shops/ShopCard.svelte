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

	$: imageUrl = item.image_url
		? item.image_url.startsWith('http')
			? item.image_url
			: `${WEBUI_API_BASE_URL}/files/${item.image_url}/content`
		: null;
</script>

<div
	class="group bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-2xl transition-all duration-300 cursor-pointer overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-600 hover:-translate-y-1"
	role="button"
	tabindex="0"
	on:click={() => goto(`/shops/${item.id}`)}
	on:keydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			goto(`/shops/${item.id}`);
		}
	}}
>
	<div class="relative overflow-hidden">
		{#if imageUrl}
			<img
				src={imageUrl}
				alt={item.name}
				class="w-full h-48 object-cover transition-transform duration-300 group-hover:scale-110"
			/>
		{:else}
			<div class="w-full h-48 bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
				<span class="text-white text-sm font-medium">{$i18n.t('No Image')}</span>
			</div>
		{/if}
		<div class="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
	</div>
	<div class="p-5">
		<div class="flex items-start justify-between mb-3">
			<h3 class="text-lg font-bold text-gray-900 dark:text-gray-100 line-clamp-2 group-hover:text-orange-600 dark:group-hover:text-orange-400 transition-colors">
				{item.name}
			</h3>
			{#if $user && ($user.id === item.user_id || $user.role === 'admin')}
				<div class="relative z-10">
					<Tooltip content={$i18n.t('Options')}>
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
									label: $i18n.t('Edit'),
									action: () => {
										goto(`/shops/${item.id}/edit`);
										showMenu = false;
									}
								},
								{
									label: $i18n.t('Add Product'),
									action: () => {
										goto(`/shops/${item.id}/products/create`);
										showMenu = false;
									}
								},
								{
									label: $i18n.t('View Products'),
									action: () => {
										goto(`/shops/${item.id}/products`);
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
			<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3 leading-relaxed">
				{item.description}
			</p>
		{/if}
		<div class="flex items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
			<span class="text-xs font-medium text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/30 px-2 py-1 rounded-full">
				{$i18n.t('View Shop')} →
			</span>
		</div>
	</div>
</div>
