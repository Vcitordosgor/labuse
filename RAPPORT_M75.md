# RAPPORT M75 — Phase 0 : brancher PVGIS et Parkings APER (proposition arbitrée)

Branche `feat/m75-gisements` depuis `main` (`41fd6f40`, M74 mergé). **Proposition seule — rien
implémenté. STOP : Vic arbitre avant Phase 1.**

## État mesuré des deux gisements

| | PVGIS (`parcel_solar`) | Parkings APER (`parkings_aper`) |
|---|---|---|
| Volume | 431 663 parcelles (100 %) | 901 parkings |
| Lu aujourd'hui ? | **OUI, mais seulement par le PDF flash** (`flash/data.py` → bloc « Gisement solaire », avec un « indice /100 ») — jamais par la fiche interactive, jamais par le scoring | **Non, nulle part** |
| Lié à une parcelle ? | par idu (une ligne/parcelle) | 870/901 rattachés à des parcelles (`idus`), 806 avec SIREN propriétaire |

Nuance vs RAPPORT_M74 : PVGIS n'était pas « jamais lu » — il alimente déjà le **PDF flash** (d'où
l'« indice 59/100 » du point 4). Il est absent de la **fiche interactive** et du **scoring**.

---

## 1. Où exactement sur la fiche

### PVGIS → tiroir « Réseaux et accès », dans `ViabilisationBlock`
Emplacement naturel : **juste sous la note PV S3REnR** (`ViabilisationBlock.tsx:64`, ligne `↯`). La
logique se tient : le **S3REnR dit si le réseau peut accepter l'injection PV** (capacité d'accueil,
niveau île) ; **PVGIS dit si le soleil est bon** (productible). Deux moitiés de la même question
« puis-je faire du photovoltaïque ici ? ». Nouvelle ligne `☀ Ensoleillement`, sous la ligne `↯`.

### Parkings APER → contexte réglementaire
La fiche n'a pas de tiroir « contexte réglementaire » dédié. Deux emplacements possibles — **je
propose, Vic tranche** :
- **(a) tiroir « Urbanisme »** (droit du sol) : l'APER est une **obligation légale** portant sur la
  parcelle → sa place doctrinale est avec les règles/servitudes. *Recommandé.*
- **(b) tiroir « Réseaux et accès »**, sous la ligne solaire : cohérence thématique (PV/énergie),
  mais mélange une obligation réglementaire avec de la viabilisation.

Le parking n'existe que sur ~2 % des parcelles → ligne **conditionnelle** (rien si pas de parking).

---

## 2. La phrase exacte, sur une parcelle réelle

### PVGIS — exemple parcelle `97401000AB0001` (productible 1 428 kWh/kWc/an)
> ☀ **Ensoleillement favorable à une installation solaire** — productible estimé ~1 430 kWh/kWc/an
> (modèle SARAH3, Commission européenne). *Estimé — le gradient côtier local n'est pas capturé.*

Repli si donnée absente : rien (ligne conditionnelle). Jamais de « — » nu.

### Parkings APER — exemple parcelle `97415000DI0135` (parking 6 000 m²)
> 🅿 **Grand parking (~6 000 m²) sur cette parcelle** — potentiellement concerné par l'obligation
> d'ombrières photovoltaïques (loi APER), échéance **01/07/2028**. *Sourcé (OpenStreetMap).*

⚠ Formulation « **potentiellement concerné** », PAS « soumis à » — voir point 5.

---

## 3. Scoring ou information ? → **INFORMATION SEULE** (recommandation forte, confirmée)

Ni PVGIS ni Parkings n'entrent dans le scoring. Un gisement solaire n'est pas un signal de mutation ;
une obligation d'ombrières non plus. On **n'ajoute aucun signal au scoring sans validation
walk-forward**, et rien ici n'a été validé ainsi. Les deux restent en information → **golden diff 0
attendu** (aucune couche cascade, aucun poids touché).

---

## 4. L'« indice /100 » de PVGIS dans les PDF → à retirer

**Constat mesuré** : `flash/templates/rapport.html.j2:441` affiche
`{prod} kWh/kWc/an · indice {score_solaire}/100`. Le `score_solaire` (0-100, médiane 50) est un
**score LABUSE opaque** — un nombre inventé qui ressemble à une note, exactement ce qu'on retire du
client (même doctrine que les scores Q/A/complétude retirés en M36).

**Proposition** — remplacer partout (PDF flash + future ligne fiche) :
- **Retirer le `/100`** (le `score_solaire` ne sort plus jamais au client).
- **Garder le productible** `~1 430 kWh/kWc/an` : c'est une valeur physique **sourcée/Estimée**
  (SARAH3), pas un score inventé — utile et honnête.
- **Ajouter un mot qualitatif** dérivé du productible (bornes mesurées : q25 = 1 329, médiane
  1 399, q75 = 1 501 kWh/kWc/an — l'île entière est un bon gisement) : « **favorable** » (médian),
  « **très favorable** » (> q75). Jamais de jauge, jamais de barre.

Variante si Vic veut zéro chiffre du tout : « Ensoleillement favorable à une installation solaire
(estimation SARAH3) », sans le kWh/kWc/an. Je penche pour **garder le productible** (sourcé, concret,
c'est l'argument), retirer seulement le `/100`.

---

## 5. Parkings APER : le seuil est-il mesuré ? — OUI pour la surface, NON pour l'obligation

**La surface EST mesurée** : `surface_m2 = ST_Area(geom_2975)` exactement (vérifié sur échantillon,
source OSM). Pas une présomption. ✅

**MAIS l'obligation APER ne peut PAS se déduire de « > 500 m² »** (le cadrage de RAPPORT_M74 était
imprécis). Mesure de la répartition réelle :

| tranche | n | surface | échéance |
|---|---|---|---|
| `1000_10000` | 712 | 1 003–9 450 m² | 01/07/2028 |
| `sup_10000` | 24 | 11 316–27 406 m² | 01/07/2026 |
| **(aucune)** | **165** | **800–1 000 m²** | **aucune — SOUS le seuil** |

Trois pièges de faux positif à éviter — **une obligation légale ne se présume pas** :
1. **165 parkings (800–1 000 m²) ne sont PAS soumis** (pas de tranche). Ne rien afficher d'APER pour
   eux (ou « parking, hors seuil APER »).
2. **Le seuil de la donnée (1 000 m²) peut diverger du seuil légal.** La loi APER (2023-175, art. 40,
   codifiée L.111-19-1 c. urb.) vise les parkings **> 1 500 m²** (décret 2024-1023). Or la tranche
   commence à 1 003 m². → **la bande 1 000–1 500 m² est douteuse** : à vérifier contre le texte AVANT
   d'affirmer quoi que ce soit. D'où « **potentiellement concerné** » et non « soumis à ».
3. **`equipe` vient d'OSM (incomplet)** : l'absence de tag « ombrière » ne prouve pas l'absence
   d'ombrière. Ne jamais afficher « à équiper ». Au mieux : « équipement non renseigné ».

**Recommandation** : n'afficher la ligne APER que pour les parkings **avec une tranche + une
échéance** (736 max), formulation « potentiellement concerné … échéance X », `equipe=true` → « une
installation d'ombrières est déjà cartographiée (OSM) », jamais d'injonction. Et **trancher le seuil
1 000 vs 1 500 m²** avant Phase 1 (sinon jusqu'à ~la moitié de la tranche basse serait un faux
positif réglementaire).

---

## Décisions attendues de Vic (avant Phase 1)

1. **Placement Parkings APER** : Urbanisme (recommandé) ou Réseaux et accès ?
2. **PVGIS /100** : garder le productible kWh/kWc/an + mot qualitatif (recommandé), ou zéro chiffre ?
3. **Seuil APER 1 000 vs 1 500 m²** : quelle borne d'obligation LABUSE retient ? (bloque l'affichage
   honnête de la bande 1 000–1 500 m²).
4. **Exports** : PVGIS est déjà dans le PDF flash (à corriger : retrait du /100). Les Parkings APER
   entrent-ils aussi dans les exports, ou fiche seulement ?
5. Confirmer **information seule** (pas de scoring) — je le recommande fermement.

## Phase 1 (rappel, après arbitrage)
Brancher aux emplacements validés, libellés client seuls, PVGIS = Estimé (réserve SARAH3 visible),
Parkings = Sourcé, requalifier `partiel → connecte` (bandeau 49 → **51**, dynamique), report DA
(DA-FICHE-v6.html), golden diff 0. **NE PAS MERGER.**

**STOP.**

---

# PHASE 1 — implémentation (après arbitrage Vic)

Arbitrages appliqués : (1) parkings → Urbanisme ; (2) /100 supprimé partout ; (3) seuil mesuré
d'abord ; (4) exports oui, mêmes libellés au mot près ; (5) information seule.

## Le seuil APER, mesuré dans le texte (point 3, avant toute décision)

**Seuil légal = plus de 1 500 m²** (parkings extérieurs non intégrés à un bâtiment).
- **Loi n° 2023-175 du 10/03/2023, art. 40** + **décret n° 2024-1023 du 13/11/2024**.
- Calendrier (parcs existants au 01/07/2023) : **> 10 000 m² → 01/07/2026** ; **1 500–10 000 m²
  → 01/07/2028** (extension possible 2030). Nouveaux parkings : dès le 01/12/2024.
- Obligation : ombrières PV sur ≥ 50 % de la surface. Exemptions possibles (contraintes techniques/
  patrimoniales/économiques, ensoleillement insuffisant) → attestation du propriétaire.
- Sources : Bureau Veritas, Banque des Territoires, faceaurisque (concordantes).

**Le seuil de la donnée (1 000 m²) divergeait du seuil légal (1 500 m²)** → doctrine Vic appliquée :
**on refiltre la donnée, pas le texte.** `scripts/m75_refiltre_parkings_aper_1500.sql` :
- ≤ 1 500 m² → NON soumis (tranche/échéance NULL) : **451 parkings** (dont **286 portaient une
  tranche à tort**).
- 1 500–10 000 m² → **426** (échéance 2028) ; > 10 000 m² → **24** (échéance 2026). **450 soumis.**
- La surface (ST_Area OSM) n'est pas touchée — seule la classification d'obligation.

## PVGIS → tiroir « Réseaux et accès » (information, Estimé)
- Backend : `viabilisation_build.solaire_note()` = **point de calcul unique** du libellé ; branché
  dans `_viabilisation_block` (`via.solaire`) ET dans le PDF flash (`collect_report_data`).
- Front : `ViabilisationBlock.tsx`, ligne `☀` sous la note PV S3REnR.
- Libellé (ex. 97401000AB0001) : *« Ensoleillement favorable à une installation solaire —
  productible estimé ~1 430 kWh/kWc/an (modèle SARAH3, hors gradient côtier local). Estimé. »*
- **`score_solaire` /100 RETIRÉ** du PDF flash (`rapport.html.j2`) et exposé nulle part ailleurs
  (vérifié : aucun autre `/100` solaire dans le code). Qualitatif « favorable / très favorable »
  (bornes mesurées q25 1 329 · q75 1 501), jamais de jauge.

## Parkings APER → tiroir « Urbanisme » (information, Sourcé)
- Backend : `viabilisation_build.aper_note()` = **point de calcul unique** ; branché dans le payload
  fiche (`aper`) ET le PDF flash. N'affiche QUE les parkings avec tranche (soumis, > 1 500 m²).
- Front : carte `data-aper` en tête du tiroir Urbanisme.
- Libellé (ex. 97415000DI0135) : *« 🅿 Grand parking (~6 000 m²) sur cette parcelle —
  potentiellement concerné par l'obligation d'ombrières photovoltaïques (loi APER, décret 2024-1023 ;
  obligation au-delà de 1 500 m²), échéance 01/07/2028. Surface mesurée (OpenStreetMap). Une
  installation d'ombrières est déjà cartographiée (OSM). Sourcé. »*
- **« potentiellement concerné », jamais « soumis à »** ; `equipe` (OSM) → « déjà cartographiée »,
  jamais « à équiper ».

## Exports — mêmes libellés, au mot près
Vérifié programmatiquement : `fiche.aper.note == export.aper.note` ET `fiche.solaire.note ==
export.solaire.note`, sur parcelle avec et sans parking. Un seul point de calcul → zéro divergence.

## Requalification catalogue
`parcel_solar` (48) et `Parkings OSM (loi APER)` (51) : `partiel — ingéré non exploité` →
**connecte** (lecture effective). **Bandeau 49 → 51 = accueil 51**, dynamique.

## Report DA
`docs/DA-FICHE-v6.html` : règle « ligne d'information données dormantes » ajoutée (puce d'unité +
état ; « potentiellement concerné » ; aucun score /100). Aucune ligne concernée dans DA-LABUSE.html.

## Garde-fous (état final)
| Garde | Résultat |
|-------|----------|
| tsc --noEmit | **0** |
| vitest | **37/37** |
| npm run build | **vert** |
| golden 118 | **33 FAIL = baseline, 0 régression** (information seule confirmée) |
| pytest flash/viab | **29 passed** |
| bandeau = accueil | **51 = 51**, dynamique |
| fiche == export | solaire + APER identiques au mot près |
| exports PDF | 200 (avec/sans parking) |
| console JS | **0** (hors tuiles carto 404 du harnais dev, préexistant) |

## Pièges notés
- `to_jsonb(:idu::text)` casse le binding SQLAlchemy → `to_jsonb(CAST(:idu AS text))`.
- `parkings_aper` doit figurer dans `_NEEDED_TABLES` (flash) sinon la section APER est omise.
- Le seuil de la donnée (1 000 m²) ≠ seuil légal (1 500 m²) : refiltrer la donnée, jamais arrondir
  le texte.

**NE PAS MERGER.**
