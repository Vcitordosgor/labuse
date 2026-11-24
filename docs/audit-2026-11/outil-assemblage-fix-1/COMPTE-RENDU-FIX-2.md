# OUTIL-ASSEMBLAGE-FIX-2 — compte-rendu (réponse à `relecture-assemblage-1.md`)

> Périmètre = la **liste fermée (7 points)** de la relecture, rien d'autre. Base `labuse` en **lecture
> seule imposée par la base** (`SET default_transaction_read_only = on` ; preuve : INSERT refusé avant
> toute passe). Branche `fix/outil-assemblage-1`. Tout chiffre ci-dessous sort d'un **script commité**
> (`figures_cr.py`, `mesure_fix2.py`) dont la sortie brute est collée.

## LOT 0 — filet (commit séparé `c1769c0b7`, AVANT correction)

5 tests ajoutés (un par point), **rouges avant** les correctifs — sortie brute :
```
FAILED test_fix2_cv_affiche_obligation_mixite            payload sans champ `mixite`
FAILED test_fix2_bande_1500_1800_porte_regle_article_page no quota_pct/article
FAILED test_fix2_vingt_logements_sous_1500_declenche      declenchee=False (≥20 logts abandonné)
FAILED test_fix2_zac_savane_des_tamarins_exclue           declenchee=True (ZAC non exclue)
FAILED test_fix2_identifiant_introuvable_nomme            pas de champ `introuvables`
5 failed, 28 deselected
```
Verts après LOT 1-4 (voir fin).

---

## Point 1 & 2 (LOT 1) — l'Assemblage PORTE l'obligation de mixité + dit la « borne haute »

**Fait.** `compute_bilan` attache désormais au `Bilan` un objet `mixite` STRUCTURÉ {servitude, declenchee,
regime, quota_pct, produits, article, page, **borne_haute**, critère}. Il remonte par `_capacite_union`
→ `aggregate_assiette` → payload `/moteurs/assemblage` → écran (bloc `data-asm-mixite`). Même source
(`compute_bilan_servi`) que la fiche/Bilan/PDF/Excel → **même obligation pour la même parcelle**.

L'écran affiche : « Obligation de mixité sociale · **Art. 2 (zones U1 à U6) · pp. 14-15** », le régime
(plein / intermédiaire), le quota (**30 %**), les produits et le critère. En régime **intermédiaire**
(trio CV), un bandeau : « ⚠ Charge foncière = **borne haute** (CA au prix libre). L'obligation
d'accession sociale n'est PAS chiffrée (aucun prix d'accession sourcé) : ce n'est pas le résultat
réglementaire, mais son plafond. »

**Prix d'accession sociale : aucun n'est sourcé dans le dépôt** (seul `prix_m2_lls` = 2 900 €/m² pour le
LLS *locatif*, et le prix neuf libre ; PSLA/PTZ = liste de produits `plh_tco.yaml`, sans prix). Conforme
au mandat : **on n'invente pas** — le résultat est présenté en borne haute, et c'est **signalé**.

Sortie brute (`figures_cr.py`, trio CV) :
```
### CV (AU3c, bande intermédiaire) — ['CV0724', 'CV1506', 'CV1507']
  charge_fonciere.central = 178261  prix_sortie=4730
  mixite = regime=intermediaire quota=30.0% borne_haute=True Art. 2 (zones U1 à U6) pp. 14-15
```

---

## Point 3 (LOT 2) — déclencheur « ≥ 20 logements » rétabli

`_clause_mixite` (régime à bandes) teste de nouveau le **nombre de logements du programme chiffré** :
≥ 20 logements (programme < 1 800 m²) → **régime intermédiaire** (accession sociale), même à SDP < 1 500.
Témoin AY1666 (20 logements, programme 1 494 m²) : `declenchee=True, regime="intermediaire"` (avant :
`declenchee=False`). **Impact € = nul** (intermédiaire comme non-déclenchée valorisent le CA au prix
marché — cf. mesure) : c'est la fidélité d'étiquetage au texte qui est rétablie. Cité : Art. 2, ligne PC
« programme de 20 logements ou plus (SDP < 1 800 m²) », p. 15.

## Point 4 (LOT 2) — exclusion ZAC Savane des Tamarins

`_clause_mixite` honore `eco["zac_mixite_exclue"]` → clause **non déclenchée** avec citation « ZAC Savane
des Tamarins — Art. 2, pp. 14-15 : programme calculé à l'échelle de l'opération ». Garde **codée + citée
+ testée** (`test_fix2_zac_savane_des_tamarins_exclue`). **Réserve honnête** : aucun périmètre de la ZAC
n'est publié en donnée ouverte (vérifié : aucune couche, zone PLU ni prescription nommée « Savane / ZAC »
dans `spatial_layers` Saint-Paul ; seules des POI homonymes). Le drapeau n'est donc jamais posé sur une
parcelle réelle aujourd'hui → garde inerte, **0 impact** (comme l'a noté la relecture). Elle s'activera
dès qu'un périmètre ZAC sera ingéré.

---

## Point 5 (LOT 3) — Saint-Denis & Saint-Pierre : la clause ne se déclenche JAMAIS → rien à changer

La clause de mixité ne tourne que si la parcelle est dans un **secteur de mixité sociale** (prescription
SMS, `plu_gpu_prescription` subtype 16/17 ; `db.py` pose alors `eco["mixite"]`). Mesure (lecture seule) :

```
# parcelles CONSTRUCTIBLES intersectant un SMS (16/17), par commune
Saint-Paul   | 3441
Saint-Benoît | 2      (subtype 16 = « bâtiment agricole susceptible de changer de destination » — PAS un SMS ; hors des 7 points)
Saint-Denis  | 0
Saint-Pierre | 0
```

- **Saint-Denis** : **aucun** SMS → la clause **ne se déclenche jamais** → le « sur-déclenchement sur le
  gabarit » (point 5) **n'a aucun effet pratique**. Son règlement réel (Art. **Uavap.2, p. 27** : « les
  opérations nouvelles d'habitat collectif de **30 logements et plus** → min **15 %** de logements
  sociaux/intermédiaires ») est **logements-based**, et il vit déjà dans la fiche (`mixite` leaf des
  destinations) — jamais dans le déclencheur du bilan.
- **Saint-Pierre** : des SMS existent (23 polygones) mais **aucune parcelle constructible ne les
  intersecte**, et **aucune clause de mixité n'est encodée** pour cette commune. Le texte **ne permet pas
  de trancher** un déclencheur programme-based.

Conformément au mandat (« si le texte d'une commune ne permet pas de trancher / si rien ne se déclenche,
tu ne changes rien et tu le dis »), **je ne modifie ni Saint-Denis ni Saint-Pierre** et je le documente,
preuve à l'appui. Changer un chemin qui ne s'exécute jamais n'apporterait aucun bilan correct de plus et
risquerait le cœur partagé.

---

## Point 6 (LOT 4) — identifiant introuvable nommé (API + écran)

`POST /moteurs/assemblage` renvoie désormais `introuvables: [...]` et `n_demandes` (comme `/compare`
renvoie `echecs`/`ignores`). L'écran affiche un bandeau `data-asm-introuvables` : « 1 identifiant
introuvable — écarté du calcul · ZZ9999 · 4 parcelles demandées, 3 trouvées ». Plus de « 3 parcelles »
muet quand 4 sont saisies. Testé : `test_fix2_identifiant_introuvable_nomme`.

---

## Point 7 (LOT 5) — chiffres du compte-rendu corrigés + traçables

Deux chiffres intermédiaires du CR FIX-1 venaient d'un diagnostic à recul unique, superseded. **Valeurs
SERVIES** (`figures_cr.py`, sortie brute, trio DH) :
```
### DH (U2b/U2h) — ['DH0076', 'DH0119', 'DH0120']
  surface_totale_m2       = 21832
  surface_constructible_m2= 21638  (pct_hors_zone=1)
    zone U2b   emprise= 17544 niveaux=5 recul_lim=3.0 voie=4.0 SDP=30673
    zone U2h   emprise=  1112 niveaux=3 recul_lim=4.0 voie=4.0 SDP=1501
  sdp_terrain_libere_m2   = 32174
```
Corrigé dans `COMPTE-RENDU.md` : **21 638** (servi ; ~21 516 = intersection géométrique directe ASTRA,
écart de référentiel contenance/dessin) et **17 544** (emprise U2b servie, non 17 897). Désormais tout
chiffre du CR sort de `figures_cr.py` / `mesure_fix2.py` (commités).

---

## MESURE ÎLE (lecture seule) — impact € des LOTS 1-3 vs FIX-1

Passe `mesure_fix2.py` (lecture seule prouvée, une connexion). Compare la charge foncière **NEW (FIX-2)**
vs **OLD (FIX-1 simulé)** pour chaque parcelle en secteur de mixité sociale. Sortie brute :

```
PREUVE read-only OK : (psycopg.errors.ReadOnlySqlTransaction) cannot execute INSERT in a read-only ...

commune        SMS-constr  testées changées   médian€      max€     total€
Saint-Paul           3441     3428        0         0         0          0
Saint-Pierre            0        0        0         0         0          0
Saint-Benoît            2        1        0         0         0          0
Saint-Denis             0        0        0         0         0          0
Saint-Louis             0        0        0         0         0          0
Le Tampon               0        0        0         0         0          0

parcelles qui bougent : 0
```

**Lecture : aucun bilan ne change d'un euro, sur toute l'île.** Les LOTS 1-3 sont de la **restitution /
étiquetage**, pas du montant : l'obligation de mixité est désormais *affichée* (LOT 1), le déclencheur
« ≥ 20 logements » *relabellise* en régime intermédiaire mais le CA reste au prix marché dans les deux
cas (LOT 2, impact € nul — confirmé), l'exclusion ZAC est inerte faute de périmètre (LOT 2), et
Saint-Denis / Saint-Pierre n'ont **aucune** parcelle constructible en SMS (LOT 3 — la clause ne tourne
jamais). CSV complet des parcelles qui bougent : **vide** (`fix2-parcelles-qui-bougent.csv`, en-tête
seul). Saint-Paul : 3 428 bilans recalculés des deux côtés, 0 écart.

---

## « Aucun bilan ne change en euros » — trois explications (demande du mandant)

Sortie brute `regimes_fix2.py` (lecture seule) :
```
Saint-Paul, parcelles constructibles en SMS : 3441
  plein                          123
  intermediaire                  31
  intermediaire_via_logements    1
  non_declenchee                 3274
  sans_bilan                     13
  exemples borne haute (idu, charge €) : [('AT0257',209512),('AW0299',294487),('AW0307',284594)]
  exemples ≥20 logts seuls (idu, critère) : [('AY1666','20 logements ≥ 20 (SDP < 1800 m²)')]
Saint-Denis  — AV0004 eco[mixite]=None · DO0049 None · BW0601 None
Saint-Pierre — CR0845 eco[mixite]=None · ER0718 None · CV0490 None
```

### Q1 — Trio CV : borne haute + prix d'accession sourcé ? combien de parcelles ?
Le trio CV (+178 261 €) est **affiché en borne haute** : `figures_cr.py` →
`mixite = regime=intermediaire quota=30.0% borne_haute=True Art. 2 (zones U1 à U6) pp. 14-15` ; l'écran
porte le bandeau « ⚠ Charge foncière = borne haute (CA au prix libre) ; obligation d'accession sociale
non chiffrée ». **Aucun prix d'accession sociale (PSLA/PTZ) n'est sourcé dans le dépôt** — vérifié :
`grep -rniE 'prix.*accession|psla.*[0-9]{3,}|prix_m2_(accession|psla|ptz)' config/ src/labuse` ne rend
que `prix_m2_lls = 2 900 €/m²` (LLS **locatif**, ≠ accession) et `prix_m2_neuf` (prix **libre**) ; PSLA/PTZ
n'apparaissent que comme liste de produits (`plh_tco.yaml`). **Oui, c'est le cas — signalé.** Nombre de
parcelles dans cette situation (`regimes_fix2.py`, sortie brute) : **31** parcelles Saint-Paul en régime
**intermédiaire = borne haute** (CA au prix libre, accession non chiffrée ; ex. AT0257 +209 512 €,
AW0299 +294 487 €, AW0307 +284 594 €) ; à côté, **123** parcelles en **plein régime** où la décote
30 % LLS EST réellement appliquée (programme ≥ 1 800 m² ou terrain > 6 000 m² — ce n'est PAS une borne
haute) ; 3 274 non déclenchées. Le trio CV (assemblage) relève de la même situation que les 31
(programme ~1 583 m², intermédiaire, borne haute).

### Q2 — « ≥ 20 logements » : combien de parcelles Saint-Paul, et pourquoi 0 € ?
Parcelles Saint-Paul que le seul déclencheur « ≥ 20 logements (SDP < 1 800) » fait entrer en régime
(programme chiffré < 1 500 m², donc pas prises par le seuil SDP) : **1** — `97415000AY1666` (critère
« 20 logements ≥ 20 (SDP < 1 800 m²) ») ; les 30 autres parcelles intermédiaires le sont par le seuil
SDP 1 500–1 800. **Leur bilan ne
bouge pas** parce que le régime **intermédiaire** valorise le CA **au prix libre** (aucune pondération :
pas de prix d'accession sourcé), **exactement comme l'état « non déclenchée »** d'avant — le `_px` du CA
est l'identité dans les deux cas (`bilan.py`). Le rétablissement du ≥ 20 logts corrige donc l'**étiquette**
(et fait apparaître l'obligation à l'écran, Q1), pas le **montant**. Mesure : 0 € de delta (tableau
ci-dessus).

### Q3 — Saint-Denis / Saint-Pierre : sur-déclenchement ou jamais déclenchée ?
**Les deux énoncés se concilient.** La relecture 1 décrit le **chemin de code** : *si* la clause se
déclenchait pour ces communes (branche `s_haut ≤ 0`), elle le ferait sur le **gabarit** — ce code existe.
Mais la clause ne tourne QUE si la parcelle est dans un **secteur de mixité sociale** (prescription SMS
16/17 ; `db.py` pose alors `eco["mixite"]`). **Aucune** parcelle constructible de Saint-Denis ni de
Saint-Pierre n'est dans un SMS → `eco["mixite"] = False` → **la branche n'est jamais atteinte**. Le
chemin existe (relecture), mais est **inerte en pratique** (ma mesure) — il n'y a aucun bilan erroné à
corriger.

- **Saint-Denis** — règlement : **Art. Uavap.2, p. 27** « les opérations nouvelles d'habitat collectif de
  30 logements et plus sous réserve qu'elles comportent un minimum de 15 % de logements sociaux et/ou
  intermédiaires » (déclencheur = **nombre de logements**, pas la SDP ; quota 15 %). 3 parcelles
  constructibles (`regimes_fix2.py`) → `eco["mixite"]` : AV0004 = **None**, DO0049 = **None**,
  BW0601 = **None** (aucune en SMS).
- **Saint-Pierre** — règlement : **mixité sociale NON RÉGLEMENTÉE** (Art. Ue2 p. 191, Art. A2 p. 205,
  Art. N2 p. 216 : « mixité fonctionnelle et sociale non réglementée »). Aucune obligation chiffrée à
  encoder. 3 parcelles constructibles → `eco["mixite"]` : CR0845 = **None**, ER0718 = **None**,
  CV0490 = **None** (aucune en SMS).

Conclusion : rien changé pour Saint-Denis / Saint-Pierre (mandat : « si le texte ne permet pas de
trancher / si rien ne se déclenche, ne change rien et dis-le »).

## Tests (avant push)

- **Python, famille unitaire du hook** (`not db …`) : **5031 passent**, 0 échec (dont `test_mixite`,
  `test_mn_faisabilite`, `test_plu_calibrage9_mixite` — cœur mixité enrichi sans régression).
- **Python DB** `tests/test_assemblage.py` : **32 passent** (5 filets FIX-2 + valeurs FIX-1 à l'euro),
  1 skip (run résiduel absent de `labuse_test`).
- **Front** : `tsc -b` OK ; **349 vitest** (dont `FIX-2 LOT 1` obligation/borne haute, `FIX-2 LOT 4`
  introuvable).
- Cohérence 12 témoins : relancée au hook (verte attendue — aucun € ne bouge).
