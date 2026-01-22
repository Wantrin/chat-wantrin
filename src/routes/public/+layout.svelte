<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { getBackendConfig } from '$lib/apis';
	import { WEBUI_NAME, config } from '$lib/stores';
	import CartIcon from '$lib/components/cart/CartIcon.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		// Load config but don't require authentication
		try {
			const backendConfig = await getBackendConfig();
			if (backendConfig) {
				await config.set(backendConfig);
				await WEBUI_NAME.set(backendConfig.name);
			}
		} catch (error) {
			console.error('Error loading config:', error);
		}
		loaded = true;
	});
</script>

{#if loaded}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
		<nav class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="flex justify-between items-center h-16">
					<div class="flex items-center">
						<a href="/public/shops" class="text-xl font-bold text-gray-900 dark:text-gray-100">
							{$WEBUI_NAME || 'Shops'}
						</a>
					</div>
					<div class="flex items-center gap-4">
						<a href="/public/shops" class="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100">
							{$i18n ? $i18n.t('Shops') : 'Shops'}
						</a>
						<CartIcon />
					</div>
				</div>
			</div>
		</nav>
		<slot />
	</div>
{/if}
