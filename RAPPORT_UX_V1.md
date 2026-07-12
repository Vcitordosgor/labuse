# RAPPORT UX V1 — mandat du 12/07/2026

**Branche : `feat/ux-v1`** (depuis main à jour, 15 commits — un par item). **Aucun merge effectué** (merge : Vic, `--no-ff`).
Preuves : `audit_shots/ux_v1/` (`avant_*` = état main avant travaux, `apres_*` = état livré).
E2E : `qa/ux_v1/e2e.mjs` (30 asserts, **tout vert**) + `tests/test_ux_v1.py` (10 pytest, **tout vert**).
Captures : `qa/ux_v1/shots.mjs avant|apres` (rejouable).

## Table item → commit → preuve → E2E

| # | Item (réf AMELIORATIONS-UX) | Commit | Preuves (audit_shots/ux_v1/) | E2E |
|---|---|---|---|---|
| 1.1 | réf 1 — mobile : carte plein écran, COUCHES + légende VERDICT en tiroir « Couches » | `8a6fb3a` | `avant/apres_375_1_1_boot.png` · `apres_375_1_1_tiroir.png` | ✓ carte = viewport − rail · bouton flottant · tiroir avec VERDICT |
| 1.2 | réf 6 — builder segments : onglets Filtres / Résultats sous 640 px | `c522428` | `avant/apres_375_1_2_builder*.png` | ✓ onglets visibles à 375, bascule OK |
| 1.3 | réf 11 — warning MapLibre au boot 375 | `1e73a37` | `avant_console.json` (2 warnings) → `apres_console.json` (0) | ✓ 0 « Map cannot fit » (boot + commune ↔ île) |
| 2.1 | réf 2 — mode dégradé NL visible dans la restitution + badge « mode mots-clés » | `83d85cd` | `avant/apres_1440_2_1_restitution_stub.png` | ✓ badge + explication + « n'ont pas été traduits » |
| 2.2 | réf 10 — verbes hors périmètre → out_of_scope systématique | `5cd0c4f` | pytest (pièges de l'audit rejoués) | ✓ 3 pièges refusés via l'API sans clé (:8021) + 6 pytest ; recherches légitimes intactes |
| 2.3 | ajout C — 0 résultat → relâchement proposé et relançable | `bced12f` | `apres_1440_2_3_zero.png` · `apres_1440_2_3_relance.png` | ✓ proposition + relance → résultats |
| 2.4 | ajout A — page « Sources & fraîcheur » | `9b9b23c` | `avant/apres_1440_2_4_sources.png` · `apres_1440_2_4_sources_print.png` | ✓ positionnement · 4 précisions mesurées · licence sur 51/51 lignes · `derniere_ingestion` lue dans ingestion_runs (API) |
| 3.1 | réf 3 — erreur fiche : wording client, détail discret | `68375fa` | `avant/apres_1440_3_1_fiche_erreur.png` | ✓ « Connexion au serveur impossible… », zéro jargon |
| 3.2 | réf 4 — liste vide : message explicite + CTA | `8cce3bc` | `avant/apres_1440_3_2_liste_vide.png` | ✓ « Aucune parcelle chaude à Cilaos… » + « Élargir à toute l'île » |
| 3.3 | réf 13 — labels porteurs de sens ≥ 11 px | `6ae6811` | `apres_1440_3_3_fiche.png` · `apres_1440_3_3_galerie.png` | (visuel) 0 occurrence 9,5–10 px hors décoratifs mono |
| 3.4 | réf 14 — note « compteur du JJ/MM à HH:MM » sur la galerie | `700b78e` | `avant/apres_1440_3_4_galerie.png` | ✓ format vérifié sur chaque carte |
| 4.1 | réf 5 — ranges : min=0 + garde ambre, hors-domaine non envoyé | `f675f3c` | `avant/apres_1440_4_1_range_negatif.png` | ✓ min=0 · garde visible · critère exclu de la requête |
| 4.2 | réf 9 — focus-visible : anneau mint 2 px, parcours clavier complet | `ae163ed` | `avant/apres_1440_4_2_focus_rail.png` · `apres_1440_4_2_focus_couches.png` | ✓ outline calculé `2px rgb(92,230,161)` sur rail, couches, chips |
| 4.3 | réf 7 — tooltips Q / A / V (une phrase chacun, partout) | `422387f` | `avant/apres_1440_4_3_fiche_scores.png` | ✓ `title` Q—/A—/V— lus dans le DOM (fiche, liste, restitution, CRM) |
| 5 | ajout B — copy commerciale des presets (picto + bénéfice, compteur réel) | `29cc01b` | `avant_1440_3_4_galerie.png` → `apres_1440_lot5_galerie.png` | ✓ 5 pictos · 5 phrases · compteur piscines de la phrase = count réel du segment |

## Détails notables

- **2.4 (Sources & fraîcheur)** : `GET /sources` sert désormais `derniere_ingestion` + `ingestion_runs`
  par source — max des runs `ok` d'`ingestion_runs`, rattachés au catalogue par `_source_pour_run()`
  (cadastre = runs par commune, Sitadel, tuiles ortho ; fonction pure testée). C'est le **seul
  endpoint métier modifié**, en **lecture seule**, comme prévu au mandat. La page affiche la date
  la plus récente entre `last_sync_at` (posé par les jobs) et cette ingestion tracée — jamais une
  date en dur. Précisions mesurées affichées : piscines 90,7 % (échantillon interne) · NL 20/20 ·
  BAN 99,99 % · ANC calé Office de l'eau. Licences : `legal_notes` d'abord, référentiel vérifié
  sinon. Imprimable (`@media print` sobre, page seule, bouton Imprimer).
- **2.1/2.2** : le jargon « (repli stub) » a disparu des textes face client ; le badge « mode
  mots-clés » + une phrase disent ce qui n'a pas été traduit. Le stub refuse désormais
  supprimer/modifier/écrire/ajouter/envoyer/ignorer… **avant** toute extraction de critères.
- **2.3** : heuristique de relâchement = premier critère numérique présent dans l'ordre
  SDP → surface min → score → surface max ; la relance rejoue la chorégraphie complète et
  l'explication mentionne le critère retiré.
- **3.3** : passe typographique sur 18 composants ; restent < 11 px uniquement les libellés
  décoratifs `font-mono tracking-widest` (exclus par le mandat), les glyphes (★, ◠, #N), les
  extraits de code du bandeau dégradé et le détail technique volontairement discret de l'item 3.1.
- **4.2** : la règle globale `:focus-visible` existait (commit `3833e18`) — l'item a été traité en
  **vérification mesurée** (outline calculé en E2E sur rail/couches/chips) + correction du dernier
  input sans retour de focus (renommage de projet) + documentation de la règle.

## Confirmations du mandat

- **Items reportés NON touchés** : n°8 (offline global — post-VPS), n°12 (gabarits courrier
  métier — post premier envoi), n°15 (section copro du PDF Flash — Lots 2-4). Aucun fichier de
  ces périmètres modifié.
- **DA intacte** : noir / mint, violet réservé copilote-modules — aucun nouvel usage du violet ;
  la garde de saisie utilise l'ambre d'avertissement existant (#E8B44C), les pictos galerie sont mint.
- **Aucun endpoint métier modifié** hors `GET /sources` (lecture `ingestion_runs`, ajout de champs,
  aucun champ retiré) et le wording du repli de `POST /ia/search` (mêmes structures de réponse).
- **Aucun merge** — la branche `feat/ux-v1` attend Vic (`git merge --no-ff feat/ux-v1`).
- Wording FR ton produit sur tout ce qui est face client (enums traduits sur la page Sources,
  « repli stub » et « labuse api » purgés).

## Comment rejouer

```bash
# serveur avec la base : LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
.venv/bin/python -m pytest tests/test_ux_v1.py -q          # 10 verts
BASE=http://127.0.0.1:8000/socle/ node qa/ux_v1/e2e.mjs     # 30 asserts (STUB_API=… pour l'item 10 via API)
node qa/ux_v1/shots.mjs apres                               # regénère les captures
```

## Definition of Done

- [x] 15 items livrés, un commit chacun, preuves avant/après
- [x] E2E : mode dégradé NL visible · out_of_scope stub · état vide + CTA · garde ranges · page Sources renseignée depuis ingestion_runs
- [x] Mobile 375 : carte plein écran au boot, builder utilisable (onglets)
- [x] Aucun item hors liste, DA intacte, items reportés intacts
- [x] RAPPORT_UX_V1.md complet
