# M118 — le Copilote resserré à 4 missions

Livré le 18/08/2026. Arbitrage définitif de Vic : le Copilote fait 4 choses, tout le reste QUITTE le
chat (avec une voie). 3 commits sur `feat/m118-copilote-4-missions` (non mergé).

## Les 4 missions (tout le reste part)

1. **Trouver une donnée** — la facette (QUESTION→compter_parcelles, le chemin le plus durci
   M109/M110/M111/M116). Chiffre sourcé, critères dits, aveu si non applicable.
2. **Renseigner par le web** — court, sourcé, daté (D5 réglé en M117).
3. **Expliquer une notion** — AU, ZFANG, charge foncière… pédagogie courte, barrière thématique,
   JAMAIS un chiffre LABUSE (`_expliquer` + `EXPLIQUE_SYSTEM`).
4. **Préparer un script** — appel/argumentaire propriétaire ; faits SOURCÉS repris si contexte
   parcelle, sinon générique métier — jamais inventer ni calculer (`_preparer` + `PREPARE_SYSTEM`).

Ce qui QUITTE : instruction (RECHERCHE), création de projet, surveillance, ouverture d'outils,
rédaction de courriers/dossiers, vérification de prix (VERIFICATION → fiche, arbitré). Les
générateurs (courrier/PDF) restent dans l'app (fiche, CRM) — ils quittent seulement le chat.

## Phase 0 — vérification avant coupe

**Moteurs atteignables sans le Copilote** ✓ : `ProjetKanban.tsx:95-100` appelle `proposerProjet(pid)`
à l'ouverture d'un projet (= le run), endpoints `/projets/{pid}/proposer` + `/rejouer` intacts. Flux :
`ProjetsPanel` « + Nouveau projet » → `ParcoursProjet` (M114) → kanban → auto-proposer → tri. Aucun
moteur touché. **Arbitrage** : VERIFICATION → refus-voie **fiche** (l'avis DVF vit sur la fiche).

## Phase 1 — le retrait, au SERVEUR, avec des voies

Le routeur gagne `EXPLIQUER`/`PREPARER` (intents). L'aiguillage `_answer_with_route` renvoie
`RECHERCHE/PROJET/VERIFICATION/VEILLE/OUTIL` (+ les concepts-outils M112 + les documents) à leur VOIE
via `_refus_voie(...)` → `refus="hors_mission"` + `voie={cible, libelle, idu?}` (gabarit D6,
NAVIGATION pure, jamais une exécution) :
- « trouve un terrain » → **Projets** · « crée un projet » → **Projets**
- « mets sous surveillance » → **Surveillance** · « vaut-elle 320k ? » → **fiche** (idu)
- « ouvre le baromètre » → **Outils** · « rédige un courrier » → **fiche/CRM**

Une demande VISUELLE de données (« montre-moi les friches à Saint-Paul ») reste MISSION 1 (compte +
carte) — pas une instruction. Front : `ReponseInline` rend la voie (carte warn + bouton de
navigation `data-reponse-voie` → setView/openSurveillance/toggleOutils/select) ; `CopiloteView` ne
lance PLUS le run sur un refus-voie (garde `!r.refus`). « Décrire au copilote » retiré de la page
Projets (la création n'a plus de porte vers le chat).

## Phase 2 — l'accueil à 4 missions

Quatre cartes en grille 2×2 (sous-titres serveur `SCENARIOS.sub`). Champ libre conservé (route vers
les 4 missions ou vers un refus-voie). Brief mint + « Reprendre » inchangés. Chips 6 → 4.

## Phase 3 — les 2 missions nouvelles

- **Expliquer** : réponse 2–4 phrases, hors-sujet → refus poli, JAMAIS un chiffre LABUSE.
- **Préparer** : script structuré (accroche/intérêt/proposition/ouverture) ; faits sourcés de la
  fiche repris si IDU en contexte (`_substance`), jamais recalculés.

## Phase 4 — gates et vérification

| Contrôle | Résultat |
|---|---|
| **NOUVEAU** gate `qa/m118/missions.py` — 4 missions + 4 refus-voies + gate NÉGATIVE | **8/8** (hors mission 1, aucun chiffre LABUSE) |
| Facette (mise à jour : fantôme/bailleur → refus-voie outils) | **11/11** |
| Véracité (mise à jour : Q31/Q32 OUTIL → `refus_voie`) | **33/33** |
| Fil · routeur (EXPLIQUER/PREPARER ajoutés) | **6/6 · 100 %** |
| Tests déterministes (scénario, defauts_m116 màj, `test_copilote_missions_m118` nouveau) | verts |
| Suite | **1612 passed, 0 failed** |
| Golden | **0 FAIL** (33 INDÉTERMINÉ = quota API du jour, env) |
| tsc · build | **0 · OK** |
| Captures (`qa/m118`) | accueil 4 missions · expliquer (notion, 0 chiffre) · refus-voie (carte warn + « Ouvrir Projets », run NON lancé) |

## Interdits respectés

Aucun chiffre LABUSE hors facette (gate négative 8/8) · aucun refus sans voie · moteurs INTACTS
(servis par Projets) · retrait au SERVEUR (le routeur/l'aiguillage, pas un masquage front) · non
mergé.

## Dette laissée (honnêteté)

Les helpers `_outil` / `_projet_form` / `preparer_veille` / `recap_recherche` / `_division` et
l'endpoint `_executer_veille` deviennent INATTEIGNABLES (interceptés en amont) mais restent en place
(du code mort à retirer dans une passe de nettoyage — non fait pour limiter le risque). Le param
`sujet` du routeur n'est plus servi (déjà M117 D7). Le formulaire projet (ParcoursProjet) reste
utilisé par la section Projets (M114), pas par le chat.
