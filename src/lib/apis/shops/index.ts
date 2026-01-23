import { WEBUI_API_BASE_URL } from '$lib/constants';

type ShopItem = {
	name: string;
	description?: string | null;
	image_url?: string | null;
	url?: string | null;
	meta?: null | object;
	is_public?: boolean | null;
	access_control?: null | object;
};

export const createNewShop = async (token: string, shop: ShopItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...shop
		})
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

export const getShops = async (token: string = '', page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/?${searchParams.toString()}`, {
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
		.then((json) => {
			return json;
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

export const searchShops = async (
	token: string = '',
	query: string | null = null,
	viewOption: string | null = null,
	permission: string | null = null,
	orderBy: string | null = null,
	direction: string | null = null,
	page: number | null = null
) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (query !== null) {
		searchParams.append('query', query);
	}

	if (viewOption !== null) {
		searchParams.append('view_option', viewOption);
	}

	if (permission !== null) {
		searchParams.append('permission', permission);
	}

	if (orderBy !== null) {
		searchParams.append('order_by', orderBy);
	}

	if (direction !== null) {
		searchParams.append('direction', direction);
	}

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/search?${searchParams.toString()}`, {
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
		.then((json) => {
			return json;
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

export const getShopById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/${id}`, {
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
		.then((json) => {
			return json;
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

export const updateShopById = async (token: string, id: string, shop: Partial<ShopItem>) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...shop
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
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

export const deleteShopById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/${id}/delete`, {
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
		.then((json) => {
			return json;
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

// Public API functions (no authentication required)
export const getPublicShopById = async (id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/public/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
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

export const searchPublicShops = async (
	query: string | null = null,
	orderBy: string | null = null,
	direction: string | null = null,
	page: number | null = null
) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (query !== null) {
		searchParams.append('query', query);
	}

	if (orderBy !== null) {
		searchParams.append('order_by', orderBy);
	}

	if (direction !== null) {
		searchParams.append('direction', direction);
	}

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/shops/public/search?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
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
