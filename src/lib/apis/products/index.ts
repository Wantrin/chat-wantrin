import { WEBUI_API_BASE_URL } from '$lib/constants';

type ProductItem = {
	name: string;
	description?: string | null;
	price: number;
	image_url?: string | null;
	image_urls?: string[] | null;
	stock?: number;
	category?: string | null;
	shop_id?: string | null;
	meta?: null | object;
	access_control?: null | object;
};

export const createNewProduct = async (token: string, product: ProductItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...product
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

export const getProducts = async (token: string = '', page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/?${searchParams.toString()}`, {
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

export const searchProducts = async (
	token: string = '',
	query: string | null = null,
	category: string | null = null,
	shopId: string | null = null,
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

	if (category !== null) {
		searchParams.append('category', category);
	}

	if (shopId !== null) {
		searchParams.append('shop_id', shopId);
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

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/search?${searchParams.toString()}`, {
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

export const getProductById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/${id}`, {
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

export const updateProductById = async (token: string, id: string, product: Partial<ProductItem>) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...product
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

export const deleteProductById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/products/${id}/delete`, {
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
