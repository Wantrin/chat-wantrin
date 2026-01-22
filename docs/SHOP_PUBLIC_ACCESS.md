# Guide d'Accès Public aux Magasins

Ce document explique comment les utilisateurs peuvent accéder aux magasins via des URLs publiques.

## URLs Publiques Disponibles

### 1. Liste des Magasins Publics
**URL :** `/public/shops`

Cette page affiche tous les magasins publics (magasins avec `access_control = null`).

**Fonctionnalités :**
- Recherche de magasins
- Affichage en grille des magasins
- Pagination automatique
- Aucune authentification requise

### 2. Page d'un Magasin Public
**URL :** `/public/shops/{shopId}`

Cette page affiche les détails d'un magasin public et ses produits.

**Exemple :**
```
https://votre-domaine.com/public/shops/5b813cef-c750-4e48-83c9-e3b925d3d352
```

**Fonctionnalités :**
- Informations du magasin (nom, description, image)
- Liste des produits du magasin
- Bouton "Ajouter au panier" sur chaque produit
- Navigation vers les pages de produits
- Aucune authentification requise

### 3. Page d'un Produit Public
**URL :** `/public/shops/{shopId}/products/{productId}`

Cette page affiche les détails d'un produit public.

**Exemple :**
```
https://votre-domaine.com/public/shops/5b813cef-c750-4e48-83c9-e3b925d3d352/products/abc123-def456-ghi789
```

**Fonctionnalités :**
- Détails complets du produit
- Galerie d'images (si plusieurs images)
- Prix, stock, catégorie
- Bouton "Ajouter au panier"
- Aucune authentification requise

## Comment Rendre un Magasin Public

Pour qu'un magasin soit accessible publiquement :

1. **Créer ou modifier un magasin**
2. **Définir `access_control` à `null`** lors de la création ou modification
3. Le magasin sera alors accessible via l'URL publique

**Exemple de création d'un magasin public :**
```json
{
  "name": "Mon Magasin",
  "description": "Description du magasin",
  "access_control": null  // null = public
}
```

## Comment Partager un Magasin

### Pour les Propriétaires de Magasins

1. **Via le bouton "Share Shop"** :
   - Aller sur la page de votre magasin (`/shops/{shopId}`)
   - Cliquer sur le bouton "Share Shop"
   - Copier l'URL publique affichée

2. **Via le menu des options** :
   - Sur la carte du magasin, cliquer sur les trois points (...)
   - Sélectionner "Copy Public URL"
   - L'URL sera copiée dans le presse-papiers

### Format de l'URL

L'URL publique d'un magasin suit ce format :
```
https://votre-domaine.com/public/shops/{shopId}
```

Où `{shopId}` est l'ID unique du magasin (UUID).

## Fonctionnalités Disponibles pour les Visiteurs Publics

Les visiteurs non authentifiés peuvent :

✅ **Voir** les magasins publics  
✅ **Voir** les produits des magasins publics  
✅ **Ajouter** des produits au panier  
✅ **Passer** des commandes (commandes invitées)  
✅ **Voir** la confirmation de commande  

❌ **Ne peuvent pas** :
- Modifier les magasins ou produits
- Voir les magasins privés
- Accéder aux commandes d'autres utilisateurs

## SEO et Partage Social

Les pages publiques incluent des métadonnées Open Graph pour un meilleur partage :

- **Titre** : Nom du magasin/produit
- **Description** : Description du magasin/produit
- **Image** : Image du magasin/produit
- **Type** : `website` pour les magasins, `product` pour les produits

Ces métadonnées permettent un affichage riche lors du partage sur les réseaux sociaux.

## Exemples d'Utilisation

### Partager un Magasin sur les Réseaux Sociaux

1. Obtenir l'URL publique via le bouton "Share Shop"
2. Partager l'URL sur Facebook, Twitter, LinkedIn, etc.
3. Les métadonnées Open Graph seront automatiquement utilisées

### Intégrer dans un Site Web

Vous pouvez créer des liens vers vos magasins publics depuis n'importe quel site web :

```html
<a href="https://votre-domaine.com/public/shops/{shopId}">
  Visitez notre magasin
</a>
```

### Envoyer par Email

Copiez l'URL publique et envoyez-la par email à vos clients. Ils pourront accéder directement au magasin sans créer de compte.

## Sécurité

⚠️ **Important** :
- Seuls les magasins avec `access_control = null` sont accessibles publiquement
- Les magasins privés retournent une erreur 404 pour les utilisateurs non autorisés
- Les commandes invitées sont accessibles uniquement via leur ID unique
- Les données sensibles (informations de paiement) ne sont jamais exposées publiquement

## Dépannage

### Le magasin n'est pas accessible publiquement

1. Vérifiez que `access_control` est bien `null` dans la base de données
2. Vérifiez que l'URL utilise bien `/public/shops/{shopId}`
3. Vérifiez que le magasin existe et n'a pas été supprimé

### Erreur 404 sur l'URL publique

- Le magasin n'est probablement pas public (`access_control` n'est pas `null`)
- Le magasin a peut-être été supprimé
- Vérifiez l'ID du magasin dans l'URL
