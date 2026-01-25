<script lang="ts">
	import { getContext } from 'svelte';
	import { tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	export let onSubmit = () => {};

	export let accountSid = '';
	export let authToken = '';
	export let phoneNumber = '';
	export let enableTwilio = false;

	let accountSidEditing = false;
	let authTokenEditing = false;
	let phoneNumberEditing = false;
</script>

<div class="flex w-full flex-col gap-4">
	<div class="flex items-center justify-between">
		<div>
			<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Twilio Configuration')}
			</h3>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
				{$i18n.t('Configure Twilio for phone calls and SMS')}
			</p>
		</div>
		<div class="flex items-center gap-2">
			<label class="text-xs font-medium text-gray-700 dark:text-gray-300">
				{$i18n.t('Enable Twilio')}
			</label>
			<Switch bind:checked={enableTwilio} on:change={onSubmit} />
		</div>
	</div>

	<div class="flex flex-col gap-3">
		<div>
			<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
				{$i18n.t('Account SID')}
			</label>
			<SensitiveInput
				bind:value={accountSid}
				placeholder={$i18n.t('Enter your Twilio Account SID')}
				on:input={() => {
					accountSidEditing = true;
				}}
				on:blur={async () => {
					if (accountSidEditing) {
						await tick();
						onSubmit();
						accountSidEditing = false;
					}
				}}
			/>
		</div>

		<div>
			<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
				{$i18n.t('Auth Token')}
			</label>
			<SensitiveInput
				bind:value={authToken}
				placeholder={$i18n.t('Enter your Twilio Auth Token')}
				on:input={() => {
					authTokenEditing = true;
				}}
				on:blur={async () => {
					if (authTokenEditing) {
						await tick();
						onSubmit();
						authTokenEditing = false;
					}
				}}
			/>
		</div>

		<div>
			<label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
				{$i18n.t('Phone Number')}
			</label>
			<input
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
				placeholder="+1234567890"
				bind:value={phoneNumber}
				on:blur={async () => {
					if (phoneNumberEditing) {
						await tick();
						onSubmit();
						phoneNumberEditing = false;
					}
				}}
				on:input={() => {
					phoneNumberEditing = true;
				}}
			/>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
				{$i18n.t('Format: E.164 (e.g., +1234567890)')}
			</p>
		</div>
	</div>
</div>
