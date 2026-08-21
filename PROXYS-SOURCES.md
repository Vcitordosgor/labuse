# PROXYS & LIBELLÉS DE SOURCE — audit du faux constat de NOM (M125-1ter)

> Balayage de **toutes** les sources du registre : chaque cas où le **libellé servi au client**
> (nom de couche affiché + nom dans le bandeau « Sources ») **ne désigne pas la couche réellement
> interrogée en base**. Un proxy servi sous le nom d'une autre couche est un **faux constat** — la
> boussole l'interdit, avec ou sans date.
>
> **Aucune correction.** Rapport seul. Vic tranche source par source.
> Preuve = `spatial_layers.attrs` (source réelle par objet) + `seed_sources.py` (notes) +
> `frontend/src/lib/layers.ts` (libellé affiché) + code cascade. Base locale `labuse` (seedée).

---

## A — PROXYS FRANCS : la couche affichée n'est PAS la donnée interrogée (faux constat)

### A1 · SAR (aménagement régional)
- **Libellé affiché** : « SAR (aménagement régional) » (layers.ts:15) · bandeau Sources : « SAR Réunion (PEIGEO) ». Détail de ligne : *« espace agricole SAR (risque préemption SAFER) — à vérifier »*.
- **Couche réellement en base** : `kind='sar'`, `attrs.source = "data.regionreunion.com / potentiel-foncier"` (2 453 emprises) — le **jeu « potentiel foncier » de la Région**, PAS le SAR.
- **Ce que le constat prétend dire** : la parcelle relève d'un zonage **SAR** (Schéma d'Aménagement Régional, juridiquement **supérieur au PLU**) et d'un **risque de préemption SAFER**.
- **Ce qu'il peut honnêtement dire** : îlot repéré au jeu **« potentiel foncier » de la Région** (orientation indicative de vocation). Le zonage SAR officiel est **introuvable en open data** (PEIGEO 503, DEAL injoignable) — non détenu en base. *(Double faute : le mot « SAFER » y est aussi, cf. A2.)*

### A2 · SAFER
- **Libellé affiché** : « SAFER » (layers.ts:14) · Sources : « Zonage SAFER (DAAF) ».
- **Couche réellement en base** : `kind='safer'`, `attrs.src = "RPG.LATEST"` (38 460 emprises) — le **Registre Parcellaire Graphique** (déclarations PAC, IGN/Géoplateforme).
- **Ce que le constat prétend dire** : la parcelle est dans le **zonage SAFER** → **droit de préemption SAFER**.
- **Ce qu'il peut honnêtement dire** : parcelle **déclarée agricole au RPG** (déclarations PAC) — proxy indicatif d'un usage agricole. Le zonage SAFER/DAAF officiel est **introuvable en open data** — non détenu en base.

### A3 · OCS GE (occupation du sol)
- **Libellé affiché** : « Occupation du sol » (layers.ts:39) · Sources : « OCS GE (IGN) ». Détail : *« Sol classé {naturel|agricole|artificialisé} »*.
- **Couche réellement en base** : `kind='ocs_ge'`, `attrs.src = "BDCARTO_V5"` (1 643 emprises) — **BD CARTO® V5** occupation du sol (grain grossier).
- **Ce que le constat prétend dire** : classe **OCS GE** (référentiel fin, millésimé, standard national d'artificialisation ZAN).
- **Ce qu'il peut honnêtement dire** : occupation du sol **dérivée de BD CARTO® V5** (3 classes : naturel/agricole/artificialisé, grain grossier) — signal non juridique. L'OCS GE natif 974 n'est **pas exposé** au WFS Géoplateforme (400) — non détenu en base.

### A4 · ENS (Espace naturel sensible)
- **Libellé affiché** : « Espace naturel sensible » (layers.ts:31) · Sources : « ENS (Département) ».
- **Couche réellement en base** : `kind='ens'`, `attrs.src = "patrinat_rb:reserve_biologique"` (etc. : APB/RNN/CEN/conservatoire littoral, INPN/patrinat, 73 emprises).
- **Ce que le constat prétend dire** : la parcelle est en **ENS départemental** → **droit de préemption ENS** du Département (art. L.215-1 C. urb.).
- **Ce qu'il peut honnêtement dire** : **espace protégé réglementaire** (réserve biologique, APB, réserve naturelle, CEN, conservatoire du littoral — INPN/patrinat). Le zonage **ENS départemental officiel est introuvable** (à demander AGORAH/DEAL) — non détenu en base. *(Le préempteur et le régime diffèrent : ENS ≠ espace protégé.)*

---

## B — ATTRIBUTION DE FOURNISSEUR ERRONÉE (le nom du producteur ne correspond pas)

### B1 · Trait de côte
- **Libellé affiché** : « Trait de côte » (layers.ts:29) · Sources : **« DEAL Réunion — trait de côte »**, provider « Cerema / GéoLittoral ».
- **Couche réellement en base** : `kind='trait_de_cote'`, `attrs.src = "GéoLittoral/Cerema — indicateur érosion (SHP, EPSG:2975)"` (24 168 objets), millésime **2018**.
- **Ce que le constat prétend dire** : le **trait de côte** (position du rivage), source **DEAL Réunion**.
- **Ce qu'il peut honnêtement dire** : **indicateur national de l'érosion côtière** (**Cerema / GéoLittoral**, 2018) — ce n'est ni « la DEAL » ni un trait de côte instantané, mais un indicateur d'érosion. *(Le nom de source « DEAL Réunion » contredit le provider « Cerema ».)*

### B2 · Propriétaire (personne morale)
- **Libellé affiché** : ligne cascade « Propriétaire » attribuée à **« Fichiers fonciers (Cerema) »** (`phase2.py:16` `SRC_FF`) ; le bandeau « Sources » liste donc **« Fichiers fonciers (Cerema) »** via `_data_sources_fiche`.
- **Couche réellement en base** : la source « Fichiers fonciers (Cerema) » est **sous convention NON branchée** → la couche cascade `proprietaire` renvoie **100 % UNKNOWN** (`phase2.py:154`). Les **82 701 liens parcelle↔PM réellement servis** (bloc `proprietaire_moral`, `parcelle_personne_morale`) viennent de **« DGFiP — parcelles des personnes morales »** (open data), source **distincte** (constat explicite `seed_sources.py`).
- **Ce que le constat prétend dire** : propriétaire issu des **Fichiers fonciers (Cerema)**.
- **Ce qu'il peut honnêtement dire** : la dénomination PM affichée vient de **DGFiP — parcelles des personnes morales** (open data) ; les « Fichiers fonciers Cerema » ne sont **pas branchés** (aucune donnée). Créditer Cerema = créditer une source non utilisée. *(Voir aussi `app.py:811` « source DGFiP/Cerema » qui mélange les deux.)*

---

## C — MINEUR / NUANCE (fournisseur exact, sous-type ou couche interne)

| Cas | Affiché | Réel en base | Note |
|---|---|---|---|
| **Ravines** | « Ravines » (layers.ts:28) | `kind='ravine'` = `BD TOPO IGN — troncon_hydrographique` | Provider correct (IGN) ; « ravine » = sous-type du réseau hydro BD TOPO. Peu trompeur, mais ce n'est pas une couche « ravines » dédiée. |
| **DEAL Réunion (WMS/WFS)** | Sources : « DEAL Réunion (WMS/WFS) » | sert `kind='anru'` (`attrs.source='DEAL_REUNION_WFS'`, NPNRU) | Hôte carto DEAL injoignable → « servi par proxys », mais le **producteur DEAL/NPNRU est correct**. Le nom « WMS/WFS » est un canal, pas une donnée. |
| **tva_primo** | (interne) | `attrs.source='LABUSE (dérivé des QPV)'` | Couche **dérivée LABUSE**, pas une source externe — non trompeuse si non présentée comme un tiers. |

---

## Synthèse

- **4 proxys francs** (A) où le **libellé officiel ment sur la nature juridique** de la donnée —
  les plus graves car ils évoquent des **régimes/préemptions** (SAR, SAFER, ENS) ou un **standard
  national** (OCS GE) qui **ne sont pas la donnée en base** : **SAR, SAFER, OCS GE, ENS**.
- **2 attributions erronées** (B) : **Trait de côte** (Cerema pris pour DEAL, indicateur d'érosion
  pris pour un trait de côte) et **Propriétaire PM** (crédité Cerema/Fichiers fonciers alors que la
  donnée vient de DGFiP open data ; Cerema non branché).
- **3 mineurs** (C) : Ravines, DEAL WMS/WFS, tva_primo — fournisseur correct, à surveiller.

## Points à trancher (source par source)

Pour A1–A4, deux familles de correction possibles (Vic tranche) : **(i)** renommer le libellé_client
+ le nom de source pour désigner la **vraie** couche (« potentiel foncier Région », « RPG », « BD
CARTO V5 », « espace protégé INPN ») et **retirer** le vocabulaire juridique non fondé (SAR/SAFER/
ENS/préemption) ; **(ii)** garder le mot métier **seulement** comme « proxy indicatif de… » dit
explicitement. Pour B1/B2 : corriger l'**attribution** (Cerema/GéoLittoral ; DGFiP PM).

> Rappel : la boussole (« pas de constat non sourcé ») rend A1–A4 prioritaires **sur** la question
> du millésime — un nom juste sans date vaut mieux qu'un faux nom daté.

---

*Rapport M125-1ter. Aucune modification de comportement. Base d'arbitrage.*
