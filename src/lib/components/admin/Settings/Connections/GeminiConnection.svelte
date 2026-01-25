<script lang="ts">
	import { getContext } from 'svelte';
	import { tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let apiKey = '';
	export let baseUrl = 'https://generativelanguage.googleapis.com';

	let editing = false;
	let apiKeyEditing = false;
</script>

<div class="flex w-full gap-2 items-center">
	<div class="flex-1 flex flex-col gap-2">
		<div class="flex gap-2 items-center">
			<div class="flex-1">
				<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('API Base URL')}
				</label>
				<input
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
					placeholder="https://generativelanguage.googleapis.com"
					bind:value={baseUrl}
					on:blur={() => {
						if (editing) {
							onSubmit();
							editing = false;
						}
					}}
					on:input={() => {
						editing = true;
					}}
				/>
			</div>
		</div>
		<div class="flex gap-2 items-center">
			<div class="flex-1">
				<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('API Key')}
				</label>
				<SensitiveInput
					bind:value={apiKey}
					placeholder={$i18n.t('Enter your Gemini API key')}
					on:input={() => {
						apiKeyEditing = true;
					}}
					on:blur={async () => {
						if (apiKeyEditing) {
							await tick(); // Wait for value to sync
							onSubmit();
							apiKeyEditing = false;
						}
					}}
				/>
			</div>
			<Tooltip content={$i18n.t('Delete')} className="self-end">
				<button
					class="self-end p-2 bg-transparent hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition mt-6"
					on:click={onDelete}
					type="button"
				>
					<GarbageBin className="w-4 h-4 text-red-500" />
				</button>
			</Tooltip>
		</div>
	</div>
</div>
