# M43 — PHASE 0 · INVENTAIRE & JOINTURE (features propriétaire, PM only)

**Branche** `m43-features-proprietaire` · base `main` d91189f2 (M44 mergé). **LECTURE SEULE.**
**⚠ RGPD tenu** : PM UNIQUEMENT, au niveau SOCIÉTÉ (dénomination/SIREN/état) — aucune personne
physique. Le champ `dirigeants` de l'enrichissement (personnes) N'EST PAS touché. Le badge « gérant
âgé » n'est ni étendu ni exposé.

Tout vérifié **sur pièces** (base `labuse`, run servi `q_v8_calibre`).

---

## 1. Ce qu'on a vraiment — PM/SIREN + millésime

`pm_proprietaires_millesimes` : **461 570 lignes, 14 517 SIREN, 91 397 parcelles** à propriétaire PM.
**Le millésime EST tracé** : valeurs réelles **2019 → 2024** (Fichiers fonciers DGFiP annuels),
dernier = **2024**. → La dette #11 « millésime amont non tracé » est **inexacte au niveau donnée**
(la colonne `millesime` est peuplée ; note-vs-source, à corriger dans le suivi de dette).

**Parcelles SERVIES (tiers actifs) à propriétaire PM courant (millésime 2024)** :
| tier | parcelles PM |
|---|---|
| à creuser | 4 416 |
| réserve foncière | 470 |
| chaude | 258 |
| brûlante | 57 |
| **total** | **~5 201** |

## 2. Jointure Sirene/BODACC sur SIREN — taux de résolution & licences

Sources **déjà en base** (pas de re-téléchargement nécessaire — vérifié) :
- `owner_enrichment` (source `recherche_entreprises` = API Recherche d'entreprises, adossée INSEE
  Sirene/RNE) — **Licence Ouverte** ; payload société : `etat_administratif` (A/C), `date_fermeture`,
  `nature_juridique`, `nom_raison_sociale`… (+ `dirigeants` = **PP, NON utilisé**).
- `bodacc_annonces_owner` / `bodacc_procedures` (BODACC, **Licence Ouverte Etalab**) : radiations,
  procédures collectives (redressement/sauvegarde/liquidation), ventes/cessions.

**Taux de résolution** (1 916 SIREN servis, millésime 2024) : **1 349 (70 %) enrichis**
(recherche-entreprises) · **130 (7 %) avec une annonce BODACC** (seules les sociétés à événement y
figurent — normal). L'enrichissement donne l'état administratif ; BODACC donne l'événement daté.

## 3. « Dormance » — définition mesurable & SOURCÉE (pas de proxy flou)

Trois signaux SOCIÉTÉ, chacun sourcé et daté — **aucun proxy type « pas de site web »** (rejeté) :

| Signal | Définition (sur pièces) | Source |
|---|---|---|
| **cessée** | `owner_enrichment.payload->>'etat_administratif' = 'C'` (+ `date_fermeture`) | recherche-entreprises (INSEE Sirene) |
| **radiée** | `bodacc_annonces_owner.famille = 'radiation'` | BODACC |
| **procédure collective** | `bodacc_annonces_owner.famille = 'pcl'` (redressement/sauvegarde/liquidation) | BODACC |

(« Dissoute » ⊂ radiée/cessée ; on ne double-compte pas. « Comptes non déposés » écarté : signal
faible et non homogène — le doute ne profite pas au chiffre.)

## 4. Volumétrie par signal, par tier

`qa/m43/volumetrie_signaux_par_tier_p0.csv` :

| tier | PM | cessée | radiée | procédure coll. |
|---|---|---|---|---|
| à creuser | 4 416 | 164 | 57 | 94 |
| réserve foncière | 470 | 14 | 7 | 10 |
| chaude | 258 | 5 | 3 | 4 |
| **brûlante** | 57 | **0** | **0** | **0** |
| **total (actifs)** | | **~183** | **~67** | **~108** |

**Constat qui pèsera sur la Phase 1** : le signal est **RARE**, très concentré sur *à creuser*, et
**quasi absent des têtes** (brûlante 0 ; chaude 3-5). La mesure de lift aura donc de **petits
effectifs → IC larges** ; l'hypothèse backlog (+1/+2 RR) devra être **éprouvée**, pas confirmée.

---

## Ce que fait la Phase 1 (mesure à blanc — le cœur)

Sur le harnais gelé (RR M36) : pour chaque signal (cessée/radiée/procédure), **lift univarié de
mutation** (les parcelles au signal mutent-elles plus que la base, IC à l'appui) ; **lift BRUT vs
résiduel une fois la tenure connue** (si le signal ne fait que répéter la tenure, il n'apporte rien).
Honnêteté : effectifs, IC, « non concluant » dit tel quel. **0 poids de modèle touché** — la mesure
informe le geste [S] d'intégration, décidé par Vic.

## Annexes
- `qa/m43/volumetrie_signaux_par_tier_p0.csv` · `_global.txt`.
- Aucune écriture servie. Golden / re-mesures / M37 intacts (lecture seule).
