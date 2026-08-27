# MANDAT — PARCOURS D'ENTRÉE (onboarding, paiement, accès)
Régime AUTONOME du début à la fin. Commit par lot (E1→E9). RÈGLES COMMUNES. Findings PE-001→. Rapport : docs/audit-2026-08/ONBOARDING/RAPPORT.md. C'est la première chose que voit un client : rien d'approximatif, rien d'incohérent, rien de mort.

## LES DEUX OFFRES — SOURCE DE VÉRITÉ (décision Vic, 27/08/2026)
- **INTÉGRAL — 349 €/mois, engagement 12 mois.** Abonnement Stripe récurrent. 1 licence = 1 accès (un email actif ne peut pas être ré-invité). Accès complet à l'app.
- **FLASH — 79 €, paiement unique.** Pas d'abonnement, pas de compte : un rapport PDF sur UNE parcelle, via la page publique /flash (saisie IDU → validation → paiement → lien signé 30 jours).
Aucune autre offre n'existe : ni « Illimité », ni 499 €, ni Indé/Pro, ni sièges multiples, ni founding.

## E1 — CHASSE AUX CHIFFRES FAUX (à faire EN PREMIER)
Balaye TOUT le dépôt (front, back, CGV, mentions légales, templates Brevo référencés, PDF, docs, maquettes, tests, seeds, config Stripe) et liste chaque occurrence de : un prix (499, 249, 199, 149, 97, tout montant), un nom d'offre (« Illimité », « Intégral », « Flash », « Indé », « Pro », « Premium »…), une durée d'engagement, une périodicité. Tableau au rapport : fichier · ligne · valeur trouvée · correcte O/N.
Puis CORRIGE : les valeurs justes sont celles de la section ci-dessus. Le libellé exact est « Intégral » (pas « Illimité »), 349 €/mois, engagement 12 mois ; « Flash » 79 € paiement unique.
Et surtout : établis UNE SOURCE DE VÉRITÉ unique pour l'offre (nom, prix, périodicité, engagement) — une config serveur lue par le front, jamais un chiffre en dur dans le JSX ni dupliqué. Après ce lot, changer le prix doit se faire à UN seul endroit. Test anti-régression qui échoue si un montant est écrit en dur dans le front.
NOTE : l'écran d'invitation affichait « licence Illimité · 499 €/mois · engagement 12 mois » le 27/08 en production — c'est le symptôme, cherche la racine (placeholder de maquette ? vieille config ? valeur Stripe désynchronisée ?) et dis-la au rapport.

## E2 — ACTIVATION ADMIN (bug bloquant constaté)
Un compte créé par `labuse creer-admin` NE DOIT JAMAIS passer par un écran de paiement. Aujourd'hui le lien d'invitation admin mène à « Créer votre accès · licence … · Continuer vers le paiement » : c'est le tunnel client réutilisé à tort.
Construis un écran d'activation distinct : e-mail (affiché, non modifiable) → mot de passe → enrôlement 2FA (QR + codes de secours, mécanisme V5 déjà en place) → entrée dans l'app. Aucune mention d'offre, de prix, de CGV commerciales, de Stripe.
Vérifie aussi le cas « compte déjà promu avec mot de passe posé » (le cas de Vic ce soir) : le message CLI doit dire quoi faire, et le login normal doit déclencher l'enrôlement 2FA au premier passage admin.

## E3 — LE BUG DE LA CASE CGV
Constaté en production : case « J'ai lu et j'accepte les conditions générales » COCHÉE, et le bouton reste inactif avec le message « Vous devez d'abord accepter les conditions générales pour continuer ». Reproduis, trouve la cause, corrige, et gèle avec un test. Vérifie le même patron partout où une case conditionne un bouton.

## E4 — INVENTAIRE ET RECETTE DE TOUS LES ÉCRANS D'ENTRÉE
Recense TOUS les écrans du parcours (pars des routes réelles, n'invente pas la liste) et fais la recette de chacun — état normal, états d'erreur, mobile. Au minimum :
1. **Connexion** (compte déjà payé) — mauvais mot de passe, compte inconnu, compte suspendu, rate-limit atteint.
2. **Invitation client** — lien valide, lien expiré, lien déjà consommé, email déjà actif.
3. **Souscription INTÉGRAL** — mot de passe, CGV, Checkout Stripe, retour, premier login.
4. **Souscription FLASH** (/flash, public, sans compte) — IDU valide, IDU introuvable, IDU hors des 24 communes, paiement, attente de génération, lien signé, échec de génération (message honnête + reprise), lien expiré (>30 j).
5. **Mot de passe oublié** — demande, ce que reçoit l'utilisateur, écran de réinitialisation, lien expiré, lien déjà utilisé. ATTENTION : la décision de juillet était « pas d'e-mail automatique, la page renvoie vers Vic » ; depuis, Brevo est branché (8 templates). Tranche pour le mail automatique, et dis-le au rapport.
6. **Essai 48 h** (mécanisme D9) — entrée, écran pendant l'essai (temps restant visible), expiration, conversion en abonnement.
7. **Abonnement à régulariser** (suspension) — écran du client suspendu, lien de paiement, retour après régularisation.
8. **Déconnexion** et **session expirée** — où atterrit-on, le message est-il clair.
9. **Activation admin** (E2).
Pour chacun : capture, comportement attendu vs constaté, finding si écart. Tout écran mort, en double ou inatteignable = signalé.

## E5 — COHÉRENCE STRIPE ⇄ APP
Les produits/prix Stripe (mode LIVE et mode TEST) doivent correspondre exactement aux deux offres : Intégral 349 €/mois récurrent avec engagement 12 mois configuré comme il se doit côté Stripe, Flash 79 € paiement unique. Vérifie les IDs en .env, l'absence de produits fantômes (anciens prix, anciennes offres), et que l'app n'affiche jamais un prix différent de celui que Stripe facturera. Si un écart existe entre l'app et Stripe : le dire, ne pas modifier Stripe en LIVE sans le signaler à Vic.

## E6 — L'ENGAGEMENT 12 MOIS EST-IL TENU PARTOUT ?
L'engagement de 12 mois sur Intégral doit apparaître de façon cohérente : écran de souscription, CGV, mail de souscription (template Brevo), facture/reçu, écran de compte. Vérifie aussi la mécanique existante d'avis d'échéance (loi Chatel, commande avis-echeance) : elle doit être cohérente avec un engagement annuel, et son cron est-il actif (cf. EXPLOITATION-CRON.md) ?

## E7 — MOBILE
Tout le parcours d'entrée doit être impeccable sur téléphone (un prospect clique depuis son mail sur mobile) : lisibilité, champs, clavier, boutons atteignables, Checkout Stripe, retour de paiement, téléchargement du PDF Flash sur iOS. Recette mobile réelle (émulation mobile + tailles 375/390/414). Findings visuels documentés par capture.

## E8 — TEXTES ET DA
Relis chaque texte d'écran : français correct, vouvoiement, ton LABUSE (sobre, précis, jamais survendeur), aucun jargon technique visible, aucune clé de traduction brute, aucun lorem. Les liens CGV / mentions légales / confidentialité mènent à des pages réelles et à jour (dont les deux offres). DA : identité LABUSE respectée, mauve réservé à l'IA.

## E9 — RECETTE DE BOUT EN BOUT EN MODE TEST
Déroule les deux parcours complets en Stripe TEST, en réel : (a) invitation → mot de passe → CGV → paiement 4242 → login → app ; (b) /flash → IDU → paiement 4242 → PDF téléchargé. Plus les cas d'échec : carte refusée 4000 0000 0000 0341, 3DS 4000 0027 6000 3184. Comptes de test [PE-TEST] purgés en fin, vérifié SQL. Le mode LIVE n'est JAMAIS utilisé pour un test.

## FIN
Critères : aucun chiffre d'offre en dur nulle part (test qui le garantit) · les 9 écrans recensés et recettés, desktop et mobile · activation admin sans paiement · case CGV réparée et gelée · parcours Intégral et Flash prouvés bout en bout en test · gardées G1-G6 vertes · tsc/build verts · suite backend au niveau de la base (prouvé par worktree) · comptes [PE-TEST] purgés. Rapport : tableau E1 des occurrences, inventaire des écrans avec captures avant/après, findings PE-xxx. Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff fix/parcours-entree). Tu ne merges pas.
