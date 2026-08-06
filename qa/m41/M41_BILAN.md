# M41 — BILAN (Radar Procédures PLU, 24 communes)

**Branche `m41-radar-procedures-plu`** · base `main` ec0aef91 (M40 mergé) · commits atomiques
`[M41-Px]`. **Aucun changement de tier, aucune bascule, aucun merge.** Le radar dit le STADE d'une
procédure et ses conséquences juridiques ACTUELLES — **jamais son issue** (le Zoning Signal reste rayé).

---

## Le fil (constat P0 → arbitrages Vic → socle & fiche)

Squelette **Sudocuh** (data.gouv.fr, Licence Ouverte 2.0, millésime 31/12/2024) + chair **registre
curaté** `config/veille_plu.yaml`. Constat P0 (`M41_P0_CONSTAT.md`) : les 24 communes 974 sont dans
Sudocuh, mais **Sudocuh est périmé d'un an+** — 11 « en cours » bruts → **4 cibles genuine** après
réconciliation avec M40 ; le **stade** (débat PADD, seuil du sursis) est **ABSENT** partout ; base
légale corrigée sur pièces (**L.153-11 : sursis dès le débat PADD**, pas « projet arrêté »).

---

## PHASE 1 — Socle & registre

### P1.1 · Ingestion Sudocuh aux conventions millésime — commit `[M41-P1]`
`scripts/m41_ingest_sudocuh.py` : table de provenance `sudocuh_procedures` (24 communes 974) +
`data_sources` daté (millésime « 31/12/2024 », horizon 2024-12-31). Entrée `sudocuh` dans
`fraicheur.SOURCES`, **cadence_norme absente comme gpu_plu** → `check_fraicheur` **ne l'alarme pas**
(un Sudocuh d'un an n'est pas une faute : la chair curatée est la vérité servie).

### P1.2 · Registre + lint (confiance obligatoire) — commit `[M41-P1]`
`config/veille_plu.yaml` (24 communes, seed reproductible `scripts/m41_seed_veille_plu.py`, puis
curation main). Schéma strict, **`confiance` OBLIGATOIRE** — le lint (`labuse.veille_plu.lint`) refuse
toute entrée incomplète / sans confiance / DEDUIT sans raisonnement. Répartition (validée au STOP) :

| régime | n | servi en vigilance ? |
|---|---|---|
| **cibles** (révision/élaboration SOURCE) | 4 : Saint-André, Saint-Leu, Trois-Bassins, Saint-Philippe (dormante) | oui (sauf dormante) |
| **clôturées** (DEDUIT, raisonnement écrit) | 7 | non (on ne sert pas une inférence) |
| **aucune** (SOURCE, absence datée) | 13 | non (rien à servir) |

**Le radar ne SERT en vigilance que les entrées confiance=SOURCE.** Point de calcul UNIQUE
`src/labuse/veille_plu.py` (fiche, vigilances, outil, futur preset M45 lisent ICI).

### P1.3 · Geste trimestriel — commit `[M41-P1]`
`scripts/veille_plu_check.py` : lint + liste à re-vérifier (**90 j défaut, 30 j radar actif**) +
`--diff`. **Vide juste après la curation** (tout frais) ; à +45 j sortent **seulement les 3 cibles
actives** (seuil 30 j) ; à +106 j les 24 (testé).

### D · Bug M40 corrigé + passe de vérif des 24 lignes — commit `[M41-P1]`
`config/plu_millesimes.yaml` Trois-Bassins : `date_mairie 2022-06-02 → 2017-02-21`. Le 2022-06-02
était la **date de PRESCRIPTION** de la révision (Sudocuh), pas l'approbation de l'opposable
(2017-02-21, Sudocuh). idurba GPU conservé (discordance GPU↔Sudocuh flaggée pour M40-bis). **Passe
des 24 lignes** : un seul bug (Trois-Bassins) ; les autres écarts = M40 légitimement **plus frais**
que le Sudocuh périmé (approbations 2025-2026).

---

## PHASE 2 — Fiche & vigilances

### P2.1 · Bloc M40 enrichi + radar en fiche — commit `[M41-P2]`
`_plu_fraicheur` : « en cours — non servi » précisé pour les cibles SOURCE (« révision générale du
PLU, prescrite le X (Sourcé Sudocuh 31/12/2024, constaté le Y) »). Nouveau bloc fiche
**`radar_procedure`** (`_build_fiche` + `_q_v2_fiche`, golden-invisible comme `plu_fraicheur`) : stade
+ conséquences parcellaires servables. Rendu one-pager (`export.py`) + front (`Fiche.tsx`, `tsc -b` 0).

### P2.2/2.3 · Vigilances sursis & veille AU — commit `[M41-P2]`
- **Sursis à statuer** : servi UNIQUEMENT si `debat_padd` constaté (sourcé). **DARK aujourd'hui**
  (PADD ABSENT pour les 4 cibles) → la fiche dit « sursis : non servi (débat PADD non constaté) »,
  **jamais un conditionnel flou** (arbitrage Vic). Base légale L.153-11 + L.424-1 en dépliable. Le
  test `test_sursis_s_arme_quand_padd_source` prouve qu'il s'allume dès qu'un PADD sourcé est curé.
- **Veille AU** : sur les déclassées zone-fermée/AU des cibles → « ouverture possible à terme, à
  suivre (aucune certitude, ne préjuge pas de l'issue) ». **Ne remonte AUCUN tier.** Population :
  Saint-André 217, Saint-Leu 119, Trois-Bassins 75 = **411 déclassées** (Saint-Philippe RNU : 0).

### P2.4 · Synthèse commune — dans le bloc radar (stade + prochaine étape connue).

### P2.6 (addendum) · Outil « Vérif procédure » — commit `[M41-P2]`
Endpoint `GET /modules/verif-procedure/{idu}` + outil front (`VerifProcedure.tsx`, registre O11,
groupe Analyser). Entrée IDU → commune en procédure OUI/NON. **OUI** : type, stade, date de l'acte,
source, date de constat, confiance, + conséquences (sursis si armé / veille AU si la parcelle est
concernée). **NON** : « Aucune procédure PLU en cours servie au JJ/MM — … Dernier constat le X »
(**l'absence est datée aussi**). L'outil **LIT le radar** (point de calcul unique), il ne calcule rien.

---

## VÉRIFICATION (2026-08-06)

| Contrôle | Résultat |
|---|---|
| **Golden** | **117/117 PASS, 0 FAIL** (radar_procedure = bloc fiche golden-invisible, vérifié) |
| **Re-mesure M34/M35** | **0 divergence — PASS** |
| **SHA256 vigilances M37** | `482da6f6…e9abe9` — **INCHANGÉ** |
| **Tiers servis** | **0 tier modifié** (119 brûlante / 1041 chaude) |
| **pytest** | verts (+ tests veille_plu) — 5 échecs pré-existants (residuel×4, au_ouverture×1) |
| **lint registre** | passe (24 communes, confiance partout) |
| **geste trimestriel** | liste **vide** juste après curation ; détecte une entrée vieillie (testé) |
| **tsc -b (front)** | exit 0 |

**Écritures DB, toutes hors scoring et tracées** : `sudocuh_procedures` (provenance, 24 lignes) +
`data_sources` (catalogue). Aucune écriture `parcel_p_score_v2` / run / cache / cascade.

### Captures (`qa/m41/screens/`)
1. `1_radar_saint_leu_procedure_sursis_dark.png` — fiche Saint-Leu : bloc radar (révision prescrite
   2022-05-17) + **sursis non servi** (débat PADD non constaté) + base légale.
2. `2_veille_au_saint_leu.png` — fiche déclassée AU : **veille AU** (ouverture possible à terme).
3. `3_temoin_saint_pierre_sans_procedure.png` — commune sans procédure : **aucun bloc parasite**.
4. `4_outil_idu_en_procedure.png` — outil « Vérif procédure » : IDU en procédure (Saint-Leu).
5. `5_outil_idu_sans_procedure.png` — outil : IDU sans procédure (absence datée).

### Curation à venir (STOP Phase 0, non figé par le clone)
- **Débat PADD** des 3 cibles réelles (Saint-André, Saint-Leu, Trois-Bassins) : à trouver ensemble
  (`qa/m41/curation_padd_urls.md`). Tant qu'un PADD n'est pas sourcé, le sursis reste DARK.
- **7 clôturées** : confirmer par délibération d'approbation (→ SOURCE) ou laisser DEDUIT (hors radar).

---

## DOCTRINE rappelée / dégagée
- **La fraîcheur est celle de la source amont, et chaque affirmation porte sa source ET sa date de
  constat** (l'absence est datée aussi). Appliqué partout dans le registre + l'outil.
- **Une note de config est une affirmation d'agent, pas une source** (M40) — re-confirmé : Sudocuh
  périmé + le bug M40 Trois-Bassins, tous deux attrapés sur pièces.
- **On ne sert pas une inférence comme un fait** : `confiance` SOURCE/DEDUIT/ABSENT, radar servi = SOURCE.
- **Une vigilance juridique au conditionnel est pire que pas de vigilance** : sursis DARK sans PADD.
