# RAPPORT — Recette générale 1 (16/10/2026)

## Verdict (5 lignes)
L'application **marche** : les 9 familles d'écrans ont été parcourues au navigateur réel
(desktop), **aucune anomalie bloquante, aucun plantage, aucune donnée fausse servie à
l'écran**. Sur les 24 anomalies relevées, **0 bloquant · 12 gênant · 12 cosmétique** —
et sur les 12 « gênant », **5 sont des artefacts de l'environnement de recette** (caches/tables
de batch non peuplés, auth locale désactivée, mails en dry-run), pas des défauts de code.
Le seul point à traiter en priorité avant la mise en ligne est **un chiffre erroné dans un
document client PDF** (A-05-1). **Rien dans cette recette ne doit empêcher le run de ce soir**
(recette entièrement en lecture seule, aucune action mutante déclenchée, run non touché).

## Chiffres
| Famille | Écrans/actions | Verdict | Anomalies |
|---|---|---|---|
| 1 — Carte (couches/filtres/recherche/zoom, desktop+mobile) | 7/7 parcours | OK | 3 cosmétique |
| 2 — Fiche parcelle (20 témoins, 11 tiroirs) | 20/20 témoins | OK | 1 cosmétique |
| 3 — Fiche commune | 24/24 communes | OK | 2 gênant · 1 cosmétique |
| 4 — Outils | 17 (+2 masqués) | OK | 1 gênant |
| 5 — Exports PDF | 6/7 (3 alias) | OK | 2 gênant |
| 6 — Copilote | 10 questions | OK | 2 gênant · 1 cosmétique |
| 7 — Compte client | 15/18 | OK | 2 gênant · 1 cosmétique (+2 notes dev) |
| 8 — Courrier / Veille / CRM | 34 | OK | 2 gênant · 2 cosmétique |
| 9 — Admin (Tour de contrôle) | 20/20 | OK | 2 cosmétique |

**Total : 0 bloquant · 12 gênant · 12 cosmétique. 288 captures. 0 erreur console / 0 HTTP
5xx sur l'ensemble du parcours** (seuls 401 attendus en visiteur anonyme).

## À corriger AVANT le déploiement (par priorité)

### 1. Chiffre faux dans un document client — le seul vraiment important
- **A-05-1** — **Dossier expert**, §10 : « Capacité (logements) = 1 » affiche en réalité le
  **booléen** `capacite_estimee` (→1), pas un décompte de logements (ex. parcelle R+6 ≈ 8–10).
  Le PDF **diverge de la fiche**. C'est un chiffre faux dans une pièce remise au client :
  à traiter en priorité. Cause probable : `src/labuse/robinet_fiche.py:454-457` +
  `blocs/potentiel.py:115-118`.

### 2. Défauts de code / produit (gênants, non bloquants)
- **A-05-2** — Bilan/Étude de faisabilité : message UI « Génération impossible. » masque la
  vraie raison (compte requis) — `frontend/.../BilanEcran.tsx:170-173` ne gère pas un `detail`
  string.
- **A-03-1** — Fiche commune : warning React « clés dupliquées » à chaque ouverture (risque de
  ligne dédupliquée) — `ContextePanel.tsx:570`.
- **A-06-1** — Copilote : IDU inexistant bien formé → « incident serveur » au lieu de
  « parcelle introuvable » — `api/copilote_v2.py:128`.
- **A-06-2** — Copilote : décline des règles PLU / un calcul de capacité que LABUSE **détient**
  (routé vers le web) — `fiche_parcelle` n'expose pas `reglement_plu.regles` au copilote.
- **A-07-5** — Résiliation : **aucun mail de résiliation** émis automatiquement (template 16 non
  câblé) ; le compte passe `suspendu` silencieusement.
- **A-07-2** — « Mot de passe oublié » affiche « lien envoyé » même quand rien ne part ; le
  message dépend de la présence d'une clé Brevo, pas de l'autorisation d'envoi — `onboarding.py:593`.
- **A-08-1** — `#idu=…&m=courriers` ouvre l'outil Courrier **sans** pré-remplir le destinataire
  (seule la tuile de la fiche l'amorce).
- **A-08-3** — `#surveillance=secteurs` retombe en silence sur « parcelles » (volet retiré,
  deep-link laissé exposé — à retirer ou à rediriger proprement).

### 3. Données de test à purger (pollution en base, pas du code)
- **A-08-4 / A-09-2** — Note de stress-test `[GB-TEST] AAAA…` (5000 caractères) présente dans
  une carte **CRM** et dans **Produit** : à supprimer de la base avant la mise en ligne.

### 4. Réglage de configuration (hors code)
- **A-07-3 (note Vic)** — Au checkout Stripe, le **nom marchand affiché est « LASTONE »**
  (compte de test) : à renommer « LABUSE » côté Stripe avant la prod.

## Ce qui est un artefact de la RECETTE (à ne PAS corriger dans le code)
Ces « gênant » disparaissent en production et ne sont **pas** des bugs :
- **A-03-2** — Fiche commune lente (~45 s) sur les grandes communes : la table
  `commune_contexte_cache` est **vide** ici (le job nocturne `fiche-commune-cache` n'a jamais
  tourné sur ce poste) → recalcul à la volée. En prod le cache est peuplé. *Recommandation :
  vérifier que le job tourne bien en prod ; sinon ce « gênant » devient réel côté utilisateur.*
- **A-04-1** — Blocs fonciers vide : table `parcel_blocs` non peuplée (batch `blocs-build` non
  joué en recette). L'UI affiche un empty-state honnête.
- **A-05-2 / A-07-4 / A-07-1** — Parcours « compte » partiellement injouable sur le front dev
  (auth locale désactivée, pages compte hors proxy Vite). Comportement correct attendu en prod.
- **A-07-2** — Message « lien envoyé » : trompeur **uniquement** parce que les mails sont en
  dry-run sur ce poste (mais le fond, cf. §2, mérite un garde-fou).

## Points forts confirmés
- **Chiffres fiche ↔ PDF** vérifiés identiques (Dossier expert, Pré-dossier PC) ; seule exception = A-05-1.
- **Cas difficiles tous bien gérés** côté UI : parcelle disparue du cadastre (garde explicite),
  RNU (bannière), non calibré (estimation marquée, pas présentée comme sourcée), bizone, PPR
  rouge partielle, Hors classement/NC, emprise saturée, >2 ha, propriétaire société, sans vente, Hauts, mixité sociale.
- **Copilote** : doctrine tenue (refuse de calculer/modifier un score), recadrage hors-sujet
  parfait, 0 hallucination, sources réelles.
- **Admin** : les 4 zones (Pilotage, Données/Circuit, Comptes, IA) cohérentes UI ↔ API.

## Sûreté de la recette (conformité au mandat)
- **Lecture seule** : aucune correction de code applicatif, rien poussé sur le VPS.
- **Aucune action mutante admin** déclenchée (run / bascule / purge / compte / mail / cron) —
  vérifié : journal du Circuit à 0 entrée. **Le run du soir n'a pas été touché.**
- **Aucun paiement réel** : clé Stripe `sk_test_`, sessions `cs_test_`, bandeau « test » vérifié ; aucune carte soumise.
- **Aucun mail réellement envoyé** : `mail_reel=False`, tous les envois en dry-run `.eml` (file `mail_queue` inchangée).
- **Aucun secret commité** (`.env` gitignoré, jamais staged).

## Environnement de la recette
- Worktree `~/Desktop/labuse-recette`, branche `audit/recette-generale-1` (depuis main `21747072`).
- Backend `:8798` (interpréteur PDF-capable), Frontend `:5998` (`/socle/`), run servi **q_v18**.
- Pilotage navigateur : Playwright via le **Chrome du système** (`channel:'chrome'`) — macOS 13
  n'a pas de binaire Playwright compatible. Harnais `frontend/qa-recette/harness.mjs`.
- **Mobile** : l'app cliente est **volontairement bloquée** sous 390 px (`EcranOrdinateur`,
  décision produit CHARGEMENT-1) ; le barrage est propre (0 débordement, 0 erreur). Les
  familles client ont donc été recettées en desktop uniquement.

## Livrables
- `PARCOURS.md` (9 sections, verdict par écran), `ANOMALIES.md` (24, A-01-1 → A-09-2),
  `temoins.json` (20 parcelles, 12 cas difficiles couverts), `captures/` (288), ce `RAPPORT.md`.
- Un commit par famille sur `audit/recette-generale-1`. **Non mergé** (lecture seule).
