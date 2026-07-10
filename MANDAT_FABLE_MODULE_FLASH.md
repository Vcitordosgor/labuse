# MANDAT FABLE — Module Flash : le rapport parcelle à l'unité

**Repos** : moteur `~/Desktop/labuse` (Lots 1, 2, 4) + site marketing `labuse.immo` (Lot 3) · **Branches** : `feat/module-flash` sur chaque repo · **Merge** : Vic uniquement (`git merge --no-ff`).

---

## 1. Contexte business

Produit : **rapport de faisabilité PDF pour UNE parcelle**, généré automatiquement depuis la base, vendu à l'unité **sans abonnement**. Cibles : notaires (due diligence, négociation immobilière) et architectes/experts fonciers (pré-faisabilité) — plus la longue traîne (particuliers avertis, agents ponctuels). Prix : paramètre config `FLASH_PRICE_EUR`, valeur de lancement suggérée 79€ TTC, décision finale Vic au moment de créer le produit Stripe.

Rôle stratégique : monétiser la longue traîne sans support, lead magnet vers l'abo, et destination naturelle du libellé "potentiel indicatif" du moteur de segments (l'analyse fine que ce libellé promet, c'est Flash).

## 2. Règles anti-cannibalisation (NON NÉGOCIABLES)

Flash vend l'analyse d'UNE parcelle que le client a déjà identifiée. L'abo vend la DÉCOUVERTE des parcelles. Donc :

- Le sélecteur Flash permet de trouver **sa** parcelle (adresse via géocodage BAN, ou saisie de références cadastrales) — AUCUNE exploration : pas de carte des parcelles chaudes, pas de filtres, pas de tri, pas de "parcelles similaires".
- Le rapport présente les attributs de LA parcelle. Le score Q×A y figure en valeur absolue avec sa grille de lecture — **jamais** de classement, percentile île, ou comparaison multi-parcelles (c'est la valeur de l'abo).
- Pas d'achat en lot, pas d'API, pas de code promo volumique. Un besoin récurrent = l'abo, et la page de vente le dit.

## 3. Schéma

```sql
flash_orders(id PK, order_ref unique,             -- ex. FL-2026-00042, visible client
             stripe_session_id unique, stripe_payment_intent,
             email text, idu text, adresse_saisie text,
             statut text,                          -- 'paid'|'generating'|'delivered'|'failed'|'refunded'
             pdf_path text, download_token text, token_expires_at,
             price_paid_cents int, created_at, delivered_at)
```

---

## Lot 1 — Le générateur de rapport

1. **Moteur** : fonction `generate_flash_report(idu) -> pdf_path`. HTML/CSS → PDF via WeasyPrint (stack Python cohérent). Template versionné.
2. **DA print** : déclinaison imprimable de la DA LABUSE — fond BLANC (un notaire imprime), typographies de la marque, accents vert menthe, en-tête/pied avec logo, n° de rapport, date de génération et pagination. Pas le thème sombre du site.
3. **Sections** (chacune conditionnelle : le générateur détecte les tables/colonnes disponibles — même résilience que le moteur de segments — et omet proprement une section sans donnée) :
   - **Page de garde** : adresse, références cadastrales, commune, carte de situation (fond cartographique aux tuiles libres avec attribution), n° et date.
   - **Identité parcellaire** : surface, contenance, zonage PLU **avec les règles calibrées** (emprise, hauteur si calibrée) — c'est LA valeur différenciante, le calibrage "premium fin" des 23 communes + RNU Saint-Philippe.
   - **Constructibilité** : synthèse zonage + si parcelle bâtie, droits résiduels/surélévation (libellé "potentiel indicatif" du M2) ; si nue, lecture du score Q×A en absolu.
   - **Risques** : Géorisques (aléas), ICPE à proximité, PEB si concerné.
   - **Patrimoine & environnement** : ABF/Mérimée, ENS, QPV, Cartofriches.
   - **Marché** : mutations DVF dans un rayon de 500 m sur 3 ans — nombre, prix médian au m², 3-5 comparables anonymisés (type, surface, prix, mois — jamais d'adresse exacte des comparables).
   - **Dynamique locale** : permis de construire Sitadel à proximité (nombre 24 mois, plus gros projets en nb de logements).
   - **Terrain & réseaux** (selon mandats mergés) : pente moyenne, exposition solaire PVGIS, zone/proba ANC, canopée.
   - **Sources & millésimes** : tableau final citant chaque source avec son millésime — les notaires sont exigeants sur le sourcing, cette page est un argument de vente, pas une annexe.
   - **Mentions** : "Document d'information établi à partir de données publiques. Ne constitue ni un document d'urbanisme opposable, ni une étude de faisabilité réglementaire, ni un conseil juridique. Les règles complètes du PLU peuvent modifier les potentiels indiqués."
4. Génération idempotente, < 30 s, stockage local + chemin en base.

## Lot 2 — Le parcours d'achat

1. **Page Flash** (app, publique, sans compte) : champ adresse (autocomplete BAN) OU saisie références cadastrales → confirmation visuelle (contour de la parcelle sur mini-carte, surface, commune) → email → bouton payer.
2. **Stripe Checkout** (pas Payment Link : il faut lier la session à l'IDU) : produit créé via l'API en mode test pour le dev, **procédure de bascule production documentée** dans le rapport de fin. ⚠️ **AUCUN lien ou bouton de paiement factice ne doit exister à aucun moment, même temporairement, sur une page accessible** — leçon du P0 TANIA, non négociable : tant que la prod Stripe n'est pas branchée, la page affiche "bientôt disponible", pas un faux bouton.
3. **Webhook** `checkout.session.completed` : vérification de signature obligatoire, idempotence (re-livraison sur re-notification, jamais de double génération), création `flash_orders` → génération → **email de livraison** avec lien signé (`download_token`, expiration 30 jours, re-téléchargeable). Envoi via le SMTP existant du projet ; s'il n'y en a pas, l'implémenter proprement (provider en config) et le noter au rapport.
4. Page de confirmation post-paiement avec téléchargement direct (sans attendre l'email) une fois la génération finie — polling léger sur le statut.
5. **Échecs** : génération en erreur → statut `failed`, email d'excuse automatique + alerte admin. Jamais un client payé sans rapport ni nouvelle.
6. Anti-abus : rate limiting sur la page et le géocodage, pas de génération sans paiement confirmé, CAPTCHA léger si nécessaire.

## Lot 3 — Rapport exemple + page marketing (repo labuse.immo)

1. **Rapport exemple** : générer le rapport d'une parcelle démo (choisie par Vic ou une parcelle communale sans enjeu), watermark diagonal "EXEMPLE" sur chaque page → PDF téléchargeable librement. C'est l'argument de conversion n°1 pour un notaire : il juge sur pièce.
2. **Page /flash sur labuse.immo** : promesse ("l'analyse complète d'une parcelle en 5 minutes, [prix]€"), les deux cas d'usage (notaire : due diligence avant acte ; architecte : pré-faisa avant esquisse), aperçu visuel des sections, lien vers le rapport exemple, CTA vers la page d'achat, FAQ courte (sources, limites, délai, "besoin de plusieurs parcelles ? → l'abonnement"). Respecter la DA et les patterns existants du site.
3. Ajouter Flash au maillage : mention dans la nav et sur la home (bloc court), sans cannibaliser le CTA abo principal.

## Lot 4 — Admin & suivi

Vue admin (accès Vic) : liste `flash_orders` (statut, email, parcelle, montant), actions : régénérer + renvoyer l'email, marquer remboursé (le remboursement lui-même se fait dans le dashboard Stripe — pas d'API refund dans ce mandat). Compteur mensuel simple (nb ventes, CA).

---

## Critères d'acceptation

- Parcours complet en mode test Stripe : sélection → paiement carte test → webhook → PDF généré → email reçu → téléchargement OK → re-téléchargement OK → lien expiré correctement après modification manuelle de la date.
- Le PDF d'une parcelle riche (toutes sections) ET d'une parcelle pauvre (sections manquantes) se génèrent proprement — pas de section vide, pas d'erreur.
- Webhook rejoué 3× → une seule génération, une seule livraison.
- `SELECT count(*) FROM flash_orders WHERE statut='paid' AND delivered_at IS NULL AND created_at < now()-interval '10 min';` → 0 en fonctionnement nominal.
- Aucun élément de paiement factice accessible à aucun commit (revue manuelle Vic sur ce point avant merge).
- Playwright : page marketing /flash charge, le rapport exemple se télécharge, le CTA mène à la page d'achat ; page d'achat : l'autocomplete BAN retourne des parcelles, la confirmation affiche le bon contour.
- Rapport exemple relu visuellement par Vic (sa validation est le critère qualité du template).

## Contraintes

- Clés Stripe et SMTP en variables d'environnement, jamais commitées. Signature webhook vérifiée.
- RGPD : email client = donnée personnelle → stockage minimal, pas de réutilisation marketing sans consentement (case décochée par défaut si newsletter proposée, sinon rien). **Actions Vic hors mandat, à lister dans le rapport de fin** : CGV Flash (décliner depuis l'existant), mise à jour politique de confidentialité labuse.immo (nouveau traitement), mention du statut TVA sur les reçus Stripe selon son régime.
- Les règles anti-cannibalisation de la section 2 priment sur toute idée d'amélioration UX qui les contredirait.
- Réseau : Stripe, BAN, tuiles cartographiques libres. Rien d'autre.
- Ordre : 1 → 2 → 4 → 3 (le produit avant la vitrine).

## Rapport de fin attendu

Temps de génération moyen, liste des sections conditionnelles avec leur disponibilité actuelle, procédure de bascule Stripe test→prod pas à pas, provider email retenu, parcelle démo utilisée, et la liste des 3 actions Vic (CGV, confidentialité, produit Stripe prod + prix).
