import type { PaymentConfig, PaymentProvider, PaymentResult } from './types';
import { StripePaymentService } from './stripe';
import { PayPalPaymentService } from './paypal';

/**
 * Payment Service Factory
 * 
 * This module provides a unified interface for different payment providers.
 * Currently supports:
 * - Stripe
 * - PayPal
 * - Manual (for cash on delivery, bank transfer, etc.)
 */

export class PaymentService {
	private config: PaymentConfig;
	private stripeService?: StripePaymentService;
	private paypalService?: PayPalPaymentService;

	constructor(config: PaymentConfig) {
		this.config = config;

		if (config.provider === 'stripe' && config.stripe) {
			this.stripeService = new StripePaymentService(config.stripe.publicKey);
		}

		if (config.provider === 'paypal' && config.paypal) {
			this.paypalService = new PayPalPaymentService(
				config.paypal.clientId,
				config.paypal.mode
			);
		}
	}

	async processPayment(
		amount: number,
		currency: string,
		orderId: string,
		paymentMethodId?: string
	): Promise<PaymentResult> {
		switch (this.config.provider) {
			case 'stripe':
				if (!this.stripeService) {
					return {
						success: false,
						error: 'Stripe not configured'
					};
				}
				// Stripe payment intent creation is handled separately
				// This method is kept for compatibility but should use createPaymentIntent + processPayment
				return {
					success: false,
					error: 'Use createPaymentIntent and processPayment methods for Stripe'
				};

			case 'paypal':
				if (!this.paypalService) {
					return {
						success: false,
						error: 'PayPal not configured'
					};
				}
				return await this.paypalService.createPayment(amount, currency, orderId);

			case 'manual':
				// Manual payment - just return success
				// The order will be marked as pending and paid manually
				return {
					success: true,
					transactionId: `manual-${orderId}-${Date.now()}`
				};

			default:
				return {
					success: false,
					error: 'Unknown payment provider'
				};
		}
	}

	async createStripePaymentIntent(
		amount: number,
		currency: string,
		orderId: string
	): Promise<{ clientSecret: string; paymentIntentId: string } | null> {
		if (this.config.provider !== 'stripe' || !this.stripeService) {
			return null;
		}
		const intent = await this.stripeService.createPaymentIntent(amount, currency, orderId);
		return {
			clientSecret: intent.clientSecret || '',
			paymentIntentId: intent.id
		};
	}

	async processStripePayment(
		clientSecret: string,
		paymentMethodId: string
	): Promise<PaymentResult> {
		if (this.config.provider !== 'stripe' || !this.stripeService) {
			return {
				success: false,
				error: 'Stripe not configured'
			};
		}
		return await this.stripeService.processPayment(clientSecret, paymentMethodId);
	}

	getProvider(): PaymentProvider {
		return this.config.provider;
	}
}

/**
 * Example usage:
 * 
 * const paymentService = new PaymentService({
 *   provider: 'stripe',
 *   stripe: {
 *     publicKey: 'pk_test_...'
 *   }
 * });
 * 
 * const result = await paymentService.processPayment(100, 'EUR', 'order-123');
 */
