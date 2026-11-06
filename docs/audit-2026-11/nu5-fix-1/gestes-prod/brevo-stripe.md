# Gestes Brevo & Stripe pour Vic (hors code)

Ces points ne se corrigent PAS dans le dépôt — ils vivent dans les consoles Brevo et Stripe. Liste
prête à appliquer.

## Brevo

- **C-F1 — expéditeur unique `contact@labuse.immo`.** Les 16 templates du cycle de vie partent
  aujourd'hui de `victor@labuse.immo` (adresse personnelle) ; les mails techniques partent de
  `contact@labuse.immo`. Décision Vic : **un seul expéditeur, `contact@labuse.immo`**. Dans Brevo :
  régler l'expéditeur par défaut **et** l'expéditeur de chacun des 16 templates sur
  `contact@labuse.immo` (alias vérifié), puis vérifier l'alignement **SPF / DKIM / DMARC** du domaine
  pour cette adresse. (La doctrine interne « un seul expéditeur » devient alors vraie.)

- **C-F3 — lien de désinscription visible dans `radar_alerte` (et `radar_digest` s'il revit).** Le
  code passe bien `{{ params.LIEN_DESABO }}` et pose l'en-tête `List-Unsubscribe`, mais le **corps du
  template Brevo `radar_alerte` (id 13) ne référence pas** `{{ params.LIEN_DESABO }}` → aucun lien
  visible. Ajouter au pied du template HTML : `<a href="{{ params.LIEN_DESABO }}">Se désabonner de
  cette veille</a>`. (Mail récurrent de prospection → opt-out visible exigé CNIL/LCEN.)

- **C-F9 — retirer le template mort `radar_digest` (id 12).** Il est **actif chez Brevo mais mort
  dans le code** (retiré par VEILLE-FIX-1, remplacé par `radar_alerte` par veille). Le désactiver /
  archiver chez Brevo pour qu'il ne puisse plus partir par erreur.

## Stripe

- **C-F10 — nom du marchand « LASTONE » → « LABUSE ».** Sur le Checkout et l'autorisation de
  prélèvement (« vous autorisez **LASTONE** à vous débiter »), donc sur le **relevé bancaire** du
  client, le marchand s'appelle encore « LASTONE » (ancien nom de projet). Les lignes produit disent
  bien « LABUSE Intégral ». Dans Stripe → **Paramètres → Informations publiques / Nom public du
  compte** : passer à « LABUSE » (et vérifier le *statement descriptor* = « LABUSE »).

- **C-F8 (rappel) — reçu Stripe.** Confirmer que l'**envoi automatique du reçu/facture Stripe** est
  activé sur l'abonnement (Checkout `invoice_creation` / receipts) : LABUSE n'émet pas de facture (par
  conception, CGV art. 4) ; sans le reçu Stripe, le client n'a aucune trace comptable.
