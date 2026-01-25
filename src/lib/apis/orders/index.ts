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
	tracking_number?: string;
	carrier?: string;
	tracking_url?: string;
	shipped_at?: number;
	estimated_delivery_date?: number;
	delivered_at?: number;
	assigned_user_id?: string;
	assigned_delivery_person_id?: string;
	notes?: string;
	meta?: object;
	created_at: number;
	updated_at: number;
}

export interface OrderStatusHistory {
	id: string;
	order_id: string;
	status: string;
	notes?: string;
	created_at: number;
}

export interface OrderUpdateForm {
	status?: string;
	tracking_number?: string;
	carrier?: string;
	tracking_url?: string;
	estimated_delivery_date?: number;
	assigned_user_id?: string;
	assigned_delivery_person_id?: string;
	notes?: string;
	meta?: object;
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

	const queryString = searchParams.toString();
	const url = queryString 
		? `${WEBUI_API_BASE_URL}/orders/user/${userId}?${queryString}`
		: `${WEBUI_API_BASE_URL}/orders/user/${userId}`;

	const res = await fetch(url, {
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

	// Clean shopId to remove any trailing colons or invalid characters
	const cleanShopId = shopId?.trim().replace(/[:;]/g, '');
	if (!cleanShopId) {
		throw new Error('Invalid shop ID');
	}

	const queryString = searchParams.toString();
	const url = queryString 
		? `${WEBUI_API_BASE_URL}/orders/shop/${cleanShopId}?${queryString}`
		: `${WEBUI_API_BASE_URL}/orders/shop/${cleanShopId}`;

	const res = await fetch(url, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) {
				const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
				throw errorData;
			}
			return res.json();
		})
		.catch((err) => {
			error = err.detail || err.message || err;
			console.error('Error in getOrdersByShopId:', err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateOrderById = async (token: string, id: string, updates: OrderUpdateForm) => {
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

export const getOrderStatusHistory = async (token: string, orderId: string): Promise<OrderStatusHistory[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/${orderId}/status-history`, {
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
			error = err.detail || err.message;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

export interface PhoneCallForm {
	phone_number: string;
	order_id?: string;
	delivery_person_id?: string;
	call_type: 'customer' | 'delivery_person';
	context?: object;
}

export interface PhoneCallResponse {
	call_id: string;
	status: string;
	message: string;
}

export const initiatePhoneCall = async (
	token: string,
	orderId: string,
	formData: PhoneCallForm
): Promise<PhoneCallResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/orders/${orderId}/initiate-phone-call`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(formData)
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

export interface SMSForm {
	phone_number?: string;
	message: string;
	delivery_person_id?: string;
	send_to: 'customer' | 'delivery_person' | 'both';
	context?: object;
}

export interface SMSResponse {
	message_sid?: string;
	status: string;
	message: string;
	sent_to: string[];
}

export const sendSMS = async (
	token: string,
	orderId: string,
	formData: SMSForm
): Promise<SMSResponse> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/orders/${orderId}/send-sms`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(formData)
		});

		if (!res.ok) {
			const errorData = await res.json();
			throw errorData;
		}

		return await res.json();
	} catch (err: any) {
		console.error('SMS API error:', err);
		// Re-throw to be caught by the component
		throw err;
	}
};
