<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	
	export let images: string[] = [];
	export let showThumbnails = true;
	export let showIndicators = true;
	export let showArrows = true;
	export let autoPlay = false;
	export let autoPlayInterval = 5000;
	export let enableZoom = false;
	export let transitionType: 'slide' | 'fade' = 'fade';
	
	const dispatch = createEventDispatcher();
	
	let currentIndex = 0;
	let autoPlayTimer: ReturnType<typeof setInterval> | null = null;
	let imageContainer: HTMLDivElement;
	let touchStartX = 0;
	let touchEndX = 0;
	let isZoomed = false;
	let imageError = false;
	
	$: if (images.length > 0 && currentIndex >= images.length) {
		currentIndex = 0;
	}
	
	$: currentImage = images[currentIndex] || null;
	
	function nextImage() {
		if (images.length > 0) {
			currentIndex = (currentIndex + 1) % images.length;
			imageError = false;
			isZoomed = false; // Reset zoom when changing image
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function prevImage() {
		if (images.length > 0) {
			currentIndex = currentIndex === 0 ? images.length - 1 : currentIndex - 1;
			imageError = false;
			isZoomed = false; // Reset zoom when changing image
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function goToImage(index: number) {
		if (index >= 0 && index < images.length) {
			currentIndex = index;
			imageError = false;
			isZoomed = false; // Reset zoom when changing image
			dispatch('change', { index: currentIndex, image: currentImage });
		}
	}
	
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'ArrowLeft') {
			prevImage();
		} else if (event.key === 'ArrowRight') {
			nextImage();
		}
	}
	
	function handleTouchStart(event: TouchEvent) {
		touchStartX = event.changedTouches[0].screenX;
	}
	
	function handleTouchEnd(event: TouchEvent) {
		touchEndX = event.changedTouches[0].screenX;
		handleSwipe();
	}
	
	function handleSwipe() {
		const swipeThreshold = 50;
		const diff = touchStartX - touchEndX;
		
		if (Math.abs(diff) > swipeThreshold) {
			if (diff > 0) {
				nextImage();
			} else {
				prevImage();
			}
		}
	}
	
	function toggleZoom() {
		if (enableZoom) {
			isZoomed = !isZoomed;
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
	
	onMount(() => {
		if (imageContainer) {
			imageContainer.addEventListener('keydown', handleKeyDown);
			imageContainer.addEventListener('touchstart', handleTouchStart);
			imageContainer.addEventListener('touchend', handleTouchEnd);
			imageContainer.setAttribute('tabindex', '0');
		}
	});
	
	onDestroy(() => {
		stopAutoPlay();
		if (imageContainer) {
			imageContainer.removeEventListener('keydown', handleKeyDown);
			imageContainer.removeEventListener('touchstart', handleTouchStart);
			imageContainer.removeEventListener('touchend', handleTouchEnd);
		}
	});
</script>

<div class="relative w-full h-full group">
	<!-- Main Image Container -->
	<div
		bind:this={imageContainer}
		class="relative w-full h-full {isZoomed && enableZoom ? 'overflow-auto' : 'overflow-hidden'} bg-gray-100 dark:bg-gray-900 rounded-lg cursor-{enableZoom ? (isZoomed ? 'zoom-out' : 'zoom-in') : 'default'}"
		on:click={toggleZoom}
		role="img"
		aria-label="Product image carousel"
	>
		{#if currentImage && !imageError}
			<div
				class="w-full h-full {transitionType === 'fade'
					? 'transition-opacity duration-500 ease-in-out'
					: 'transition-transform duration-500 ease-in-out'} {isZoomed && enableZoom
					? 'scale-150'
					: ''}"
			>
				<img
					src={currentImage}
					alt="Product image {currentIndex + 1} of {images.length}"
					class="w-full h-full {isZoomed && enableZoom ? 'object-contain' : 'object-cover'} {enableZoom ? 'cursor-zoom-in' : ''}"
					on:error={() => {
						imageError = true;
					}}
					loading="lazy"
				/>
			</div>
		{:else if imageError}
			<div class="w-full h-full bg-gradient-to-br from-gray-200 via-gray-300 to-gray-400 dark:from-gray-700 dark:via-gray-600 dark:to-gray-800 flex items-center justify-center">
				<div class="text-center">
					<svg
						class="w-16 h-16 mx-auto text-gray-400 dark:text-gray-500 mb-2"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
						/>
					</svg>
					<span class="text-gray-500 dark:text-gray-400 text-sm">Image failed to load</span>
				</div>
			</div>
		{:else}
			<div class="w-full h-full bg-gradient-to-br from-blue-400 via-orange-500 to-blue-600 dark:from-blue-600 dark:via-orange-600 dark:to-blue-800 flex items-center justify-center">
				<span class="text-white text-lg font-medium">No Image</span>
			</div>
		{/if}
		
		<!-- Navigation Arrows -->
		{#if showArrows && images.length > 1}
			<button
				on:click|stopPropagation={prevImage}
				class="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 bg-white/90 dark:bg-gray-800/90 hover:bg-white dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 p-2 md:p-3 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-all duration-200 z-20 hover:scale-110 active:scale-95"
				aria-label="Previous image"
			>
				<svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<button
				on:click|stopPropagation={nextImage}
				class="absolute right-2 md:right-4 top-1/2 -translate-y-1/2 bg-white/90 dark:bg-gray-800/90 hover:bg-white dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 p-2 md:p-3 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-all duration-200 z-20 hover:scale-110 active:scale-95"
				aria-label="Next image"
			>
				<svg class="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
		<div class="mt-4 flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent snap-x snap-mandatory">
			{#each images as image, idx}
				<button
					on:click={() => goToImage(idx)}
					class="flex-shrink-0 w-16 h-16 md:w-20 md:h-20 rounded-lg overflow-hidden border-2 transition-all duration-200 snap-start {currentIndex === idx
						? 'border-blue-500 dark:border-blue-400 ring-2 ring-blue-200 dark:ring-blue-800 scale-105'
						: 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 hover:scale-105'}"
					aria-label="View image {idx + 1}"
					aria-current={currentIndex === idx ? 'true' : 'false'}
				>
					<img
						src={image}
						alt="Thumbnail {idx + 1}"
						class="w-full h-full object-cover {currentIndex === idx
							? 'opacity-100'
							: 'opacity-70 hover:opacity-100'} transition-opacity duration-200"
						loading="lazy"
					/>
				</button>
			{/each}
		</div>
	{/if}
</div>
