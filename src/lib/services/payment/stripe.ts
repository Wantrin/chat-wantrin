import type { PaymentIntent, PaymentResult } from './types';
import { createStripePaymentIntent } from '$lib/apis/payments';

/**
 * Stripe Payment Service
 * 
 * This service handles Stripe payment processing.
 * To use this, you need to:
 * 1. Set up Stripe account and get API keys
 * 2. Configure the backend to create payment intents
 * 3. Add Stripe.js script to your HTML
 */

declare global {
	interface Window {
		Stripe?: any;
	}
}

export class StripePaymentService {
	private stripe: any = null;
	private publicKey: string;

	constructor(publicKey: string) {
		this.publicKey = publicKey;
		this.initializeStripe();
	}

	private async initializeStripe() {
		if (typeof window === 'undefined') return;

		// Load Stripe.js if not already loaded
		if (!window.Stripe) {
			await this.loadStripeScript();
		}

		if (window.Stripe && this.publicKey) {
			this.stripe = window.Stripe(this.publicKey);
		}
	}

	private loadStripeScript(): Promise<void> {
		return new Promise((resolve, reject) => {
			if (typeof window === 'undefined') {
				resolve();
				return;
			}

			// Check if script is already loaded
			if (window.Stripe) {
				resolve();
				return;
			}

			const script = document.createElement('script');
			script.src = 'https://js.stripe.com/v3/';
			script.async = true;
			script.onload = () => resolve();
			script.onerror = () => reject(new Error('Failed to load Stripe.js'));
			document.head.appendChild(script);
		});
	}

	async createPaymentIntent(
		amount: number,
		currency: string,
		orderId: string
	): Promise<PaymentIntent> {
		try {
			const response = await createStripePaymentIntent(orderId);
			return {
				id: response.payment_intent_id,
				amount,
				currency,
				status: 'pending',
				clientSecret: response.client_secret
			};
		} catch (error: any) {
			throw new Error(error || 'Failed to create payment intent');
		}
	}

	async processPayment(
		clientSecret: string,
		paymentMethodId: string
	): Promise<PaymentResult> {
		if (!this.stripe) {
			await this.initializeStripe();
		}

		if (!this.stripe) {
			return {
				success: false,
				error: 'Stripe not initialized'
			};
		}

		try {
			const result = await this.stripe.confirmCardPayment(clientSecret, {
				payment_method: paymentMethodId
			});

			if (result.error) {
				return {
					success: false,
					error: result.error.message
				};
			}

			return {
				success: true,
				paymentIntentId: result.paymentIntent.id
			};
		} catch (error: any) {
			return {
				success: false,
				error: error.message || 'Payment processing failed'
			};
		}
	}
}
