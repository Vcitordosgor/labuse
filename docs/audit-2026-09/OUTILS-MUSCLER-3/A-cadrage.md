# Lot A — Cadrage (lecture seule) — Blocs fonciers

Mesuré sur base locale `labuse` (431 663 parcelles), run résiduel servi `run_seq=2` (m135-run2-ile).

## 1. Ce qui existe déjà / à écrire
- **Réutilisable tel quel** : le prédicat de contiguïté `ST_DWithin(a.geom_2975, b.geom_2975, 0.5)` (`ADJ_BUFFER_M=0.5`, `src/labuse/assemblage.py:18,58`) ; le graphe + DFS de connexité `src/labuse/moteurs.py:183-197` ; la jointure propriétaire `LEFT JOIN parcelle_personne_morale pm ON pm.idu` (`moteurs.py:176`) ; la vue résiduel `parcel_residuel` (`src/labuse/faisabilite/residuel_runs.py`, filtrée sur `is_served`).
- **À écrire** : le balayage **île entière** (le moteur existant part d'UNE parcelle-fiche, il n'a pas de composantes connexes globales par SIREN) ; la table `parcel_blocs` ; la commande CLI `@app.command` (modèle `cli.py:643` flux-run, journal `run_progress.py`) ; l'endpoint liste + l'outil front.

## 2. Identité du propriétaire
Regroupement sur **SIREN** (`parcelle_personne_morale.siren`, PK `idu`, une ligne courante par parcelle). Les particuliers n'ont **aucune identité stable** exposée (`_proprio()` renvoie `{type: particulier}` sans nom, `moteurs.py:199-203`). → **L'outil se limite aux personnes morales** et le dit à l'écran (tiroir « Détail et méthode »). Aucun regroupement par nom approché.

## 3. Volume réel (contiguïté 0,5 m, même SIREN, ≥ 2 parcelles)
- **11 225 blocs** — le chiffre ~12 000 de l'audit est **confirmé** (léger en-dessous). 3 827 SIREN, 59 835 parcelles regroupées.
- Distribution taille : **2 → 5 394 · 3-5 → 3 739 · 6-10 → 1 196 · 10+ → 896** (max 426, médiane 3).
- Top communes : Saint-Paul 1 558 · Saint-Denis 1 533 · Saint-Pierre 1 206 · Le Tampon 855 · Saint-Benoît 565. 21 blocs à cheval sur 2 communes.
- SQL rejouable : `parcelle_personne_morale` ⋈ `parcels`, HAVING count≥2, arêtes `ST_DWithin(geom_2975,0.5)`, composantes connexes (union-find) — voir `scripts/blocs_cadrage.sql`.

## 4. Coût du batch
- Sélection parcelles PM multi-SIREN ≈ 0,7 s · **arêtes de contiguïté île entière ≈ 18 s** (79 857 arêtes) · union-find < 1 s · agrégat résiduel via vue. **Total estimé ~30-60 s.**
- Index : `idx_parcels_geom_2975` (GIST) **existe et est utilisé** (EXPLAIN : Index Scan `&& st_expand`, self-join du plus gros SIREN 4 183 parc. = 151 ms). `parcelle_personne_morale_pkey`, `residuel_runs` OK. **Aucun index manquant.**
- Table produite : **11 225 lignes** (+ ~59 835 liens IDU si table de liaison séparée).

## 5. Verdict
1. **Tenable tel que décrit** — volume, coût et index conformes ; le chiffre d'audit tient.
2. Ajustement : le résiduel agrégé se lit sur la **vue `parcel_residuel` (run résiduel servi)**, pas via `q_v11_m137` (le pin scoring ne porte pas le résiduel ; cohérent avec « aucun badge de score »). Contiguïté inter-communes conservée (21 blocs) — un bloc peut lister plusieurs communes.
3. **Aucun index à créer.**
