# MANDAT — TOUR DE CONTRÔLE (dashboard admin) · V1
Régime AUTONOME du début à la fin : aucun checkpoint, aucune question. CC tranche seul tous les arbitrages ; en cas d'hésitation, l'option la plus conservatrice, notée en une ligne au rapport. Commits par lot (D1→D9). RÈGLES COMMUNES. App en route, rien tuer. Aucun chiffre métier recalculé : le dashboard LIT (moteur unique, doctrine LOT AP).
DA : identité LABUSE dark + menthe, Space Grotesk/Inter/IBM Plex Mono, MAUVE STRICTEMENT RÉSERVÉ à la section IA.

## Périmètre et accès
Route /admin dans l'app existante, réservée au compte admin de Vic (réutilise le cloisonnement existant ; tout endpoint /admin/* renvoie 403 à un compte client — testé). Rail latéral : Pilotage · Licences · IA · Sources · Produit · Courrier + LED santé (serveur/run/carte/backup) en pied de rail, visibles partout. Badge rouge sur « Pilotage » quand paiement en échec > 0.

## D1 — CAPTEURS (l'app s'instrumente ; léger, par licence, RGPD-sobre : des compteurs, jamais du contenu)
- usage_events : ouverture d'outil (licence, outil, ts) + heartbeat de session (pour le temps d'usage). Agrégats jour/30j. Fire-and-forget, aucun poids perceptible côté client.
- retours : bouton « Signaler » en haut à droite de l'app cliente (type bug/idée/question + message) → table retours (statut nouveau/traité/répondu).
- ia_budget : conso IA par licence et par jour (€ estimés + nb questions). NE PAS merger la branche WIP fix/ia-modele-budget (divergée des fichiers remaniés depuis) : t'en inspirer et réimplémenter proprement sur le main actuel.
- quota Copilote par licence, modifiable (défaut 80/jour) — le /ask le lit.
- actifs/jour : dernier login + connectés 24 h.

## D2 — STRIPE (lecture seule)
Clé restreinte lecture via .env (STRIPE_RESTRICTED_KEY, jamais en dur, jamais la clé complète). Si la variable est absente : tout construire derrière une interface avec un mode « non configuré » propre (aucun crash, message explicite dans l'UI) et le noter au rapport. Lus : MRR, abonnements actifs, statut par client (active/past_due + date + prochaine retentative). Rapprochement Stripe ⇄ comptes app : tout orphelin (compte sans abo actif, abo sans compte) = alerte ambre sur Licences. Cache court (5 min).

## D3 — PILOTAGE
Héros : CA du mois (+ delta vs mois précédent + sparkline 6 mois), carte « Paiement en échec » (rouge si >0, lien vers la licence), licences actives. Tuiles : actifs aujourd'hui, conso IA du mois (lien section IA), âge du dernier backup (lit le mtime du dump — chemin de backup GB-054 ; ambre ≥2 j, rouge ≥7 j), santé serveur (/readyz N/N). Fil : event_log filtré admin (courrier, échecs e-mail avec bouton relancer, heal, gels anti-burst avec bouton Dégeler). Horodatages à l'heure Réunion (dette fuseau connue : ne pas afficher d'heure serveur brute).

## D4 — LICENCES
Une fiche par client : statut Stripe (chip), date/prix, séquence onboarding Mail 1/2/3 (templates Brevo, statut + date d'envoi stockés, bouton Envoyer), KPI en cartes alignées (temps d'usage 7 j, dernière connexion, Copilote jour/quota), actions : Suspendre l'accès (MANUEL, confirmation, flag en base → le client voit « abonnement à régulariser » + lien de paiement ; données intactes ; réversible) / Rétablir / Relancer par mail. Parcours « nouveau client » : créer le compte (mécanisme officiel) → envoyer le lien de souscription → dérouler les mails.

## D5 — IA (mauve)
Tuiles : conso du mois, coût moyen/question, quota/jour/licence (éditable), projection fin de mois. Panneaux : conso journalière 30 j (barres), conso par licence 30 j. Bouton « Recharger le crédit ↗ » → console Anthropic (externe). Note honnête : solde non exposé par l'API, conso trackée localement.

## D6 — SOURCES
Table des 59 : millésime amont, ingéré le, cadence attendue (nouveau champ de config par source), badge « À mettre à jour » = cadence dépassée (calcul auto), bouton « Relancer l'ingestion » quand une commande d'ingestion existe pour la source (sinon absent). Synthèse en tête (N à mettre à jour · N OK) + recherche. Panneau CRON : dernières exécutions nocturnes depuis event_log.
AGENT DE VEILLE DES SOURCES : ne pas l'implémenter. À la place, ÉCRIRE sa spécification dans docs/audit-2026-08/DASHBOARD/AGENT-VEILLE-SPEC.md (ce qu'il surveille portail par portail, comment il détecte un nouveau millésime, ce qu'il notifie, ce qu'il ne fait jamais, coût estimé) et afficher un panneau grisé descriptif.

## D7 — PRODUIT
Usage par outil 30 j (barres, depuis usage_events ; « Par client » = V2). Retours clients : table filtrée (Tous/Bugs/Idées/Questions), statuts éditables.

## D8 — COURRIER
Tuiles (à traiter / en cours / postées ce mois). Table des demandes : client, parcelles, date, statut Demandé→Imprimé→Posté (transitions par bouton, journalisées, visibles côté client), lien « Voir le PDF ».

## D9 — COMPTES D'ESSAI 48 H
Type de compte « essai » avec date d'expiration : accès complet, puis bascule automatique à l'échéance sur l'écran « abonnement » (réutiliser le mécanisme de suspension de D4 — seul le déclencheur change : une date au lieu du bouton ; données conservées). Bouton « Créer un compte d'essai » dans le parcours nouveau client, chip « Essai · expire dans N h » sur la fiche Licences, bouton « Convertir en abonnement ». Durée par défaut 48 h, paramétrable.

## MAILS (Brevo)
7 templates référencés par identifiant en .env : essai 48 h, lien de souscription, onboarding 1/2/3, relance carte refusée, suspension, rétablissement. Si les identifiants sont absents : mode « non configuré » propre (bouton visible, message explicite, aucun envoi silencieux) et noté au rapport. Rappels sur la fiche client : « Mail 2 à envoyer (J+3 atteint) » / « Mail 3 (J+10) » en ambre — l'app rappelle, Vic déclenche. Aucun envoi automatique en V1, sauf rien.

## Critères de fin
Gardées G1-G6 vertes ; 403 admin prouvé depuis un compte client ; expiration d'essai prouvée (compte de test créé, date forcée, bascule constatée, puis détruit) ; zéro régression front (tsc/build) ; suite backend au même niveau qu'avant (les 5 échecs pré-existants restent 5) ; capteurs sans poids perceptible. Compte-rendu « Demandé → traité » par lot + la commande de merge en dernier élément isolé. Pas de merge par CC.

## V2 (hors mandat)
Agent de veille implémenté · usage « par client » · exports du dashboard · résumé hebdo par e-mail · envois automatiques J+3/J+10.
