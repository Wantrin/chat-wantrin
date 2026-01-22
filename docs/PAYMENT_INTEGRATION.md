# Guide d'Intégration des Paiements

Ce document explique comment intégrer les systèmes de paiement (Stripe, PayPal) dans l'application.

## Architecture

Le système de paiement est modulaire et supporte plusieurs providers :
- **Stripe** : Paiements par carte bancaire
- **PayPal** : Paiements PayPal
- **Manual** : Paiement manuel (virement bancaire, espèces, etc.)

## Structure des Fichiers

```
src/lib/services/payment/
├── index.ts          # Service principal et factory
├── types.ts          # Types TypeScript
├── stripe.ts         # Implémentation Stripe
└── paypal.ts         # Implémentation PayPal
```

## Configuration

### Stripe

1. **Créer un compte Stripe** : https://stripe.com
2. **Obtenir les clés API** :
   - Clé publique (pk_test_... ou pk_live_...)
   - Clé secrète (sk_test_... ou sk_live_...)
3. **Configurer le backend** :
   - Ajouter les clés dans les variables d'environnement
   - Créer un endpoint pour créer des Payment Intents

### PayPal

1. **Créer un compte PayPal Business** : https://www.paypal.com/business
2. **Obtenir le Client ID** :
   - Aller dans PayPal Developer Dashboard
   - Créer une application
   - Copier le Client ID
3. **Configurer le backend** :
   - Ajouter le Client ID dans les variables d'environnement
   - Configurer les webhooks pour les notifications

## Utilisation

### Exemple avec Stripe

```typescript
import { PaymentService } from '$lib/services/payment';

const paymentService = new PaymentService({
  provider: 'stripe',
  stripe: {
    publicKey: 'pk_test_...'
  }
});

// Créer un payment intent (côté backend)
// Puis utiliser le client secret pour confirmer le paiement
const result = await paymentService.processPayment(
  100,      // Montant en centimes
  'EUR',    // Devise
  'order-123', // ID de la commande
  'pm_...'  // Payment Method ID
);
```

### Exemple avec PayPal

```typescript
import { PaymentService } from '$lib/services/payment';

const paymentService = new PaymentService({
  provider: 'paypal',
  paypal: {
    clientId: 'your-client-id',
    mode: 'sandbox' // ou 'live' pour la production
  }
});

const result = await paymentService.processPayment(
  100,      // Montant
  'EUR',    // Devise
  'order-123' // ID de la commande
);
```

### Exemple avec Paiement Manuel

```typescript
import { PaymentService } from '$lib/services/payment';

const paymentService = new PaymentService({
  provider: 'manual'
});

// Le paiement manuel retourne toujours success
// L'ordre sera marqué comme "pending" et payé manuellement
const result = await paymentService.processPayment(
  100,
  'EUR',
  'order-123'
);
```

## Intégration Backend

### Endpoint pour créer un Payment Intent (Stripe)

```python
@router.post("/orders/{order_id}/payment-intent")
async def create_payment_intent(
    order_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    order = Orders.get_order_by_id(order_id, db=db)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    import stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    intent = stripe.PaymentIntent.create(
        amount=int(order.total * 100),  # Convertir en centimes
        currency=order.currency.lower(),
        metadata={"order_id": order.id}
    )
    
    return {
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id
    }
```

### Webhook pour confirmer le paiement (Stripe)

```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        order_id = payment_intent["metadata"]["order_id"]
        
        # Mettre à jour le statut de la commande
        order = Orders.get_order_by_id(order_id, db=db)
        if order:
            Orders.update_order_by_id(
                order_id,
                OrderUpdateForm(status="confirmed"),
                db=db
            )
    
    return {"status": "success"}
```

## Sécurité

⚠️ **Important** :
- Ne jamais exposer les clés secrètes côté client
- Toujours valider les paiements côté serveur
- Utiliser HTTPS en production
- Vérifier les signatures des webhooks
- Ne jamais faire confiance aux données client pour les montants

## Prochaines Étapes

1. **Implémenter les endpoints backend** pour créer les payment intents
2. **Configurer les webhooks** pour recevoir les notifications
3. **Ajouter l'UI de paiement** dans la page de checkout
4. **Tester en mode sandbox** avant de passer en production
5. **Ajouter la gestion des erreurs** et des remboursements

## Ressources

- [Documentation Stripe](https://stripe.com/docs)
- [Documentation PayPal](https://developer.paypal.com/docs)
- [Stripe Testing](https://stripe.com/docs/testing)
- [PayPal Sandbox](https://developer.paypal.com/docs/api-basics/sandbox/)
