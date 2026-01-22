export type PaymentProvider = 'stripe' | 'paypal' | 'manual';

export interface PaymentConfig {
	provider: PaymentProvider;
	stripe?: {
		publicKey: string;
	};
	paypal?: {
		clientId: string;
		mode: 'sandbox' | 'live';
	};
}

export interface PaymentIntent {
	id: string;
	amount: number;
	currency: string;
	status: 'pending' | 'succeeded' | 'failed' | 'cancelled';
	clientSecret?: string;
}

export interface PaymentResult {
	success: boolean;
	paymentIntentId?: string;
	transactionId?: string;
	error?: string;
}
