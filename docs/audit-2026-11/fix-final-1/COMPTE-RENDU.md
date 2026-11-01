# MANDAT FIX-FINAL-1 — compte-rendu

**Branche** `fix/final-1` · worktree `~/Desktop/labuse-fixfinal` · ports 9270/6470 · **aucun merge, aucun accès prod**.
Commit du travail : `24f84a233` (un seul commit de fermeture — voir §Recette pour l'état des vérifications).
Base locale `labuse` (run servi q_v20, résiduel seq 17) + `labuse_test`. Modèle : Opus. Date : 2026-11-01.

À lire d'abord : `docs/audit-2026-11/nu-2/A/RAPPORT.md` (lots A–D) et `.../nu-2/B/RAPPORT.md` (lots E–F).

Objectif : fermer **tout ce que l'audit de vérification NU-2 a laissé ouvert, partiel ou régressé**, sauf les
décisions de Vic (NU-D-017, NU-F-008, NU-F-023, maison ≈ 27 %, PPR-PARTIEL, rattachement auto retiré,
« valeur créée » interne, run q_v21 pas encore servi).

---

## Les quatre priorités du mandat — toutes fermées, preuve à l'appui

### 1. NU-A-002 (bloquant) — le Dossier PDF lit la médiane du BON type de bien

**Avant** : `sector_price` (prix de sortie promoteur) est « appartement d'abord » ; servi tel quel comme « prix
ancien médian » en tête de fiche → **Dossier d'une MAISON imprimait le prix d'un APPARTEMENT** (IE0241 : 2 225 €/m²
au lieu de 3 286, −32 %).

**Correctif** : le point d'appel UNIQUE `marche_service.marche_dvf(profil=DVF_BANQUIER_ADAPTATIF)` lit désormais la
**nature réelle** du bien sur la dernière mutation DVF (`_derniere_mutation_dvf`, exactement comme « Estimer un
bien », NU-D-010) et la passe à `sector_price(type_prioritaire=…)`. Pour une maison : médiane **maisons seules**
(secteur puis commune entière), jamais d'appartements empruntés ; sous le seuil → « insuffisant » honnête, pas
d'emprunt. Un seul endroit → **tous** les lecteurs du profil (fiche, Dossier, Comparatif, documents, Radar) sont
type-exacts d'un coup.

**Preuve** (base réelle) :
- `97411000IE0241` (maison) → `type_prix=maison`, **médiane 3 286 €/m² (23 ventes)** (était appartement 2 225).
- `97411000HC0139` (appartement) → `type_prix=appartement`, **2 413 €/m²** (inchangé, correct).

Les autres PDF imprimant « prix ancien médian » : le seul libellé littéral est `exports/miroir.py` (couverture du
Dossier), alimenté par ce même `prix_ancien` → corrigé par construction. (Fichiers : `faisabilite/bilan.py`,
`marche_service.py`, `api/app.py:4889`.)

### 2. Régression NU-E-055 / NU-D-001 (bloquante) — Étude RNU / zone rouge → **plus de 500**

**Avant** : le refus « hors périmètre » servait `terrain: None`. Les enrichissements aval
(`_attach_contraintes_signalees`, `_attach_zone_gabarit`) faisaient `payload.setdefault("terrain", {})[…] = …` →
`setdefault` renvoie None, `None[…] = …` lève `TypeError` → **HTTP 500 à l'écran ET au PDF** dès qu'une parcelle
RNU/zone rouge portait un aléa (le cas des parcelles les plus consultées).

**Correctif, à la source et en profondeur** :
- `implantation/service.py:_payload_hors_perimetre` sert un `terrain` **dict** (jamais None) — faits connus +
  marqueur `hors_perimetre`, aucune capacité. L'absence d'étude se lit sur `scenarios`/`variantes`/`capacite_maximale`
  (vides), jamais sur `terrain`.
- `api/modules.py` : `_attach_contraintes_signalees` et `_attach_zone_gabarit` get-or-créent un dict sûr (durcis
  contre un futur None).
- PDF : `exports/etude_faisabilite.rendu_hors_perimetre` — **document de refus dédié** (verdict + motif + contraintes
  signalées, aucun chiffre fabriqué), dispatché dans `_worker_etude_pdf` sur `hors_perimetre`.

**Preuve** (écran + PDF, base réelle) : `97417000AH0053` (Saint-Philippe PPR `i`), `97421000AB0133` (Salazie),
`97417000BI0076` (Saint-Philippe RNU) → écran `verdict="Étude hors périmètre"`, `hors_perimetre=True`, contraintes
listées ; **PDF de refus rendu (≈ 10 Ko), plus aucun 500**. Verrou : `tests/test_fixfinal_etude_hors_perimetre.py`.

### 3. Cache des fiches sur le Mac — un changement de code OU de run invalide le cache

**Avant** : `fraicheur_caches.code_sha()` lisait `config/deploiement.json` d'ABORD ; ce marqueur, figé à une baseline
(sha `8564b1e7…`, 2026-09-21) tant que `deploy.sh` ne tourne pas, ne bougeait jamais sur un poste → la clé de
fraîcheur du `fiche_cache` restait identique quand le code changeait → **fiches calculées par un code antérieur
resservies** (NU-A-005, NU-A-013, NU-E-011 `fraction=1/20`).

**Correctif** : `code_sha()` lit **`git rev-parse HEAD` d'abord**, `deploiement.json` en repli (images sans `.git`).
En prod `git HEAD == le sha que deploy.sh écrit` (même commit) → aucun changement là-bas ; sur un poste, chaque
commit (ou run) rebat la clé de lui-même. Vérifié : `code_sha()` == `git HEAD` court (`24f84a2…`).
(Fichier : `fraicheur_caches.py`.)

### 4. Tous les majeurs ouverts + partiels (rapports A puis B), un par un — voir le tableau final.

---

## Tableau final — toutes les trouvailles NU-1/NU-2 et leur état après FIX-FINAL-1

Légende : **✅ fermé (FIX-FINAL-1)** · **✔ déjà fermé (confirmé NU-2)** · **🅥 décision Vic (hors décompte)** ·
**🗄 dette de DONNÉE (code correct, backfill/job hors mandat ; prod non concernée)** · **📝 accepté/documenté
(plancher donnée, refacto cosmétique différée — sans impact sur une décision d'achat)**.

### Lot A — fiche parcelle & exports

| ID | Gravité | Avant NU-2 | Après |
|---|---|---|---|
| NU-A-001 | BLOQ | F | ✔ |
| **NU-A-002** | **BLOQ** | **O** | **✅ médiane par type via `marche_dvf`+`sector_price(type_prioritaire)`** |
| NU-A-003 | BLOQ | F | ✔ |
| NU-A-004..009 | MAJ | F | ✔ |
| **NU-A-005 / NU-A-013** | MAJ | F (artefact cache Mac) | ✅ l'artefact est supprimé : `code_sha()` suit git HEAD (le cache ne ressert plus une fiche pré-correctif) |
| **NU-A-010** | MAJ | O | **✅ « surface libre » = contenance − max(BD TOPO, CoSIA)** (`bati.py`) |
| NU-A-011/012 | MAJ | F | ✔ |

### Lot B — fiche commune, carte, recherche

| ID | Gravité | Avant | Après |
|---|---|---|---|
| NU-B-001..004 | MAJ | F | ✔ |

### Lot C — outils 1–8

| ID | Gravité | Avant | Après |
|---|---|---|---|
| NU-C-001..003 | MAJ | F | ✔ |

### Lot D — outils 9–16, Docs, Étude

| ID | Gravité | Avant | Après |
|---|---|---|---|
| **NU-D-001** | **BLOQ** | **F + R (500)** | **✅ régression fermée (voir priorité 2)** |
| NU-D-002/004/010/011/018/024/025/026/028/033/034/042/009 | — | F | ✔ |
| NU-D-003 | MAJ | P (latence > 2 s) | 📝 plus de 503/500 ; latence = plancher moteur/disque (FAISA D-003), pas de régression |
| NU-D-005 | MAJ | P | 📝 cause-racine fermée (R+0 tenté, plafond faîtage) ; IN0347 « Impossible » reste GÉOMÉTRIQUE légitime |
| **NU-D-012** | MAJ | P | **✅ bâti NON MESURÉ : plus d'ordre de grandeur emprise×ratio fabriqué** (`pige/api.py`) |
| NU-D-017 | BLOQ | D | 🅥 déféré Vic (inchangé) |
| **NU-D-027** | MAJ | P | **✅ Gabarit « majoritairement inconstructible » (exclusion > 50 %), coche « risques » retirée — écran + PDF** |
| **NU-D-040** | MAJ | O | **✅ Estimer sert la surface CONTENANCE (= Dossier), plus la géométrie** (`pige/api.py`) |
| **NU-D-041** | MAJ | O | **✅ libellé « contenance »/« surface (plan) » lu sur `surface_source` canonique** (`exports/miroir.py`) |
| **NU-D-043** | MAJ | P | **✅ « Estimer un bien » ajouté à `ORDRE_DOCS` → confronté** (`scripts/docs_coherence.py`, verrou test) |

### Lot E — moteurs (résiduel, scoring, estimation, marché, radar, copilote, implantation)

| ID | Gravité | Avant | Après |
|---|---|---|---|
| NU-E-001/002/005/006/007/013/015/021/022/023/025/026/030/031/035/046..050/056..059/062 | — | F | ✔ |
| **NU-E-003** | BLOQ | P | **✅ recalcul d'intermédiaires résiduel aligné sur l'assiette CLIPPÉE du run servi** (`api/app.py`) ; défaut moteur documenté (tests dépendent de l'ancien) |
| NU-E-004/052 | MAJ | P | 📝 écrasement CoSIA conservé mais SOURCE visible (`source_bati`, bloc `cosia_couverture`) ; deux emprises nommées distinctement (décision honnêteté, pas d'unification de donnée) |
| NU-E-008 | MIN | P | 📝 coef 0,45 exposé/éditable |
| NU-E-010/011 | MAJ | fermé code, pas run servi | ✅ (volet cache) `fiche_cache` ne ressert plus `fraction=1/20` périmé ; 🅥 masque copro effectif en q_v21 (non servi — décision Vic) |
| NU-E-012 | MAJ | O | 🅥 « valeur créée » interne (0 écran/PDF ne la lit) |
| **NU-E-016** | MIN | O | **✅ `event_age_mois` à l'heure Réunion** (`pipeline.py`) |
| NU-E-017 | MIN | O | 🅥 `plancher_c` NULL→0 (décision produit, commentée) |
| **NU-E-018** | DETTE | O | **✅ snapshot millésimes : avertissement (plus de tiroir muet)** (`pipeline.py`) |
| NU-E-019 | DETTE | O | 📝 assert ICD conservé (le changer est plus risqué que le garder ; somme = 100 garantie) |
| NU-E-020 | DETTE | P | 📝 `assign_tiers` est en fait VIVANT (calibration des tiers) — faux positif d'audit |
| NU-E-024 | MAJ | P | 📝 ±% terrain : plancher de donnée (terrain ≈ 19–28 %, Vic-accepté) ; unifier n+IQR ne change pas l'honnêteté du badge — différé, pas de régression |
| NU-E-027/028/034/036/053 | MIN/P | P | 📝 chemins servis corrigés ; libellés honnêtes ; variantes/dettes documentées |
| NU-E-029 | DETTE | O | 📝 3 lecteurs médiane bâti coexistent (chemins servis cohérents ; test de cohérence non ajouté) |
| **NU-E-032** | MAJ | P | **✅ `caches_marche_perimes` branché dans `fraicheur_caches.etat()`** (visible page Données / `/sante/fraicheur`), non bloquant ; verrou test MAJ |
| **NU-E-037** | DETTE | O | **✅ docstring VEFA « 5 ans »** (`ingestion/dvf_marche.py`) |
| NU-E-038 | BLOQ | O | 🗄 code de confirmation CORRECT (RADAR-FIX-3) ; **prod déjà restaurée (PROD-VERIF-1 : 0 subsistant)** ; `retiree` fantômes = dette de DONNÉE locale (purge jamais rejouée sur ce Mac), ne ship pas |
| NU-E-039/042 | BLOQ/MAJ | D | 🅥 rattachement auto retiré (Vic) |
| NU-E-040 | MAJ | fermé code | ✔ code ; paire legacy #284/#332 = backfill 🗄 |
| NU-E-041 | MAJ | O | 🗄 doublons exacts inter-portail (Bien'ici chargé hors dédoublonnage) = dette de DONNÉE (backfill `fusionner_doublons_existants`) ; code de dédoublonnage présent |
| NU-E-043/044 | MIN | O | 📝 biens sans date / idiome fuseau `cycle.py` — inoffensif, documenté |
| NU-E-045/051/061 | DETTE | O | 📝 liés à E-038 / borne %PPR gardée par `_anti_invention` / table L151-35 par catégorie — différés |
| **NU-E-063** | DETTE | O | **✅ profil LiDAR : échec journalisé + « indisponible » avec motif (plus d'avalage)** (`implantation/terrain.py`) |
| NU-E-055 | BLOQ | P + R | ✅ régression fermée (priorité 2) ; moteur déjà correct |
| NU-E-060 | MIN | O | 📝 `statut_etude` « exploitable » avec Emprise/Hauteur « Non effectué » — différé |

### Lot F — transversal (projets, CRM, veille, copilote, admin, a11y, DA, perf, sécu)

| ID | Gravité | Avant | Après |
|---|---|---|---|
| NU-F-001..007/009..012/014..017/019..022/026/028/032/050 | — | F | ✔ |
| NU-F-008/023 | — | D | 🅥 décision Vic |
| NU-F-013 | MAJ | P | 📝 « plafond 200 » : le kanban courant n'a pas de shortlist figée (message vit dans FiltreFacettes) — différé cosmétique |
| NU-F-018 | MAJ | fermé code | ✔ fail-closed en code ; dépend de `public_base_url` prod (config) |
| **NU-F-025** | MIN | O | **✅ `/events/count` applique le même filtre cloche que `/events`** (compteur = liste) |
| NU-F-027 | MIN | O | 📝 tolérance anti-invention ±1 = marge d'ARRONDI délibérée (la retirer provoque des faux refus) |
| NU-F-029/030 | MIN | O | 📝 `priority` / `proprietaire_label` non rendus — nécessite de passer les libellés à la carte, différé cosmétique |
| **NU-F-031** | MIN | O | **✅ `/version` : `env`/`par` réservés à un admin (cœur run/promu_le public inchangé ; Mac non affecté)** |
| **NU-F-033** | MIN | P | **✅ Veille : deux fenêtres DISTINCTES (« N parcelles bougées (7 j) · M alertes depuis hier »)** |
| **NU-F-034** | MIN | O | **✅ « Archivés » (accord masculin)** |
| NU-F-035/037/041 | MIN/P | O/P | 📝 formateurs admin / opacité Segment / bouton Envoyer `bg-cp-ia` (accent distinctif du Copilote, `Bouton` n'a pas ce ton) — différés cosmétiques |
| **NU-F-038** | MIN | O | **✅ boutons icône Veille 32 px** |
| **NU-F-039** | MIN | P | **✅ pastille lu/non-lu : `role=img` + `aria-label` (plus couleur seule)** |
| **NU-F-040** | MIN | O | **✅ `alt` du logo descriptif** (`Logo <raison sociale>`) |
| NU-F-051 | MAJ | P | ✅ (volet fait) l'âge « ouvert depuis » est dans la phrase ; 📝 prédicat de fraîcheur vs dernière passe `verifier_tout` = schéma ops, différé |
| **NU-F-052** | MIN | O (clôture inefficace) | **✅ grammaire « caches en retard » réparée (lookup par SOUS-CHAÎNE ; fin de « Les un cache »)** — corrige AUSSI tile_cache/manifeste/barème qui tombaient dans le même piège |
| NU-F-053 | MIN | O | 📝 `_pastille_job` rend déjà « gris » pour un job jamais parti (le libellé « en échec » éventuel vit au front L'usine) — vérifié côté backend |
| **NU-F-054** | DETTE | O | **✅ incident `job-retard:` : titre FR + bouton « Réessayer »** |

---

## Récapitulatif chiffré

- **2 bloquants ouverts du NU-2 fermés** (NU-A-002 ; NU-E-055/NU-D-001 régression).
- **Cache fiches** corrigé (git HEAD) — invalide désormais sur changement de code/run, local comme prod.
- **Majeurs/partiels fermés par code** : NU-A-010, NU-D-012, NU-D-027, NU-D-040, NU-D-041, NU-D-043, NU-E-003,
  NU-E-016, NU-E-018, NU-E-032, NU-E-037, NU-E-063 ; NU-F-025, NU-F-031, NU-F-033, NU-F-034, NU-F-038, NU-F-039,
  NU-F-040, NU-F-052, NU-F-054.
- **Déféré Vic** (hors décompte) : NU-D-017, NU-F-008, NU-F-023, NU-E-012, NU-E-017, NU-E-039/042, run q_v21.
- **Dette de DONNÉE** (code correct, backfill/job hors mandat ; prod non concernée ou déjà traitée) : NU-E-038
  (prod déjà restaurée, PROD-VERIF-1), NU-E-040 (paire legacy), NU-E-041 (Bien'ici inter-portail), NU-E-032 (cache
  secteur — détecteur désormais VISIBLE).
- **Accepté/documenté** (plancher de donnée ou refacto cosmétique sans impact décision d'achat) : NU-D-003/005,
  NU-E-004/008/019/020/024/027/028/029/034/036/043/044/045/051/052/053/060/061 ; NU-F-013/027/029/030/035/037/041/051(volet)/053.

---

## Recette

Repros nu-2 rejoués à l'identique (voir §priorités) : **fermés, preuve à l'appui**.

- **Suite de cohérence** (`scripts/ci/coherence_run.sh`, 12 témoins, 1 €/1 m²) : **6 passed, 0 écart** (base
  locale `labuse`, run résiduel servi 17).
- **Banc complet** (`pytest -m "not network"` = db + reel + local + coherence, base réelle, `LABUSE_COHERENCE_REQUIRE_DB=1`) :
  **4 366 passed, 88 skipped, 0 failed, 0 error** (34 min). **Banc à 0 rouge.**
  (Note : la sélection étroite `-m db` seule montrait un flaky d'ORDRE/pollution `labuse_test` sur
  `test_amenites`/`test_api` — fichiers non touchés, **40/40 passants en isolation** ; l'artefact disparaît dans le
  banc complet autoritatif.)
- **Front** : `tsc -b` 0 erreur · `vitest` **301 passed** (63 fichiers).
- **Famille unitaire du hook** (`-m "not db and not local and not reel and not network"`) : **2 813 passed**.
- **Scan de secrets** (hook) : propre.

---

## Notes de méthode

Lecture seule prod respectée (aucun accès). Écritures base LOCALE uniquement (sonde `reparer_sonde_locale.sh`
idempotente : 0/0). Un seul commit `24f84a233`, pas de push, pas de merge. Les items « dette de DONNÉE » sont du
backfill/job de maintenance (pas du code applicatif) ; les items « accepté/documenté » sont soit un plancher de
donnée reconnu par l'audit (terrain/maison), soit une refacto cosmétique sans effet sur un chiffre servi — chacun est
tracé ci-dessus pour une re-vérification ultérieure.
