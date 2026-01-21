<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	onMount(() => {
		// Ancienne route -> nouvelle route
		goto(`/products/${$page.params.id}/edit`);
	});
</script>

