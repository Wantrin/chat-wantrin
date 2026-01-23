<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { copyToClipboard } from '$lib/utils';
	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let shop;
	export let show = false;

	const i18n = getContext('i18n');

	let publicUrl = '';

	$: if (shop && typeof window !== 'undefined') {
		const identifier = shop.url || shop.id;
		publicUrl = `${window.location.origin}/public/shops/${identifier}`;
	}

	const copyPublicUrl = async () => {
		if (publicUrl) {
			await copyToClipboard(publicUrl);
			toast.success($i18n ? $i18n.t('Public URL copied to clipboard!') : 'Public URL copied to clipboard!');
		}
	};

	const checkIfPublic = () => {
		return shop && shop.is_public === true;
	};
</script>

<Modal bind:show size="md">
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<h2 class="text-lg font-semibold">
				{$i18n ? $i18n.t('Share Shop') : 'Share Shop'}
			</h2>
			<button
				class="rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
				on:click={() => {
					show = false;
				}}
			>
				<XMark class="w-5 h-5" />
			</button>
		</div>

		<div class="px-5 pb-5">
			{#if !checkIfPublic()}
				<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-4">
					<p class="text-sm text-yellow-800 dark:text-yellow-400">
						{$i18n ? $i18n.t('This shop is not public. To share it, enable "Make this shop public" in the shop settings.') : 'This shop is not public. To share it, enable "Make this shop public" in the shop settings.'}
					</p>
				</div>
			{:else}
				<div class="mb-4">
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
						{$i18n ? $i18n.t('Public URL') : 'Public URL'}
					</p>
					<div class="flex items-center gap-2">
						<input
							type="text"
							readonly
							value={publicUrl}
							class="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-mono text-gray-900 dark:text-gray-100"
						/>
						<button
							on:click={copyPublicUrl}
							class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
						>
							<Link class="w-4 h-4" />
							{$i18n ? $i18n.t('Copy') : 'Copy'}
						</button>
					</div>
				</div>

				<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
					<p class="text-sm text-blue-800 dark:text-blue-400">
						{$i18n ? $i18n.t('Anyone with this link can view your shop and products without logging in.') : 'Anyone with this link can view your shop and products without logging in.'}
					</p>
				</div>
			{/if}
		</div>
	</div>
</Modal>
