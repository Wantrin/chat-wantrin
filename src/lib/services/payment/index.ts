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
				// For Stripe, you would first create a payment intent on the backend
				// then use the client secret here
				return {
					success: false,
					error: 'Stripe payment processing requires backend integration'
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
