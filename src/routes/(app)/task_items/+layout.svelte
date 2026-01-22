<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar, functions, config, user, showArchivedChats } from '$lib/stores';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (
			!(
				$user?.role === 'admin' || ($user?.permissions?.features?.task_items ?? true)
			)
		) {
			// If the user doesn't have permission, redirect to the home page
			goto('/');
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Tasks')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<slot />
{/if}
