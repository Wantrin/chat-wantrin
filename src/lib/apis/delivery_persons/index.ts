import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface DeliveryPerson {
	id: string;
	shop_id: string;
	user_id?: string;
	name: string;
	email?: string;
	phone?: string;
	vehicle_type?: string;
	vehicle_plate?: string;
	is_active: boolean;
	notes?: string;
	meta?: object;
	created_at: number;
	updated_at: number;
}

export interface DeliveryPersonForm {
	shop_id: string;
	user_id?: string;
	name: string;
	email?: string;
	phone?: string;
	vehicle_type?: string;
	vehicle_plate?: string;
	is_active?: boolean;
	notes?: string;
	meta?: object;
}

export interface DeliveryPersonUpdateForm {
	name?: string;
	email?: string;
	phone?: string;
	vehicle_type?: string;
	vehicle_plate?: string;
	is_active?: boolean;
	notes?: string;
	meta?: object;
}

export const createDeliveryPerson = async (token: string, deliveryPerson: DeliveryPersonForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/delivery-persons/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(deliveryPerson)
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

export const getDeliveryPersonById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/delivery-persons/${id}`, {
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

	return res;
};

export const getDeliveryPersonsByShopId = async (
	token: string,
	shopId: string,
	activeOnly: boolean = false
): Promise<DeliveryPerson[]> => {
	let error = null;
	const searchParams = new URLSearchParams();
	if (activeOnly) {
		searchParams.append('active_only', 'true');
	}

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/delivery-persons/shop/${shopId}?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const updateDeliveryPersonById = async (
	token: string,
	id: string,
	updates: DeliveryPersonUpdateForm
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/delivery-persons/${id}/update`, {
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

export const deleteDeliveryPersonById = async (token: string, id: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/delivery-persons/${id}/delete`, {
		method: 'DELETE',
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

	return res;
};
