# DOCS-1 — compte-rendu

> Branche `fix/docs-1`, worktree `~/Desktop/labuse-docs1`, Opus. Base Mac `labuse` (run servi
> `q_v20`, 434 582 parcelles), rendu PDF in-process (venv `~/Desktop/labuse/.venv`, weasyprint 70,
> `LABUSE_PDF_PROCESS_ISOLE=0`). **Aucun merge, aucun accès prod.** Pièce à conviction lue d'abord :
> `~/Desktop/LABUSE-EXPORTS-2026-11-07/` (16 documents sur `97411000BZ1065` + `SOMMAIRE.md`),
> `docs/audit-2026-11/nu-5/B/RAPPORT.md`, `docs/audit-2026-11/ecarts-zero-1/COMPTE-RENDU.md`.

## Décision de Vic appliquée

« Un fait a une seule valeur dans tous les documents, celle de la fiche. Chaque correction se fait
à la source, jamais document par document. Plus aucun mot de cuisine interne dans un document
client. Un seul format partout. » Les documents **Argumentaire**, **Dossier banquier** et
**Lettre de zonage** sont **supprimés** ; le **Courrier** garde l'unique point d'entrée ; le
**Bilan** (`/financier`) reste le seul document financier.

---

## 1. Le banc des documents (l'outil qui refuse un fait à deux valeurs)

NOUVEAU `scripts/coherence/documents_banc.py` + test `tests/test_docs1_banc.py` (marqué
`reel`+`local`). Il **rejoue tous les documents servis par un GET sur les 12 parcelles témoins**
(liste canonique `tests/coherence_ecrans/conftest.TEMOINS`), extrait du texte rendu (`pdftotext`)
les faits énumérés par le mandat, et applique **trois contrôles distincts** :

1. **un fait = une valeur** — pour chaque (parcelle, fait), la valeur imprimée par chaque document
   doit être identique ; deux valeurs = rouge ;
2. **jetons de cuisine interne** — `config/mots_interdits.yaml` rejoué sur le texte de chaque document ;
3. **format** — décimale au point (« 4.5 ») et date ISO (« 2026-04-16 ») refusées.

En process (TestClient, base réelle), aucune écriture, aucun mail.

```
PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
  ~/Desktop/labuse/.venv/bin/python -m scripts.coherence.documents_banc
```

### Avant / après (44 documents, 12 témoins)

| Contrôle | Avant | Après |
|---|---:|---:|
| Faits à deux valeurs | 7 | **7** _(2 chantiers moteur, §4)_ |
| Jetons de cuisine interne | 44 | **0** |
| Fautes de format | 14 | **0** |
| **Total** | **65** | **7** |

Les 7 restants sont **deux** divergences de type, toutes deux à cause unique **côté moteur** (le
lecteur unique n'est pas encore branché), documentées au §4 et explicitement listées dans le test.

---

## 2. Suppression des trois documents (à la source)

| Point de câblage | Fichier | Geste |
|---|---|---|
| Routes de redirection `/argumentaire`, `/dossier-banquier` | `src/labuse/api/documents.py` | supprimées |
| Robinets registre `pdf_argumentaire`, `pdf_banquier`, `pdf_lettre_zonage` | `src/labuse/registre/robinets.py` | supprimés ; les postes du bilan du Banquier (charge foncière, prix terrain/neuf, mixité, `bilan_*`) **rejoignent `pdf_financier`** (aucun chiffre déclaré orphelin) |
| Lecteur déclaré `prix_terrain_secteur_eur_m2` | `src/labuse/registre/lectures.py`, `marche_service.py` | re-pointé `pdf_banquier` → `pdf_financier` |
| Rate-limit `/lettre-zonage`, `/argumentaire` | `src/labuse/api/protection.py` | préfixes morts retirés |
| Porte Copilote (`_DOC_MAP`) banquier/argumentaire | `src/labuse/copilote_v2/answering.py` | retirée |
| Front : proxy, libellés, exemple Copilote, boutons | `frontend/vite.config.ts`, `lib/strings.ts`, `lib/capaciteMax.ts`, `lib/api.ts`, `store/useApp.ts`, `components/copilote/*`, `components/fiche/constructibilite.tsx`, `qa/audit_m6_outils.mjs` | retirés (tsc vert) |
| Tests / QA / scripts | `tests/test_copilote_guidage.py`, `tests/test_circuit2_lot0bis.py`, `qa/loadtest.py`, `scripts/donnees1_matrice.py` | mis à jour |

**Décision assumée** : la table persistée `lettre_zonage_refs` **reste** dans la purge RGPD
(`api/tenant.py`), le dictionnaire des tables (`registre/tables.py`) et le `conftest` — la supprimer
affaiblirait la purge de données personnelles historiques et casserait la cohérence du registre des
tables. Le document disparaît du produit ; sa table historique et sa purge RGPD restent.

**Non touché (hors mandat)** : artefacts d'audit figés dans `qa/` (snapshot OpenAPI, rapports M14x,
scripts d'inventaire) — `pytest` ne collecte que `tests/`, ils ne bloquent pas le hook.

Recette : `test_registre` (32), `test_exports2_lot0/4/5`, `test_circuit2_lot0bis`,
`test_copilote_guidage` **verts** ; tsc front **0 erreur**.

---

## 3. Jetons de cuisine interne & format — 0 fuite, 1 format

`config/mots_interdits.yaml` (version `2026-11-07`, 30 → **48 jetons**) reçoit les 18 jetons du
mandat ; `tests/test_circuit2_lot0bis.py::test_mots_interdits_liste_versionnee` les verrouille.
Corrections **à la source** (le banc confirme 0 jeton, 0 format sur les 12 témoins) :

| Fuite / format | Producteur unique corrigé |
|---|---|
| « volet D », « VERITE-TERRAIN-2 » (note capacité, Financier + Comparatif) | `src/labuse/capacite_max.py` + miroir TS `frontend/src/lib/capaciteMax.ts` |
| « verrou de test », « géométrie servie » (Étude de faisabilité) | `src/labuse/exports/etude_faisabilite.py` |
| « config/plu_destinations », « troncon_de_route » (Gabarit) | `src/labuse/gabarit/builder.py` |
| « INONDATION_MOUVEMENT_DE_TERRAIN », « PM1_PPR_… », « édition non enregistrée » (Gabarit) | `src/labuse/exports/blocs/gabarit.py` — chaque fragment de source/règle passe par le nettoyeur client (`risques_arbitrage.libelle_client_detail`, `millesime_source.nettoyer_notes_internes`) |
| « ingéré le » (Dossier, ligne servitude/aléa) | `src/labuse/millesime_source.py` (producteur unique `libelle_date_source` : « ingéré le » → « au ») + filet au rendu `exports/miroir._mill_client` (payload de fiche en cache) |
| « Classement D », « 0 · Non retenue » (Estimer) | `src/labuse/exports/blocs/annonce.py` : la phrase de classement garde son **motif factuel**, le préfixe de classement interne (bande · signal) est retiré |
| date ISO « 2026-04-16 » → « 16/04/2026 » | `src/labuse/millesime_source.composer` (producteur unique) + filet `miroir._mill_client` |
| décimale « 4.5 m » → « 4,5 m » (§5 règles PLU calibrées) | `src/labuse/exports/blocs/zonage._regles` (virgule entre deux chiffres, « Art. Uh.10 »/« p.73 » intacts) |

---

## 4. Un fait, une valeur — état par fait

Référence = la valeur de la **fiche** (`/parcels/{idu}`), lue par le robinet unique
(`exports/robinet_fiche.py`). Sur `97411000BZ1065` :

| Fait | Valeur unique (fiche) | État |
|---|---|---|
| Date des données | **21/10/2026** | ✅ identique sur tous les documents |
| Plafond d'emprise (30 % de la contenance) | **470 m²** | ✅ Dossier = Gabarit = Comparatif (contenance 1 567, pas le dessin 1 625) |
| Hauteur à l'égout | **4,5 m** | ✅ (point décimal corrigé) |
| Nombre de bâtiments | **2** | ✅ Dossier (l'Étude « 4 bâtiments » = chantier, §ci-dessous) |
| Marge de surélévation | **−3,3 m** | ✅ Dossier (lecteur unique `marge_surelevation_m`) |
| Servitude PPR | **1 servitude — PM1** | ⏳ Dossier ✅ / **Gabarit « Aucune SUP » ✗** |
| SDP maximale réglementaire, terrain libéré | **212 m²** | ⏳ Dossier = Comparatif ✅ / **Financier « 325 m² » ✗** |
| Surface vendable | **non calculable (capacité nulle)** | ⏳ lié au Financier (programme inventé) |
| Date du PPR | approbation **17/10/2012** ; millésime source en jj/mm/aaaa | ✅ (plus de date ISO ; cf. §3) |

### Les deux chantiers qui restent (cause unique, côté MOTEUR)

Le banc les isole et le test les liste nommément (toute **nouvelle** divergence fait rougir le test) :

1. **`servitude_sup` — Gabarit « Aucune SUP » vs fiche « 1 PM1 » (6 témoins).**
   Le Gabarit **déduit** les SUP de la zone d'implantation (`src/labuse/gabarit/builder.py`,
   `src/labuse/gabarit/engine.py`) au lieu de lire les **SUP servies par la fiche**
   (`dispositifs.sup`, robinet `_c_dispositifs_sup`). Correctif à venir : brancher le lecteur SUP du
   Gabarit sur la fiche (lecteur unique), comme le Dossier.

2. **`sdp_max_terrain_m2` — Financier « 325 m² » vs fiche « 212 m² » (BZ1065).**
   Le Financier compose un **programme** (`surface_plancher` dérivée d'un nombre de logements)
   `src/labuse/exports/builder.py:270-281` même quand le client n'a **rien saisi** — exactement
   l'« hypothèse inventée » du mandat (§5). Correctif à venir : un `logements_vises_saisi` non saisi
   par le client s'affiche **« non renseigné »** et n'entre dans aucun calcul (la SDP imprimée reste
   la SDP maximale réglementaire de la fiche, 212 m²). Même famille que « l'Argumentaire inventait
   300 000 € et 4 logements ; le Bilan 250 m² taxables ».

---

## 5. Recette (état)

| Recette | Résultat |
|---|---|
| Banc des documents (12 témoins, 44 documents) | **65 → 7 écarts** ; **jetons 0**, **format 0** |
| `tests/test_docs1_banc.py` (reel+local) | jetons ✅, format ✅, faits : 2 chantiers listés |
| Régression zone touchée (capacité, exports, registre, provenance, copilote, logements) | **103 passed, 0 failed** |
| tsc front | 0 erreur |
| Suppressions (registre / routes / front / tests) | verts |

---

## 6. Reste à faire (hors de ce lot, scope précis)

- **Faits — 2 chantiers moteur** (§4) : Gabarit lit la fiche `dispositifs.sup` ; Financier
  « non renseigné » pour un programme non saisi.
- **Prix au m²** (#mandat prix) : un seul prix en titre par document (type du bien de la parcelle),
  sa définition en une ligne ; les autres indicateurs en annexe « Marché ». Non traité ici.
- **Hypothèses inventées** (#mandat) : généraliser « non renseigné » (prix demandé, logements,
  surface taxable) — lié au chantier Financier.
- **Abréviations du Bilan** : écrire en clair SUV/DROC/DAT/TRE/GIEP/M.O.D./Pack ;
  « Taxe logements » → « Taxe d'aménagement » (`src/labuse/bilan/excel.py`, `bilan/pdf.py`,
  `faisabilite/bilan.py`). Non traité ici.
- **Forme** (#mandat) : couvertures (carte + résumé), pied raccourci, page quasi vide du Flash,
  3D du Gabarit plafonnée à l'emprise + mention « bâti existant dépasse », tuile manquante de
  l'Étude de zone, carte d'Estimer avec contexte, phrase « valeur du terrain », Courrier au nom/
  logo du client, « VÉRIFIÉ : RIEN » → « Vérifié : rien à signaler », « Vides » → « Vide »,
  §11 « Simulation » du Dossier, PPR une seule fois dans l'Étude, Excel « 8,5 % » et non « 0.085 ».
- **Régénération V2** : régénérer les documents sur `BZ1065` + une parcelle nue zone U + une parcelle
  rouge partielle dans `~/Desktop/LABUSE-EXPORTS-2026-11-07-V2/`, captures avant/après des couvertures.

---

*DOCS-1 — lecture base locale, prod jamais touchée. Banc : `scripts/coherence/documents_banc.py`.
Branche `fix/docs-1`, non mergée.*
