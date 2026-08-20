# M134 — Phase 1 : inventaire des dispositifs et périmètres (STOP)

> **À arbitrer par Vic : ce qui entre dans la couche « Dispositifs », et 3 questions de
> représentation (§C).** Rien n'est construit avant ton GO.

## A. Le tableau

| Dispositif | En base (table) | **Géométrie ?** | Volume | Parcelles concernées | Source · millésime | Déjà à la carte ? |
|---|---|---|---|---|---|---|
| **QPV 2024** | `spatial_layers` kind=`qpv` | **OUI** — 57 polygones | 57 quartiers · 13 communes | **43 825** | ANCT · génération 2024 | Non (fiche/bilan commune seulement) |
| **NPNRU / ANRU** | `spatial_layers` kind=`anru` (+ `anru_quartiers` attribut) | **OUI** — 8 emprises | 8 · 6 communes | **9 844** | DEAL Réunion / ANCT | **OUI déjà** (couche « anru », mapTheme) |
| **ZFANG** | `territoire_fiscal_commune.zfang_regime` | **NON** — attribut commune | 24 communes : **6 renforcé** / 18 standard | commune entière | Décret n° 2026-421 (29/05/2026) | Non (fiche `territoire_fiscal`) |
| **FRR ex-ZRR** | `territoire_fiscal_commune.frr_classement` | **NON** — attribut commune | 23/24 : 3 totalité · 20 partie · **1 hors (Le Port)** | commune entière | ZSAR 1978 · FRR 01/07/2024 | Non (fiche `territoire_fiscal`) |
| **Buffer QPV 500 m** (TVA réduite primo-accédant) | **N'EXISTE PAS** | dérivable (`ST_Buffer` sur QPV) | dérivé | dérivé (à mesurer) | **LABUSE — dérivé (Estimé)** | Non |

Rien d'autre en base : la recherche `data_sources` + `spatial_layers` + colonnes ne renvoie
que ces dispositifs. La **défiscalisation** (Girardin/Pinel, `defisc_fenetres`) est un **signal
PAR PARCELLE** (facette « Sortie de défisc »), pas un zonage — elle reste hors de cette couche
(je le signale pour qu'elle ne soit pas réputée oubliée).

## B. Les deux familles (pour les couleurs)

- **Périmètres opérationnels** (géométrie fine, dessinables tels quels) :
  **QPV** · **NPNRU/ANRU**.
- **Dispositifs fiscaux** :
  - **ZFANG · FRR** = attribut COMMUNE (pas de périmètre fin) → aplat commune ;
  - **Buffer QPV 500 m** = fiscal MAIS géométrié (dérivé LABUSE).

## C. Trois points qui demandent ton arbitrage

**1. NPNRU = ANRU dans cette base.** Ce sont les **mêmes 8 emprises** (« intérêt national »,
source DEAL/ANCT) — « NPNRU absent open data » au-delà de ces 8 (seed_sources). Et la couche
existe DÉJÀ (`anru`, mapTheme chartreuse #C6E82E/#8FA818, aplat 0,30 + trame). → Un SEUL item
« NPNRU/ANRU », pas deux. **Question : la couche « Dispositifs » absorbe-t-elle la couche
`anru` existante (un seul endroit), ou la double-t-on ?** (Recommandation : l'absorber /
la ré-étiqueter, pas la dupliquer.)

**2. ZFANG et FRR sont des COMMUNES, pas des périmètres.** Interdit du mandat : ne pas les
dessiner en périmètre fin. → Rendu proposé : **aplat de la commune entière** (fond des
frontières IGN existantes), teinte de la famille « fiscale », **avec une glose qui dit « commune
entière »**. **Question : aplat commune OK, ou tu préfères un rendu dédié (hachures, bord épais) ?**

**3. ZFANG « dit son taux » (Phase 2.4) vs doctrine « ni taux ni plafond ».** Aujourd'hui
`territoire_fiscal.py` refuse explicitement taux/abattement/plafond ; la fiche distingue déjà
le **régime** (renforcé « commune de l'Est classée par décret 2026-421 » / standard) mais pas
l'**intensité**. Le mandat veut distinguer renforcé (80 % bénéfices·TFPB, 100 % CFE — 6 communes
Est : Bras-Panon, La Plaine-des-Palmistes, Saint-André, Saint-Benoît, Sainte-Rose, Salazie) du
standard (~50 %). **Question : (a) distinguer visuellement renforcé/standard + dire « abattements
majorés (régime renforcé) » SANS le %, ou (b) énoncer le taux comme un FAIT du décret (80/100
vs 50) ?** L'interdit vise « vous économiserez X » (un gain personnalisé) — énoncer le taux
statutaire est un fait, pas un conseil, mais c'est un écart à la doctrine « ni taux » que je ne
franchis pas sans ton GO.

## D. Ce que je propose de mettre dans la couche (à valider)

Un item activable par dispositif :
- **QPV 2024** (aplat + contour, famille opérationnelle) — géométrie ✓
- **NPNRU/ANRU** (existant, ré-étiqueté, famille opérationnelle) — géométrie ✓
- **ZFANG** (aplat commune, famille fiscale ; renforcé vs standard distingués) — attribut
- **FRR ex-ZRR** (aplat commune, famille fiscale) — attribut
- **TVA primo-accédant (QPV + 500 m)** (dérivé LABUSE, famille fiscale, glose « Estimé ») — Phase 3

Contraste : chaque aplat ≥ 1,25:1 / contour ≥ 3:1 (critère M105-B, mesuré à l'implémentation).
Chaque item portera son « i » (ce que c'est · ce que ça change · source·millésime), sans sigle nu.

**STOP — j'attends ton arbitrage sur A/C/D avant de construire la Phase 2.**
