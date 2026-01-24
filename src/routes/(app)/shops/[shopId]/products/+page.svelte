<script>
	import { getContext, onMount } from 'svelte';

	let i18n;
	try {
		i18n = getContext('i18n');
	} catch (e) {
		console.error('i18n context is not available in shop products page:', e);
		i18n = null;
	}

	import { mobile, showSidebar, user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getShopById } from '$lib/apis/shops';
	import { toast } from 'svelte-sonner';

	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import Products from '$lib/components/products/Products.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Loader from '$lib/components/common/Loader.svelte';

	let loaded = false;
	let shop = null;
	let shopId = null;
	let loading = true;

	onMount(async () => {
		if (typeof window !== 'undefined') {
			loaded = true;
			await loadShop();
		}
	});

	const loadShop = async () => {
		loading = true;
		try {
			const identifier = $page.params.shopId;
			const token = typeof window !== 'undefined' ? localStorage.token : '';
			if (!token) {
				toast.error($i18n ? $i18n.t('No token available') : 'No token available');
				goto('/shops');
				return;
			}

			const res = await getShopById(token, identifier);
			console.log('Shop loaded:', res);
			if (res) {
				shop = res;
				// Use the actual shop ID (database ID) instead of the URL identifier
				shopId = res.id;
				console.log('Using shop ID:', shopId, 'for identifier:', identifier);
			} else {
				toast.error($i18n ? $i18n.t('Shop not found') : 'Shop not found');
				goto('/shops');
			}
		} catch (error) {
			console.error('Error loading shop:', error);
			toast.error(`${error}`);
			goto('/shops');
		} finally {
			loading = false;
		}
	};
</script>

{#if loaded}
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-var(--sidebar-width))]'
			: ''} max-w-full"
	>
		<nav class="   px-2 pt-1.5 backdrop-blur-xl w-full drag-region">
			<div class=" flex items-center">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$i18n ? ($showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')) : ($showSidebar ? 'Close Sidebar' : 'Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="ml-2 py-0.5 self-center flex items-center justify-between w-full">
					<div class="">
						<div
							class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium bg-transparent py-1 touch-auto pointer-events-auto"
						>
							<a class="min-w-fit transition" href="/shops/{$page.params.shopId}/products">
								{$i18n ? $i18n.t('Products') : 'Products'}
							</a>
						</div>
					</div>

					<div class=" self-center flex items-center gap-1">
						{#if $user !== undefined && $user !== null}
							<UserMenu
								className="max-w-[240px]"
								role={$user?.role}
								help={true}
							>
								<button
									class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
									aria-label="User Menu"
								>
									<div class=" self-center">
										<img
											src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
											class="size-6 object-cover rounded-full"
											alt="User"
										/>
									</div>
								</button>
							</UserMenu>
						{/if}
					</div>
				</div>
			</div>
		</nav>

		<div class="flex-1 overflow-hidden">
			{#if loading}
				<div class="flex items-center justify-center h-full">
					<Loader />
				</div>
			{:else if shop && shopId}
				<Products shopId={shopId} showCreateButton={true} />
			{:else}
				<div class="flex items-center justify-center h-full">
					<div class="text-center p-8">
						<p class="text-xl font-semibold text-gray-600 dark:text-gray-400">
							{$i18n ? $i18n.t('Shop not found') : 'Shop not found'}
						</p>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
