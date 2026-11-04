# ECARTS-ZERO-1 — compte-rendu

> Branche `fix/ecarts-zero-1`, worktree `~/Desktop/labuse-ecarts`, Opus. Base Mac `labuse`
> (run servi `q_v20`), **aucun merge, aucun accès prod**. Lecture seule sur la base ; aucune
> écriture (le banc lit, ne modifie rien). Sessions voisines respectées : **ni Copilote, ni John,
> ni vigies/tableau de bord touchés** (leurs compteurs « écarts connus » retombent à 0 d'eux-mêmes,
> cf. §4).

## Décision de Vic appliquée

« Aucun écart n'est tolérable, même d'un euro ou d'un mot. Un fait a une seule fonction de lecture,
un seul arrondi, un seul format, partout. » Traduction concrète dans le banc de cohérence :

1. **La gravité « TOLERABLE » n'existe plus.** `scripts/coherence/lib.py` : le dégradé
   `arrondi → TOLERABLE` est retiré de `Ecarts.noter`. Tout écart est désormais **rouge**
   (INCOHERENT) ou FAUX-CLIENT. L'arrondi reste une *cause* lisible, jamais une excuse.
2. **Plus de marge floue.** La « tolérance » d'une vérification ne dit plus *combien on tolère*
   mais la **précision d'affichage du fait** (le nombre de décimales de son arrondi unique) :
   `"0"`/`"0 (entier)"` = l'entier (m², €, compte) ; `"1"` = une décimale (hauteur, pourcentage).
   On arrondit les deux lecteurs à cette précision puis on exige l'**égalité stricte** : une
   différence d'un m² / d'un euro / d'un dixième est rouge ; le bruit flottant *sous* l'unité
   affichée (float32 d'une tuile, `ST_Area` recalculé) n'est jamais montré à l'écran, donc n'est
   pas un écart *entre deux écrans*.
3. **L'arrondi se fait une seule fois, au point de calcul / au bord.** La fiche sert la surface
   BRUTE (plus de `round()` dans le producteur) ; l'arrondi d'affichage passe par `lib/format`
   `fmtM2` (écran) et `registre_fmt.fmt_m2` (PDF).

## Le banc avant / après (120 parcelles + 24 communes, 12 témoins)

| | écarts | dont TOLERABLE | dont INCOHERENT/FAUX-CLIENT |
|---|---:|---:|---:|
| **Avant** (tol floues + TOLERABLE) | **153** | 87 | 66 |
| **Après** (précision affichée, 0 toléré) | **_(voir §5)_** | 0 | _(voir §5)_ |

Le « 153 » du résumé du matin et le « 87 » toléré du tableau de bord **sont ce chiffre** : la sortie
du banc sur les 120 parcelles, classée par gravité. Les corriger à la source les fait tomber
ensemble (cf. §4).

## Les causes → les correctifs (à la source, jamais écran par écran)

| Cause | Écart (avant) | Correctif à la source |
|---|---|---|
| **Arrondi hors point de calcul** | 63 `surface_parcelle_m2` TOLERABLE : la fiche arrondissait `surface_m2` (int) alors que la tuile/SQL la servent brute | `app.py:5053` — la fiche sert `surface_m2` **brute** ; l'arrondi se fait au bord (`fmtM2`/`registre_fmt`). Banc : comparaison à la **précision affichée** (le m²), plus de bruit flottant. |
| **Deux notions sous un même mot (surface)** | 109 `fiche:surface_m2` (dessin géométrique) ≠ `tuile:surface_m2` (contenance cadastrale `round(COALESCE(contenance,surface))`) | Banc : **scission en deux faits** — `surface_terrain_m2` (contenance servie = fiche `surface_terrain_m2`, SQL `COALESCE(contenance_m2,surface_m2)`, tuile) et `surface_dessin_m2` (géométrique). Chacun a une valeur unique, vérifiée chez tous ses lecteurs. |
| **Double calcul (copropriété)** | 3 `copro_presente` : fiche (liste RNIC) ≠ `p_model_ext_copro` (flag SCORING `copro_rnic OR copro_dvf`, copro inférée par mutations DVF) | Banc : le lecteur jumeau lit le **même producteur que la fiche** (`rnic_coproprietes` par `parcelle_idu`). Le signal DVF inféré reste interne au scoring, jamais servi comme « copropriété » au client. |
| **Deux notions sous un même mot (prix du neuf)** | 3 `prix_neuf_eur_m2` : `comparable.neuf` (VEFA déclaré) ≠ `prix_neuf_observe` (reventes observées ≤3 ans) | Banc : **suppression de la comparaison croisée** (C3-03) — deux faits distincts, étiquetés comme tels, un producteur chacun. |
| **Deux champs différents (taxe)** | 2 croisements `taxe_amenagement_taux_communal_pct` : fiche `taux_parcelle` (secteur à taux MAJORÉ 20 %) ≠ commune `part_communale_pct` (taux de base 3 %) | Banc (`banc.py` passe_croisements) : on **ne croise pas** quand la fiche indique `taux_communal_secteur_majore=true` (fait distinct, étiqueté « Secteur à taux majoré »). Hors secteur majoré, le croisement tient à 0. |
| **Définition divergente (compte parc)** | 24 `n_parcelles_commune` : servi = parc VIVANT (`cadastre_disparue_le IS NULL`), jumeau = tout | Banc : le jumeau applique le **même filtre vivant** (CHASSE-DONNEES-FIX-1). |
| **Jumeau mal défini (classement)** | 22 `tiers_hauts_n` : servi = 4 tiers {brulante,chaude,priorite,a_suivre} vivants ; jumeau = 2 tiers sans filtre → 0 partout | Banc : jumeau aligné sur `app._communes_data` (4 tiers + filtre vivant + run courant). |
| **Arrondi (pourcentage SRU)** | 15 `deficit_sru_pts` : 22,1 servi vs 22,06 recalculé | Banc : précision affichée = **une décimale** (`"1"`) ; les deux arrondis au dixième coïncident. |
| **Jumeau sans garde (hauteur)** | 6 `hauteur_faitage_m` : fiche ∅ (pas de bâti significatif) vs jumeau `max(faitage)` d'un abri <10 m² | Banc : le jumeau applique la **même porte de significativité** que la fiche (bâti BD TOPO ≥ 10 m²) et l'arrondi unique au dm. |
| **Lecteur trop étroit (vigilance)** | 5 `vigilance_cinquante_pas` : fiche `flags[]` (poids 0 seulement) ≠ carte `parcel_flags` (tout SOFT_FLAG) ; cinquante_pas = SOFT_FLAG poids −5 | Banc : le lecteur fiche lit `lines` (toutes les lignes cascade servies) avec le **même crible que la carte** (SOFT_FLAG \| abf/UNKNOWN). Vigilance présente des deux côtés. |
| **Précédence du scoring (SDP) — fiche vs SQL** | 6 `sdp_residuelle_m2` : fiche ∅ (parcelle hors_classement : forêt publique/inacquérable) vs SQL 77 | Banc : le jumeau SQL applique les **deux portes de la fiche** (cause résiduelle **et** cause `score_labuse`). |
| **Précédence du scoring (SDP) — fiche vs TUILE** | 6 `sdp_residuelle_m2` : fiche ∅ vs **tuile** 77 (la tuile matérialisée n'applique que la porte résiduelle) | **Source** : `tiles.py:243` — le builder MVT applique désormais la **même double porte** (résiduelle + scoring). Prend effet au prochain `rebuild_mvt_servies` (bascule / `labuse build-mvt`). _(cf. §5 : matérialisation)_ |

## 4. Les « écarts connus » du résumé du matin et le « toléré » du tableau — sans y toucher

Le compteur « écarts tolérés » du tableau de bord (`dashboard.py`) et le « N écarts connus » du
résumé du matin (`cockpit_resume.py`) lisent la colonne `coherence_runs.tolerable`, que
`coherence_journal.journaliser_passage` remplit en comptant les lignes de gravité **TOLERABLE**.
Comme cette gravité **n'est plus jamais assignée** (§1), tout passage de banc ultérieur journalise
`tolerable = 0` → le tableau et le résumé affichent **0** d'eux-mêmes. Aucune ligne de leur code
(session vigies/tableau) n'a été modifiée : la liste d'acceptation se vide **à la source**.

De même, aucune « liste d'acceptation SILENCE-1 » n'est lue par le banc : sa seule tolérance était
le dégradé TOLERABLE + les marges floues des vérifications, tous deux supprimés.

## 5. Recette

**Banc de cohérence (120 parcelles + 24 communes, EN-PROCESS)** : **153 → 6 écarts, 0 toléré.**
Les 6 restants sont tous `sdp_residuelle_m2`, et tous de la forme `fiche:∅ vs tuile:77` sur
**6 parcelles `hors_classement`** (forêt publique, domaine public fluvial, délaissé de voirie,
pente) : la fiche n'y sert aucune SDP (précédence du scoring), la **tuile matérialisée** en sert
encore une. C'est **corrigé à la source** (`tiles.py:243`, double porte résiduelle + scoring) et
**vérifié** : l'expression corrigée du builder rend `∅` pour les 6 → le banc tombe à **0** au
prochain `rebuild_mvt_servies` (bascule / `labuse build-mvt`).

> **Décision (Vic, ce run)** : le rebuild MVT n'est PAS lancé ici — il réécrit `mvt_parcels`,
> table partagée lue par la carte des 3 sessions voisines (Copilote, John, vigies/tableau). Le
> correctif reste en place ; le 0 littéral se matérialise au rebuild nocturne/déploiement normal,
> sans perturber les sessions en cours. Tout le reste du banc (surface, contenance, hauteur, SDP
> côté SQL, copro, prix neuf, taxe, compte parc, classement, SRU, vigilances, pente) est à **0**.

| Recette | Résultat |
|---|---|
| Banc 120 parcelles + 24 communes | **6** (tous SDP-tuile, corrigés source, rebuild différé) ; **0 toléré** |
| Suite de cohérence `tests/coherence_ecrans/` (12 témoins) | **6/6 vert** |
| Garde-fou `tests/test_ecarts_zero_garde.py` | **4/4 vert** |
| Régression ciblée (surface/fiche/exports/flash) | **12 passés**, 3 skip (témoin absent) |
| Hook de pré-push | _(voir sortie du run)_ |

### Fichiers touchés
- `scripts/coherence/lib.py` — suppression de TOLERABLE ; comparaison à la précision d'affichage.
- `scripts/coherence/checks_parcelle.py` — tolérances → précision ; surface scindée (contenance /
  dessin) ; jumeaux copro (RNIC), hauteur (porte bâti significatif + dm), SDP (porte scoring) ;
  lecteur vigilance aligné sur la carte (`lines`).
- `scripts/coherence/checks_commune.py` — tolérances → précision ; jumeaux n_parcelles (vivant),
  tiers_hauts (4 tiers + vivant) ; prix neuf (comparaison croisée retirée, 2 faits distincts).
- `scripts/coherence/banc.py` — croisement taxe non appliqué en secteur à taux majoré.
- `src/labuse/api/app.py` — fiche sert `surface_m2` brute (arrondi au bord).
- `src/labuse/api/tiles.py` — tuile SDP : double porte (résiduelle + scoring), comme la fiche.
- `tests/test_ecarts_zero_garde.py` — garde-fou (nouveau).

## 6. Garde-fou (refuse un nouvel arrondi / format toléré)

`tests/test_ecarts_zero_garde.py` — permanent :
- aucune tolérance non nulle (floue : `%`, `point`, virgule décimale) ne peut réapparaître dans une
  vérification du banc (parcelle / commune / croisement) ;
- la gravité `TOLERABLE` ne peut pas redevenir assignable (test unitaire sur `noter` + scan source) ;
- un écart d'un m² à la précision affichée est rouge ; le bruit sous l'unité ne l'est pas ;
- la surface de la fiche est servie brute (pas de `round()` réintroduit dans le producteur).
