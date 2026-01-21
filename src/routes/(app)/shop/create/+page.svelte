<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		// Ancienne route -> nouvelle route
		goto('/products/create');
	});
</script>
