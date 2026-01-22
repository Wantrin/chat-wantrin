import { writable } from 'svelte/store';

export interface CartItem {
	product_id: string;
	shop_id: string;
	name: string;
	price: number;
	currency: string;
	image_url?: string;
	quantity: number;
}

interface Cart {
	items: CartItem[];
}

const createCartStore = () => {
	const { subscribe, set, update } = writable<Cart>({ items: [] });

	// Load from localStorage on initialization
	if (typeof window !== 'undefined') {
		const stored = localStorage.getItem('cart');
		if (stored) {
			try {
				const parsed = JSON.parse(stored);
				set({ items: parsed.items || [] });
			} catch (e) {
				console.error('Error loading cart from localStorage:', e);
				set({ items: [] });
			}
		}
	}

	return {
		subscribe,
		addItem: (item: Omit<CartItem, 'quantity'> & { quantity?: number }) => {
			update((cart) => {
				const existingIndex = cart.items.findIndex(
					(i) => i.product_id === item.product_id
				);

				if (existingIndex >= 0) {
					// Update quantity if item already exists
					cart.items[existingIndex].quantity += item.quantity || 1;
				} else {
					// Add new item
					cart.items.push({
						...item,
						quantity: item.quantity || 1
					});
				}

				// Save to localStorage
				if (typeof window !== 'undefined') {
					localStorage.setItem('cart', JSON.stringify(cart));
				}

				return cart;
			});
		},
		removeItem: (productId: string) => {
			update((cart) => {
				cart.items = cart.items.filter((item) => item.product_id !== productId);
				
				// Save to localStorage
				if (typeof window !== 'undefined') {
					localStorage.setItem('cart', JSON.stringify(cart));
				}

				return cart;
			});
		},
		updateQuantity: (productId: string, quantity: number) => {
			update((cart) => {
				const item = cart.items.find((i) => i.product_id === productId);
				if (item) {
					if (quantity <= 0) {
						cart.items = cart.items.filter((i) => i.product_id !== productId);
					} else {
						item.quantity = quantity;
					}
				}

				// Save to localStorage
				if (typeof window !== 'undefined') {
					localStorage.setItem('cart', JSON.stringify(cart));
				}

				return cart;
			});
		},
		clear: () => {
			set({ items: [] });
			if (typeof window !== 'undefined') {
				localStorage.removeItem('cart');
			}
		},
		getTotal: () => {
			let total = 0;
			update((cart) => {
				total = cart.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
				return cart;
			});
			return total;
		},
		getItemCount: () => {
			let count = 0;
			update((cart) => {
				count = cart.items.reduce((sum, item) => sum + item.quantity, 0);
				return cart;
			});
			return count;
		}
	};
};

export const cart = createCartStore();
