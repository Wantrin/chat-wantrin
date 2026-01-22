<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	onMount(() => {
		// On réutilise l'éditeur global (il redirige ensuite vers /shops/{shop_id}/products/{id})
		goto(`/products/${$page.params.productId}/edit`);
	});
</script>

