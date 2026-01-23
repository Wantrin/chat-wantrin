import { writable } from 'svelte/store';

export interface ShopColors {
	primary: string | null;
	secondary: string | null;
}

export const shopColors = writable<ShopColors>({
	primary: null,
	secondary: null
});
