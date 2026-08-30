# OUTILS-4 — finitions + un ajout produit (recette Vic d'OUTILS-3) · compte-rendu

Poste : `~/Desktop/labuse` · branche : `feat/outils-1` (OUTILS-1/2/3 commités). **Ne pas merger** — commande
au dernier point, isolée.

Écriture Postgres : **une seule** — la colonne `sirene_etablissements.date_dernier_traitement` (F2/F3),
migration propre (ALTER + backfill de la seule colonne, comme A3-bis). Golden : 0 fichier de scoring touché → intact.

**Preuve que la branche est servie** : API redémarrée (uvicorn tué/relancé), front **rebâti**, servi sous
`/socle/`. Endpoints O2/O3 répondent (naf_label, millésime réel « SIRENE géolocalisé 2026-08 »). Nouveaux
endpoints O4 servis (`/outils/etude-zone/entreprises`, `date_maj`/`maj_ancienne` sur concurrents). Captures
Playwright sur ce build.

---

## F1 — COMMUNES : « voir ses parcelles » ouvre le LISTING ✅
`ContextePanel.tsx`.
- Le bouton fait désormais, dans l'ordre : `setView('cartes')` (quitte l'outil, ferme la fiche) →
  `setCommune` (périmètre carte) → `setCommunesFilter([commune])` (filtre le listing) →
  `setFilter('analyseLabuse', true)` + `setVerdict(true)` (ouvre le **regard LABUSE** = la liste des
  parcelles classées). Le client atterrit sur la **liste ouverte, filtrée sur la commune, carte à côté**.
- **Check (3 communes, listing = stock foncier du comparateur)** : le champ `opportunites` du listing filtré
  (= même moteur `parcel_p_score_v2`, run servi, que le tableau comparatif) —
  **Saint-Paul 285**, **Le Tampon 144**, Cilaos 18 — chaque `page` filtré sur sa commune. Capture
  `01-F1-listing-commune.png` : « ✓ Analyse LABUSE affichée » + section RÉSULTATS, en-tête Saint-Paul.

## F2 — ÉTUDE DE ZONE : la fraîcheur de chaque concurrent ✅
`zone.py` + `EtudeZone.tsx` (+ **migration** `date_dernier_traitement`).
- **Le champ EXISTE dans la source** (`StockEtablissement.dateDernierTraitementEtablissement`) mais n'était
  pas ingéré → **migration propre** : colonne ajoutée à l'ingestion (DDL/SELECT/INSERT) + **backfill de la
  seule colonne** (158 515/158 515). CHANTECLAIR = 2025-12-06, comme le parquet.
- **Affichage par établissement** : « déclaré actif · **mis à jour MM/YYYY** » (capture : « CHANTECLAIR ·
  depuis 2006 · déclaré actif · mis à jour 12/2025 »).
- **Seuil d'ancienneté** = constante nommée backend `SEUIL_FRAICHEUR_MOIS = 24`, **justifiée** : l'INSEE
  retraite un établissement à CHAQUE déclaration (création, adresse, activité, **cessation**) ; un
  enregistrement non retouché depuis 24 mois (2 cycles annuels) n'a plus vu passer de déclaration récente —
  c'est précisément le cas où une fermeture non signalée peut se cacher. Au-delà, mention **« registre
  ancien — vérifier sur place »** (flag `maj_ancienne` servi, jamais décidé au front).
- **Libellé** : « **Concurrents déclarés au registre** » — jamais « Concurrents » tout court.
- Millésime affiché comme ailleurs.

## F3 — ÉTUDE DE ZONE : « Toutes les entreprises de la zone » (ajout produit) ✅
`zone.py` (`entreprises_zone`) + endpoint `POST /outils/etude-zone/entreprises` + `EtudeZone.tsx`
(`ToutesEntreprises`).
- **Bouton** « Toutes les entreprises de la zone (N) » sous les concurrents (N = total déjà calculé,
  `emplois.n_etablissements`).
- **Vue GROUPÉE PAR FAMILLE d'activité** (section NAF A-U), chaque famille avec son **compte exact**,
  **dépliable** pour voir les établissements. Familles/libellés = source UNIQUE `naf_nomenclature`
  (`SECTIONS` + `NAF_SOUS_CLASSES`), jamais en dur au front.
- **Comptes EXACTS** via un `GROUP BY naf` sur toute l'emprise (pas l'échantillon) ; établissements détaillés
  **plafonnés** (`ENTREPRISES_CAP_CARTE = 1000`, `ENTREPRISES_CAP_LISTE = 40`) — le count reste exact, on
  DIT « + N autres — aperçu plafonné ».
- **Mêmes règles que les concurrents** : actifs seuls, nom ou « non diffusé », activité en clair, date de
  création, **pastilles cliquables sur la carte** (popup nom/activité/date + lien parcelle), millésime.
- **Check** : somme des comptes par famille = total du bouton = count SQL des actifs sur l'emprise —
  vérifié live : **8 518 = 8 518 = emplois.n_etablissements** (zone témoin 5 min). Captures
  `03-F3-toutes-entreprises.png` / `04-F3-famille-depliee.png` (17 familles, « Activités immobilières 168 »
  dépliée, pastilles orange sur la carte).

---

## Gates

- **tsc** : 0. **build** : OK. **vitest** : **108/108**.
- **pytest** : **2000 passed, 42 skipped, 0 failed** (374 s, `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`).
  `test_zone_donnees` adapté à la colonne date_dernier_traitement (6/6).
- **Golden** : **0 fichier de scoring touché** → intact.
- **Écriture DB** : la seule autorisée — colonne `date_dernier_traitement` (migration propre + backfill).

---

## Fichiers touchés

Backend : `zone.py` (F2 date_maj/maj_ancienne/seuil, F3 entreprises_zone) · `api/app.py` (endpoint
entreprises) · `ingestion/sirene_etablissements.py` (colonne date_dernier_traitement).
Front : `outils/EtudeZone.tsx` (F2 fraîcheur, F3 toutes entreprises) · `contexte/ContextePanel.tsx` (F1) ·
`lib/api.ts` + `lib/types.ts` (types entreprises/concurrent). Tests : `test_zone_donnees`.
Docs : `docs/OUTILS-4/` (compte-rendu, captures).

**Note sur la règle d'écriture** : la migration `date_dernier_traitement` sert F2 (fraîcheur par concurrent)
ET F3 (mêmes règles que les concurrents). Le champ existe dans la source SIRENE ; la migration est propre
(ALTER + backfill d'UNE colonne, patron A3-bis déjà éprouvé) et documentée ici — conforme à l'esprit de
l'autorisation « colonne manquante, migration propre, documentée ».

---

## Merge

**Ne pas merger.** Après revue Vic :

```
git checkout main && git merge --no-ff feat/outils-1
```
