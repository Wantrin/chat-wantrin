import { WEBUI_BASE_URL } from '$lib/constants';

const GEMINI_API_BASE_URL = `${WEBUI_BASE_URL}/gemini`;

export const getGeminiConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${GEMINI_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) {
				const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status} Error` }));
				throw errorData;
			}
			return res.json();
		})
		.catch((err) => {
			console.error('getGeminiConfig error:', err);
			if (err && typeof err === 'object') {
				if ('detail' in err) {
					error = err.detail;
				} else if ('error' in err) {
					error = err.error;
				} else {
					error = 'Server connection failed';
				}
			} else {
				error = err?.toString() || 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	// Ensure we always return an object with the expected structure
	return res || {
		GEMINI_API_KEY: '',
		GEMINI_API_BASE_URL: 'https://generativelanguage.googleapis.com'
	};
};

type GeminiConfig = {
	GEMINI_API_KEY: string;
	GEMINI_API_BASE_URL: string;
};

export const updateGeminiConfig = async (token: string = '', config: GeminiConfig) => {
	let error = null;

	const res = await fetch(`${GEMINI_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getGeminiKey = async (token: string = ''): Promise<string | null> => {
	let error = null;

	const res = await fetch(`${GEMINI_API_BASE_URL}/key`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.GEMINI_API_KEY || null;
};
