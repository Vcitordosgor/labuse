# ETUDE-ZONE-2 — Étoffer « Étude de zone » : 7 sections, faits sourcés et datés

Branche `feat/etude-zone-2` (worktree `labuse-etudezone2`, base main `5f44ecec` = ETUDE-ZONE-1
+ PIEGES-RISQUES-2 mergés). Non mergé. Outil `frontend/src/components/outils/EtudeZone.tsx` ·
moteur `src/labuse/zone.py` · endpoint `POST /outils/etude-zone`.

Doctrine tenue : chaque chiffre = un fait, sa source, son millésime ; jamais une projection ;
les données à maille commune sont dites « à l'échelle de la commune ». **Règle transversale : chaque
agrégation réutilise un point de calcul existant** (jamais de recalcul maison — c'est ce qui avait
produit le 100 888 €/m² en ETUDE-ZONE-1).

Deux témoins : **T1** = 3 Chemin de la Citerne (parcelle `97411000BZ1065`, 97417 Saint-Denis),
10 min voiture (isochrone) · **T2** = zone dessinée Saint-Paul (box ~324 ha, centre).

---

## Lot A — Résultat en 7 sections repliables (commit `fd68e590`)

Le panneau passe d'une **liste plate** (~12 indicateurs à la file) à **7 accordéons** dans l'ordre du
mandat : **Population · Économie · Immobilier · Foncier · Contraintes · Équipements · Dynamique**.
Composant `Section` (chevron `▸` fermé / `▾` ouvert = idiome de l'outil, ligne « Source · millésime »
en bas). Population + Économie ouvertes par défaut, les autres repliées. Indicateurs existants
redistribués, rien perdu (ActifsStat → Économie ; trafic + générateurs → Équipements ; zone de demain
→ Immobilier ; zones PLU + destinations → Contraintes).

Captures : `avant-t1-citerne.png` / `avant-t2-saintpaul.png` (liste plate, état main) vs
`apres-t1-citerne.png` / `apres-t2-saintpaul.png` (7 sections). Prises sur l'app réelle
(back `:8335`, front `:5535`).

---

## Lot B — Ajouts par section (commit `671071a0`)

Chaque agrégateur (dans `zone.py`) et son point de calcul réutilisé :

| Section | Ajout | Point de calcul réutilisé | Source · millésime |
|---|---|---|---|
| **Population** | Structure d'âge par tranche, pondérée par la part de surface d'IRIS dans la zone | `iris_rp` (déjà lu par `population_zone` pour vacance/bâti) | RP 2022 (INSEE, par IRIS) |
| **Immobilier** | Prix médian €/m² **par type** (maison / appartement / terrain nu), 36 mois | `flash.data._marche` (table `dvf_mutations` maille mutation, `vente%`, bâti≥20 / terrain≥100) | DVF (DGFiP/Etalab) |
| **Immobilier** | Permis **par type** (logements / locaux d'activité), 36 mois | `sitadel_permits.raw->>'famille'` | Sitadel (SDES) |
| **Foncier** | **Top 5 propriétaires PM** par surface cumulée (SIREN, dénomination, nb parcelles) | `parcelle_personne_morale` par SIREN (jointure Scan patrimoine) | DGFiP — parcelles PM |
| **Contraintes** | **PPR** rouge (interdiction) / bleu (prescription), % de la zone | couche DEAL `spatial_layers` kind=`ppr` (comme Pièges & risques) | DEAL Réunion (Lizmap) |
| **Contraintes** | **Aléas** par niveau (fort/moyen/faible) par type, % de la zone | couche `georisque_alea` (`attrs->>'niveau'`) | DEAL Réunion |
| **Contraintes** | **Assainissement** collectif vs ANC, % de la zone | couche `zonage_assainissement` (subtype collectif/anc) | GPU (communes SIG) |
| **Contraintes** | **Espaces protégés** (ZNIEFF, ENS, Parc) + **ZFANG / FRR / QPV**, % recouvrement | couches `spatial_layers` (union clippée) | INPN / Légifrance / ANCT |
| **Équipements** | **BPE complet A→G** (compte par domaine + 3 plus proches) | `spatial_layers` kind=`amenite_bpe` (comme `equipements_proches`) | BPE (INSEE) |
| **Dynamique** | **Acquisitions PM récentes** (dernier millésime vs précédent) | `pm_proprietaires_millesimes` (2024 vs 2023) | DGFiP — parcelles PM |
| **Dynamique** | **Loyer OLL** (médian €/m²) — à l'échelle de la commune | `oll_loyers` × `oll_zonage` (secteur OLL) | OLL 2024 |
| **Dynamique** | **Fibre FttH** (% immeubles raccordables) — sur la zone | `arcep_immeubles` ∩ zone (déjà servi par l'endpoint) | Arcep 2026_T1 |

Le % de recouvrement d'une catégorie = `ST_Area(ST_Intersection(ST_Union(geom_2975), zone)) /
ST_Area(zone)` sur `geom_2975` (union pour ne jamais compter deux fois un chevauchement interne).

---

## Lot C — Vérification data (recompte SQL indépendant = valeur affichée)

Recompte sur le **même polygone** que le témoin T2 (box Saint-Paul), par une requête SQL
indépendante de l'agrégateur. Écart nul partout (≤ ±1 %).

| Indicateur | Table / champ | Millésime | Affiché (module) | Recompte SQL | OK |
|---|---|---|---|---|---|
| Structure d'âge — pop. pondérée IRIS | `iris_rp.pop` × part surface | RP 2022 | 4 556 | 4 556 | ✅ |
| Structure d'âge — 0–14 ans | `iris_rp.pop_0014` | RP 2022 | 21 % | 21 % | ✅ |
| Prix médian Maison | `dvf_mutations` valeur/bâti | DVF 36 m | n=30 · 4 329 €/m² | n=30 · 4 329 | ✅ |
| Prix médian Appartement | idem | DVF 36 m | n=57 · 4 937 €/m² | n=57 · 4 937 | ✅ |
| Prix médian Terrain nu | `dvf_mutations` valeur/terrain | DVF 36 m | n=0 → « — » (< 5 ventes) | n=0 | ✅ |
| Top PM #1 (Commune de Saint-Paul) | `parcelle_personne_morale`+`parcels.surface_m2` | DGFiP 2025 | 144 parc · 155 352 m² | 144 · 155 352 | ✅ |
| PPR rouge (interdiction) | `spatial_layers` ppr | DEAL | 20 % | 20 % | ✅ |
| PPR bleu (prescription) | `spatial_layers` ppr | DEAL | 13 % | 13 % | ✅ |
| Assainissement collectif | `zonage_assainissement` | GPU | 47 % | 47 % | ✅ |
| ZFANG (recouvrement) | `spatial_layers` zfang | Légifrance | 71 % | 71 % | ✅ |
| QPV (recouvrement) | `spatial_layers` qpv | ANCT | 10 % | 10 % | ✅ |
| BPE domaine D (Santé) | `spatial_layers` amenite_bpe | BPE INSEE | 257 | 257 | ✅ |
| Acquisitions PM (2023→2024) | `pm_proprietaires_millesimes` | DGFiP | 33 parcelles | 33 | ✅ |
| Loyer médian commune | `oll_loyers` | OLL 2024 | 11 €/m² | 11 | ✅ |
| Fibre FttH (zone) | `arcep_immeubles` | Arcep 2026 | 97,7 % | (ST_Intersects zone) | ✅ |

(Recompte transverse aussi vérifié sur la buffer 900 m — mêmes écarts nuls.)

---

## Temps de réponse (endpoint, 2 témoins)

| Témoin | Compute | Note |
|---|---|---|
| T1 (isochrone, 1er appel) | **7,9 s** | inclut l'appel réseau IGN (isochrone), **caché 30 jours** (design existant) |
| T1 (isochrone, en cache) | **2,3 s** | calcul pur |
| T2 (polygone Saint-Paul) | **4,7 s** | calcul pur, sous 5 s |

**Section la plus coûteuse : les risques** (`risques_zone`, ~3,4 s) — `georisque_alea` compte 917
polygones de mouvement de terrain, unis par niveau. Optimisation déjà appliquée : **clip-then-union**
(intersecter chaque feature avec la zone AVANT de l'unir → morceaux petits) a ramené la section de
**15,2 s à 3,4 s** sans rien dégrader (valeurs identiques). Le calcur reste sous 5 s ; si l'on voulait
gagner encore, la piste serait de **précalculer/cacher les % PPR-aléa par zone** (les couches DEAL sont
statiques) — non fait ici pour ne pas ajouter d'état, le budget étant tenu.

---

## Ce qui est explicitement reporté (hors mandat / non servi honnêtement)

- **Bande LABUSE (parcelles à potentiel)** et **nu constructible en ha** : PAS dans ce mandat —
  attendent la bascule q_v15 (dit dans le mandat). La section Foncier ne porte donc que le top 5 PM.
- **BODACC** (procédures collectives des PM de la zone) : hors mandat, non ajouté.
- **Évolution démographique 2016→2022** : `iris_rp` ne porte que le millésime RP2022 (aucune
  population 2016 en base) → seule la **structure d'âge 2022** est servie, l'évolution est dite
  « non servie » à l'écran, jamais inventée. (Ajouter une source 2016 = hors mandat « pas de nouvelle
  source ».)
- **Permis commerce vs activité** : la **famille** Sitadel distingue fiablement logements / locaux
  d'activité ; le sous-split commerce/activité repose sur le code `destination` (SDES) non décodé en
  base — non deviné (dit en note à l'écran). À reprendre avec la table de correspondance SDES.
- **Loyers OLL / fibre** : loyer servi **à l'échelle de la commune** (maille secteur OLL, dit tel
  quel) ; la fibre est, elle, servie **zonalement** (immeubles Arcep ∩ zone), meilleure que la commune.

---

## Tests
- Front : `tsc --noEmit` vert · `vitest` **178/178**.
- Back : `pytest` zone (`test_zone_donnees/recette/1/moteur/norm`) **29/29**.
- Endpoint réel : les 11 blocs B présents sur les 2 témoins ; recompte Lot C à l'identique.

## Recette navigateur (environnement)
Back `:8335`, front `:5535`. La base était libre (aucun calcul lourd — vérifié avant lancement).
Captures via **node playwright direct** (chromium-1217) après retrait de la carte WebGL
(`window.__labuse_map.remove()`, le screenshot MCP expire sur la carte) ; polygone T2 injecté via
`window.__labuse.setZone(...)` (le dessin manuel n'est pas automatisable) ; avant/après capturés par
`cp` de côté + `git checkout <main> -- fichier` + HMR + restauration (jamais `git stash`). Scripts de
capture jetables supprimés avant commit.
