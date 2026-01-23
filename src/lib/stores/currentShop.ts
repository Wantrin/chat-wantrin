import { writable } from 'svelte/store';

export const currentShopName = writable<string | null>(null);
