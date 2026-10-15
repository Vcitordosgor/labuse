# CHASSE-INVARIANTS-2 — BRIEF partagé (contrat des familles)

> Mille règles, **générées, pas écrites à la main**. Audit **LECTURE SEULE** : aucun correctif,
> aucune écriture base, rien sur le VPS. Base servie **q_v18 / run_seq 15 / cascade q_v18_sources**,
> **434 582 parcelles** (433 229 vivantes), 24 communes, corrections de FIX-1 mergées.
> Worktree `labuse-chasse-inv2`, branche `audit/chasse-invariants-2`. API locale **8793** (front 5993).

## Recette d'exécution (toujours celle-ci)
```bash
export LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse
export PYTHONPATH=/Users/openclaw/Desktop/labuse-chasse-inv2/src
VPY=/Users/openclaw/Desktop/labuse/.venv/bin/python   # le worktree n'a PAS de .venv
cd /Users/openclaw/Desktop/labuse-chasse-inv2
# JAMAIS .venv/bin/labuse (code figé). API déjà lancée sur 127.0.0.1:8793.
```

## Le noyau (`scripts/coherence/invariants2/noyau.py`) — à réutiliser, pas à réécrire
- `RuleSpec(id, famille, source, libelle, gravite, attendu, sql_violations|check, exemples_sql, params)`.
  Deux formes : **SQL** (`sql_violations` compte les lignes QUI VIOLENT, 0 attendu) **XOR** **callable**
  (`check(cx, api)->(statut,message)`).
- `run_specs(cx, specs, api)` exécute, défensif (toute surprise = **SKIP**, jamais un crash) → `Resultat`.
- Introspection : `colonnes(cx, table)`, `toutes_les_tables(cx)`, `table_existe`, `Colonne.numerique/date_like/texte`.
- Registre : `registre_chiffres(cx)`, `registre_robinets(cx)`.
- `echantillon_stratifie(cx, n=2000)` → idu stratifiés par commune, **déterministe** (ordre md5).
- API : `api_json(base, path) -> (status, payload|None)`, `api_dispo(base)`.
- `run_servi()` → `('q_v18', 15, 'q_v18_sources')`. `connexion()` → `Cx` lecture seule, statement_timeout 120 s.

## Règles du jeu (mandat)
- **Vraie par construction.** Une règle qui n'a pas de sens est **écartée AVANT de tourner**
  (`Ecartee(id, famille, source, raison)`), jamais après. Chaque famille rend : générées / retenues /
  écartées (+ raison) / parcelles ou lignes passées / violations.
- **Un faux positif coûte cher.** Toute violation est **revérifiée à la main sur 3 exemples** avant
  d'entrer dans ECARTS-2.md.
- Requêtes lourdes **une par une**, `statement_timeout` partout. **Jamais deux jointures île entière
  en même temps** (surtout F6 : contenance parcelle⊂commune, union PPR).
- Ne refait pas les 97 de la vague 1 (`scripts/coherence/chasse_invariants.py`) : base reprise telle quelle.

## Les sources que l'app sait d'elle-même
- **Schéma** : `information_schema` (272 tables base). Tables servies au client : `parcels`,
  `parcel_residuel`, `parcel_zone_plu`, `score_labuse`, `score_e`, `dpe_records`, `sitadel_permits`,
  `dvf_mutations*`, `parcelle_personne_morale`, `pm_dirigeants`, `parcel_terrain`, `parcel_amenites`, …
- **Registre** : `registre_chiffres` (248 : id/libelle/unite/niveau/moteur/reservoirs/portee), `registre_robinets`
  (158 : id/categorie/nom/parent/**route**/mode_rendu/chiffres), `registre_aretes` (581 : reservoir→chiffre…).
- **Routes API** (GET client) : `/parcels/{idu}?source=`, `/parcels` (liste), `/parcels/search`, `/parcels/at`,
  `/recherche/suggest?q=`, `/communes/{c}/contexte`, `/communes`, `/map/tiles/{z}/{x}/{y}.pbf`,
  `/map/tiles/meta`, `/filtre` (source REQUISE), `/stats`, `/stats/entonnoir`, `/parcels/{idu}/zone`,
  `/parcels/{idu}/export`, `/adresses/autocomplete?q=`, `/config/run`, `/vocabulaire/*`, `/sante/fraicheur`,
  `/discover`, `/healthz`. Auth désactivée en local (trace admin-only sinon).
- **PLU** : règles calibrées `config/plu_destinations/97*.yaml` (`zones.{code}.regles.{hauteur|retraits|emprise_sol|
  stationnement|pleine_terre|mixite}.{feuille}` avec `article`,`page_pdf`,`citation`,`statut ∈ valide|propose|absent`).
  Métadonnées `config/plu_zonage.yaml`. Moteur `src/labuse/faisabilite/zonage.py` (ZoneRules ; `_val` ne lit
  une feuille QUE si `statut=="valide"`, `propose`→`A_VERIFIER` non numérique). Extraits PDF : table
  `plu_reglement_extrait` (insee, zone, article_ref, **page_pdf**, texte_verbatim). Zones GPU : `spatial_layers`
  `kind='plu_gpu_zone'` (geom 4326 + geom_2975).
- **Limites communales officielles** : `frontend/public/communes974.geojson` (24 features {nom, code},
  Polygon/MultiPolygon, WGS84). `parcels.commune` est assignée à la SOURCE (Etalab), **jamais** par
  `ST_Contains` → c'est la zone muette de la vague 1. Charger la geojson en **couche temporaire de session**
  (table TEMP ou CTE VALUES), **jamais** en base servie.

## Livrables par famille
Chaque famille écrit **ses propres fichiers** (pas de collision) :
- `scripts/coherence/invariants2/fN_<nom>.py` : le **générateur** (`def generer(cx) -> (list[RuleSpec], list[Ecartee])`)
  + un `if __name__=="__main__"` qui génère, exécute via `run_specs`, imprime le bilan.
- `docs/audit-2026-10/chasse-invariants-2/FN.md` : rapport de famille (générées/retenues/écartées+raison/
  lignes passées/violations, + les 3-exemples revérifiés par violation confirmée).
- Les ECARTS confirmés : une liste dans FN.md, format `gravité · id · exemples · attendu · obtenu · cause · fichier:ligne`.
Le chef d'orchestre fusionne les FN.md dans INVARIANTS-2.md / ECARTS-2.md / RAPPORT-2.md et commite (1/famille).
