# SAINT-PAUL — Audit qualité « gold standard »

> Objectif : faire de Saint-Paul (INSEE **97415**) la **commune étalon** de LA BUSE — complète,
> auditable, fiable, explicable — avant toute réplication sur les 23 autres communes.
>
> **Statut de ce document : DIAGNOSTIC (lecture seule).** Aucun import lancé, aucune donnée
> modifiée, aucun service redémarré, aucun merge. Diagnostic établi le 2026-06-20 sur la branche
> `claude/brave-davinci-NaRd4`.

---

## 1. État actuel — couverture cadastrale

| Mesure | Valeur | Source |
|---|---:|---|
| Parcelles Saint-Paul **chargées** (`parcels`) | **3 000** | base applicative |
| Parcelles Saint-Paul **réelles** (cadastre complet) | **51 129** | cadastre.data.gouv.fr (Etalab, `latest`) |
| **Taux de couverture** | **5,9 %** | 3 000 / 51 129 |
| Sections chargées / totales | **14 / 98** | base vs Etalab |
| Parcelles **manquantes** | **48 129** (94,1 %) | — |

**Source de vérité** : le GeoJSON bulk Etalab
`…/communes/974/97415/cadastre-97415-parcelles.json.gz` (5,6 Mo compressés, **51 129 features,
98 sections**) — c'est le même fichier que celui utilisé par l'ingestion (`ingestion/cadastre_bulk.py`).

### Pourquoi seulement ~3 000 ?
Ce n'est ni un bug ni un échantillon aléatoire : c'est un **passage borné** volontaire (brief §4 :
« on ne boucle pas l'API sur 40 000 parcelles »). Saint-Paul a été ingéré via
`labuse ingest-real --commune 97415` avec un **cap** (`--limit` / `bbox`), centré sur le **cœur
urbain**. Preuve : les 3 000 parcelles sont **concentrées géographiquement** —

| Section | BN | BO | BP | BV | BS | autres (10) |
|---|---:|---:|---:|---:|---:|---:|
| Parcelles | 1 029 | 668 | 637 | 245 | 146 | 275 |

→ BN + BO + BP = **78 %** des 3 000. Ce sont des sections « B* » (frange urbaine côtière). Les
3 000 sont donc une **ZONE pilote urbaine**, pas un échantillon d'opportunités ni des parcelles
filtrées par verdict. Verdicts actuels : **83 opportunités · 782 à creuser · 166 écartées ·
1 969 faux positifs** (le fort taux de faux positifs est normal en cœur urbain déjà bâti).

### Ce qui est DÉJÀ propre sur les 3 000 (vérifié, cf. `tests/test_saint_paul_quality.py`)
- **0 doublon d'IDU**, **0 géométrie invalide**, **0 `geom_2975` nulle**, IDU 14 car. préfixe 97415.
- **100 % évaluées** (toutes ont un verdict), **100 % avec zonage PLU**, index GIST présents.
- **Aucune « opportunité » bâtie à > 50 %** (le correctif R1 tient).
- Requête fiche représentative **< 1 s**.

> **Conclusion §1 :** ce qui est chargé est de **qualité gold standard**. Le seul écart majeur est
> la **couverture** (5,9 %). Saint-Paul n'est pas « sale », il est **incomplet**.

---

## 2. Écarts à 100 %

| Écart | Ampleur | Bloquant pour le modèle ? |
|---|---|---|
| **Parcelles manquantes** | 48 129 (94 %) — surtout les **Hauts** (sections hors frange urbaine) | 🔴 OUI — c'est LE chantier |
| **Couches « zone pilote »** (bâti, PPR, ravines, prescriptions) ingérées sur l'**emprise urbaine** seulement | à re-fetcher sur l'**emprise commune complète** | 🟠 OUI — sinon les Hauts auront une analyse risque/bâti incomplète |
| **PPR complet** | 4 entités (zones majeures, 55,9 % de couverture) ; détail prescriptif complet indisponible | 🟠 partiel — bloqué source (PEIGEO) |
| **Bilan promoteur** | valeurs `estimée` (placeholders) | 🟡 non bloquant — gabarit `bilan-calibrate` prêt (case C) |
| **Propriétaires nominatifs** | niveau 2 non implémenté | 🟡 non bloquant — verrou légal assumé |

---

## 3. Matrice qualité des données — Saint-Paul

Statut : ✅ complet · 🟧 partiel · ⛔ bloqué (source externe) · ⬜ absent.

| Couche | Statut | Source | Fraîcheur | Couverture SP | Fiabilité | Impact métier | Action |
|---|---|---|---|---|---|---|---|
| **Cadastre / parcelles** | 🟧 | Etalab cadastre.data.gouv.fr | `latest` | **5,9 %** (3 000/51 129) | Haute (propre) | 🔴 Critique | **LOT 2 — import complet** |
| **PLU / zonage** | ✅ | GPU / IGN (`plu_gpu_zone`) | GPU courant | **100 %** des parcelles | Haute | Critique | Rien (couvre l'île — vaut pour les 51 k) |
| **Règles d'urbanisme** | 🟧 | Prescriptions GPU + moteur faisabilité | GPU | prescriptions sur zone urbaine ; règles chiffrées par zone | Moyenne | Fort | Vérifier prescriptions sur les Hauts (LOT 2) |
| **SAR** | 🟧 (proxy) | ODS Région (`sar`, 303 entités) | millésime SAR | 0,7 % d'intersection (vocations ciblées) | Faible (indicatif) | Moyen | Garder en proxy non bloquant |
| **PPR / risques** | ⛔ partiel | PPR (`ppr`, 4 entités) | — | 55,9 % (zones majeures) | Moyenne | Fort | Détail complet **bloqué PEIGEO** |
| **BD TOPO / bâti** | 🟧 | BD TOPO IGN (`batiment`, 11 285) | BD TOPO | 81,6 % (emprise urbaine) | Haute | Fort (R1) | **Re-ingérer sur emprise complète** (LOT 2) |
| **Accès / voirie / enclavement** | ✅ | BD TOPO (`voirie`, 78 451, 17 comm.) | BD TOPO | 61 % à < 5 m | Moyenne (axes) | Fort | Rien (île) |
| **Pente / topographie** | ✅ | RGE ALTI (`pente`, 98 329) | RGE ALTI | **100 %** | Haute | Moyen | Rien |
| **DVF / prix de marché** | ✅ | DVF geo-dvf (`dvf_mutations`) | **2021–2025** | ~3 651 mutations SP | Haute | Fort | Rien (clé sur transactions) |
| **SITADEL** | ✅ | Région ODS (`sitadel_permits`) | **2017–2023** | 2 519 permis SP | Haute | Moyen | Rien |
| **Obsimmo (vente)** | ✅ | Dataset client (`data/obsimmo_*`) | **2026-06-19** | commune (100 %) | Sourcée | Fort | Rien |
| **Loyers** | ✅ | Carte des loyers DHUP (`data/carte_loyers_*`) | **2025** | commune (100 %) | Sourcée | Moyen | Rien |
| **Occupation INSEE** | ✅ | RP 2022 (`data/insee_occupation_*`) | **2022** | commune (100 %) | Sourcée | Moyen | Rien |
| **Potentiel d'assemblage** | ✅ | Calcul live (`voisinage.py`) | temps réel | dérivé | Haute | Moyen | Recalcul auto après LOT 2 |
| **Bilan promoteur** | 🟧 | Calibration `bilan_params` | placeholders `estimée` | commune | À affiner | Fort | **Case C** (`bilan-calibrate`) |
| **Propriétaires / prospection** | 🟧 | Fichiers fonciers Cerema (`parcelle_personne_morale`, 12 539) | sous convention | 12 539 parcelles SP (> 3 000 chargées) | Moyenne | Fort | Niveau 2 nominatif **bloqué légal** |
| **Exports / fiche PDF / fiche parcelle** | ✅ | `api/export.py` + CSS print | — | 100 % | Haute | Fort | Rien (PDF = print navigateur) |

> Note positive : la couche **propriétaires** (12 539 parcelles) est **plus large** que les 3 000
> chargées → l'import complet **révélera mécaniquement plus de propriétaires** (jointure par IDU).

---

## 4. Audit qualité parcelle (les 3 000 actuelles)

Chaque critère « la parcelle peut-elle produire une fiche propre ? » est **automatisé** dans
`tests/test_saint_paul_quality.py` (10 tests, **tous verts** au 2026-06-20) :

| Critère | Résultat |
|---|---|
| Géométrie valide (`ST_IsValid`, `geom_2975`) | ✅ 0 invalide |
| Commune correcte | ✅ toutes « Saint-Paul » |
| IDU propre (14 car., préfixe 97415) | ✅ 0 non conforme |
| Zonage trouvé | ✅ 100 % |
| Contraintes remontées (cascade) | ✅ 100 % évaluées |
| Verdict compréhensible | ✅ 4 régimes présents |
| Bilan calculable **ou** explicitement non calculable | ✅ (placeholders → « à affiner », jamais muet) |
| Raison du verdict compréhensible | ✅ accordéon « Pourquoi ce verdict » |
| Absence de « fausse opportunité » évidente | ✅ aucune opportunité bâtie > 50 % (R1) |
| Affichage propre dans la fiche | ✅ (refonte LOT 1, E2E verts) |

---

## 5. Tests Saint-Paul (livrés)

Fichier **`tests/test_saint_paul_quality.py`** — contrôles DATA-QUALITÉ **en lecture seule** sur la
base applicative (skip propre si données absentes / CI). Couvre : nombre minimal de parcelles,
absence de doublons IDU, géométries valides, IDU propre, index GIST présents, 100 % évaluées,
couverture zonage ≥ 95 %, échantillon des verdicts, anti-fausse-opportunité (R1), requête fiche < 1 s.

> Le **plancher** est aujourd'hui `MIN_PARCELS = 3000` ; il passera à **≥ 51 129** après le LOT 2
> (à monter dans le test au moment de la validation de l'import).

---

## 6. Données bloquées par source externe (on ne force pas)

| Donnée | Blocage | Levée |
|---|---|---|
| PPR détail prescriptif complet | serveur **PEIGEO** injoignable | whitelist PEIGEO (infra) |
| 50 pas géométriques / assainissement collectif | idem PEIGEO | idem |
| Propriétaires **nominatifs** | RGPD + convention | convention + AIPD |
| Annonces « à vendre » | pas d'open data ; ToS | convention SAFER/Vigifoncier |

Ces manques **ne dépendent pas de nous** : ils sont documentés, pas masqués. Le modèle Saint-Paul
peut être « gold standard » **avec** ces réserves explicites (badges « non vérifié » déjà en place).

---

## 7. Risques métier

| Risque | Probabilité | Mitigation |
|---|---|---|
| Import destructif (le `--reset` par défaut **vide toutes les communes**) | Élevée si commande naïve | **LOT 1 backup** + import **`--no-reset`** (cf. plan) |
| Doublons de couches (re-ingestion `spatial_layers` non dédupliquée) | Moyenne | Nettoyer les couches SP « zone pilote » avant re-ingestion sur emprise complète |
| Parcelles des Hauts sans bâti/PPR (couches non re-fetchées) | Moyenne | Re-ingérer bâti/PPR/ravines/prescriptions sur l'**emprise commune** |
| Explosion temps de calcul cascade (×17 parcelles) | Moyenne | Évaluer **hors démo**, par lots ; mesurer |
| Fiche lente après import | Faible | Index GIST déjà là ; tuning PG (pack VPS) |

---

## 8. Plan d'action — rendre Saint-Paul complet

### Faisabilité : ✅ OUI, proprement — MAIS pas en une commande
- `ingest_parcels` est **idempotent** (`ON CONFLICT (idu) DO UPDATE`) → ré-importer ne **duplique
  pas** les parcelles et **préserve** leur `id` (donc évaluations / pipeline / prospection / propriétaires liés).
- **MAIS** `ingest-real` a `reset=True` **par défaut** → il **VIDE** `parcels` (toutes communes) +
  re-ingère les couches. **Ne JAMAIS lancer la commande naïve.**
- **ET** `ingest-real` **n'évalue pas** : l'import pose les parcelles, le **recalcul cascade est une
  étape séparée** (LOT 3).

### Chemin contrôlé retenu
1. **Backup** (point de retour daté).
2. **Import parcelles** Saint-Paul complet : bulk Etalab (51 129) → `ingest_parcels` en
   **`--no-reset`** (dédup IDU, autres communes intactes, 3 000 pilotes préservées).
3. **Couches** : nettoyer puis re-ingérer les couches **spécifiques SP** (bâti, PPR, ravines,
   prescriptions) sur l'**emprise commune complète** ; les couches « île » (PLU, pente, voirie, DVF…)
   couvrent déjà les Hauts.
4. **Recalcul cascade** sur Saint-Paul (les 48 k nouvelles + cohérence d'ensemble).
5. **QA données + QA fiches** (tests + échantillon manuel).

### Impacts chiffrés (projection)
| Élément | Avant | Après import complet |
|---|---:|---:|
| Parcelles `parcels` (toutes communes) | 329 k | ~377 k (+48 k SP) |
| `cascade_results` | 3,47 M lignes / 596 Mo | ~4,0 M / ~680 Mo |
| `parcel_evaluations` | — | +48 k évaluations |
| Base sur disque | 1,3 Go | ~1,7 Go |
| Temps recalcul cascade (48 k parcelles) | — | à mesurer (lot, hors démo) |
| Rollback | — | restauration du dump du LOT 1 |

---

## 9. Plan d'exécution en LOTS (à valider avant le LOT 2)

| Lot | Contenu | Sûr maintenant ? |
|---|---|---|
| **LOT 1 — Backup & sécurité** | `labuse backup-db --dir /var/backups/labuse` ; vérifier la restauration ; figer un instantané des compteurs (parcelles, cascade, verdicts) | ✅ sûr |
| **LOT 2 — Import cadastre complet SP** | bulk Etalab 51 129 → `ingest_parcels` `--no-reset` ; re-ingestion ciblée des couches SP sur emprise complète ; **dédup vérifiée** | ⛔ **attend ta validation** |
| **LOT 3 — Recalcul cascade SP** | évaluer les 48 k nouvelles parcelles ; contrôler la distribution des verdicts (les Hauts ajoutent surtout des « écartées » zone A/N) | ⛔ après LOT 2 |
| **LOT 4 — QA données SP** | monter `MIN_PARCELS` à 51 129 ; relancer `test_saint_paul_quality` ; re-vérifier la couverture par couche | ⛔ après LOT 3 |
| **LOT 5 — QA fiches parcelles** | échantillon de fiches par verdict et par section (urbain + Hauts) ; E2E ; contrôle visuel | ⛔ après LOT 4 |
| **LOT 6 — Modèle reproductible** | documenter la « recette » exacte pour rejouer à l'identique sur les 23 autres communes | ⛔ après LOT 5 |

---

## 10. Checklist « Saint-Paul prêt à servir de modèle »

- [ ] **51 129 parcelles** chargées (98 sections) — couverture 100 %.
- [ ] 0 doublon IDU · 0 géométrie invalide · 100 % `geom_2975`.
- [ ] 100 % des parcelles **évaluées** (verdict présent).
- [ ] Zonage PLU ≥ 99 % · bâti/PPR/ravines re-ingérés sur **emprise complète**.
- [ ] Aucune « opportunité » bâtie > 50 % (R1) sur l'ensemble des 51 129.
- [ ] `tests/test_saint_paul_quality.py` vert avec `MIN_PARCELS = 51129`.
- [ ] Échantillon de fiches OK (urbain **et** Hauts) — verdict + bilan + marché + export.
- [ ] Réserves externes explicitement marquées (PPR/PEIGEO, propriétaires nominatifs, annonces).
- [ ] Bilan calibré (case C) **ou** placeholders assumés « à affiner ».
- [ ] **Recette reproductible documentée** (LOT 6) → « fais pareil pour la commune X » devient une
      duplication maîtrisée, paramétrée par l'INSEE.

---

*Diagnostic en lecture seule. Aucune donnée modifiée. Le LOT 2 (import) n'est pas lancé : il attend
la validation de ce diagnostic et du plan.*
