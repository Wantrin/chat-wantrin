<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getContext } from 'svelte';
	import { getBackendConfig } from '$lib/apis';
	import { WEBUI_NAME, config } from '$lib/stores';
	import EcommerceHeader from '$lib/components/ecommerce/EcommerceHeader.svelte';
	import EcommerceFooter from '$lib/components/ecommerce/EcommerceFooter.svelte';

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
		
		// Enable scrolling for public pages
		if (typeof document !== 'undefined') {
			document.documentElement.classList.add('public-page');
			document.body.classList.add('public-page');
		}
		
		loaded = true;
	});
	
	onDestroy(() => {
		// Clean up classes when leaving public pages
		if (typeof document !== 'undefined') {
			document.documentElement.classList.remove('public-page');
			document.body.classList.remove('public-page');
		}
	});
</script>

{#if loaded}
	<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col w-full">
		<EcommerceHeader />
		<main class="flex-1 w-full overflow-visible pt-16">
			<slot />
		</main>
		<EcommerceFooter />
	</div>
{/if}

<style>
	:global(html.public-page) {
		height: auto !important;
		min-height: 100vh;
		overflow-x: hidden !important;
		overflow-y: auto !important;
	}

	:global(body.public-page) {
		height: auto !important;
		min-height: 100vh;
		overflow-x: hidden !important;
		overflow-y: auto !important;
		position: relative !important;
	}
</style>
