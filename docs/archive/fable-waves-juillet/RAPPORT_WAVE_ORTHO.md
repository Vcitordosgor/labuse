# Rapport de fin — mandat Wave Détection Ortho (piscines, PV, pente) · 12/07/2026

**Branche** : `feat/wave-ortho-detection` (17 commits atomiques, jamais mergée — merge Vic
`--no-ff`). **Clôture : Option B** (décision Vic — piscines matérialisées avec précision
mesurée en interne, PV en stub, dette v1.1 tracée ci-dessous).
**QA** : 21/21 pytest + E2E Playwright **10/10** (`qa/e2e_wave_ortho.mjs` : 2 vues
piscinistes chargent/filtrent/exportent non-vide, badges fiche, stub PV, quota outil,
2 viewports).

## Millésime & tuiles

- **BD ORTHO 974 millésime 2025** (20 cm, fiche IGN des prises de vues) — l'âge de
  l'image = l'âge de la vérité terrain. Accès WMS Géoplateforme EPSG:2975 natif
  (choisi vs ~50-80 Go de dalles JP2).
- **5 041 tuiles utiles** (512 m, bâti ∪ parkings — océan/remparts ignorés),
  acquisition 100 %, 0 échec. **Couverture traitement : 5 041/5 041 = 1.0** ✓.
- Cache purgé en clôture (5,6 Go → 0, contrainte disque) ; tables conservées.
  `data/ml` conservé (399 Mo : crops + embeddings + verdicts = dataset v1.1).

## Volumétries par type

| Objet | Volume | Statut |
|---|---|---|
| Détections piscine (candidats V0 calibrés) | 19 899 | scorées probe + FLAIR |
| **Parcelles piscine matérialisées** | **8 299** | `parcel_equipements.piscine` + signal |
| Candidats PV (dont CES probables 4-8 m²) | 23 529 (10 056) | **STUB — en base, non matérialisés** |
| Parkings APER passés `equipe = TRUE` (ombrières) | 153 | appliqué |
| Pente non bâtie (`parcel_terrain.pente_non_batie_deg`) | 383 051/423 452 | job checkpointé, finit seul |

Critère volumétrie (15 000-45 000 piscines attendues) : les 19 899 candidats y sont ;
la matérialisation à 8 299 est un choix de PRÉCISION (juge), pas un défaut de détection.

## Précision / recall — matrice des seuils retenus

**Méthodologie** : 1 619 verdicts Vic ; **300 sanctuarisés** (stratifiés confiance ×
commune) jamais utilisés pour régler quoi que ce soit ; règles choisies sur les 1 319
d'entraînement (probas croisées 5-fold), UNE mesure sanctuaire par règle pré-déclarée.

| Juge (piscines) | Précision | Rappel des vrais |
|---|---|---|
| V0 colorimétrique seule (profil strict) | 79,3 % | — |
| Probe DINOv2+logreg (meilleur point) | 85,4 % | 74,5 % |
| VLM Haiku seul | 64,8 % | 87,9 % |
| FLAIR-INC seul (≥ 0,3) | 81,4 % | 89,2 % |
| **RETENU : FLAIR ≥ 0,30 ET probe ≥ 0,50** | **90,7 %** | **74,5 %** |

Matérialisé : juge ∪ verdicts humains 'ok'. **Libellé produit (Option B)** :
« précision **90,7 % mesurée sur échantillon indépendant interne** » — affiché sur les
presets, la fiche (badges) et le filtre. Recall global estimé ≈ 55-65 % des piscines
bleues visibles (rappel juge 74,5 % × recall V0 amont ; eau sombre/couverte exclue par
construction). Seuils : `config/detection_ortho.yaml` (piscines V0 + materialisation.juge).

**Sessions du 11/07 soir invalidées** (vérité : bug outil — verdicts décalés par
l'auto-répétition clavier + quota inopérant sans ?profil ; preuves en planches, piscines
évidentes et une centrale PV marquées « faux positif »). Les 472 verdicts sont
conservés dans `ortho_verdicts_quarantaine` (audit) et EXCLUS de toute métrique.
L'outil est blindé depuis (verdict refusé avant affichage image, 300 ms mini,
touche maintenue ignorée, quota au POST → 409, re-validation refusée).

## Taux d'équipement piscine par commune (matérialisé, parcelles bâties)

Top 5 : La Possession 6,2 % · L'Étang-Salé 6,0 % · Saint-Paul 4,9 % · Saint-Denis 4,7 %
· Les Avirons ~3,7 %. Flop : Plaine-des-Palmistes, Cilaos, Salazie, Sainte-Rose (~1 %).
Gradient Ouest/Sud > Est conforme au critère du mandat ✓.

## Statut PV (Lot 4) — resté en CANDIDATS (stub)

23 529 candidats scorés en base (`ortho_detections type='pv'`, criteres + confiance),
dont 10 056 CES probables (signal « pas de chauffe-eau à vendre ici » prêt). PAS de
matérialisation (`materialiser_pv` auto-gated : il refuse tant qu'une validation
≥ 75 % n'existe pas — règle du mandat, inchangée). Les 153 ombrières parkings ont
été appliquées (`parkings_aper.equipe`), donnée factuelle indépendante du gating.

## Lot 8 ML — verdict

GO exécuté sous forme de **cascade de juges** (décision Vic) : le fine-tune n'a pas
été nécessaire — **FLAIR-INC (IGN, licence Etalab 2.0, classe piscine native) en
inférence pure × probe locale** a atteint le critère. 0 € de coût récurrent, 100 %
local, ~1 h de re-score île sur cette machine. Détail : `RAPPORT_CASCADE_JUGES.md`.

## ⚠ Dette v1.1 (Option B — à planifier)

1. **Certification sur vignettes fraîches** (100, `?profil=juge&quota=100`) → devient
   LE chiffre contractuel à la place de « échantillon indépendant interne ».
2. **Bande d'incertitude** (298, `?profil=bande&quota=298`) → vérité humaine sur les
   cas limites du juge.
3. **Validation PV** (150, `?type=pv&quota=150`) → si ≥ 75 % : matérialisation PV +
   `pv_existant='detecte'` + **repowering** (PV détecté × communes 2006-2013 — la seule
   voie de localisation) + signal `repowering_candidate`.
   Préalable technique aux 3 : re-télécharger les tuiles (cache purgé) —
   `UPDATE ortho_tiles SET acquise_at=NULL;` puis `labuse ortho-tiles` (~1 h).
4. Optionnel : ré-entraîner la probe avec les 1 319+ labels (les 226 récents n'ont
   pas été utilisés) — gain attendu modeste, re-mesure sanctuaire obligatoire.

## Contraintes respectées

Positionnement qualification commerciale uniquement (aucun code/texte fiscal) ✓ ·
RGPD exports « à l'occupant » ✓ · Attribution IGN + « fiabilité statistique, non
contractuelle » sur fiche/presets/exports ✓ · CPU only, checkpoint/reprise partout ✓ ·
Refresh par millésime (`labuse ortho-refresh`, pas de cron — re-survol ~3-4 ans) ✓.

## Avant merge (fait / à faire par Vic)

- FAIT : E2E 10/10, pytest 21/21, exports rouverts avec mention, purge cache, rapports.
- Le job de pente finit seul (~40 min restants au moment de la clôture) ; le sanity
  (bâties 6,5° < île 7,4°) est déjà vérifié.
- **À toi : merge `--no-ff` de `feat/wave-ortho-detection` (17 commits)**, et planifier
  la dette v1.1 (une session outil de ~45 min au total, tuiles à re-télécharger avant).
