import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface PaymentIntentRequest {
	order_id: string;
}

export interface PaymentIntentResponse {
	client_secret: string;
	payment_intent_id: string;
}

export interface ConfirmPaymentRequest {
	payment_intent_id: string;
	order_id: string;
}

export interface PayPalOrderRequest {
	order_id: string;
}

export interface PayPalOrderResponse {
	order_id: string;
	approval_url?: string;
}

export interface ConfirmPayPalRequest {
	paypal_order_id: string;
	order_id: string;
}

/**
 * Create a Stripe payment intent for an order
 */
export const createStripePaymentIntent = async (
	orderId: string
): Promise<PaymentIntentResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/payments/stripe/create-intent`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ order_id: orderId })
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

/**
 * Create a PayPal order for payment
 */
export const createPayPalOrder = async (orderId: string): Promise<PayPalOrderResponse> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/payments/paypal/create-order`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ order_id: orderId })
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

/**
 * Confirm a PayPal payment
 */
export const confirmPayPalPayment = async (
	paypalOrderId: string,
	orderId: string,
	payerId: string
): Promise<{ status: string; order_id: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/payments/paypal/confirm`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			paypal_order_id: paypalOrderId,
			order_id: orderId,
			payer_id: payerId
		})
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
