<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getProductById } from '$lib/apis/products';
	import { user } from '$lib/stores';

	const i18n = getContext('i18n');

	let product = null;
	let loading = true;

	const formatPrice = (price: number) => {
		return new Intl.NumberFormat('fr-FR', {
			style: 'currency',
			currency: 'EUR'
		}).format(price);
	};

	onMount(async () => {
		try {
			const res = await getProductById(localStorage.token, $page.params.id);
			if (res) {
				product = res;
			} else {
				toast.error($i18n.t('Product not found'));
				goto('/shop');
			}
		} catch (error) {
			toast.error(`${error}`);
			goto('/shop');
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if product}
	<div class="max-w-4xl mx-auto p-6">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div>
				{#if product.image_url}
					<img
						src={product.image_url}
						alt={product.name}
						class="w-full rounded-lg"
					/>
				{:else}
					<div class="w-full h-96 bg-gray-200 dark:bg-gray-700 flex items-center justify-center rounded-lg">
						<span class="text-gray-400 dark:text-gray-500">{$i18n.t('No Image')}</span>
					</div>
				{/if}
			</div>
			<div>
				<h1 class="text-3xl font-bold mb-4">{product.name}</h1>
				{#if product.description}
					<p class="text-gray-600 dark:text-gray-400 mb-4">{product.description}</p>
				{/if}
				<div class="mb-4">
					<span class="text-3xl font-bold text-blue-600 dark:text-blue-400">
						{formatPrice(product.price)}
					</span>
				</div>
				{#if product.stock !== undefined}
					<div class="mb-4">
						<span
							class="text-lg {product.stock > 0
								? 'text-green-600 dark:text-green-400'
								: 'text-red-600 dark:text-red-400'}"
						>
							{product.stock > 0
								? `${product.stock} ${$i18n.t('in stock')}`
								: $i18n.t('Out of stock')}
						</span>
					</div>
				{/if}
				{#if product.category}
					<div class="mb-4">
						<span class="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
							{product.category}
						</span>
					</div>
				{/if}
				{#if $user && ($user.id === product.user_id || $user.role === 'admin')}
					<div class="mt-6">
						<button
							on:click={() => goto(`/shop/${product.id}/edit`)}
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
						>
							{$i18n.t('Edit Product')}
						</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
