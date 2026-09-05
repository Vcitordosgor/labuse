# INVENTAIRE T1 — barres de recherche de l'app (RETOURS-12)

> Livrable du mandat RETOURS-12, travail T1. Inventaire exhaustif des barres de
> recherche, de l'état de la résolution, et du stockage section/numéro en base.

## 1. Barres de recherche

| Fichier | Ligne | Écran/Outil | Moteur appelé | Grammaire acceptée aujourd'hui |
|---|---|---|---|---|
| header/Header.tsx | 205-212 | Barre globale (Omnibox) | banAutocomplete + searchParcels + multi-type | IDU 14 ✓, section+numéro ✓, SIREN/SIRET ✓, nom proprio ✓, projet ✓, commune ✓, adresse ✓ |
| outils/EtudierBien.tsx | 80-83 | Étudier un bien | ParcelInput → AddressAutocomplete | IDU 14 ✓, adresse ✓ |
| outils/Faisabilite.tsx | ~26 | Faisabilité (ParcelPicker) | ParcelInput → AddressAutocomplete | IDU 14 ✓, adresse ✓ |
| outils/blocB.tsx | 52 | Pièges & risques | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/PluAnnuaire.tsx | 115 | PLU Annuaire | /modules/plu-annuaire/search | Texte libre (full-text règlement) |
| outils/ScanPatrimoine.tsx | 127-128 | Scan patrimoine | input data-scan-search → resoudre() local | Nom ✓, SIREN ✓, IDU 14 ✓, adresse ✓ |
| outils/ProspectionSolaire.tsx | 268 | Prospection solaire | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/TimeMachine.tsx | ~156 | Remonter le temps | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/ModulePanel.tsx | 494-502 | Permis | AddressAutocomplete (onEnterRaw) | Adresse ✓, commune ✓, n° permis ✓, IDU ✓ |
| outils/ModulePanel.tsx | 1056 | Courrier propriétaire | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/ModulePanel.tsx | 1194 | Diligence/Audit | ParcelInput | IDU 14 ✓, section+numéro annoncé (placeholder) mais NON résolu, adresse ✓ |
| outils/RadarView.tsx | 473-479 | Radar | AddressAutocomplete | IDU 14 ✓, commune ✓, adresse ✓ |
| outils/VeillePromoteurs.tsx | 180 | Veille promoteurs | AddressAutocomplete | Adresse ✓, IDU ✓ |
| outils/EtudeZone.tsx | 186 | Étude de zone | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/Renouvellement.tsx | 76 | Densifier l'existant | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/MonSecteur.tsx | 133 | Mon secteur | ParcelInput | IDU 14 ✓, adresse ✓ |
| outils/VerifProcedure.tsx | 28-30 | Vérif procédure PLU | champ texte direct | IDU 14 ✓ |
| outils/moteurs.tsx | 397-398 | ZAN | input data-zan-idu | IDU 14 ✓ |
| crm/Kanban.tsx | 472 | CRM | input search | Texte libre (filtre local) |
| sources/SourcesPage.tsx | 245 | Sources | input data-sources-search | Texte libre (filtre local) |
| fiche/Fiche.tsx | 1083 | Intra-fiche (loupe) | input data-fiche-search | Texte libre (filtre contenu fiche) |
| admin/Flux.tsx | 226 | Admin Flux | input value=recherche | Texte libre |
| projets/ProjetKanban.tsx | 394 | Projets/Assemblage | barre RETIRÉE (RETOURS-3 R9) | — |

## 2. État de la résolution (endpoints backend)

| Endpoint | Fichier:Ligne | Grammaire |
|---|---|---|
| GET /adresses/autocomplete | api/app.py:2210 | BAN interne (table adresses), adresse + idu |
| GET /parcels/search | api/app.py:2258 | IDU complet OU portion finale (section+numéro) via `ILIKE '%'+needle` |
| GET /modules/patrimoine/search | api/modules.py:196 | Nom PM (dénomination MAJIC pliée) |
| GET /modules/patrimoine | api/modules.py:231 | Inventaire d'un SIREN posé |
| GET /proprietaires/autocomplete | api/app.py:2478 | Nom propriétaire |
| GET /modules/plu-annuaire/search | api/modules.py:1929 | Full-text règlement |

**Omnibox (Header.tsx 119-179)** est DÉJÀ un moteur unifié multi-type, mais **limité au header**. Ordre : IDU explicite → SIREN/SIRET → nom proprio → projet → commune → IDU partiel/section+numéro → adresse. Les autres barres réutilisent partiellement (ParcelInput) ou refont une variante locale (ScanPatrimoine, Permis).

## 3. Stockage section/numéro en base

Table `parcels` : `idu VARCHAR(14) PK` = INSEE(5)+préfixe(3)+section(2)+numéro(4) ; colonnes `section`, `numero` stockées séparément (nullable). La recherche courte actuelle se fait sur `idu ILIKE '%'+needle` (pas sur les colonnes section/numero) → `?q=AC0253` → `idu ILIKE '%AC0253'`, matche tout IDU finissant ainsi (ambigu multi-communes).

## 4. Recommandation

- Moteur unique côté backend `recherche/resolveur.py` (parallèle de `geocode.py`), exposé par `GET /search/resolve?q=&commune=` renvoyant un type discriminé (parcel / parcels_ambiguous / owner / address / not_found).
- Normalisation section+numéro : `^[A-Z]{2}\d{1,4}$` (casse, espaces, zéros de tête), résolu sur colonnes `section`+`numero` (numéro zfill 4), désambiguïsation par commune (liste des candidates : commune + surface + zone).
- Rebrancher en priorité les barres qui prennent une parcelle en entrée (ParcelInput + Omnibox + ScanPatrimoine + Permis + Diligence).
