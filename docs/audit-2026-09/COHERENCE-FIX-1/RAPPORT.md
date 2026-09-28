# COHERENCE-FIX-1 — les FAUX-CLIENT corrigés à la racine, le banc rendu permanent

**Branche** `fix/coherence-1` · worktree `labuse-coherence` · 28/09/2026 · ports 8605/5805 ·
base de test dédiée `labuse_test_coherence`. Base : l'audit COHERENCE-1 (283 écarts dont
6 FAUX-CLIENT, `docs/audit-2026-09/COHERENCE-1/`). **ALGO-FIX-1 mergée dans main pendant le
mandat** : le mécanisme de reconstruction post-bascule (planifier/enchaîner/« À faire »,
bandeau carte) est RÉUTILISÉ, pas dupliqué — `labuse rebuild` devient le point d'entrée
unique et la bascule l'appelle.

## Le banc avant / après

| Mesure | Avant (audit, 28/09 matin) | Après (ce mandat) |
|---|---|---|
| Banc --echantillon (3 244 comparaisons) | **283 écarts** : 6 FAUX-CLIENT · 251 INCOHÉRENT · 26 TOLÉRABLE | **188 écarts (3 161 comparaisons)** : **0 FAUX-CLIENT** · 166 INCOHÉRENT · 22 TOLÉRABLE |
| Aléa mouvement de terrain (24 communes) | 23/24 fausses (0,1 % au lieu de 87-100 %) | 0 écart sur 24 (cache = recalcul géométrique) — 22 communes ≥ 87,9 %, Le Port 7,0 % et Saint-Denis 0,1 % conformes à LEUR vérité |
| Tuiles vs fiche (SDP résiduelle, île) | 98 004 parcelles divergentes | 0 divergence (tuile = vue = fiche — règle M125 appliquée aux tuiles, voir « banc après ») |
| « 999 % » servis (parcel_residuel) | 2 304 taux / 4 302 pct à 999 | 0 sentinelle (reste 6 vraies valeurs ≈ 999 recalculées) |
| Compteurs Filtre vs Stats (Saint-Paul) | 51 005 ≠ 51 129 | 51 005 = 51 005 (définition unique « filtrables », note Sources) |
| idus vs compte (flags=ravine, même réponse) | 13 972 ≠ 13 970 | 13 970 = 13 970 |
| Somme des tiers vs total | 40 405 ≠ total | tiers = total (declasse_* repliés dans « écartée ») |
| Habitants (oracle population légale) | 10/24 communes 5-8 % sous la légale | 24/24 VRAI (population légale 2023 servie) |

Note de mesure : un premier rejeu du banc « avant » ce jour est tombé sur le **quota
anti-scraping** (300 fiches/jour, `protection.py`) — 1 976 lignes « erreur lecteur »
(`mesures/ECARTS-rejeu-quota429.csv`). Le « avant » de référence reste celui de l'audit
(chiffres figés au commit). Correctif racine : le banc se joue contre une API en
`LABUSE_DEV_MODE=1` (dev) ou via `LABUSE_COHERENCE_API` (job nocturne, API locale du
serveur) ; le journal du banc compte désormais les « erreur lecteur » À PART et un passage
illisible est un ÉCHEC bruyant, jamais un vert par vacuité (`coherence_journal.py`).

## Lot A — la fraîcheur des caches (cause de ~70 % des écarts)

**La clé** (`src/labuse/fraicheur_caches.py`) : tout cache porte l'empreinte de ses
dépendances — run servi (`runs.current()` + cascade), run résiduel servi
(`residuel_runs.is_served`, la vérité ALGO-FIX-1), millésimes des sources
(`data_sources.source_millesime`, hash), version du code (sha). Une dépendance bouge →
l'entrée est invalide.

- `commune_contexte_cache` : colonne `cle_fraicheur` par ligne ; **l'endpoint vérifie la clé
  à la lecture et recalcule/re-stocke** une ligne périmée (seul le premier lecteur paie
  ~20 s) — correctif racine du FAUX-CLIENT n° 1 (aléa mvt servi 5 mois périmé sans le dire).
- tuiles : prédicat de péremption **UNIQUE** `tiles.tuiles_etat()` (run ≠ servi, **résiduel
  seq au build ≠ servi** — la clé attrape un `residuel-serve` vers un run plus ancien que
  les dates ne voient pas —, amont recalculé), partagé par `/map/tiles/meta` (bandeau carte
  ALGO-FIX-1), l'onglet « À faire » et `/sante/fraicheur`. `rebuild_mvt_servies` stampe
  `mvt_meta.residuel_seq`.
- `ia_cache` (fiche_ask + explication faisabilité) : l'empreinte entre dans la CLÉ de ligne
  (`run+empreinte`) — auto-invalidant, les vieilles réponses ne sont plus jamais resservies.
- `spatial_layers_sub` : garde existante (max(lid)) exposée au même contrôle.

**Le geste unique** : `labuse rebuild [--dry-run] [--force]` — régénère ce qui est périmé
(spatial_layers_sub → geste M48 build-mvt + tiles-warm + servitudes → fiche commune 24).
Appelé automatiquement par : la **bascule scoring** (dashboard — la stratégie ALGO-FIX-1
planifier/enchaîner décide, le geste détaché devient `labuse rebuild`), **`residuel-serve`**
(détaché, log dans /tmp), **`deploy.sh`** (rebuild + fumée). `--dry-run` = **test de fumée** :
liste chaque cache clé attendue / clé réelle et sort en erreur si un cache est périmé.

**Le contrôle** : endpoint admin **`/sante/fraicheur`** ; la page Données (onglet Sources)
affiche « Fraîcheur des caches » avec chaque cache **« périmé » en rouge** + le remède.

Régénération jouée ce jour : spatial_layers_sub 1 548 388 pièces · mvt_parcels 431 663 + 26 tuiles z9-11 pré-chauffées · fiche commune 24/24 · fumée `--dry-run` VERTE (5 caches à la clé attendue). La matérialisation des SERVITUDES (`parcel_couche_intersection`, poste indépendant du geste, ~heures par tranches) a été interrompue pour ne pas sérialiser la recette : la fiche sert les servitudes par le REPLI au calcul au vol (comportement documenté VITESSE-FIX-1) — relancer `labuse build-intersections` au calme.

## Lot B — densité consommée : plus de « 999 % », plus de zéro-pour-absence

- `residuel.py` : le plafond `min(999, …)` est RETIRÉ ; dénominateur manquant → **None**
  (jamais 0) ; `sous_densite` suit (None si taux inconnu) ; le libellé dit « > 300 % » ou
  « non calculable ».
- **Seuil d'affichage 300 %** (défini avec le rapport : 17 880 parcelles > 300, le chiffre
  exact n'apporte rien au-delà) : partagé back (`fmt_pct_consomme`,
  `SEUIL_PCT_AFFICHAGE = 300`) et front (`format.ts fmtPctConsomme`) — fiche (§Potentiel +
  Règles), Comparer, Dossier (blocs potentiel + verdicts), Copilote (le fait cité est celui
  que le client voit).
- **Colonne servie recalculée SANS run île** : les valeurs exactes étant PERDUES en base
  (emprise_max/sdp_max non stockés — constaté, le « depuis les colonnes existantes » du
  mandat était impossible au sens strict), les 4 947 lignes à 999 du run servi (seq 10) ont
  été recalculées par le MOTEUR parcelle par parcelle (`scripts/coherence/fix_999_seq10.py`,
  266 s) : **4 634 valeurs exactes réécrites**, **313 passées à NULL** (parcelles devenues
  indisponibles au moteur du jour — valeur du plafond inconnaissable, on le dit au lieu de
  servir 999), 6 valeurs ≈ 999 réelles conservées.
- `DISTRIBUTIONS.csv` rejoué : 0 alarme (les deux colonnes déclarées « %>100 », ratio à dépassement légitime) ; max 41 374 / 42 878 % (vraies valeurs extrêmes, affichées « > 300 % ») ; part de nuls 39,4 % = part réelle d'absence

## Lot C — les compteurs disent tous le même nombre

Trois causes trouvées (mesurées à l'audit) et corrigées dans `_q_v2_stats` / `/filtre` :

1. **Slivers** : `/filtre` excluait les slivers < 2 m² (FIX-FILTRES F2), `/stats` non →
   Saint-Paul 51 005 ≠ 51 129. `exclure_slivers=True` devient le **défaut** partout :
   UNE définition du « nombre de parcelles » = « parcelles filtrables » (RETOURS-14 P6,
   note Sources).
2. **Requête idus** : le masque slivers manquait au SELECT idus du même endpoint →
   13 972 idus vs compte 13 970 **dans la même réponse**. Ajouté.
3. **Tiers `declasse_*`** : six tiers non repliés → somme 40 405 ≠ total. `declasse_%` se
   replie dans « écartée » (son sens produit) : la ventilation somme au total.

Oracles du banc (`aggregats.py`) réécrits à la **définition déclarée** (arrondi
`round(surface)` — la valeur que la fiche affiche — + masque slivers) : un oracle qui
recompte une autre définition ne mesure pas une incohérence. Vérifié en live :
Saint-Paul filtre=stats=51 005, ravine compte=idus=13 970, tiers=total.
10 combinaisons rejouées : 13/13 OK (10 compteurs + prédicat=fiche 20/20 + bande liste=fiche 15/15 + zone)

## Lot D — absence ≠ zéro, partout

Sites corrigés (chaque `?? 0`/`or 0` de l'audit **justifié ou retiré**) :

| Site | Avant | Après |
|---|---|---|
| `MonSecteur.tsx` | médiane nulle → « 0 €/m² » | « — » |
| `ProfilAltimetrique.tsx` (×6) | « 0 m » / « 0 % » | « — » |
| `Licences.tsx` fmtEur | « 0,00 € » | « — » |
| `moteurs.py` part habitat ZAN | habitat NULL → « 0 % » | None (« — ») |
| `fiche_couches2.py _pct` | coverage NULL → « < 1 % » | « part non mesurée » |
| `financier_bilan.py` | surfaces/logements `or 0` → postes à 0 € | None → « non chiffré » ; `maximum` couvre TOUT poste non chiffré |
| `miroir.py` | « 0 ménages » | mention omise si absente |
| `ResultsSection.tsx` cluster, AdminView KPIs | `?? 0` | **justifiés** : gardes de flux (le zéro n'est pas affiché comme valeur) — documenté ici |
| `_ca_ht` part_sociale `or 0` | — | **justifié** : une part sociale non déclarée EST une part nulle (sémantique) |

**Vocabulaire d'absence** : les 178 phrases déclarées tiennent désormais dans **5 formes**
définies au registre (`src/labuse/registre/absences.py`) : `non_disponible` (72) · `aucun`
(66) · `hors_perimetre` (38) · `non_calculable` (17) · `sans_objet` (1) — mesuré 0 phrase
hors vocabulaire, verrouillé par V6b. Idiomes d'écran : « — » partout (format.ts) ; « n.c. »
reste réservé à la sentinelle SIRENE 1900 (sens spécifique documenté) ; « non chiffré » est
la forme PDF de `non_disponible` (postes financiers).

## Lot E — population : bon millésime, année affichée

Nouvelle source servie `population_legale` (ingestion `population_legale.py`, CLI
`labuse population-legale-sync`, ~2 s) : populations municipales **LÉGALES en vigueur**
(geo.api.gouv/INSEE), millésime stocké (2023) et déclaré à `data_sources` (il entre dans la
clé de fraîcheur du lot A). La fiche commune sert « **Population légale 2023 (INSEE)** »
(étiquette `habitants_etiquette` + année dans le chip « INSEE 2023 » du bandeau) ; Sudocuh
devient le REPLI avec SON millésime affiché ; `pop_totale` n'est plus mélangée entre
millésimes. Le Dossier (quartier IRIS) affiche aussi le millésime du recensement ; l'Étude
de zone affichait déjà le sien (Filosofi 2021). Oracle habitants rejoué : 24/24 VRAI

## Lot F — les 19 FAUX de VERITE.csv, tranchés un à un

| FAUX | Cause | Décision |
|---|---|---|
| 11 × habitants_n | millésime Sudocuh en retard sur la légale | **corrigé** (lot E) — oracle 24/24 VRAI |
| catnat_n Saint-Joseph 20 vs 21 | **GASPAR sert l'arrêté INTE1401216A EN DOUBLE** (2 lignes, même code national/date, date_fin_evt 02 vs 03/01/2014) ; l'upsert LABUSE dédoublonne | **justifié** (LABUSE avait juste) + **oracle corrigé** : compte les arrêtés DISTINCTS (code, risque, date) |
| 2 × surface (AD0527 99↔83, AV0152 93↔87) | contenance cadastrale PCI ≠ aire géométrique sur micro-parcelles (< 100 m²) | **justifié** : LABUSE sert l'aire géométrique (source PCI géométrie, règle documentée) ; l'oracle mesure la contenance déclarative — deux grandeurs, écart connu sur les petites parcelles |
| zone AM0515 N↔U | parcelle à cheval : dominante N (54,1 %) / Ub (45,9 %), centroïde en Ub | **justifié** : LABUSE attribue à la SURFACE DOMINANTE (règle produit affichée) ; l'oracle au centroïde mesure un point |
| 5 × Saint-André « U » vs GPU ∅ | **le GPU ne sert AUCUN document au point** (zone-urba ET document vides sur DU_97409 — trou de publication GPU, vérifié au centroïde d'AH0155) ; LABUSE sert le zonage OPPOSABLE ingéré (partition DU_97409, géométries valides) | **justifié** (limite oracle) — la sonde sources verra la republication GPU (millésime) |

**Règle PLU « 29/30 »** : la 30ᵉ (Saint-Denis Uj recul_limites, Art. Uj.7 p.61) n'était PAS
une règle introuvable — l'oracle avait échoué sur un téléchargement tronqué (curl 92,
HTTP/2). Re-vérifiée ce jour au PDF direct des annexes GPU : les nombres (4 m min, 18 m,
h/2) **se lisent p.61**. Ni recalibrage ni passage « propose » : la règle est bonne, 30/30.

## Lot G — le banc devient permanent

1. **`labuse coherence`** (+ `--ile`, `--comparer`, `--accepter`) — alias CLI du banc ;
   `lib.py` lit désormais l'API (`LABUSE_COHERENCE_API`), le DSN (`LABUSE_DATABASE_URL`) et
   le run servi (`runs.current()`) de l'environnement — plus de littéraux figés.
2. **Verrou V6b** (circuit_verrous + `tests/verrous/test_v6b_coherence.py`, marque
   `verrous`, joué à chaque commit et par `labuse circuit verrous`/deploy) : tables de
   vérification bien formées (tolérance + ≥ 2 lecteurs ou croisement déclaré), vocabulaire
   d'absence 5 formes, **règle du registre** (toute donnée sans lecteur déclaré ni chantier
   `en_attente` casse — le référentiel du banc est dérivé, un chiffre nouveau est couvert
   automatiquement), **golden rejoué** via l'app EN-PROCESS (TestClient — mêmes lecteurs que
   le banc, `Contexte(fetch=…)`) ; en pytest il joue sur la base de TEST du process, jamais
   la vraie base ; témoin hors base = dit, pas cassé. Trouvailles à la pose : 2 checks
   commune mono-lecteur (croisés — règle affinée), 2 données registre sans lecteur
   (mixite_* : `en_attente` EXPORTS-2, exemptées dites).
3. **Job nocturne `coherence-banc`** (registre CRON, 23:45 UTC = 03:45 Réunion, après le
   cache fiche commune) : banc `--ile` contre l'API locale, résumé dans `coherence_runs`
   (`coherence_journal.py`), **onglet « Cohérence »** page Données (passages, écarts par
   gravité, erreurs lecteur, golden posés), **cloche admin au premier FAUX-CLIENT NOUVEAU**
   (diff par (notion, objet) vs passage précédent — un écart connu ne re-sonne pas).
4. **Golden** : 7 témoins (`tests/golden/coherence/*.json`, `scripts/coherence/golden.py`) —
   la valeur du premier lecteur (l'écran client) de chaque notion des checks ; toute dérive
   non acceptée casse V6b ; acceptation = `labuse coherence --accepter` (motif au commit).
5. **Règle du registre** : cf. V6b (2) — mesurée verte à la pose après affinage.

## Les 188 écarts restants (instruits, aucun FAUX-CLIENT)

| Famille | n | Statut |
|---|---|---|
| « Secteur » multi-périmètres (fiche fenêtre 2021-25 vs Mon secteur rayon adaptatif) | 96 | ÉTIQUETTE de l'audit — deux VRAIS chiffres, le libellé de la fiche ne dit pas son périmètre. Hors lots du mandat (aucun des lots A-G ne le couvre) — reste la première matière d'un COHERENCE-FIX-2. |
| Emprise bâtie fiche (clippée/arrondie) vs `p_model_bati` (brute) | 72 | « À trancher par une définition unique » (audit) — arbitrage produit non couvert par le mandat, documenté. |
| Surfaces fiche arrondies vs float (< 1 %) | 6 | TOLÉRABLE (arrondi documenté). |
| Vigilances 50 pas fiche (live) vs `parcel_flags` (run) | 5 | Rejeu de cascade postérieur à la bascule (audit) — hors lots. |
| Prix neuf `comparable` (live O8) vs `prix_neuf_observe` (bloc caché) | 4 | Deux moteurs dans un même payload — hors lots, matière FIX-2. |
| Copro fiche (`coproprietes`) vs RNIC (`p_model_ext_copro`) | 3 | La fiche ne lit pas le RNIC — hors lots (cité par l'audit en « matière », pas au mandat). |
| Taxe d'aménagement 20 %/14 % (secteur majoré) vs taux commun commune | 2 | ÉTIQUETTE (audit) : le taux de droit commun sans « hors secteurs majorés ». |

Trois correctifs de BANC faits en instruisant l'« après » (le banc aussi doit être vrai) :
le cache disque des tuiles décodées est clé par processus (l'ancien `/tmp/coherence_tile_z_x_y.pbf`
survivait à un rebuild → le banc mesurait des tuiles périmées) ; les lecteurs SQL
`sdp_residuelle`/`sous_densite` appliquent la règle M125 des lecteurs vivants (`cause IS NULL`) ;
le lecteur habitants lit `population_legale` (la définition servie). Et UN correctif produit :
`build_mvt_table` applique la MÊME règle M125 (une ligne à cause — terrain_exigu… — ne bake plus
son « 0 » dans la tuile pendant que la fiche dit « non calculée ») — c'était les 6 lignes
FAUX-CLIENT « ∅ contre 0 » résiduelles.

## Vérifications

- pytest complet (base `labuse_test_coherence`) : 3 474 P · 7 échecs PRÉ-EXISTANTS hors périmètre (test_circuit2_lot6 — commentaire EXPORTS-FIX-1, fichier non touché ; test_retours11f3 ×2 — dépendants de l'ordre, verts isolés ET verts joués après les tests de ce mandat ; test_garanties g3/g4/g7 ×4 — famille état de base connue TESTS-FIX-1). 12 → 7 : les 5 échecs INDUITS par le mandat (compte jobs 25, compte verrous 24, VERROUS.md, dépendance `scripts`, graphe lectures) ont été corrigés.
- tsc : 0 erreur · vitest : 225/225
- V6b : ok (19 checks parcelle + 19 commune bien formés, vocabulaire 5 formes, registre couvert, golden 7 témoins rejoués)
- `labuse rebuild --dry-run` (fumée) : verte (5 caches à la clé attendue)

## Fichiers

`mesures/` (banc avant/après, distributions), ce rapport. Livrables code : voir les commits
(un lot = un commit).
