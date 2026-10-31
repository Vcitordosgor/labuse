# PPR-UNIQUE-1 — un seul module de lecture des PPR

**Branche** `fix/ppr-unique-1` · worktree `~/Desktop/labuse-ppr` · ports 9130/6330 · base Mac `labuse`
(434 582 parcelles, run servi `q_v20`). Aucun merge, aucun accès prod. Registre lu d'abord :
`docs/audit-2026-11/nu-1/` lots A, D, E.

**Décision de Vic appliquée telle quelle.** La doctrine **PPR-PARTIEL** tient : *seule la partie en
zone rouge est interdite ; le reste suit les règles de sa zone.* Les auditeurs proposant « rouge =
toute la parcelle inconstructible » ne sont PAS suivis. On ne retranche que le rouge ; le bleu et la
part hors rouge restent constructibles (sous prescriptions pour le bleu).

---

## Ce qui a été fait

### 1. Un seul module de lecture — `src/labuse/ppr.py` + fonction SQL `labuse_ppr_couleur`

Avant PPR-UNIQUE-1, **quatre classificateurs** divergeaient :

| Lieu | Ancien classement | Reconnaissait `i` ? |
|---|---|---|
| Étude `implantation/terrain.py` | sous-chaîne `"interdict"`/`"rouge"` sur `subtype` | **non** → bug D-001 |
| Résiduel/fiche `faisabilite/db.py` | `subtype = ANY(ppr_red)` (`['INTERDICTION']`) | non |
| Gabarit `gabarit/builder.py` | `subtype='INTERDICTION'` (+ flag du run figé) | non |
| Pièges/fiche `api/servitudes.py` | `subtype IN ('INTERDICTION','PRESCRIPTION')` | non → **ligne PPR silencieusement SUPPRIMÉE** |
| Sous-sol `implantation/service.py` | `lower(subtype) IN ('interdiction','i')` | oui (seul) |

Désormais **une seule vérité**, consommée partout :

- **Fonction SQL `labuse_ppr_couleur(subtype, attrs)`** → `'rouge'` | `'bleu'` | `'autre'`, posée dans
  `models.SQL_FUNCTIONS` (donc créée au boot / `doctor --fix` / `create_all` et **surveillée par
  `readyz`/`schema_status`** au même titre que `labuse_zone_famille`). Priorité : `subtype` DEAL
  faisant foi (INTERDICTION/PRESCRIPTION), repli sur `attrs->>'code_degre'` (R…/rR… = rouge,
  B…/rB… = bleu), **tout le reste → `'autre'`**.
- **Miroir Python `labuse.ppr.classer(...)`** (parité prouvée avec le SQL, test `test_ppr_unique`) +
  `est_interdit(...)`, `lire_zones_interdites_wkt(...)` (Étude), `couleur_sql()/interdit_sql()`
  (prédicats partagés par les requêtes), `inventaire()`/`codes_non_classes()` (recette).

**Prudence + journalisation (jamais ignoré).** La surface INTERDITE retranchée = **rouge ∪ autre**
(`labuse_ppr_couleur(...) <> 'bleu'`). Un code non classé est **traité en rouge** et **journalisé une
fois** (`log.warning("PPR : code non classé … traité en ROUGE par prudence …")`). On ne dessine jamais
dans une zone PPR dont la couleur n'est pas certaine.

### 2. Codes normalisés — inventaire de la base

Tous les codes PPR distincts de `spatial_layers` (kind=`ppr`), rangés :

| Couleur | n zones | codes |
|---|---|---|
| **rouge** (interdiction, inconstructible) | **74** | `subtype=INTERDICTION` : R, R1, R1B1, R1G, R1H, R1c, R2, R2 HACHUREE ILET FURCY, R2G, Rg, Rrtc, rR1, rR2 |
| **bleu** (prescription, constructible sous conditions) | **88** | `subtype=PRESCRIPTION` : B, B2, B2U, B2UG, B2u, B3, Bg, R1B1, RB, RB1, rB2, rB3 |
| **autre** (code non classé → traité ROUGE + journalisé) | **2** | `subtype='i'` (PM1 hérité, Saint-Philippe, `code_risque='i'`) |

Le `subtype` DEAL classe 162/164 zones ; les 2 zones `i` (Saint-Philippe) sont le cœur de D-001.

### 3. Les 1 237 parcelles de D-001 — avant / après

Univers : **1 243** parcelles touchant une zone PPR `i` (recomptage ; l'audit citait 1 237). On
recalcule, pour l'ancien et le nouveau classement, la zone d'implantation (`terrain.charger`) et la
part de cette zone qui tombe **dans le rouge**. Résultat (`recette_1237_resultat.json`, 1 242 traitées,
1 écartée sur géométrie dégénérée) :

| | AVANT | APRÈS |
|---|---|---|
| Parcelles dont la zone dessinée **empiétait le rouge** | **1 217** | **0** |
| Aire rouge traitée « constructible » | **5 110 065 m²** | — |
| Empiètement rouge **maximum** d'une zone dessinée | > 0 partout | **0,0 m²** |
| Parcelles ~100 % rouge → **0 logement** | — | **380** |
| Parcelles gardant une part HORS rouge (PPR-PARTIEL) | — | **862** |
| **Invariant « aucun logement dessiné en zone rouge »** | faux | **VRAI** |

Témoin D-001 `97417000AH0053` (100 % code `i`), via `POST /modules/etude` :

| | AVANT (audit NU-D-001) | APRÈS |
|---|---|---|
| `terrain.ppr_rouge_m2` | **0,0** | **1 308,9** (toute la parcelle) |
| `capacite_maximale.logements` | **42** | **0** (capacité nulle) |
| `verdict` | « À compléter » / « exploitable » | **« Impossible pour cause établie »** |

### 4. Tous les niveaux d'aléa, chacun avec sa part (A-007, D-033)

`aleas_parcelle` ne garde plus **le seul niveau le plus fort** (`best[typ]`) : il liste **tous** les
niveaux par type, triés, avec la part de chacun et l'exposition cumulée. Témoin Salazie
`97421000AB0133` :

> Aléa mouvement de terrain — niveau **fort** ~3 % — *exposition totale au risque mouvement de terrain :
> ~100 %* · niveau **moyen** ~33 % · niveau **faible** ~64 %.

(Avant : « mouvement de terrain — fort ~3 % » seul, laissant lire « 97 % sûr ».)

### 5. Part rouge et part constructible nommées, « à confirmer au règlement du PPR » (A-008, D-027, D-034)

Le verdict ne dépend plus d'un seuil de scoring 50 %. Toute zone rouge est énoncée **inconstructible,
quelle que soit la surface** (C. env. L562-1), et la part hors rouge est nommée :

> PPR … — zone rouge sur **24 %** de la parcelle : partie **INCONSTRUCTIBLE** (interdiction, C. env.
> L562-1), quelle que soit la surface. Partie hors zone rouge (**76 %**) : constructible selon les
> règles de sa zone, **à confirmer au règlement du PPR**.

(Avant, sur `97411000EY0173` : « zone rouge sur 24 % … **pas d'exclusion automatique** ».) Le moteur
(Étude, Gabarit, résiduel) **ne dessine que hors rouge** — prouvé §3.

### 6. Un seul compteur de risques — tuile = section = PDF (A-011)

Définition unique « N vigilances » = lignes de l'onglet `risques` en vigilance (SOFT/HARD), **bassin
versant exclu** (contexte hydrographique). Portée par `robinet_fiche._c_vigilances` (`n_vigilances`),
lue **à l'identique** par la tuile d'en-tête (`Fiche.tsx`), le badge §5 (`risques.tsx`) et la tuile
« Risques » de la garde du Dossier (`miroir.py`, l'ancien repli `_n_aleas` retiré).

| Parcelle | tuile | section §5 | PDF garde |
|---|---|---|---|
| `97411000IE0241` | 2 | 2 | **2 vigilances** |
| `97421000AB0133` | 7 | 7 | **7 vigilances** |

(Avant, audit A-011 : tuile 3 / section 2 / PDF « 1 relevé ».)

### 7. Doublons retirés (D-035, D-036, E-051)

- **D-036** — le PPR n'est plus servi deux fois : quand le zonage PPR live (rouge/bleu) est servi,
  l'assiette SUP `pm1` (« enveloppe des zonages PPR », périmètre sans couleur) est masquée
  (`contraintes_parcelle`). Une seule lecture du même PPR.
- **D-035** — le drapeau `redhibitoire` atteint enfin l'écran : la ligne « zone rouge = interdiction »
  teinte sa carte en rouge et remonte en tête dans Pièges et risques (`blocB.tsx`), au lieu d'une carte
  grise indistincte.
- La graduation rouge est cohérente d'un outil à l'autre (plus de drapeau incohérent fiche vs outil).

### 8. Bande littorale proportionnée (E-006)

`faisabilite/db.py` sert désormais `littoral_pct` (part réelle de la parcelle dans la bande), non un
booléen ; `engine.py` ne retranche que cette part (`facteur ×= 1 − littoral_pct`). Une parcelle en
contact de 12 % n'est plus annulée en entier (témoin `97404000AM0097` : 36,6 % dans la bande →
63,4 % conservés). Une parcelle 100 % dans la bande (`97415000BR0025`) reste, à juste titre, nulle.

---

## Recette

- **1 243 parcelles D-001** : `recette_1237.py` → `recette_1237_resultat.json` — invariant « aucun
  logement en zone rouge » **VRAI** (empiètement max 0,0 m²), 1 217 → 0.
- **6 témoins avant/après** : `recette_temoins.py` → `recette_temoins_resultat.json` (Salazie AB0133,
  D-001 AH0053, Cilaos AE0050, grande EY0173, littoral BR0025, maison IE0241) — écran (liste de risques
  + compteur) et Étude (rouge retranché, zone d'implantation).
- **PDF** : Dossier généré pour IE0241 et AB0133 — tuile « Risques » = compteur unifié (2 / 7), §4
  imprime le libellé canonique (part rouge + part hors rouge + L562-1 + « à confirmer au règlement du
  PPR ») et **tous** les niveaux d'aléa. PDF == écran (même `aleas_parcelle_liste`).
- **Tests** : suite complète `pytest -m "not reel and not local and not network"` = **4 088 passés**,
  82 skipped, **8 échecs TOUS pré-existants** (vérifiés un à un `git stash` sur la base : 6 `test_cascade`
  + `test_pente_exposition::…pas_exclusion` + `test_implantation2::…sert_les_scenarios` — fixtures/parcelles
  absentes de `labuse_test`, sans rapport avec le PPR). Nouveau `tests/test_ppr_unique.py` (classification
  + parité SQL/Python + `i`→autre) vert. Tests mis à jour au libellé/à la source canoniques :
  `test_servitudes` (libellé PPR), `gabarit/test_builder` (part rouge en direct), `test_opportunites_c`
  (bande littorale PROPORTIONNÉE : `littoral_pct=1.0` rédhibitoire, 0,15 constructible).
- **Garde-fou attrapé en recette** : un `:ppr_red` resté dans un COMMENTAIRE SQL de `_GREVE_CERTAINE`
  était lu par SQLAlchemy comme un bind manquant (les `text()` parsent `:nom` même en commentaire `--`) →
  corrigé (colon retiré) ; sans quoi tout le chemin résiduel « legacy » tombait.
- **Lint** : `ruff` — 0 erreur introduite (`ppr.py` et `test_ppr_unique.py` nets ; le reste = dette de
  style pré-existante, identique avant/après par `git stash`).

## Fichiers touchés

Backend : `ppr.py` (neuf), `models.py` (fonction SQL + registre), `implantation/terrain.py`,
`faisabilite/db.py`, `faisabilite/engine.py`, `gabarit/builder.py`, `api/servitudes.py`,
`exports/robinet_fiche.py`, `exports/miroir.py`. Front : `fiche/Fiche.tsx`, `outils/blocB.tsx`.
Tests : `test_ppr_unique.py` (neuf), `test_servitudes.py`, `gabarit/test_builder.py`.
Recette : `docs/audit-2026-11/ppr-unique-1/` (scripts + résultats JSON + ce compte-rendu).

## Ce qui n'a PAS été touché (et pourquoi)

- **Le scoring en cascade** (`cascade/layers/phase1.py`, `cascade_rules.yaml`) n'est pas re-joué : le
  run servi `q_v20` est figé et le mandat n'ouvre pas de re-scoring. Les surfaces d'AFFICHAGE (fiche,
  Étude, Gabarit, Pièges, PDF) lisent désormais la classification unique **en direct** — donc le `i`
  est corrigé **sans** re-run. Un prochain run de scoring pourra adopter `labuse_ppr_couleur` pour
  aligner la couche `risques` (geste séparé, hors mandat).
