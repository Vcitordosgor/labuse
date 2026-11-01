# FIX-NU3-1 — chiffres et libellés (compte-rendu)

**Branche** `fix/nu3-1` · worktree `~/Desktop/labuse-fix1` · ports 9400/6600 (réservés) · base Mac `labuse`
run servi **q_v20 (run 17)** · **aucun merge, aucun accès prod**. Deux sessions sœurs tournaient
(FIX-NU3-2 : Copilote/carte/filtres/comptes/a11y ; FIX-NU3-3 : jobs/admin/chaîne) — leurs fichiers n'ont
pas été touchés.

Mandat : refermer les écarts de **chiffres et libellés** des lots **J, O, G, M** + la borne taxe,
chaque écart rejoué sur son témoin, suite de cohérence verte, banc complet 0 rouge, hook vert.

## Recette

| Vérification | Résultat |
|---|---|
| Suite de cohérence (`scripts/ci/coherence_run.sh`, run 17 servi, 12 témoins, égalité 1 €/1 m²) | **6 passed, 0 écart** ✅ |
| Banc Python unitaire (`pytest -m "not db and not local and not reel and not network"`) | **2813 passed / 0 rouge** (48 skipped) ✅ |
| Front `tsc -b` | **0 erreur** ✅ |
| Front `vitest run` | **266 tests passed** ✅ (8 suites « 0 test » = artefact du `node_modules` symlinké vers le worktree voisin : vite refuse le worker maplibre hors racine ; non lié au code — tsc propre + 266 tests verts) |
| Décisions de Vic respectées | Flash livre le Dossier, seul le **sous-titre** change (M-T02) ; palier « Priorité » reste masqué partout ; noms de particuliers **non** masqués (J02 RGPD non touché) |

> Un test-garde a été **mis à jour** et non contourné : `test_f31_blocb_zan_horizon_sans_defaut_fabrique`
> épinglait l'ancienne expression front `horizon < 5` que le correctif OUT-COMMUNE-019 remplace
> volontairement par le `statut` servi par l'API (palier ≤ 5 ans) — la garde vérifie désormais la
> nouvelle vérité (couleur pilotée par le statut API, toujours « pas de 99 fabriqué »).

## Table des identifiants traités

### Lot J — vérité & même vérité (10 écarts)

| ID | Correctif | Fichier(s) | État |
|---|---|---|---|
| J#1 | Faisabilité : dès que la zone du verdict ne couvre pas 100 % de la parcelle → « {zone} sur {pct} % » **et** drapeau à cheval levé si minoritaire, **indépendamment du seuil 90 %** (une parcelle 93 % N / 7 % Uf ne se titre plus « Uf » nu) | `api/modules.py` (`faisabilite_sens1`) | ✅ |
| J#2 | Dossier « Prix ancien médian » : type du bien affiché + **caveat de fiabilité** (fragile/insuffisant dit) ; plus de bâti en tête d'un terrain nu | `exports/miroir.py`, `exports/robinet_fiche.py` | ✅ |
| J#3 | Médiane de marché fiche == comparateur (déjà : le comparateur lit `prix_ancien` de la fiche, DOCS-COHERENCE A8) ; Estimer garde son comparateur **typé** (ESTIMER-2) — libellés distincts | — | ✅ (fiche=comparateur) · Estimer by-design |
| J#4 | Nombre d'aléas = familles DISTINCTES (`distinct_hazards`), **compteur unique** fiche (`aleas.n_hazards`) == Estimer (`n_aleas`) == PDF (`_risques_rows`) | `pige/api.py`, `api/app.py`, `fiche/risques.tsx`, `lib/types.ts` | ✅ |
| J#5 | « Surface libre » retranche la part en **PPR zone rouge** (inconstructible L562-1) comme l'emprise imperméable (AO0010 : 100 % rouge → 0 libre, plus « 696 563 m² ») | `bati.py` | ✅ |
| J#6 | Seconde « pente moyenne » de `/exposition` **retirée** (elle contredisait la table source sur 115/117) | `faisabilite/exposition.py`, `lib/api.ts` | ✅ |
| J#7 | Type de propriétaire : vocabulaire partagé, le caractère **PUBLIC** ne disparaît plus sur le comparateur (règle unique `PUBLIC_DGFIP_GROUPES`, comme le badge liste/carte) | `proprietaire_type.py`, `api/app.py`, `compare/ComparePanel.tsx` | ✅ |
| J#8 | Taux de bâti du comparateur = même **dénominateur** (surface de terrain contenance) que la fiche | `api/app.py` | ✅ |
| J#9 | Parcelles servies par la fiche et absentes de la carte = **décision produit assumée** (carte = gisement, ne peint pas les écartées) — documentée | — | 📄 documenté |
| J#10 | VEFA hors de la chaîne « ancien » : déjà exclu des médianes (`sector_price` filtre `vefa`, `comparables` filtre `nature_mutation='Vente'`) — vérifié | — | ✅ (déjà en place) |

### Lot O — les 34 écarts

| ID | Correctif | Fichier(s) | État |
|---|---|---|---|
| DOC-DOSSIER-045 | SCOT « approuvé le {date} » **seulement si `statut` est approuvé** ; sinon statut réel (« en projet ») | `exports/robinet_fiche.py`, `api/fiche_blocs3.py` | ✅ |
| CF-013 | Bande **« Hors classement »** (HC) rendue dans la ventilation et le `bande_total` (425 691 → vrai 432 350) | `api/app.py` | ✅ |
| FP-B-039 | Bloc **« Signal de marché »** désormais servi par la fiche premium (`_q_v2_fiche`) | `api/app.py` | ✅ |
| OUT-ASSEMB-001/002/013 | Assemblage : surfaces d'assiette et items sur la **contenance cadastrale** (COALESCE), pas le dessin | `assemblage.py`, `api/moteurs.py` | ✅ |
| OUT-CALC-003 | Calculette : surface de terrain = **contenance** (homogène Comparer/Estimer/Dossier) | `api/modules.py` | ✅ |
| OUT-SCAN-003 | Scan « surface totale » = somme des **contenances** | `api/modules.py` | ✅ |
| OUT-SECTEUR-005 | « Commune entière » qui l'est vraiment : médiane DVF **de la commune** (`mediane_commune` via `_dvf_bati_type`), par type, plus le `sector_price` au centroïde | `api/mon_secteur.py` | ✅ |
| OUT-ZONE-032 | « Loyer médian · commune » = **médiane des secteurs OLL** de la commune (plus le secteur le plus bas) | `zone.py` (fork) | ✅ |
| OUT-COMPARER-009 | Charge foncière Comparer (bilan calibré) ≠ Calculette (hypothèses saisies + prix neuf) : **deux méthodes légitimes** — reporté, décision Vic sur la méthode canonique à trancher (voir Notes) | — | 📄 reporté |
| OUT-CALC-006 | VRD : la phrase ne dit plus « sur {terrain} m² » (base × **emprise aménagée**, pas le terrain) | `fiche/constructibilite.tsx` (fork) | ✅ |
| OUT-PERMIS-009 | Compteurs c100/c200 = **COUNT exacts** (plus le `len()` d'une liste plafonnée à 100) ; `affiches`/`tronque` servis | `api/modules.py` | ✅ |
| OUT-PLU-008 | « N affichés sur M » (total réel via `count_reglement`, plus le compte plafonné pris pour le total) | `api/modules.py`, `ingestion/plu_ingest.py`, `outils/PluAnnuaire.tsx`, `lib/api.ts` | ✅ |
| OUT-SCAN-006 | Blocs contigus : « N affichés sur M » (liste plafonnée à 12 dite) | `api/modules.py`, `outils/ModulePanel.tsx` | ✅ |
| OUT-PERMIS-011 | Fenêtre Permis : « sur toute la profondeur Sitadel servie » (plus « 240 derniers mois ») | `outils/ModulePanel.tsx` (fork) | ✅ |
| OUT-PERMIS-017 | Colonne **commune** peuplée dans les items `/modules/permis` | `api/modules.py` | ✅ |
| DOC-APPORTEUR-018 | §6 **ICPE** : la description + distance (orpheline) est désormais rendue | `exports/builder.py`, `exports/blocs/apporteur.py` (fork) | ✅ |
| DOC-APPORTEUR-017 | §6 **Ligne HT** : branche morte supprimée (aucune donnée source dans le socle — plus de question jamais déclenchable) | `exports/builder.py`, `exports/blocs/apporteur.py` (fork) | ✅ |
| DOC-ETUDEZONE-013 | Lignes **Risques / Assainissement** de l'Étude de zone : clé `libelle` ajoutée aux producteurs → rendues | `zone.py`, `exports/blocs/etude_zone.py` (fork) | ✅ |
| DOC-DOSSIER-063 | **Fibre** : libellé lisible (ou `detail`), plus l'enum brut `aucun_immeuble` | `exports/miroir.py` | ✅ |
| DOC-ESTIMER-009 | Exposition **fiche == Estimer == Dossier** : le robinet lit `exposition_parcelle` (comme l'écran et Estimer), plus le calcul 4-points d'`enrichment` | `exports/robinet_fiche.py` | ✅ |
| DOC-ETUDE-029 | « Espaces libres · dont pleine terre » → libellé aligné à la valeur (« Pleine terre ») | `exports/etude_faisabilite.py` (fork) | ✅ |
| FP-B-060 | « Parc social » : ligne « % QPV » retirée (champ non servi, 100 % sur les 24 communes = mal ingéré) | `fiche/MarcheSecteurBlock.tsx` | ✅ |
| OUT-SECTEUR-004 | « Tendance » ne dit plus « 12 m » (comparaison récent↔ancien sur l'échantillon retenu, pivot = année médiane) | `outils/MonSecteur.tsx` | ✅ |
| OUT-SECTEUR-007 | « {n} écartés (extrêmes + hors domaine) » (plus « (5 %) » faux sur petits échantillons) | `outils/MonSecteur.tsx` (fork) | ✅ |
| OUT-SECTEUR-009 | Cellule vide par type : « échantillon < **8** » (SEUIL_N), plus « < 5 » | `outils/MonSecteur.tsx` (fork) | ✅ |
| OUT-ZONE-007 | « postes salariés **estimés (tranches d'effectif)** » (plus « déclarés », qui sur-promettait) | `zone.py` (fork) | ✅ |
| OUT-COMMUNE-010 | Légende terrain nu : seuil **10** ventes (config `terrain_cellule_commune:10`), plus « 5 » | `outils/blocB.tsx` (fork) | ✅ |
| OUT-COMMUNE-018 | Barre ZAN : lit `pct_budget_restant` **servi** par l'API (plus de recalcul front ni plancher 4 % trompeur) | `outils/blocB.tsx` (fork) | ✅ |
| OUT-COMMUNE-019 | Statut rareté : ton de couleur piloté par le `statut` **servi** (palier ≤ 5 ans), un seul vocabulaire | `outils/blocB.tsx` (fork) | ✅ |
| OUT-ZONE-013 / OUT-ZONE-016 | Champ JSON `seuil` = **8** (SEUIL_N), plus « 5 » trompeur | `zone.py` (fork) | ✅ |
| O-32 / O-33 (OUT-ZONE-013/016 « servi ≠ live ») | Confirmé **artefact Mac** (snapshot DVF ≠ `dvf_mutations`, cf. PROD-VERIF-1 — pas d'accès prod) ; le `seuil` trompeur, lui, est corrigé | — | 📄 artefact Mac (seuil corrigé) |

### Lot G — parcours clients

| ID | Correctif | Fichier(s) | État |
|---|---|---|---|
| G-003 | Surface 907 vs 913 : Estimer et Assemblage servent la **contenance** (907), comme fiche/comparateur | `pige/api.py`, `assemblage.py`, `api/moteurs.py` | ✅ |
| G-004 | Dossier d'un terrain nu ne met plus un **bâti** en tête (gaté sur `etat_bien == "nu"`) ; fiche met déjà le terrain en tête | `exports/robinet_fiche.py` | ✅ (Dossier) |
| G-005 | Dossier reporte le qualificatif **type + fiabilité** (mixte/fragile) sur le prix de tête | `exports/miroir.py` | ✅ |
| G-007 | Assemblage : surface d'assiette alignée (contenance). **Bornage de la SDP cumulée à la part en zone constructible + % hors zone** = reporté (change de capacité, voir Notes) | `assemblage.py`, `api/moteurs.py` | ◑ partiel |
| G-009 | Trois €/m² : fiche == comparateur (même source) ; Estimer typé distinct (ESTIMER-2) — cf. J#3 | — | ✅ / by-design |
| G-010 | Terrain nu : plus de « Prix ancien médian » bâti en tête du Dossier (= G-004) | `exports/robinet_fiche.py` | ✅ |
| G-012 | Copilote « prix médian maison » : **outil Copilote (domaine FIX-NU3-2)** — non touché pour éviter la collision ; la médiane maison est disponible via `marche_dvf_commune.mediane_commune(commune,'maison')` | — | 📄 déféré (session 2) |
| G-014 | Compteur de risques identique fiche/Estimer = **J#4** (`distinct_hazards`) | voir J#4 | ✅ |

### Lot M — textes & aide

| ID | Correctif | Fichier(s) | État |
|---|---|---|---|
| M-T01 | « SDP restante » **partout** (libellés/messages/tooltips, PDF compris) — plus de « SDP résiduelle » pour la même grandeur `sdp_residuelle_m2` | `fiche/Fiche.tsx`, `outils/Blocs.tsx`, `compare/ComparePanel.tsx`, `exports/blocs/comparatif.py`, `copilote_v2/resume_fiche.py` | ✅ |
| M-T02 | Sous-titre du Flash : « Pré-analyse d'une parcelle » (ne reprend plus « Étude de faisabilité ») | `flash/templates/rapport.html.j2` | ✅ |
| M-H01 | Aide « Info classement » / tri : « d'abord le potentiel (bande), puis la probabilité de vente » (aligné sur `_cle_classement`) | `lib/strings.ts` (fork) | ✅ |
| M-H02 | Infobulle comparateur : « par type du bien » (plus « appartements priorisés », méthode supprimée par FIX-FINAL-1) | `outils/blocB.tsx` (fork) | ✅ |
| M-H03 | Badge copro : « hors univers de classement (copropriété) » (exclusion inconditionnelle) | `fiche/ScoreV2Block.tsx` (fork) | ✅ |
| M-H04 | Tip Loyers OLL : maille = **ZONE OLL** (6 zones), pas la commune | `fiche/marche.tsx` (fork) | ✅ |
| M-H05 | Fourchette ±30 % « indicative » (plus « incertitude mesurée », qui survendait une marge forfaitaire) | `fiche/marche.tsx` (fork) | ✅ |

### Fiscal (hors-402)

| ID | Correctif | Fichier | État |
|---|---|---|---|
| OUT-TAXE-EXTRA-BOUNDARY | Exonération petites surfaces : borne **inclusive** `≤ 5 m²` (CGI 1635 quater D, 10° ; BOFiP BOI-IF-TU-10-20-30-160) — à 5 m² pile, exonéré | `taxe_amenagement.py` | ✅ |

### Décision de Vic — palier « Priorité »

Aucune surface n'annonce le palier **Priorité** du classement : `PRIORITE_SERVIE=false` (légende carte à
3 éléments ; `codePalier` résout `priorite→a_suivre`), fiche/filtres gatés sur ce drapeau, PDF idem. Le
registre CA-002 (« Priorité listé comme servi ») est donc un **fait de registre périmé**, le produit le
masque déjà — aucun code à changer. (La notion CRM « priorité dossier » est distincte et hors périmètre.)

## Notes — écarts reportés / partiels (avec plan)

- **OUT-COMPARER-009** (charge foncière Comparer ≠ Calculette, ×3,5) : deux méthodes légitimes — Comparer
  sert le bilan **calibré par secteur** (`fiche_payload.bilan`), la Calculette applique les **hypothèses
  saisies** + prix neuf. Les rendre identiques exige que Vic tranche la méthode canonique (ou qu'on
  signale explicitement les hypothèses de chaque écran). Non résolu faute de décision produit.
- **G-007** (Assemblage ↔ Étude) : la **surface** d'assiette est désormais la contenance (OUT-ASSEMB) et
  le ton/`sdp_m2` viennent déjà du moteur de capacité sur l'union (`aggregate_assiette`). Reste à
  **borner l'affichage « SDP cumulée ×N » à la part en zone constructible et afficher le % hors zone** —
  changement de capacité (intersection zone U/AU dans `aggregate_assiette`), reporté pour ne pas
  déstabiliser le moteur d'implantation partagé.
- **G-012** (Copilote prix médian maison) : l'outil `marche` du Copilote relève de **FIX-NU3-2** ; non
  touché pour éviter une collision inter-sessions. Donnée disponible : `mediane_commune(commune,'maison')`.
- **J#9** (parcelles absentes de la carte) : décision produit assumée (la carte = le gisement, ne peint
  pas les parcelles écartées) ; à documenter côté UI, pas un bug de chiffre.
- **O-32/O-33** : « instantané DVF servi ≠ table live » = artefact du Mac (PROD-VERIF-1), à confirmer en
  prod ; le défaut de **libellé** attaché (`seuil:5`) est corrigé.

## Méthode des reproductions

Chaque écart a été rejoué sur sa cause `fichier:ligne` (lecture avant/après) et, pour les faits chiffrés,
re-vérifié par la **suite de cohérence** (12 témoins, égalité stricte fiche↔outils↔PDF) et le **banc
complet** (2813 tests). Les labels front sont validés par `tsc -b` (0 erreur) et `vitest` (266 tests).
Trois agents forkés ont traité des grappes de fichiers disjointes (labels front ; Étude de zone ;
Apporteur PDF) ; leurs sorties ont été re-typées et banchées ici.
