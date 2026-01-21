<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		// Rediriger vers /auth-shops/create
		goto('/auth-shops/create');
	});
</script>
