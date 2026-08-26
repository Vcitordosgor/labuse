# MANDAT — TOUR DE CONTRÔLE (dashboard admin) · V1
Référence visuelle : maquette validée par Vic le 26/08 (si docs/audit-2026-08/DASHBOARD/maquette.html est présent, il fait foi pour la DA ; sinon la spec ci-dessous suffit). DA : identité LABUSE dark + menthe, Space Grotesk/Inter/IBM Plex Mono, MAUVE STRICTEMENT RÉSERVÉ à la section IA. RÈGLES COMMUNES du fichier de suivi. Commits par lot (D1→D8). Aucun chiffre métier recalculé : le dashboard LIT (moteur unique).

## Périmètre et accès
Route /admin dans l'app existante, réservée au compte admin de Vic (réutilise le cloisonnement existant ; tout endpoint /admin/* renvoie 403 à un compte client — testé). Rail latéral : Pilotage · Licences · IA · Sources · Produit · Courrier + LED santé (serveur/run/carte/backup) en pied de rail, visibles partout. Badge rouge sur « Pilotage » quand paiement en échec > 0.

## D1 — CAPTEURS (l'app s'instrumente ; léger, par licence, RGPD-sobre : des compteurs, jamais du contenu)
- usage_events : ouverture d'outil (licence, outil, ts) + heartbeat de session (pour le temps d'usage). Agrégats jour/30j.
- retours : bouton « Signaler » en haut à droite de l'app cliente (type bug/idée/question + message) → table retours (statut nouveau/traité/répondu).
- ia_budget : conso IA par licence et par jour (€ estimés + nb questions). NE PAS merger la branche WIP fix/ia-modele-budget (divergée des fichiers remaniés depuis) : t'en inspirer et réimplémenter proprement sur le main actuel.
- quota Copilote par licence, modifiable (défaut 80/jour) — le /ask le lit.
- actifs/jour : dernier login + connectés 24 h.

## D2 — STRIPE (lecture seule)
Clé restreinte lecture via .env (STRIPE_RESTRICTED_KEY, jamais en dur, jamais la clé complète). Lus : MRR, abonnements actifs, statut par client (active/past_due + date + prochaine retentative). Rapprochement Stripe ⇄ comptes app : tout orphelin (compte sans abo actif, abo sans compte) = alerte ambre sur Licences. Cache court (5 min) pour ne pas marteler l'API.

## D3 — PILOTAGE
Héros : CA du mois (+ delta vs mois précédent + sparkline 6 mois), carte « Paiement en échec » (rouge si >0, lien vers la licence), licences actives. Tuiles : actifs aujourd'hui, conso IA du mois (lien section IA), âge du dernier backup (lit le mtime du dump au chemin du LOT AK ; ambre ≥2 j, rouge ≥7 j), santé serveur (/readyz N/N). Fil : event_log filtré admin (courrier, échecs e-mail avec bouton relancer, heal, gels anti-burst avec bouton Dégeler).

## D4 — LICENCES
Une fiche par client : statut Stripe (chip), date/prix, séquence onboarding Mail 1/2/3 (templates Brevo, statut + date d'envoi stockés, bouton Envoyer par mail), KPI (temps d'usage 7 j, dernière connexion, Copilote jour/quota), actions : Suspendre l'accès (MANUEL, confirmation, flag en base → le client voit « abonnement à régulariser » + lien de paiement ; données intactes ; réversible) / Rétablir / Relancer par mail (lien de paiement Stripe). Parcours « nouveau client » : créer le compte (mécanisme officiel) → envoyer le lien de souscription → dérouler les mails.

## D5 — IA (mauve)
Tuiles : conso du mois, coût moyen/question, quota/jour/licence (éditable), projection fin de mois. Panneaux : conso journalière 30 j (barres), conso par licence 30 j. Bouton « Recharger le crédit ↗ » → console Anthropic (externe). Note honnête : solde non exposé par l'API, conso trackée localement.

## D6 — SOURCES
Table des 59 : millésime amont, ingéré le, cadence attendue (nouveau champ de config par source), badge « À mettre à jour » = cadence dépassée (calcul auto), bouton « Relancer l'ingestion » quand une commande d'ingestion existe pour la source (sinon absent). Synthèse en tête (N à mettre à jour · N OK) + recherche. Panneau CRON : dernières exécutions nocturnes depuis event_log. Agent de veille : NON (V2) — panneau grisé descriptif autorisé.

## D7 — PRODUIT
Usage par outil 30 j (barres, depuis usage_events ; « Par client » = V2). Retours clients : table filtrée (Tous/Bugs/Idées/Questions), statuts éditables.

## D8 — COURRIER
Tuiles (à traiter / en cours / postées ce mois). Table des demandes : client, parcelles, date, statut Demandé→Imprimé→Posté (transitions par bouton, journalisées, visibles côté client), lien « Voir le PDF ». Purge admin possible des lignes de test.

## Critères de fin
Gardées G1-G6 vertes ; 403 admin prouvé depuis un compte client ; zéro régression front (tsc/build) ; backend tests verts ; les capteurs n'ajoutent aucun poids perceptible côté client (event fire-and-forget). Compte-rendu « Demandé → traité » par lot + la commande de merge en dernier élément isolé. Pas de merge par toi.

## V2 (plus tard, pas dans ce mandat)
Agent de veille des sources · usage « par client » · exports du dashboard · notifications e-mail à Vic (résumé hebdo).
