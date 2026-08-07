# Soccer Fans PRO — Telegram Mini App

Version optimisée de la boutique.

## Inclus
- UI mobile premium
- Navigation Boutique / Favoris / Panier / Compte
- Identification Telegram côté interface
- Catalogue + recherche + catégories
- Fan / Player / Rétro / Enfant
- Tailles et flocage
- Favoris persistants
- Panier persistant
- Code promo démo WELCOME10
- Livraison offerte dès 100 €
- Exemple d'endpoint sécurisé de validation `initData`
- Prêt pour Vercel / Telegram Mini Apps

## Installation
```bash
npm install
npm run dev
```

## Mise en ligne Vercel
1. Mets le projet sur GitHub ou importe le dossier dans Vercel.
2. Ajoute la variable serveur `TELEGRAM_BOT_TOKEN`.
3. Déploie.
4. Récupère l'URL HTTPS.
5. Dans BotFather, configure cette URL comme Mini App / Menu Button.

## Sécurité
Ne jamais exposer `TELEGRAM_BOT_TOKEN` dans le navigateur.

Les données `Telegram.WebApp.initDataUnsafe` sont pratiques pour afficher l'utilisateur,
mais ne doivent jamais être considérées comme authentifiées côté serveur.

Pour créer un compte, une commande ou accepter un paiement, envoie
`Telegram.WebApp.initData` à ton serveur et valide sa signature côté serveur.

Le fichier `app/api/telegram-auth/route.js` contient un exemple de validation HMAC.

## Prochain niveau production
À brancher ensuite :
- Supabase (produits, clients, commandes, stock, codes promo)
- stockage images
- dashboard administrateur
- paiement
- webhook bot Telegram
- suivi colis
- emails / notifications
