import { WEBUI_API_BASE_URL } from '$lib/constants';
import { getTimeRange } from '$lib/utils';

type TaskItem = {
	title: string;
	description?: string | null;
	completed?: boolean;
	data?: object;
	meta?: null | object;
	access_control?: null | object;
};

export const createNewTaskItem = async (token: string, taskItem: TaskItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...taskItem
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

export const getTaskItems = async (token: string = '', raw: boolean = false) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/`, {
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

	if (raw) {
		return res; // Return raw response if requested
	}

	if (!Array.isArray(res)) {
		return {}; // or throw new Error("TaskItems response is not an array")
	}

	// Build the grouped object
	const grouped: Record<string, any[]> = {};
	for (const taskItem of res) {
		const timeRange = getTimeRange(taskItem.updated_at / 1000000000);
		if (!grouped[timeRange]) {
			grouped[timeRange] = [];
		}
		grouped[timeRange].push({
			...taskItem,
			timeRange
		});
	}

	return grouped;
};

export const searchTaskItems = async (
	token: string = '',
	query: string | null = null,
	viewOption: string | null = null,
	permission: string | null = null,
	completed: boolean | null = null,
	sortKey: string | null = null,
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

	if (completed !== null) {
		searchParams.append('completed', completed.toString());
	}

	if (sortKey !== null) {
		searchParams.append('order_by', sortKey);
	}

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/search?${searchParams.toString()}`, {
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

export const getTaskItemList = async (token: string = '', page: number | null = null) => {
	let error = null;
	const searchParams = new URLSearchParams();

	if (page !== null) {
		searchParams.append('page', `${page}`);
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/?${searchParams.toString()}`, {
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

export const getTaskItemById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/${id}`, {
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

export const updateTaskItemById = async (token: string, id: string, taskItem: TaskItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...taskItem
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

export const deleteTaskItemById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/task_items/${id}/delete`, {
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
