<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getShopById } from '$lib/apis/shops';
	import {
		getDeliveryPersonsByShopId,
		deleteDeliveryPersonById,
		type DeliveryPerson
	} from '$lib/apis/delivery_persons';
	import { showSidebar } from '$lib/stores';
	import Loader from '$lib/components/common/Loader.svelte';

	const i18n = getContext('i18n');

	let shop = null;
	let deliveryPersons: DeliveryPerson[] = [];
	let loading = true;
	let deleting = false;

	const formatDate = (timestamp: number) => {
		return new Date(timestamp / 1000000).toLocaleDateString('fr-FR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	};

	const loadData = async () => {
		loading = true;
		try {
			const shopId = $page.params.shopId;
			const token = typeof window !== 'undefined' ? localStorage.token : '';

			const [shopRes, deliveryPersonsRes] = await Promise.all([
				getShopById(token, shopId),
				getDeliveryPersonsByShopId(token, shopId, false)
			]);

			if (shopRes) {
				shop = shopRes;
			}
			if (deliveryPersonsRes) {
				deliveryPersons = deliveryPersonsRes;
			}
		} catch (error) {
			console.error('Error loading data:', error);
			toast.error(`${error}`);
		} finally {
			loading = false;
		}
	};

	const deleteDeliveryPerson = async (id: string, name: string) => {
		if (!confirm($i18n ? $i18n.t('Are you sure you want to delete {{name}}?', { name }) : `Are you sure you want to delete ${name}?`)) {
			return;
		}

		deleting = true;
		try {
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			const result = await deleteDeliveryPersonById(token, id);

			if (result) {
				toast.success($i18n ? $i18n.t('Delivery person deleted successfully') : 'Delivery person deleted successfully');
				await loadData();
			}
		} catch (error) {
			console.error('Error deleting delivery person:', error);
			toast.error(`${error}`);
		} finally {
			deleting = false;
		}
	};

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>{shop ? `${shop.name} - Delivery Persons` : 'Delivery Persons'} • {$i18n ? $i18n.t('Delivery Persons') : 'Delivery Persons'}</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<Loader />
	</div>
{:else if shop}
	<div class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full">
		<div class="px-5 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{$i18n ? $i18n.t('Delivery Persons') : 'Delivery Persons'}
				</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{shop.name}</p>
			</div>
			<div class="flex items-center gap-2">
				<a
					href="/shops/{shop.id}"
					class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
				>
					← {$i18n ? $i18n.t('Back to Shop') : 'Back to Shop'}
				</a>
				<a
					href="/shops/{shop.id}/delivery-persons/create"
					class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
				>
					+ {$i18n ? $i18n.t('Add Delivery Person') : 'Add Delivery Person'}
				</a>
			</div>
		</div>

		<div class="flex-1 overflow-auto p-5">
			{#if deliveryPersons.length === 0}
				<div class="text-center py-12">
					<p class="text-gray-500 dark:text-gray-400 mb-4">
						{$i18n ? $i18n.t('No delivery persons yet') : 'No delivery persons yet'}
					</p>
					<a
						href="/shops/{shop.id}/delivery-persons/create"
						class="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold"
					>
						+ {$i18n ? $i18n.t('Add First Delivery Person') : 'Add First Delivery Person'}
					</a>
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
					{#each deliveryPersons as dp}
						<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
							<div class="flex items-start justify-between mb-4">
								<div class="flex-1">
									<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
										{dp.name}
									</h3>
									{#if !dp.is_active}
										<span class="inline-block mt-1 px-2 py-1 text-xs rounded bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
											{$i18n ? $i18n.t('Inactive') : 'Inactive'}
										</span>
									{/if}
								</div>
								<div class="flex gap-2">
									<a
										href="/shops/{shop.id}/delivery-persons/{dp.id}/edit"
										class="p-2 text-gray-500 hover:text-blue-600 transition"
										title={$i18n ? $i18n.t('Edit') : 'Edit'}
									>
										<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
											<path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
										</svg>
									</a>
									<button
										on:click={() => deleteDeliveryPerson(dp.id, dp.name)}
										disabled={deleting}
										class="p-2 text-gray-500 hover:text-red-600 transition disabled:opacity-50"
										title={$i18n ? $i18n.t('Delete') : 'Delete'}
									>
										<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
											<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
										</svg>
									</button>
								</div>
							</div>
							<div class="space-y-2 text-sm text-gray-600 dark:text-gray-400">
								{#if dp.email}
									<p>
										<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Email') : 'Email'}:</strong> {dp.email}
									</p>
								{/if}
								{#if dp.phone}
									<p>
										<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Phone') : 'Phone'}:</strong> {dp.phone}
									</p>
								{/if}
								{#if dp.vehicle_type}
									<p>
										<strong class="text-gray-900 dark:text-gray-100">{$i18n ? $i18n.t('Vehicle') : 'Vehicle'}:</strong> {dp.vehicle_type}
										{#if dp.vehicle_plate}
											<span class="ml-1">({dp.vehicle_plate})</span>
										{/if}
									</p>
								{/if}
								<p class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n ? $i18n.t('Created') : 'Created'}: {formatDate(dp.created_at)}
								</p>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
