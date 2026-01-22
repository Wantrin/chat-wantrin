import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface OrderItem {
	product_id: string;
	name: string;
	price: number;
	quantity: number;
	currency: string;
}

export interface ShippingAddress {
	street: string;
	city: string;
	postal_code: string;
	country: string;
	state?: string;
}

export interface OrderForm {
	shop_id: string;
	customer_name: string;
	customer_email: string;
	customer_phone?: string;
	shipping_address: ShippingAddress;
	items: OrderItem[];
	shipping_cost?: number;
	notes?: string;
	meta?: object;
}

export interface Order {
	id: string;
	user_id?: string;
	shop_id: string;
	customer_name: string;
	customer_email: string;
	customer_phone?: string;
	shipping_address: ShippingAddress;
	items: OrderItem[];
	subtotal: number;
	shipping_cost: number;
	total: number;
	currency: string;
	status: string;
	notes?: string;
	meta?: object;
	created_at: number;
	updated_at: number;
}

export const createNewOrder = async (token: string | null, order: OrderForm) => {
	let error = null;

	const headers: HeadersInit = {
		Accept: 'application/json',
		'Content-Type': 'application/json'
	};

	// Add authorization header only if token is provided
	if (token) {
		headers['authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/create`, {
		method: 'POST',
		headers,
		body: JSON.stringify(order)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOrderById = async (token: string | null, id: string) => {
	let error = null;

	const headers: HeadersInit = {
		Accept: 'application/json',
		'Content-Type': 'application/json'
	};

	// Add authorization header only if token is provided
	if (token) {
		headers['authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/${id}`, {
		method: 'GET',
		headers
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOrdersByUserId = async (token: string, userId: string, page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/user/${userId}?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOrdersByShopId = async (token: string, shopId: string, page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/shop/${shopId}?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateOrderById = async (token: string, id: string, updates: { status?: string; notes?: string; meta?: object }) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(updates)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
