import { writable } from 'svelte/store';

export const currentShopImage = writable<string | null>(null);
