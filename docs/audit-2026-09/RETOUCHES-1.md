# RETOUCHES-1 — petits restes des audits (exports, sources, algo)

Branche `fix/retouches-1` (worktree `~/Desktop/labuse-retouches`, base `origin/main` **8c1e38bf**,
API 8655 / front 5855, modèle Opus). Un commit par point, aucun merge. Aucune écriture en base,
aucune réingestion, aucun run.

> ⚠️ **Collision de nom.** Un *précédent* mandat « RETOUCHES-1 » (lots A→D, D.15 SUP au moteur…)
> a déjà été mergé dans `main` ; son rapport vit dans `docs/audit-2026-09/retouches-1/RETOUCHES-1.md`
> (dossier en minuscules). Le présent mandat réutilise le nom de branche mais traite **7 points
> distincts** ; son rapport est ce fichier (`RETOUCHES-1.md`, à la racine de `audit-2026-09/`), ses
> artefacts sous `retouches-1/{avant,apres,captures}/`.

Parcelles témoins : **97408000AO1424** (La Possession, zone A) · **97415000EO0796** (Saint-Paul, U5b).
Parcelle de démonstration du point 4 : **97411000AE0001** (Le Tampon, secteur avec catégorie DVF « autre »).

## Tableau de bord

| # | Constat | Fait / STOP | Preuve | Commit |
|---|---------|-------------|--------|--------|
| 1 | « Généré via LABUSE » coupé sur 3 lignes en pied de page | **fait** | `captures/p1-footer-avant.png` (Généré / via / LABUSE) → `p1-footer-apres.png` (une ligne) ; `p1-planche-bas-de-page.png` = les 9+10 pages des 2 Dossiers, une ligne partout | `f3fb7b5e` |
| 2 | Taxe foncière « part communale 48,68 % · EPCI 0,00 % · TEOM 16,00 % » sans dire ce qui manque | **fait** (+ retouche TEOM) | `p2-taxe-avant.png` → **la même ligne** dans les 3 surfaces : `p2-taxe-dossier-apres.png`, `p2-taxe-fiche-apres.png`, `p2-taxe-copilote-apres.png` | `8ba0d011` · `82911ecd` |
| 3 | Titre Apporteur « Un bien bâti à sonder » sur une parcelle agricole | **fait** | `p3-titre-avant.png` (« Un bien bâti à sonder » sur zone A) → `p3-titre-apres.png` (« Une parcelle agricole à sonder ») | `ef0744ef` |
| 4 | §8 Marché « Autre 215 000 € — 43 ventes » (fourre-tout DVF, prix total) | **fait** | `p4-autre-avant.png` (Appartement/**Autre**/Maison) → `p4-autre-apres.png` (Autre retirée) | `6c53b273` |
| 5 | §1 « Filiation cadastrale : Filiation cadastrale disponible » — annonce vide | **fait** | `p5-filiation-avant.png` → `p5-filiation-apres.png` (« Issue de 97408000AO1402 (document d'arpentage, 12/06/2006) ») | `5e4df172` |
| 6 | Pipeline `flash/` orphelin (SOURCES-FIX-2) — à supprimer | **STOP** | `flash/` est **activement appelé** (voir §Point 6) — non supprimé, non orphelin | — |
| 7 | Servitudes : date d'ingestion non affichée (SOURCES-FIX-2) | **fait** (+ retouche Dossier) | `p7-servitudes-millesime.png` (fiche/outil) ; **au Dossier** §5 `p7-dossier-aleas-avant/apres.png`, §4 `p7-dossier-sup-avant/apres.png` | `ba07355c` · `114709c8` · `6c0e19c6` |

## Détail par point

### Point 1 — pied « Généré via LABUSE » sur une seule ligne — `f3fb7b5e`
**Cause.** La case de marge `@page` `@bottom-left` (feuille `exports/theme.css`) réservait une largeur
fixe `width: 150mm`. Son contenu (`string(doc-foot)`) est pourtant **vide** au rendu (le `string-set`
posé sur un `<span style="display:none">` n'est pas capté par WeasyPrint 69 — constat annexe, hors
périmètre), mais la largeur reste réservée et **écrase** la case `@bottom-center` où la route
`api/dossier.py` injecte la mention → « Généré / via / LABUSE » sur trois lignes.
**Correctif.** On retire le `width: 150mm` (la case s'ajuste à son contenu) et on pose
`white-space: nowrap` sur la mention. Vérifié **toutes pages** des deux Dossiers témoins
(`p1-planche-bas-de-page.png`). Seul le Dossier porte cette mention (l'Apporteur est `marque=False`).

### Point 2 — taxe foncière : un libellé unique, identique fiche/Dossier/Copilote — `8ba0d011`
**Constat.** Le Dossier énumérait « part communale 48,68 % · EPCI 0,00 % · TEOM 16,00 % » : le lecteur
croyait lire la taxe foncière entière, alors qu'il manquait la part départementale (et les taxes
spéciales), et EPCI/TEOM étaient listés comme s'ils s'additionnaient.
**Correctif.** Producteur **unique** `src/labuse/fiscalite_libelle.py::lignes_taxe_fonciere(fisc)` →
« **Taxe foncière (bâti) — part communale X % · TEOM Y % · hors part départementale et taxes
spéciales** » (+ une ligne **non bâti** si la TFPNB est servie). _Retouche de recette (`82911ecd`) :
la TEOM est **réintégrée** — elle était juste et utile, elle ne doit pas être annoncée comme exclue ;
elle s'affiche quand on l'a (bâti seul, jamais sur le non-bâti) et disparaît sinon ; la mention EPCI
à 0 % reste retirée._ La même chaîne alimente :
- le **Dossier** : `exports/miroir.py::_r_tfpb` (valeur) + intitulé `declarations/fiche/sections_restantes.yaml` (« Taxe foncière (bâti) ») ;
- le **Copilote** : `copilote_v2/resume_fiche.py` (réponse `champ_precis` + carte « Fiscalité ») ;
- la **fiche** : bloc fiscalité servi (`api/fiche_commune.py::fiscalite` → `lignes`), affiché tel quel
  par `Fiche.tsx` (`data-tf-ligne`) — **jamais recomposé à l'écran**.

Les trois captures montrent la **ligne identique** (La Possession) :
- Dossier `p2-taxe-dossier-apres.png` · Fiche `p2-taxe-fiche-apres.png` · Copilote `p2-taxe-copilote-apres.png`.

Le **Financier** garde sa présentation chiffrée propre (`blocs/financier.py`, déjà « part
départementale et TEOM en sus » — non trompeuse) ; il n'est pas dans les trois surfaces nommées et son
verrou `test_recette4` reste vert.

### Point 3 — titre Apporteur selon la nature de la parcelle — `ef0744ef`
`exports/blocs/apporteur.py` : le titre suit **la famille de zone AVANT le bâti** — zone A →
« Une parcelle agricole à sonder », zone N → « Une parcelle naturelle à sonder », sinon bâti →
« Un bien bâti à sonder », sinon « Un terrain à sonder ». **Jamais « bâti » sans bâti.** Témoins : La
Possession (zone A, 6 bâtiments) passe de « bien bâti » à « parcelle agricole » (le constat exact) ;
Saint-Paul (U5b, bâti) reste « bien bâti ». Verrous F1 (`test_recette6`, `test_exports2_lot6`) verts.

### Point 4 — §8 Marché : la ligne « Autre » retirée — `6c53b273`
`exports/miroir.py::_r_dvf_liste` : la catégorie **fourre-tout DVF « autre »** (dépendances, locaux,
biens mixtes) est une médiane en **prix total** (pas de €/m², `mediane_prix_m2` absente), sans surface
comparable aux lignes maison/appartement/terrain. La fiche ne l'affiche **jamais** (`marche.tsx` ne
rend que terrain/maison/appartement) ; on la retire du Dossier pour la même raison — cohérence
**fiche == Dossier**. Vérifié sur 97411000AE0001 : « Autre 215 000 € — 43 ventes » disparaît, Maison
et Appartement (au m²) restent.

### Point 5 — filiation cadastrale : la filiation elle-même — `5e4df172`
`exports/miroir.py::_r_filiation` : le rendeur retombait sur le libellé par défaut « Filiation
cadastrale disponible » car la valeur est un **dict** mères/filles (jamais une liste). On rend
désormais la filiation elle-même — « **Issue de** ‹parcelle› (nature, date) » pour les mères,
« **A donné** … » pour les filles — comme le fait déjà la fiche (`FiliationBlock`, FICHE-FIX-4). Sans
mère ni fille exploitable, la valeur est vide → la ligne bascule en « Non disponible ici » (absence
déjà déclarée « aucune filiation connue »). Témoins : La Possession « Issue de 97408000AO1402
(document d'arpentage, 12/06/2006) », Saint-Paul « Issue de 97415000EO0653 (document d'arpentage
numérique, 27/01/2014) ».

### Point 6 — pipeline `flash/` — **STOP** (encore appelé)
Le mandat : « supprimé après avoir vérifié qu'aucun export ni écran ne l'appelle. S'il est encore
appelé quelque part : STOP, et le dire. » → **STOP.** Le module `src/labuse/flash/`
(`carte.py`, `data.py`, `report.py`) n'est **pas orphelin** ; il est appelé par du code de production :

| Appelant | Symbole importé de `flash/` | Rôle |
|---|---|---|
| `api/pre_dossier.py` (l. 269, 791) | `flash.data.collect_report_data` | données du **Pré-dossier PC** (export ZIP) |
| `api/plan_situation.py` (l. 22, 61) · `api/partners.py` (l. 388) | `flash.carte.build_situation_map`, `IGN_ORTHO_*` | **plan de situation** (Dossier / partenaires) |
| `exports/builder.py` (l. 378) · `facturation.py` (216, 285) · `api/division_review.py` (132) · `api/pre_dossier.py` (599) | `flash.report.storage_dir` | résolveur du dossier de **tuiles / PDF** |
| `marche_service.py` (126, 128) | `flash.data._marche`, `_existing_tables`, `_NEEDED_TABLES` | médianes de marché |
| `api/dossier.py` (49) | `import labuse.flash` | sonde de disponibilité du générateur |

Ce que SOURCES-FIX-2 (row 74) qualifiait d'« orphelin » disait aussi qu'il « **survit via le
pré-dossier** » : c'est exactement le cas — le supprimer casse le Pré-dossier PC, le plan de situation
et le stockage des exports. **Aucune suppression** ; aucun commit pour ce point.

### Point 7 — servitudes : millésime depuis `data_sources.source_millesime` — `ba07355c`
`api/servitudes.py` : la « date » des servitudes et aléas était la seule **date d'ingestion**
(`COALESCE(last_sync_at, updated_at)`). Elle passe au **millésime de la source**, composé par le
**producteur unique** `millesime_source.composer` (le même que la fiche §Sources et les pieds
d'export) depuis `data_sources.source_millesime` — le magasin unique posé par SOURCES-FIX-2. Repli sur
la date d'ingestion quand une source n'a pas de millésime amont publié (la promesse « chaque servitude
datée » tient). Corrigé dans les deux fonctions partagées `contraintes_parcelle` et `aleas_parcelle`,
donc sur les **trois surfaces** (outil Risques, fiche §Pièges & risques, union « un lot »).
Témoin La Possession (`p7-servitudes-millesime.png`) : DEAL PPR « PPR/PPRL approuvés 2011–2026 »,
Cerema « arrêtés déc. 2023 », PLU/GPU « révisions » ; SUP assiettes GPU (sans millésime amont) →
repli sur la date d'ingestion.

**Retouche de recette (`114709c8`) — le millésime au Dossier.** Le premier correctif ne touchait que la
fiche et l'outil ; **aucun millésime n'apparaissait dans les deux Dossiers**. Le §12 « Limites et
sources » masque volontairement tout millésime (décision EXPORTS-2 lot 2), donc on l'imprime **sur la
ligne**, là où le lecteur regarde :
- **§5 Risques** (`miroir._r_aleas`) : « …niveau moyen · millésime PPR/PPRL approuvés 2011–2026 (DEAL
  Lizmap) » — la donnée est déjà composée par `servitudes.aleas_parcelle` ;
- **§4 Urbanisme, SUP** (`miroir._r_sup`) : « 1 servitude — PM1 … · ingéré le 14/09/2026 » — après
  jonction de `data_sources` aux deux requêtes `_DISPOSITIFS_SQL(_MAT)` et composition dans
  `_dispositifs_block`.

**Retouche de recette (`6c0e19c6`) — nommer le repli.** Le mot « **millésime** » est RÉSERVÉ aux
dates **publiées en amont** par la source ; quand seule la date d'ingestion existe (l'assiette SUP GPU
n'a pas de millésime amont), on écrit « **ingéré le JJ/MM/AAAA** », jamais « millésime ». Un producteur
unique `millesime_source.libelle_date_source(source_millesime, source_horizon_at, ingere_le)` rend le
libellé nommé (« millésime <X> » sinon « ingéré le <JJ/MM/AAAA> »), utilisé **partout où ce repli
sert** : `servitudes.aleas_parcelle` / `contraintes_parcelle` (fiche, outil), `_dispositifs_block`
(Dossier §4). Les rendeurs `_r_aleas` / `_r_sup` impriment ce libellé verbatim. Témoin La Possession :
aléa PPR « millésime PPR/PPRL approuvés 2011–2026 (DEAL Lizmap) », SUP PM1 « ingéré le 14/09/2026 »
(assiette GPU sans millésime amont). Verrou `test_servitudes` mis à jour (repli nommé).

Captures : §5 `p7-dossier-aleas-avant.png`→`…-apres.png`, §4 `p7-dossier-sup-avant.png`→`…-apres.png`,
table `p7-servitudes-millesime.png`.

## Vérification (verrous)

| Verrou | Résultat |
|---|---|
| `tsc -b` (frontend) | **0 erreur** |
| `vitest run` | **225 passés** (50 fichiers) — baseline |
| Mots interdits des exports (`config/mots_interdits.yaml` sur les 4 PDF `apres/`) | **aucun** |
| pytest ciblé (exports/miroir/dossier/apporteur/filiation/marché/servitudes/risque/copilote/fiscalité) | **verts** (voir §détail des runs) |
| Verrous « mots interdits » (`test_exports2_lot1/2/5/6`, `test_recette12_d5_sources`, `test_circuit2_lot0bis`, `test_front_chiffres_orphelins`) | **60 passés** |
| Banc de cohérence `--echantillon` | _(voir ci-dessous)_ |

**Banc `--echantillon`** (API 8655, `LABUSE_COHERENCE_API=http://127.0.0.1:8655`, `LABUSE_DEV_MODE=1`) :
3 161 comparaisons · **188 écarts** (166 INCOHERENT + 22 TOLERABLE) — **exactement la baseline
documentée (188)**. Aucun écart nouveau introduit par les 7 points. (⚠️ sans
`LABUSE_COHERENCE_API`, le lecteur `fiche:` du banc tape le port 8000 par défaut et rend « Connection
refused » sur toutes les notions : ce n'est pas un écart de donnée, c'est l'API de référence non
branchée — piège d'environnement, pas de régression.)

**Runs pytest ciblés** (base réelle, `PYTHONPATH=src`, venv `~/Desktop/labuse/.venv`) :
- `-k "miroir or filiation or dossier"` → 29 passés / 3 skip ;
- `-k "marche or dvf or miroir"` → 83 passés / 9 skip ;
- `-k "apporteur"` + `test_recette6` + `test_exports2_lot6` → 16 passés ;
- `-k "servitude or risque or piege or alea or duedilig"` → 60 passés / 4 skip ;
- `-k "tfpb or fiscal or taxe or copilote or resume or fiche_commune or miroir"` → 216 passés / 5 skip.

## Fichiers touchés

| Point | Fichiers |
|---|---|
| 1 | `src/labuse/exports/theme.css`, `src/labuse/api/dossier.py` |
| 2 | `src/labuse/fiscalite_libelle.py` (nouveau), `src/labuse/api/fiche_commune.py`, `src/labuse/exports/miroir.py`, `declarations/fiche/sections_restantes.yaml`, `src/labuse/copilote_v2/resume_fiche.py`, `frontend/src/components/fiche/Fiche.tsx`, `frontend/src/lib/types.ts` |
| 3 | `src/labuse/exports/blocs/apporteur.py` |
| 4 | `src/labuse/exports/miroir.py` |
| 5 | `src/labuse/exports/miroir.py` |
| 7 | `src/labuse/api/servitudes.py` (fiche/outil) · `src/labuse/exports/miroir.py` + `src/labuse/api/app.py` (millésime au Dossier §4/§5, retouche) |

Outillage de recette (non produit, sous `scripts/`) : `retouches1_gen.py` (génère les 4 PDF par
les vraies routes, TestClient, `carte=false`) et `retouches1_crop.py` (recadrage des bandes par
`pdftotext -bbox`).
