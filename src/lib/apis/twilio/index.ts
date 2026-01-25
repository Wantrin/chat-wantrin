import { WEBUI_BASE_URL } from '$lib/constants';

const TWILIO_API_BASE_URL = `${WEBUI_BASE_URL}/twilio`;

export const getTwilioConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${TWILIO_API_BASE_URL}/config`, {
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
			console.error('getTwilioConfig error:', err);
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
		TWILIO_ACCOUNT_SID: '',
		TWILIO_AUTH_TOKEN: '',
		TWILIO_PHONE_NUMBER: '',
		ENABLE_TWILIO: false
	};
};

type TwilioConfig = {
	TWILIO_ACCOUNT_SID?: string;
	TWILIO_AUTH_TOKEN?: string;
	TWILIO_PHONE_NUMBER?: string;
	ENABLE_TWILIO?: boolean;
};

export const updateTwilioConfig = async (token: string = '', config: TwilioConfig) => {
	let error = null;

	const res = await fetch(`${TWILIO_API_BASE_URL}/config/update`, {
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
