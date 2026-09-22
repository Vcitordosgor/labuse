# VEILLE-2 — Trois endroits, deux chemins, un mail par jour

**Branche** `feat/veille-2` (depuis main `c83c14a3`) · **worktree** `~/Desktop/labuse-veille2` ·
**ports** :8145/:5345 · **modèle** Opus · **date** 22/09/2026 · **un commit par lot, branche poussée** ·
**aucun envoi réel** (dry-run) · **base partagée : un seul backend**.

**Étape 0 — hash gravé** : `captures/veille-2/00-hash.txt` (HEAD `c83c14a3`, run servi `q_v11_m137`).
Aucun run rescoré/basculé/ingéré.

Le modèle (décision Vic 22/09) : la veille apparaît à **trois endroits** (cloche de fiche · cloche du
haut · page Veille) ; la page Veille a **deux chemins** — PARCELLE et RADAR, rien d'autre ; la cloche du
haut porte tout ce qui change pour le compte (parcelles suivies · Radar · marché · nouveautés de l'app),
jamais un millésime ni une date de donnée ; **un seul mail par jour**.

Commits : `e070e2cb` (Lot 1) · `f9387e4c` (Lot 2) · `be187643` (Lot 3) · `718a8562` (Lot 4) ·
`0688383e` (Lot 5) · `eb770a7e` (arête G6).

---

## Lot 1 — Chemin PARCELLE

Un seul suivi (table `watched_parcels`), deux entrées : la **cloche de la fiche** (`WatchButton`,
allumée = suivie, re-clic = retirée) et la **barre IDU** de la page Veille (`ParcelInput` → `toggleWatch`).
Même table, même job `evaluer-suivis`.

- **Refus AVEC MOTIF** (`events.watch_toggle`, validé AVANT toute résolution compte/base) : IDU malformé
  → 422 « IDU invalide » ; IDU hors des 24 communes → 422 « hors des 24 communes » ; IDU du périmètre mais
  absent du cadastre → 404 « Parcelle inconnue ». Le front (`SurveillancePanel`) remonte le motif serveur.
- **Cinq déclencheurs, écrits noir sur blanc** : vente (DVF) · permis (Sitadel) · procédure (BODACC) ·
  **changement de propriétaire PM** (empreinte SIREN `pm_snap`, nouveau) · bascule du score (detect-events,
  kind `parcelle_suivie` sur parcelle suivie). Le **zonage** n'est plus un déclencheur.
- La liste des parcelles suivies : IDU · commune · dernier événement · retirer.

Preuve : `tests/test_veille2_lot1.py` (refus IDU ×2 ; changement PM bout-en-bout ; zonage non
déclencheur) — 5 verts.

## Lot 2 — Chemin RADAR, prouvé sur de vraies pages leboncoin

Critères du modèle : **commune(s), type de bien, surface min/max, prix max** (`veille.matche` étendu :
`communes` liste, `surface_min`/`surface_max` sur la surface pertinente terrain/habitable ; rétro-compatible).
Le formulaire Radar (`VeilleExterne`) expose la sélection multi-commune + surface min/max + prix max.

Chaîne prouvée sur **5 dépôts HTML RÉELS** (`qa/radar-html/ECH-1.html` = 35 annonces variante A,
`ECH-2-varianteB.html` = variante B DOM, 3 pages d'annonce `qa/radar-terrains/T-*.html`) :

- **Extraction** prix/surface/commune/type/date/lien = valeurs brutes du `__NEXT_DATA__` de la page
  (`captures/veille-2/lot2-en-face.md`, `lot2-extraction.md`) — aucun fait inventé.
- **Rattachement** par convergence ≥2 critères indépendants (surface cadastrale + emprise bâtie) OU
  « non rattachée » ; jamais une parcelle inventée.
- **Annonce déjà vue** = pas de nouvel événement (dédup par `list_id`). **Annonce expirée** = retirée
  (`cycle.marquer_expirees` : `expiration_date` passée → statut `retiree`, sort des biens du jour et des veilles).
- **Matching** : 3 veilles aux critères différents → matrice annonce × veille attendu == obtenu
  (`captures/veille-2/lot2-annonce-veille.md`).

Note honnête : les pages leboncoin sauvegardées sont des SPA — hors ligne, le DOM ne s'hydrate pas
(capture visuelle = logo seul) ; la vérité de la page est son `__NEXT_DATA__` (données serveur), comparée
à l'extraction dans `lot2-en-face.md`. Preuve : `tests/test_veille2_lot2.py` — 5 verts.

## Lot 3 — La cloche du haut : liste fermée

Quatre catégories, chacune son texte et son clic ; **tout autre kind n'apparaît pas** côté client (le
bucket pilote garde sa vue de diagnostic) :

| Catégorie | kind event_log | clic |
|---|---|---|
| parcelle suivie | `parcelle_suivie` (compte) | la fiche |
| Radar | `radar` (compte, un match) | l'annonce |
| marché | `bascule`/`bodacc`/`match` (broadcast NULL) | la fiche |
| nouveauté de l'app | `nouveaute` (broadcast NULL) | la page Sources (jamais un millésime) |

`_CLOCHE_KINDS` + `_BROADCAST_KINDS` + `_cloche_closed_sql` (client seulement) bornent `list_events`,
`events_count` et le moteur `notifications_non_lues`. `annoncer_nouveaute()` diffuse une nouveauté
(broadcast → `/sources`, dédup permanente, sans date). `digests.evaluer_radar_cloche()` pose les
événements `radar` (idu NULL, lien = annonce). **Non-lus en tête ; compte neuf à 0** (broadcast antérieur
à la création = lu d'office).

Preuve : `tests/test_veille2_lot3.py` (un événement de chaque type, intrus filtrés ; compte neuf à 0) — 2
verts. `tests/test_audit_secu.py` adapté au modèle (kind perso affiché = `parcelle_suivie`, IDU d'une
commune réelle) — **intention de cloison inchangée, 39 verts**.

## Lot 4 — Retirer secteur et recherche sauvegardée

Vérifié : **aucune UI ne crée plus de veille secteur** (`createWatchZone` jamais câblé côté front).

- `detect_events` : appel `_veilles_match` (recherches sauvegardées) **retiré**, fonction supprimée ; ne
  restent que les **bascules du marché** + la bascule du score sur parcelle suivie. `saved_searches`
  archivée (plus aucun lecteur).
- Job **`evaluer-secteurs` retiré** (`jobs.py`, `jobs_impl.evaluer_secteurs`, commande CLI) ; **V8a** passe
  de 7 à 6 fonctions, **vert**. Crontab 20 → 19 jobs.
- Front : volet **« Critères » supprimé** (`VoletCriteres`) ; **plus aucun bouton « Créer une veille »**
  depuis les filtres carte (`data-creer-veille` + mutation `saveSearch` retirés) ni les projets. La page
  Veille n'a plus que **PARCELLE et RADAR**.

Tests adaptés au modèle : `test_veille_fix1` (3 jobs, secteurs absent), `test_cron1_lot3` (19 jobs),
`test_events_bascule` (recherche sauvegardée archivée = plus de `veille`, la bascule marché reste).

## Lot 5 — Un mail par jour

Le digest du matin porte **tout** : parcelles suivies + Radar + nouveautés (`_DIGEST_KINDS` +
`nouveaute` broadcast postérieure à la création). **Plus d'alerte Radar séparée** : le job `radar-digests`
(alerte 18:00) devient **`radar-cloche`** (07:05) — il pose les événements Radar à la cloche
(`evaluer_radar_cloche`), et le digest (07:15) les e-maile avec le reste. La ligne « secteurs » du mail est
retirée. **Un compte sans événement la veille = pas de mail** ; **un compte = un mail max par jour** (dédup
`mail_queue` par compte+jour). V8a mis à jour (6 fonctions, vert).

Preuve dry-run 3 comptes (`captures/veille-2/lot5-dry-run-3comptes.txt`) : A (suivi + Radar) = 1 mail,
B (suivi) = 1 mail, C (rien) = 0 ; rejeu le même jour = dédup (toujours 1). `tests/test_veille2_lot5.py` — 2 verts.

---

## Portes

- **tsc -b** : **vert**.
- **pytest tests/ complet** (hors `tests/verrous/`, qui exigent la base réelle) : **3008 passés, 67 skipped,
  11 échecs — TOUS pré-existants** (vérifiés identiques sur le commit de base `c83c14a3`) :
  `test_circuit_provenance` (9, documents sur IDU réels) + `test_circuit_p3_lot3::…base_reelle` (1) +
  `test_reparations1_lot2::…graphe` — ce dernier **cassé par mon Lot 2 puis RÉPARÉ** (arête
  `pige_annonces ← pige/cycle.py` déclarée dans `registre/lectures.py`, commit `eb770a7e`). **0 échec
  nouveau restant.**
- **labuse circuit verrous -w G8** : **V8a vert** (« 6 fonctions de veille/envoi, chacune portée par un
  job »), **G6 vert** (0 dette fine, arête déclarée). Les 8 CASSÉ (V1c, V2a, V4a-c, V7a, G3, G4) + G8
  (avertissement non bloquant) sont **pré-existants et IDENTIQUES sur le commit de base** (verrous de
  données réelles : tuiles/sources/parcelles absentes de `labuse_test`) — **0 verrou nouvellement cassé**.

## Preuves (captures/veille-2/)

`00-hash.txt` · `page-veille-avant-apres.md` (deux blocs) · `lot2-extraction.md` · `lot2-en-face.md` ·
`lot2-annonce-veille.md` (tableau annonce × veille) · `lot5-dry-run-3comptes.txt`.
Générateur reproductible : `qa/veille2/preuve_radar.py`. Suite VEILLE-2 : `tests/test_veille2_lot{1,2,3,5}.py`
= **14 verts**.

Note environnement : `labuse_test` est sans cadastre réel et le rendu carte (WebGL) n'est pas capturable ;
démarrer l'app contre la base partagée `labuse` est proscrit (famine de verrou). Les preuves
comportementales (suivi IDU → événement → cloche ; cloche avec un événement de chaque type ; digest un/jour)
sont donc portées par la **suite de tests**, qui exerce les VRAIS endpoints et les VRAIES pages leboncoin.
