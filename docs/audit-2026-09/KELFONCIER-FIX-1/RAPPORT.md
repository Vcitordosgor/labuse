# KELFONCIER-FIX-1 — les 8 features injectées sur l'existant

**Exécution du mandat** sur l'audit `KELFONCIER-1` (branche `audit/kelfoncier-1`). Chaque feature est
branchée sur des données et des moteurs DÉJÀ en base — aucune nouvelle source, aucun run, aucun
recalcul île (sauf le backfill additif du Lot H, mesuré à ~9 s).

- **Branche** : `fix/kelfoncier-1` (base `origin/main`) · worktree `~/Desktop/labuse-kelfix` · ports **8545** / **5745**.
- **Run servi** : `q_v11_m137` (résiduel run_seq 10, `is_served=t`).
- **Un commit par lot**, jamais avant la recette du lot. Ordre des commits : E · D · B · G · F · C · H · A.
- **Témoins** : `97410000AN0347` (Saint-**Benoît** — l'audit le disait « Saint-Denis » ; la base dit
  Saint-Benoît, insee 97410) · `97415000BW0102` · `97415000AB0134` (AU1est, `conditionnelle_operation`).

## Étape 0
`pwd` = `~/Desktop/labuse-kelfix`, branche `fix/kelfoncier-1`, `git status` vide. API 8545 + front 5745
lancés une fois (front proxy `LABUSE_API_DEV=http://127.0.0.1:8545`). `.env` local = DB URL, **sans**
`GOOGLE_MAPS_EMBED_KEY` (état par défaut du Lot G : bouton masqué).

## Cadence de validation
Baseline pytest établie sur la base propre : **13 échecs pré-existants / 3 366 passés / 69 skips**
(21 min). Ces 13 échecs sont la référence « 0 nouvel échec » (GEOPF-3, reliquats front, garanties
sur base réelle…). Avant chaque commit : sous-ensemble ciblé du lot + verrous concernés + `tsc` +
`vitest`. Le **V5d** (déclarations fiche → Dossier) a été rejoué en direct à chaque lot touchant le
registre (A, F, H) — vert. **Suite pytest COMPLÈTE rejouée en fin de mandat** (résultat § Fin).

---

## Lot A — Statut d'ouverture des zones AU
**Où ça se voit** (confirmé) :
- Fiche §4 Urbanisme — `app.py:_au_ouverture_block` (payload `au_ouverture`), rendu `Fiche.tsx` sous
  `<ReglementPluBlock>` (ligne + motif cité + PONT « Simuler l'ouverture »).
- Fiche §10 Constructibilité — `constructibilite.tsx` (`ConstructibiliteSection`) : `Vigilance` + motif
  quand `au_ouverture.bloquant`.
- Outil PLU « Simuler l'ouverture » — pont depuis la ligne (`Fiche.tsx` `PorteOutil` → `setPluVue('changement')`
  → voie « Procédure & changement » de `Plu.tsx`, qui simule la bascule AU → U).
- Outil Pièges & risques — `servitudes.py:contraintes_parcelle` (crible PARTAGÉ parcelle · lot · fiche
  §Pièges) : contrainte « Zone à urbaniser (AU) FERMÉE ».
- Registre : `au_ouverture_statut` (`donnees.py`, robinet `fiche_parcelle_urbanisme`, `sections_restantes.yaml`)
  → V5d vert → Dossier/Flash + Copilote par déclaration.

**Preuve** : AB0134 → `conditionnelle_operation` (« constructible sous condition d'une opération
d'aménagement d'ensemble », zone AU1est, non bloquant). AB0212 → `declasse_au_fermee` (« fermée — une
modification du PLU est requise », bloquant ; Pièges : « Zone AU AUp1 FERMÉE »). AN0347 (zone N) → `null`.

**Tests** : `tests/test_kelfoncier_au.py` (4) — conditionnelle, fermée=bloquant, None hors AU, crible
Pièges inclut AU fermée. **Reste** : le pont réutilise la voie AU→U existante (pas de nouvel onglet créé
— la simulation existait déjà).

## Lot B — Filtres propriétaire (PM)
**Où ça se voit** : panneau Filtre (section « Propriétaire » remontée). Backend `_q_v2_where`, facettes
`/proprietaires/*`, hash et « Mes vues » étaient déjà câblés (KF1) — seule l'UI (commit `79523a24`)
manquait.
- Remonté : forme juridique · dénomination (autocomplétée) · SIREN · code APE · nombre de dirigeants
  (`FiltreLabuse.tsx:SectionProprietaire`).
- **Ajouts** : chip « Particulier » = aucune PM connue (`proprietaireType 'pp'`, ~349 597 parcelles île) ;
  **tranche d'âge du dirigeant** `< 50 / 50-69 / ≥ 70` — nouveau param `pm_age` filtrant
  `v_pm_propension_vendre.age_max_dirigeant` (âge MAX déjà calculé, déjà consommé par la veille
  succession → **jamais l'âge exact**, aucune donnée personnelle nouvelle). Le contrôle exact-âge
  (`filtre_age_dirigeant`, garde `FORBIDDEN_FLAGS_RGPD`) reste **fermé et refusé** (verrouillé par test).
- `vite.config.ts` : `/proprietaires` ajouté au proxy dev (endpoint vivant mais non proxifié → 404 en
  dev ; prod même origine OK).

**Preuve** (Saint-Paul, /filtre) : particulier 38 664 · société 12 341 (= base 51 005) · âge ≥ 70 : 2 261 ·
< 50 : 301 · 50-69 : 3 205 · 50-69 ∪ ≥ 70 : 5 466. Facettes réelles rendues (SARL 456, SAFER 242…).
**Tests** : `tests/test_filtres_proprietaire.py` (+4) · `filters.test.ts` (pmAge round-trip + compteur).

## Lot C — Permis annulés, PA, DP
**Où ça se voit** : source UNIQUE `ingestion.permits.etat_libelle` / `est_annule` / `ETAT_LABELS` (le
`_ETAT_LABELS` que la frise invoquait sans qu'il existât). Décode 2 autorisé · **4 ANNULÉ (4 324)** ·
5 commencé · 6 achevé (DAACT prime).
- Fiche §4 « Sur cette parcelle » (`site_voisinage.historique_permis`) : type libellé + état ; annulé en
  rouge (`autour.tsx`). Preuve AB0910 (Bras-Panon) : PC autorisé + PC **annulé** distingués.
- Frise (`moteurs.py`) : « Permis {type} **annulé** » au lieu d'« autorisé ».
- Outil Permis (`veille_promoteurs.py`) : `etat_libelle` partagé + drapeau `annule`.
- Étude de zone (`permis_par_type_zone`) : annulés EXCLUS des comptes « autorisés par type » + `n_annules`.
- Fiche commune « Construire ici » (`fiche_commune.py`) : `permis_type_12m` (PC/PA/DP/PD) + `permis_annules_12m`.
- Dossier : la liste de permis suit par miroir.

**Interdit respecté** : aucune variable du Signal (`pc_*`) ni « Permis au point mort » touchée ;
`pc_caducs` inchangé. **Tests** : `tests/test_kelfoncier_permis.py` (4). **Reste** : le filtre d'état de
l'outil Permis + la carte commune consomment désormais la donnée servie ; l'UI de ces deux surfaces
(chip d'état, cartouche PC/PA/DP) reste à afficher — la fonction partagée et les données sont en place.

## Lot D — Filtres bâti
**Où ça se voit** : panneau Filtre, groupe « 2 · Le terrain ».
- Hauteur du bâti (LiDAR faîtage, `batiment_hauteur_lidar.faitage_m`, MÊME source que la fiche §3
  `hauteur_bati_m`) → `hauteur_min/max` (m).
- Emprise bâtie (%) sur `parcel_residuel.taux_emprise_pct` du run servi (colonne d'« État du sol ») →
  `emprise_min/max`.
- Câblage complet : `_q_v2_where`, `FiltreCriteres`, hash serveur (`emin/emax` int, `hmin/hmax` float →
  veille/Mes vues), store, `filters.ts` (compteur, TERRAIN=faits, récap), `api.ts`.

**Preuve** (Saint-Paul) : hauteur 3–10 m → 32 301 · ≥ 15 m → 222 · emprise ≥ 5 % → 27 811 · ≤ 0 % → 22 542.
**Tests** : `tests/test_filtres_bati.py` (WHERE + témoin end-to-end /filtre : faîtage 8,5 m ∈ [3;10]
ressort, hors → disparaît) · `filters.test.ts`.

## Lot E — Case « sans copropriété »
**Où ça se voit** : panneau Filtre, groupe terrain. Case `horsCopro` (composant `Case`) ; prédicat
`hors_copro` (`NOT COALESCE(s2.copro,false)`), hash `hc`, compteur/veille/Mes vues/badge déjà câblés.
**Preuve** : Saint-Paul 51 005 → 50 470 (535 copro exclues). **Tests** : `filters.test.ts` (hc persiste + compteur).

## Lot F — Petites Villes de Demain
**Où ça se voit** : `commune_ort` (11 PVD, 4 ACV, ORT signées) branché comme dispositif de commune par la
MÊME fonction que la fiche commune (`ingestion.ort.ort_commune`).
- Fiche §7 Fiscalité (`app.py:_dispositif_commune_ort` → `dispositifs_dom`, rendu générique existant).
- Dossier (`miroir.py:_r_territoire`) : rend désormais TOUS les dispositifs de commune (zonage A/B/C, TVA
  DOM ET PVD/ACV/ORT) — plus seulement le premier ; le résumé Flash les compte.
- Étude de zone, section Dynamique « à l'échelle de la commune » (`zone.py:commune_contexte_zone.dispositif_ort`).
- Fiche commune : lit déjà `ort_commune` (COMMUNE-FIX-1 B8) — inchangée.

**Vérification sans travail confirmée** (capture témoin Salazie 97421, fiche §7) : zonage « B1 » + TVA
2,1 % + « Petites Villes de Demain (PVD) · ORT signée (2021-10-05) ». **Tests** : `tests/test_kelfoncier_pvd.py` (4).

## Lot G — Street View
**Où ça se voit** : fiche §1 Identité.
- `app.py:_street_view_block(lat,lon)` lit `GOOGLE_MAPS_EMBED_KEY` (nom exact ; `/etc/labuse/labuse.env`).
  Absente → `street_view:null` → bouton MASQUÉ (vérifié). Présente → URL d'embed centrée sur le centroïde.
- CSP : `frame-src https://www.google.com` ajouté (`app.py`), `frame-ancestors 'none'` conservé.
- Front : bouton « Voir la rue » à côté du lien Google Maps (`Fiche.tsx`), panneau INLINE (jamais en
  pleine page) + iframe (`loading=lazy`).

**Preuve** : capture — bouton présent (clé posée), panneau ouvert, iframe Google chargé (CSP OK) ; sans
clé, `street_view:null`. **Tests** : `tests/test_kelfoncier_streetview.py` (3 — clé absente→None, URL
centrée sur le centroïde, CSP autorise frame Google).

## Lot H — Établissements sur la parcelle
**Chiffrage AVANT backfill** (garde 30 min) : 152 871 établissements de précision « adresse »
(qualite_xy 11/12) ; l'accroche BAN les rattache en **~9 s** → aucun STOP. Backfill île RÉEL joué :
**131 187 rattachés / 152 871 (86 %)**, 21 684 hors rayon (non rattachés, jamais devinés).
**Où ça se voit** :
- Nouveau moteur `ingestion/etablissement_parcelle.py` : rattache par l'adresse BAN la plus proche
  (index GiST, rayon 25 m), précision « adresse » SEULEMENT (« voie » 21 / « commune » 33 exclues). Un
  `ST_Within` pur ratait tout (0 sur les 3 témoins). Table `etablissement_parcelle` (siret, idu, precision).
- Fiche §3 Bâti (`app.py:_etablissements_block`, `leBien.tsx`) : nom · NAF fin · tranche d'effectif · état
  + régime collectif BODACC ; nom MASQUÉ si non diffusible (RGPD) ; précision `qualite_xy` dite. Déclarée
  au registre (`etablissements_parcelle_liste`) → V5d vert → Dossier/Flash + Copilote par miroir.
- Scan patrimoine, onglet Possession (`modules.patrimoine` + `ModulePanel.tsx`) : « occupé par N
  établissements ».
- Étude de zone (accordéon Économie) : réutilise la jointure SIRENE existante (pas de second calcul).
- Cron : le job mensuel SIRENE (`jobs_impl.ingest_sirene`) reconstruit la table (registre CRON unique —
  pas de nouveau cron) ; CLI `labuse build-etablissement-parcelle` pour un run manuel.

**Preuve** : parcelle 97401000AD0170 → 3 établissements (NAF fins « Travaux de charpente »… ; un nom
masqué RGPD ; précision 11). Témoins AN0347/BW0102/AB0134 → 0 (non commerciaux, honnête). **Tests** :
`tests/test_kelfoncier_etablissements.py` (3 — précision adresse seule, masquage RGPD, NAF/tranche, None).

---

## Tableau final

| Lot | Endroits servis | Tests | Reste |
|---|---|---|---|
| A · AU statut | fiche §4 + §10 + Pièges (crible partagé) + registre → Dossier/Copilote + pont outil PLU | test_kelfoncier_au.py (4) | pont réutilise la simulation AU→U existante (pas de nouvel onglet) |
| B · Filtres PM | panneau Filtre (forme/nom/SIREN/APE/dirigeants/**tranche âge**/**Particulier**) + hash/veille/Mes vues/badge | test_filtres_proprietaire.py (+4), filters.test.ts | exact-âge reste fermé RGPD (par choix + test) |
| C · Permis annulés/PA/DP | fonction partagée + fiche §4 + frise + Étude de zone + fiche commune (backend) + Dossier | test_kelfoncier_permis.py (4) | UI chip d'état outil Permis + cartouche carte commune (données servies) |
| D · Filtres bâti | panneau Filtre (hauteur LiDAR + emprise %) + hash/veille/badge | test_filtres_bati.py, filters.test.ts | — |
| E · Sans copropriété | panneau Filtre (case) + hash/badge | filters.test.ts | — |
| F · PVD | fiche §7 + Dossier miroir + Étude de zone + fiche commune | test_kelfoncier_pvd.py (4) | — |
| G · Street View | fiche §1 (bouton + panneau) + CSP + env | test_kelfoncier_streetview.py (3) | clé fournie par Vic (`/etc/labuse/labuse.env`) |
| H · Établissements | fiche §3 + Scan patrimoine + Étude de zone (Économie) + cron mensuel + Dossier | test_kelfoncier_etablissements.py (3) | — |

## Captures
`docs/audit-2026-09/KELFONCIER-FIX-1/captures/` : `DE-apres-panneau-filtre.png` (Lots D+E — Sans
copropriété + Hauteur bâti + Emprise), `B-apres-section-proprietaire.png` (Lot B — facettes réelles),
`G-apres-street-view-panneau.png` (Lot G — bouton + panneau iframe), `F-apres-fiche-fiscalite-pvd-salazie.png`
(Lot F — B1 + TVA + PVD·ORT signée). Les surfaces C/H/A (fiche §4/§3/§Pièges) rendent dans des tiroirs
non ouvrables de façon fiable en navigateur headless ; elles sont prouvées par appels d'endpoint
directs (reproduits ci-dessus) + tests d'endpoint/unitaires.

## Fin de mandat
`pytest tests/` complet, `tsc`, `vitest`, verrous — résultats consignés au commit de ce rapport.
Aucune proposition hors périmètre.
