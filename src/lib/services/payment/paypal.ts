import type { PaymentIntent, PaymentResult } from './types';
import { createPayPalOrder, confirmPayPalPayment } from '$lib/apis/payments';

/**
 * PayPal Payment Service
 * 
 * This service handles PayPal payment processing.
 * To use this, you need to:
 * 1. Set up PayPal Business account
 * 2. Get Client ID from PayPal Developer Dashboard
 * 3. Add PayPal SDK script to your HTML
 */

declare global {
	interface Window {
		paypal?: any;
	}
}

export class PayPalPaymentService {
	private clientId: string;
	private mode: 'sandbox' | 'live';

	constructor(clientId: string, mode: 'sandbox' | 'live' = 'sandbox') {
		this.clientId = clientId;
		this.mode = mode;
	}

	private async loadPayPalScript(): Promise<void> {
		return new Promise((resolve, reject) => {
			if (typeof window === 'undefined') {
				resolve();
				return;
			}

			// Check if script is already loaded
			if (window.paypal) {
				resolve();
				return;
			}

			const script = document.createElement('script');
			script.src = `https://www.paypal.com/sdk/js?client-id=${this.clientId}&currency=EUR`;
			script.async = true;
			script.onload = () => resolve();
			script.onerror = () => reject(new Error('Failed to load PayPal SDK'));
			document.head.appendChild(script);
		});
	}

	async createPayment(amount: number, currency: string, orderId: string): Promise<PaymentResult> {
		try {
			const response = await createPayPalOrder(orderId);
			return {
				success: true,
				transactionId: response.order_id
			};
		} catch (error: any) {
			return {
				success: false,
				error: error || 'Failed to create PayPal payment'
			};
		}
	}

	async createPayPalButton(
		orderId: string,
		onSuccess: (orderId: string) => void,
		onError: (error: string) => void
	): Promise<void> {
		await this.loadPayPalScript();

		if (!window.paypal) {
			onError('PayPal SDK not loaded');
			return;
		}

		// Create PayPal order via backend
		try {
			const paypalOrder = await createPayPalOrder(orderId);
			
			window.paypal
				.Buttons({
					createOrder: () => {
						return paypalOrder.order_id;
					},
					onApprove: async (data: any, actions: any) => {
						try {
							// Confirm payment via backend
							await confirmPayPalPayment(
								paypalOrder.order_id,
								orderId,
								data.payerID
							);
							onSuccess(orderId);
						} catch (error: any) {
							onError(error || 'Failed to confirm payment');
						}
					},
					onError: (err: any) => {
						onError(err.message || 'PayPal payment failed');
					},
					onCancel: () => {
						onError('Payment cancelled');
					}
				})
				.render('#paypal-button-container');
		} catch (error: any) {
			onError(error || 'Failed to initialize PayPal payment');
		}
	}
}
