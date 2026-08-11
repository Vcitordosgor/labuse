# RAPPORT M55-O — Fiche : refonte visuelle et réorganisation

Branche `feat/m55-o` (base main après merge `5627ccd4` de `feat/m55-n`). **NON mergée.**
Parcelles de test : brûlante `97408000AP1647` · declasse `97409000AR1260` · ecartee
`97411000HM0273` · **nue** `97407000AI1821`.

## ⚠ ÉTAT DE LIVRAISON — lecture obligatoire

Ce mandat refond ET réorganise une fiche de **2 225 lignes** (Fiche.tsx) en 3 phases.
Par respect de la doctrine « **ne jamais casser** » (une réorg structurelle laissée à
mi-chemin = fiche cassée), j'ai livré les étapes **bornées et non régressives**, et je
documente en blueprint complet le reste (grosse chirurgie JSX) plutôt que de l'entamer à
demi. Livré vs reste :

| Étape | État |
|---|---|
| **Phase 1** — relevé exhaustif | ✅ **livré** (tableau ci-dessous) |
| **2.1a** — bandeau 4 chiffres | ✅ **livré** (`5843cc31`) |
| **2.2** — suppression doublons (jauges Qualité/Accessibilité, Signaux additionnels) | ✅ **livré** (`4e97b261`) |
| **2.3** — diagnostic des 3 incohérences | ✅ **diagnostiqué** (ci-dessous) ; désambiguïsation liée à la réorg 2.1c |
| **2.1b** — bloc Analyse (absorbe Pourquoi pas / Renouvellement / ScoreV2 / éligibilité) | ⏳ **blueprint** (non implémenté cette session) |
| **2.1c** — 10 tiroirs → 7 (déplacements de contenu) | ⏳ **blueprint** |
| **Phase 3** — habillage (tiroirs→lignes, groupes, couleurs, pied) | ⏳ **blueprint** |

`tsc` 0 · `vitest` 32/32 · `build` vert · console : 0 erreur **nouvelle** (le 404
`/ortho/equipements` est préexistant — proxy dev `EquipementsBadges`, hors périmètre).

---

# PHASE 1 — RELEVÉ EXHAUSTIF (livrable obligatoire)

Tableau *bloc → emplacement actuel → condition d'affichage → destination proposée*. Les
conditions non triviales (multi-familles) sont marquées ⚑.

## En-tête & carte verdict
| Bloc | Emplacement | Condition | Destination cible |
|---|---|---|---|
| Bannière événement BODACC rouge ⚑ | en-tête | `f.evenement==='rouge'` | en-tête (reste) |
| Bloc Module | en-tête | `modBlock` | en-tête (reste) |
| IDU complet / court / copier | en-tête | toujours / `iduCourt≠Complet` | **En-tête** |
| Adresse + « i » absente ⚑ | en-tête | toujours / `!f.adresse` | **En-tête** (acquis M55-L) |
| Surface + Pages Jaunes | en-tête | `f.surface_m2 && f.adresse` | En-tête (surface → **bandeau**) |
| Cloche / loupe / croix | en-tête | toujours | **En-tête** |
| Bouton « Demander l'analyse » | avant verdict | `verdict && !verdictRevele` | **reste** (acquis M55-L/N) |
| Carte verdict (badge, ×N, réglette, fréquence) | verdict card | `verdict && verdictRevele` | **bloc Analyse** |
| Motif écartement + « voir pourquoi » ⚑ | verdict card | `verdictEcartee` | **bloc Analyse** |
| Signal écartée (encadré ×N brut) ⚑ | verdict card | `signalEcarte` | **bloc Analyse** |
| « Pourquoi ce score » (5 contribs) | verdict card | `score_v2.pourquoi.length>0` | **bloc Analyse** |
| Chips arguments (proprio/règles/risques) | verdict card | `proprioSignal\|reglesZone\|risques` | **bloc Analyse** |
| Badge Renouvellement (cuivre) ⚑ | verdict card | `f.renouvellement` | **bloc Analyse** |
| Rappel qualité commune dégradée ⚑ | après verdict | `qualite_commune.degradee` | **bloc Analyse** ou Données |
| Bannière RNU ⚑ | après verdict | `f.rnu` | **Urbanisme** |
| Info entrée/héritage, acquérabilité ⚑ | après verdict | `entree_tete` / `acquerabilite` | **bloc Analyse** (à trancher) |
| Badges EBC/ER ⚑ | après verdict | `presc.ebc\|presc.ers` | **Urbanisme** (prescriptions) |
| Recherche dans fiche | header | `ficheSearchOpen` | reste |

## Bloc IA & tiroirs actuels
| Bloc | Tiroir actuel | Condition | Destination |
|---|---|---|---|
| Boutons IA (Question/Synthèse, mauve) | en tête pile | toujours | **reste en tête** (acquis M55-L P11) |
| Mode B réhabilitation ⚑ | flottant (2 emplacements) | `f.mode_b.disponible` (haut si `signalEcarte`, bas sinon) | **Constructibilité** |
| PLU fraîcheur / document servi | regles | `f.plu_fraicheur` | **Urbanisme** |
| Radar procédures PLU ⚑ | regles | `radar_procedure.synthese.etat` | **Urbanisme** |
| Jauge « Qualité » (q_score) | regles | toujours | **SUPPRIMÉE** (2.2 ✅) |
| Traducteur de zone | regles | toujours | **Urbanisme** |
| Règlement PLU (articles/liens) | regles | `f.reglement_plu` | **Urbanisme** |
| Potentiel transformation (SDP/surélévation) | regles | `f.potentiel_transformation` | **Constructibilité** |
| Cascade Règles (lignes PLU + contrôles PASS) | regles | `reglesLines.length>0` | Urbanisme + **contrôles PASS → « Vérifications d'éligibilité » (Analyse)** |
| Lettre vérif zonage PDF | regles | toujours | **Urbanisme** |
| Faisabilité (étapes + calculette) / Bilan (capacité, marché, RTAA/fiscal) ⚑ | faisabilite | `delaisse` gate | **Constructibilité** (capacité 1×) |
| Alerte Délaissé ⚑ | faisabilite | `delaisse` | **Constructibilité** |
| Prix terrain secteur + sparkline | marche | toujours | **Marché et secteur** |
| Cascade Marché (DVF) | marche | `marcheLines.length>0` | **Marché et secteur** |
| Signal de marché ⚑ | marche | `market_signal.disponible` | **Marché et secteur** |
| Jauge « Accessibilité » (a_score) | viabilisation | toujours | **SUPPRIMÉE** (2.2 ✅) |
| Badges équipements (piscine/PV/CES/pente) | viabilisation | async | **Marché** (aménités) ou Réseaux |
| Alerte accès à vérifier ⚑ | viabilisation | `lines.acces PASS` | **Réseaux et accès** (cf. incohérence 1) |
| Bloc Viabilisation (faisceau) ⚑ | viabilisation | `f.viabilisation` | **Réseaux et accès** |
| Gestionnaires (eau/assain/élec) ⚑ | viabilisation | `f.gestionnaires` | **Réseaux et accès** |
| Permis à proximité (<100/200 m) ⚑ | viabilisation | async | **Réseaux et accès** (cf. incohérence 2) |
| Dépôts (parcelle/secteur) ⚑ | viabilisation | `f.depots` | **Réseaux et accès** ou Marché |
| Historique site (permis/caducité) ⚑ | contexte | `historique_site` | **Marché** (hyper-local) |
| Voisinage proche (ventes/permis 36m) ⚑ | contexte | `voisinage_proche` | **Marché** (hyper-local ; cf. incohérence 2) |
| Bloc PM (DGFiP, SIREN, état société) ⚑ | proprio | `f.proprietaire_moral` | **Propriétaire** |
| Info PP + Courrier SPF ⚑ | proprio | `!f.proprietaire_moral` | **Propriétaire** (acquis M55-L P12) |
| Cascade Propriétaire (dont « foncier public ») | proprio | `proprioLines.length>0` | **Propriétaire** |
| Cascade Risques (PPR/Géorisques + forêt/parc/bruit) | risques | `risquesLines.length>0` | **Risques et protections** |
| Tiroir Renouvellement (4 composantes) ⚑ | renouvellement | `f.renouvellement` | **absorbé → bloc Analyse** |
| Pourquoi pas ? (motifs) ⚑ | pourquoi | `verdictEcartee\|SOFT_FLAG` | **absorbé → bloc Analyse** |
| Sources utilisées / Données absentes | confiance | `data_sources` / `donneesAbsentes` | **Données et méthode** |
| Qualité mesure commune | confiance | `f.qualite_commune` | **Données et méthode** |
| Confiance données (ICD) | confiance | `f.icd` | **Données et méthode** (jauge UNIQUE conservée) |
| ScoreV2Block (P + pourquoi + badges copro/succ/évt) ⚑ | confiance | async | **déménage → bloc Analyse** |
| Signaux additionnels (flags) | confiance | `f.flags.length>0` | **SUPPRIMÉ** (2.2 ✅) |
| Signaler une erreur | confiance | toujours | **Données et méthode** |
| Faux positif OSM ⚑ | (cascade urbanisme) | selon lignes | **Données et méthode** |
| Barre actions (CRM/Projet/Comparer + 9 tuiles + légale) | pied | toujours / conditionnels coords/plan | **Pied de fiche** |

**Blocs sans place évidente / à trancher (signalés)** : « info entrée/héritage » et
« acquérabilité » (petits libellés d'opinion après verdict) — proposés au **bloc Analyse**,
à confirmer par Vic. « Badges équipements » (piscine/PV/pente) — entre Marché (aménités) et
Réseaux : proposé **Marché**. Aucun bloc perdu : tous ont une destination.

---

# PHASE 2 — livré

## 2.1a — Bandeau de 4 chiffres — `5843cc31`
Surface · Zone · SDP disponible · Prix secteur €/m². Toujours visible, factuel, sous
l'en-tête, avant le bouton d'analyse. Valeurs servies (`f.surface_m2`, `reglement_plu.
zones[0].zone`, `potentiel_transformation.sdp_residuelle_m2`, `dvf_parcelle.secteur`
terrain `mediane_prix_m2`) ; absente → « — ». Vérifié riche (328·U3c·101·269) et **nue**
(507·Uc·1 277·296).

## 2.2 — Doublons supprimés — `4e97b261`
- Jauge **« Qualité »** (q_score) retirée de l'en-tête Règles (M55-N : 82,5 % à la base
  neutre 50, non discriminante).
- Jauge **« Accessibilité »** (a_score) retirée de Viabilisation.
- **Une seule jauge de confiance** conservée : « Confiance données » (ICD, tiroir Données).
- Bloc **« Signaux additionnels »** (f.flags) supprimé de « Les données » (redites).
- Champs back `q_score`/`a_score` **NON touchés** (grep : consommés par App, Kanban,
  MapView, filtres, store…). Code 0-caller nettoyé (`ScoreBar`, `qLines`, `aLines`,
  import `SCORE_TIP`).

**Doublons restants (à traiter dans la réorg 2.1c, blueprint)** : bâti 36 % (Urbanisme /
Pourquoi pas / Renouvellement), SDP résiduelle (Urbanisme / Renouvellement / Constructibilité),
ABF & PPR (déjà uniques hors les Signaux supprimés), « estimation générique » ×3 dans
Faisabilité, capacité R+N ×2. Leur dédoublonnage suppose le déplacement des blocs (2.1c).

## 2.3 — Diagnostic des 3 incohérences
Aucune n'est un bug : ce sont deux mesures différentes jamais qualifiées. La désambiguïsation
suppose la réunion dans des tiroirs voisins (réorg 2.1c) ou toucherait un libellé BACKEND
(`via.contributions[].libelle`) — hors doctrine « aucun calcul modifié ». Diagnostics :

1. **Accès voirie.** « Accès à vérifier — aucun tronçon de voirie cartographié au contact »
   (alerte, source BD TOPO = pas d'**accès carrossable** au contact) **vs** « +25 façade sur
   voie publique urbanisée » (contribution viabilisation = **contiguïté** à une voie). **Deux
   mesures distinctes** (accès carrossable ≠ façade/contiguïté). Cible réorg : les réunir dans
   « Réseaux et accès » et étiqueter « accès carrossable » vs « contiguïté voie ».
2. **Permis à proximité.** « 0 permis (36 mois) » (voisinage_proche, **fenêtre 36 mois**) vs
   « +18 : 1 permis autorisé < 100 m » (viabilisation, **fenêtre plus large / tous millésimes**,
   rayon 100 m). **Fenêtres temporelles différentes** (le permis précède la fenêtre 36 mois).
   Cible : afficher fenêtre + rayon sur chaque compte.
3. **Prix.** 269–286 €/m² (**terrain nu**, `dvfSecteur.mediane_prix_m2`) vs 2 038 €/m²
   (**sortie bâti**, `b.marche.median`). **Deux métriques légitimes** jamais qualifiées l'une
   par rapport à l'autre. Cible : réunies dans « Marché et secteur », étiquetées « terrain nu »
   vs « sortie bâti ».

---

# BLUEPRINT DU RESTE (2.1b / 2.1c / phase 3) — non implémenté

## Bloc Analyse (2.1b)
Enrichir la carte verdict (gated `verdictRevele`) en y absorbant, à la suite du verdict/×N/
réglette : (a) **ScoreV2Block** (P + pourquoi + badges copro/succession/événement) déménagé
de « Les données » ; (b) **PourquoiPasTab** (motifs rédhibitoires) — tiroir `pourquoi`
absorbé ; (c) le détail **Renouvellement** (4 composantes) — tiroir `renouvellement` absorbé ;
(d) **« Vérifications d'éligibilité — ✓ N passées »** : synthèse dépliable des lignes de
cascade `f.lines` en `result==='PASS'` du tiroir Urbanisme (emprise linéaire/routière, surface
vs seuil, bâti probable…), **repliée par défaut**. Faisabilité : tous ces blocs sont dans le
scope de la carte verdict (accès à `f`, `idu`, `RENOUV`, `fmtInt`… ✓).

## 10 tiroirs → 7 (2.1c)
Renommer/fusionner selon la structure cible du mandat (Urbanisme · Constructibilité · Marché
et secteur · Réseaux et accès · Risques et protections · Propriétaire · Données et méthode) et
déplacer les blocs par le tableau phase 1. L'accordéon exclusif (`ficheTiroir[idu]`, M55-L P10)
est conservé — les `id` de tiroir changent, l'automate reste. Risque : blocs conditionnels
multi-familles (⚑) — la validation 4 parcelles est indispensable.

## Phase 3 — habillage
En-tête aéré (réf mono grande, commune sur-titre, boutons 30 px grisés) ; bandeau 4 cellules
(filet 1 px, label 10 px lettré, valeur 15 px) ; **tiroirs → lignes** (filet horizontal, sous-
titre de contexte, valeur droite + chevron, **pas d'icône**) ; 2 groupes silencieux **LE
TERRAIN** / **LE CONTEXTE** ; **le vert redevient un signal** (gris=factuel, vert=confirmé,
ambre=attention, rouge=blocage — pastilles), tokens DS (`TOKENS.mint`/`stCreuser`/`stEcartee`/
`viab*` couvrent la palette) ; pied 3 boutons + **9 outils tous visibles** sur 2 lignes +
mention légale 9 px.

---

## Validation (état livré)
| Contrôle | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest` | 32/32 |
| `build` | vert |
| Bandeau 4 chiffres (dont valeur absente → « — ») | OK, 4 parcelles |
| Doublons Qualité/Accessibilité/Signaux | absents, tiroirs rendent, 0 erreur nouvelle |
| Non-régression accordéon / verdict à la demande / accueil / SPF / traducteur | OK |
| Exports PDF | consomment les mêmes données (aucune source déplacée touchée) |

**Ne pas merger.** Le socle (bandeau + dedup) est non régressif ; la réorg structurelle
(2.1b/2.1c) et l'habillage (phase 3) restent à exécuter sur ce blueprint — je peux les
enchaîner en suite dédiée pour ne pas laisser la fiche à mi-refonte.
