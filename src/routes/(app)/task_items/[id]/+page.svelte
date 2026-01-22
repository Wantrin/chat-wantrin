<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { showSidebar } from '$lib/stores';

	import TaskItemEditor from '$lib/components/task_items/TaskItemEditor.svelte';

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});
</script>

{#if loaded}
	<div
		id="task-item-container"
		class="w-full h-full {$showSidebar ? 'md:max-w-[calc(100%-var(--sidebar-width))]' : ''}"
	>
		<TaskItemEditor id={$page.params.id} />
	</div>
{/if}
