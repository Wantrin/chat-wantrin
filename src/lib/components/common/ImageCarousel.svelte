<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	
	export let images: string[] = [];
	export let showThumbnails = true;
	export let showIndicators = true;
	export let showArrows = true;
	export let autoPlay = false;
	export let autoPlayInterval = 5000;
	
	const dispatch = createEventDispatcher();
	
	let currentIndex = 0;
	let autoPlayTimer: ReturnType<typeof setInterval> | null = null;
	
	$: if (images.length > 0 && currentIndex >= images.length) {
		currentIndex = 0;
	}
	
	$: currentImage = images[currentIndex] || null;
	
	function nextImage() {
		if (images.length > 0) {
			currentIndex = (currentIndex + 1) % images.length;
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function prevImage() {
		if (images.length > 0) {
			currentIndex = currentIndex === 0 ? images.length - 1 : currentIndex - 1;
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function goToImage(index: number) {
		if (index >= 0 && index < images.length) {
			currentIndex = index;
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function startAutoPlay() {
		if (autoPlay && images.length > 1) {
			autoPlayTimer = setInterval(() => {
				nextImage();
			}, autoPlayInterval);
		}
	}
	
	function stopAutoPlay() {
		if (autoPlayTimer) {
			clearInterval(autoPlayTimer);
			autoPlayTimer = null;
		}
	}
	
	$: if (autoPlay) {
		stopAutoPlay();
		startAutoPlay();
	} else {
		stopAutoPlay();
	}
	
	import { onDestroy } from 'svelte';
	onDestroy(() => {
		stopAutoPlay();
	});
</script>

<div class="relative w-full h-full group">
	<!-- Main Image Container -->
	<div class="relative w-full h-full overflow-hidden bg-gray-100 dark:bg-gray-900 rounded-lg">
		{#if currentImage}
			<img
				src={currentImage}
				alt="Product image {currentIndex + 1}"
				class="w-full h-full object-cover transition-transform duration-500 ease-in-out"
			/>
		{:else}
			<div class="w-full h-full bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
				<span class="text-white text-lg font-medium">No Image</span>
			</div>
		{/if}
		
		<!-- Navigation Arrows -->
		{#if showArrows && images.length > 1}
			<button
				on:click={prevImage}
				class="absolute left-4 top-1/2 -translate-y-1/2 bg-white/80 dark:bg-gray-800/80 hover:bg-white dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 p-2 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10"
				aria-label="Previous image"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<button
				on:click={nextImage}
				class="absolute right-4 top-1/2 -translate-y-1/2 bg-white/80 dark:bg-gray-800/80 hover:bg-white dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 p-2 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10"
				aria-label="Next image"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</button>
		{/if}
		
		<!-- Indicators -->
		{#if showIndicators && images.length > 1}
			<div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2 z-10">
				{#each images as _, idx}
					<button
						on:click={() => goToImage(idx)}
						class="w-2 h-2 rounded-full transition-all duration-200 {currentIndex === idx
							? 'bg-white w-6'
							: 'bg-white/50 hover:bg-white/75'}"
						aria-label="Go to image {idx + 1}"
					></button>
				{/each}
			</div>
		{/if}
	</div>
	
	<!-- Thumbnails -->
	{#if showThumbnails && images.length > 1}
		<div class="mt-4 flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent">
			{#each images as image, idx}
				<button
					on:click={() => goToImage(idx)}
					class="flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all duration-200 {currentIndex === idx
						? 'border-blue-500 dark:border-blue-400 ring-2 ring-blue-200 dark:ring-blue-800'
						: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}"
					aria-label="View image {idx + 1}"
				>
					<img
						src={image}
						alt="Thumbnail {idx + 1}"
						class="w-full h-full object-cover {currentIndex === idx
							? 'opacity-100'
							: 'opacity-70 hover:opacity-100'} transition-opacity duration-200"
					/>
				</button>
			{/each}
		</div>
	{/if}
</div>
