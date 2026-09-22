# AUDIT FICHE ÉCRAN ↔ PDF PREMIUM — parcelle `97402000AH1966`

> **Mandat M124-D.** Diff exhaustif, champ par champ, de ce que la **fiche écran** affiche vs
> ce que le **PDF premium** (`/parcels/{idu}/export.pdf`) sort. **Rapport seul — AUCUNE correction
> automatique.** Les arbitrages sont laissés à Vic (section 6).

## Méthode & portée

- Source de vérité des DEUX surfaces : le même dict `_q_v2_fiche` (`src/labuse/api/app.py:2375`).
  L'écran le rend via `frontend/src/components/fiche/Fiche.tsx` (+ 8 blocs frère) ; le PDF via
  `src/labuse/api/pdf_premium.py::render_fiche_pdf`, **après** enrichissement de l'endpoint
  `parcel_export_pdf` (`app.py:3135`).
- Audit **structurel** (quel champ chaque surface rend, et comment). Les valeurs exactes de
  `97402000AH1966` exigent la base `labuse_test` seedée (indisponible dans le bac à sable local ;
  provisionnée sur le runner web via `.claude/hooks/session-start.sh`). Là où la valeur elle-même
  peut diverger à données égales, c'est signalé « ⚠ divergence de source/format ».
- **État PDF = post-M124** (purges A/B/C déjà appliquées). Les retraits volontaires du mandat sont
  marqués `INTENTIONNEL M124`.

Légende statut : **=** présent des deux côtés · **PDF✗** servi/écran mais absent du PDF ·
**ÉCRAN✗** au PDF mais pas à l'écran · **⚠** divergence de source, de format ou de périmètre ·
**MORT** servi par `_q_v2_fiche` mais rendu **nulle part**.

---

## 1. En-tête & identité parcellaire

| Champ (`_q_v2_fiche`) | Fiche écran | PDF premium (post-M124) | Statut | Note |
|---|---|---|---|---|
| `idu` | header `Fiche.tsx:1467` | IDU mono `pdf_premium.py:~150` | **=** | — |
| `adresse` / `adresse_ban` | `adresse` (payload) `Fiche.tsx:1468` | `adresse_ban` (endpoint `adresse_ban_texte`, `app.py:3149`) | **⚠** | Deux clés / deux résolveurs BAN pour la **même** adresse. À confirmer qu'ils rendent la même valeur (risque de divergence silencieuse). |
| `surface_m2` | Constructibilité `Fiche.tsx:2045` | ligne méta pure `pdf_premium.py:~152` | **=** | — |
| `commune` | `Fiche.tsx:2167` | ligne méta pure | **=** | — |
| `coords` | liens Cadastre/Maps `Fiche.tsx:2177` | ligne méta pure (`lat, lon`) | **=** | — |
| `evenement` / `evenement_detail` | badge « rouge » `Fiche.tsx:1622` | bandeau « PROCÉDURE COLLECTIVE (BODACC) » | **⚠** | Écran = cadrage scoring ; PDF = **fait neutralisé** (M124-A/B : « force chaude »/« priorité »/« doctrine bascule » retirés). |
| `proprietaire_moral.denomination` | carte PM `Fiche.tsx:2282` | citée dans le bandeau événement uniquement | **⚠** | PDF n'imprime PAS la carte PM complète (siren, groupe, `etat_societe`). |

---

## 2. Analyse LABUSE — RETIRÉE du PDF (M124-A), conservée à l'écran

Asymétrie **voulue** : l'écran est le produit (il garde le verdict) ; le PDF = données pures.

| Champ | Fiche écran | PDF | Statut | Note |
|---|---|---|---|---|
| `score_v2.tier / label` (verdict) | badge verdict `Fiche.tsx:1313`, `ScoreV2Block` | — | **PDF✗** | `INTENTIONNEL M124-A1` (ancienne carte « VERDICT LABUSE » supprimée). |
| `score_v2.rang / rang_total` | « rang N/N » `Fiche.tsx:1587` | — | **PDF✗** | `INTENTIONNEL M124-A1`. |
| `score_v2.fraction / verbal / mult_base` | probabilité `Fiche.tsx:1599` | — | **PDF✗** | `INTENTIONNEL M124-A1`. |
| `score_v2.pourquoi` | « pourquoi » dépliable `Fiche.tsx:1647` | — | **PDF✗** | `INTENTIONNEL M124-A1` (bloc « POURQUOI CE CLASSEMENT » supprimé). |
| `icd` (Confiance données / complétude) | `IcdBlockView Fiche.tsx:2429` | — | **PDF✗** | `INTENTIONNEL M124-A2` (indice de complétude 90/100 retiré). |
| `completeness_score` | non rendu écran | — | **MORT** | Servi, affiché nulle part (avant/après M124). |
| `score_v` (V1.3 vendabilité) | non rendu (`ALGO-1 item 2`) | — | **MORT** | Déprécié, toujours dans le payload. |

---

## 3. Droits à bâtir / SDP — contradiction résolue (M124-B7)

| Source de donnée | Fiche écran | PDF premium | Statut | Note |
|---|---|---|---|---|
| `potentiel_transformation` (complet : `niveau`, `libelle`, `pct_consomme`, `sdp_residuelle_m2`, `surelevation_possible`, `hauteur_marge_m`) | carte « Potentiel de transformation » `TransformationBlock.tsx:327` (niveau coloré + % + SDP + surélévation) | bloc **« DROITS À BÂTIR (SDP) »** — **uniquement** `sdp_residuelle_m2` + surélévation + marge de hauteur | **⚠** | `INTENTIONNEL M124-A/B7`. PDF retire les niveaux « fort/modéré » et le `pct` (scoring), garde les FAITS, en **un seul message hiérarchisé**. |
| ligne cascade `residuel_socle` (« SDP résiduelle 0 m² — rien à construire (socle -25) ») | ligne dans un tiroir | **supprimée** des lignes (fusionnée dans le bloc SDP) | **PDF✗** | `INTENTIONNEL M124-B7` : évite le doublon d'étiquette « SDP résiduelle SDP résiduelle » et la contradiction. |
| ligne cascade `surface` (« Surface utile 1175 m² — gisement (valorisation 37%) ») | ligne | ligne, **tail de scoring purgé** → « Surface utile 1175 m². » | **⚠** | `INTENTIONNEL M124-B6` : « 1175 m² » = surface parcelle (fait), plus jamais confondu avec de la SDP. |

> ⚠ **Arbitrage possible (voir §6)** : la valeur `sdp_residuelle_m2` du PDF vient de `parcel_residuel`
> (via `potentiel_transformation`), tandis que l'écran affiche AUSSI le `niveau`/`pct`. Écran et PDF
> ne disent donc pas « la même quantité » sur la SDP — voulu, mais à valider.

---

## 4. Blocs de DONNÉES présents à l'écran, ABSENTS du PDF

Ces champs ne sont **pas** de l'analyse LABUSE — ce sont des données. Le PDF (« données pures »)
ne les imprime pourtant pas. **Candidats d'arbitrage** : à ajouter au PDF, ou à assumer hors périmètre.

| Champ | Fiche écran (où) | PDF | Statut |
|---|---|---|---|
| `reglement_plu` (zones, articles, note) | `ReglementPluBlock.tsx:347` | — | **PDF✗** |
| `plu_fraicheur` (GPU vs mairie) | `Fiche.tsx:1929` | — | **PDF✗** |
| `radar_procedure` (procédure PLU, sursis) | `Fiche.tsx:1966` | — | **PDF✗** |
| `historique_site` (permis + caducité sur la parcelle) | `Fiche.tsx:2140` | — | **PDF✗** |
| `voisinage_proche` (ventes/permis < 100 m) | `Fiche.tsx:2154` | — | **PDF✗** |
| `viabilisation` (faisceau réseaux) | `ViabilisationBlock.tsx:31` | — | **PDF✗** |
| `gestionnaires` (EPCI, eau, élec, SPANC) | `GestionnairesBlock.tsx:35` | — | **PDF✗** |
| `aper` (obligation ombrières PV) | `Fiche.tsx:1920` | — | **PDF✗** |
| `renouvellement` (segment + rang) | `Fiche.tsx:1672` | — | **PDF✗** (rang = analyse ; le reste = données) |
| `rnu` (commune sans document local) | `Fiche.tsx:1735` | — | **PDF✗** |
| `territoire_fiscal` (ZFANG / FRR, périmètres) | `Fiche.tsx:2239` | — | **PDF✗** |
| `proximites` (arrêt, pôle, téléphérique, ligne HT) | `Fiche.tsx:2195` | — | **PDF✗** |
| `qualite_commune` (fiabilité de la mesure) | `Fiche.tsx:2409` | — | **PDF✗** |
| `data_sources` (sources utilisées, millésimes) | `Fiche.tsx:2359` | pied de page (attribution générique, pas la liste par-fiche) | **⚠** |
| `depots` (activité dépôts) | `DepotsBlock.tsx:24` | — | **PDF✗** |
| `dvf_parcelle.neuf_vefa` / `.secteur` | `Fiche.tsx:2112` | — (le PDF a SA propre table `comparables`) | **⚠** (§5) |

---

## 5. Contenu présent au PDF, ABSENT de l'écran (enrichissements endpoint)

Ajoutés par `parcel_export_pdf` (`app.py:3145-3184`), pas dans le payload écran.

| Contenu PDF | Origine (endpoint) | Écran | Statut | Note |
|---|---|---|---|---|
| CONTEXTE COMMUNE (SRU, QPV/ANRU, INSEE) | `commune_contexte` | via un autre onglet/fetch | **ÉCRAN✗** | — |
| `marche_synthese` (prix ancien médian, n) | `marche_bloc.bloc_condense` | onglet Marché (fetch séparé) | **⚠** | **« 13 ventes » commune** vs **« ≤12 » comparables** — deux périmètres, désormais **explicités** au PDF (M124-C8). |
| RTAA DOM (rappel réglementaire) | `config rtaa_dom` | absent du payload | **ÉCRAN✗** | Affiché **seulement si `constructible`** (M124-C9). |
| COMPARABLES DVF (table locale) | `marche_service.comparables` (rayon/3 ans, LIMIT 12) | `dvf_parcelle` (profils VEFA/secteur, différents) | **⚠** | Profils DVF distincts entre les deux surfaces (§6). |
| PLAN DE SITUATION (ortho) | `plan_situation.plan_ortho` | carte séparée | **ÉCRAN✗** | — |
| CHARGE FONCIÈRE « selon vos hypothèses » | `_calculette_for_pdf` (query params) | onglet Bilan (fetch séparé) | **⚠** | — |
| ANC + RÉHABILITATION (cartouches) | `blocs_documents` (`fiche.anc`, `fiche.mode_b`) | ANC dans Viabilisation ; Mode B dans un drawer | **=** (données) / **⚠** (forme) | — |

---

## 6. Points d'arbitrage pour Vic (aucune action prise)

1. **Adresse à deux résolveurs** (`adresse` payload vs `adresse_ban` endpoint) : unifier la source
   pour garantir écran = papier au mot près. *(§1)*
2. **Beaucoup de DONNÉES pures écran absentes du PDF** *(§4)* : `reglement_plu`, `viabilisation`,
   `gestionnaires`, `proximites`, `territoire_fiscal`, `historique_site`, `voisinage_proche`,
   `data_sources` (liste par-fiche)… Si « PDF = données pures », plusieurs méritent d'y figurer.
   **Décision produit requise** : périmètre du PDF vs de la fiche écran.
3. **Deux périmètres DVF** : le PDF `comparables` (rayon/3 ans, ≤12) et l'écran `dvf_parcelle`
   (profils VEFA/secteur) ne comptent pas la même population. M124-C8 a **explicité** les libellés ;
   reste à décider s'il faut **unifier** les fenêtres. *(§3/§5)*
4. **Données MORTES dans le contrat** (`completeness_score`, `score_v`, `anru`, `terrain`,
   `coproprietes`, `marche_secteur`, `parc_analysees`, `flags`) : servies par `_q_v2_fiche`, rendues
   nulle part (ni écran ni PDF). À surfacer ou à retirer du payload. *(§2 + ci-dessous)*
5. **SDP** : confirmer que le message unique du PDF (§3) est bien la hiérarchie voulue
   (SDP résiduelle au sol → surélévation à défaut).

### Annexe — champs `_q_v2_fiche` rendus NULLE PART (MORT)

`completeness_score`, `score_v`, `anru`, `terrain`, `coproprietes`, `marche_secteur`,
`parc_analysees`, `flags`. *(Conservés dans le contrat API pour d'autres consommateurs — à trancher.)*

---

*Généré pour M124-D. Ne modifie aucun comportement ; sert de base d'arbitrage.*
