# RAPPORT DE RECETTE — RADAR P1 (vision IA + intake admin)

Branche `feat/radar-p1` (depuis main incluant P0+P2). Commits par lot V1→V4. Doctrines §2 tenues :
collecte 100 % humaine · zéro republication · Sourcé/Estimé/Absent · anti-invention · Radar hors scoring.

---

## V1 — Le cœur IA apprend à voir — **FAIT**

`ai/core.complete()` accepte désormais `images: list[ImagePart]`. Le contenu utilisateur devient une
LISTE de blocs (image(s) base64 PUIS texte, recommandation Anthropic). **Sans régression** : `images=None`
→ chemin texte INCHANGÉ (contenu = chaîne) → les 38 tests Copilote/IA restent verts **sans modification**.
- Modèle vision déclaré comme les autres (`MODEL_VISION`, pas en dur chez l'appelant) + tarif au `PRICE`.
- Coût logué au ledger `ia_budget` avec son kind propre `vision_pige` (distinguable au dashboard).
- Échecs honnêtes AVANT tout appel réseau (zéro coût) : format non supporté / image vide / > 5 Mo →
  `degraded` avec motif ; l'image invalide ne construit même pas le client.
- Verrou `tests/test_pige_vision.py` 5/5 (PNG réel fabriqué en mémoire ; bloc validé ; chemin vision
  mocké de bout en bout + coût logué ; chemin texte prouvé inchangé).

## V2 — L'extraction d'une annonce — **FAIT**

`extraction.extraire(image, media_type, lien)` → JSON strict des 11 champs, **chaque champ + sa
confiance**. **Anti-invention gravée** : le prompt EXIGE `null` si illisible ; les clés hors schéma sont
JETÉES ; une sortie non-JSON rend un motif honnête (rien extrait, aucun champ inventé) ; `type` hors
énumération → null. Portail déduit du lien via `portails.py` (lien inconnu accepté et signalé).
`intake` : **contrôle commune ∈ 24** (résolu via `communes.py`, sinon rejet motivé, RIEN en base) ;
**dédoublonnage V0 §3** (URL connue → mise à jour de prix proposée ; jumeau commune ∧ prix ±2 % ∧
surface ±5 % → fusion proposée) ; `deposer()` crée un **brouillon** (`valide_at NULL`, rien de publiable)
+ capture privée + **rattachement P2 réutilisé** (`rattachement.rattacher`, jamais réécrit) ;
`valider()` promeut (statut `active`, `pige.nouvelle` ; baisse → `pige.baisse_prix`).
Verrou `tests/test_pige_extraction.py` 5/5.

## V3 — La page Radar du dashboard admin — **FAIT**

**Endpoints** (`pige/api.py`, router monté, réservés admin via `exiger_admin` — même barrière que tout
`/admin/*`) : `/admin/radar/deposer` `/valider` `/extraction` `/reverif` `/toujours-en-ligne` `/prix`
`/retiree` `/check`. La file de re-vérif est PRIORISÉE (suivi client > proche 90 j > plus ancienne).
Verrou `tests/test_pige_api.py` 2/2 (réserve admin câblée + flux dépôt→file→validation→re-vérif→check).

**Page React** (`components/admin/Radar.tsx`, section « Radar » du rail admin, **pensée mobile**),
les 4 zones dans l'ordre : ① Saisie du jour (dropzone galerie + un lien par capture, retour immédiat
doublon/hors-périmètre) · ② File d'extraction (fiche pré-remplie, **champs sous seuil surlignés MAUVE**
— couleur réservée IA — via `a_verifier`, Valider en un clic) · ③ Re-vérification à 2 niveaux (léger :
Toujours en ligne ; attentif : Prix modifié / Retirée) · ④ Check quotidien (rituel ≤ 15 min +
`intake_vide_48h`). **Aucune photo/texte d'annonce** : faits + lien sortant seulement. tsc 0, build ✓.

**Captures livrées : 2** (`docs/PIGE/captures/`) — `radar-admin-d.png` (1440) et `radar-admin-m.png`
(390). La desktop montre les 4 zones, les badges de rattachement (Estimé / Non rattachée), et les
champs mauves « à vérifier ».

## V4 — Recette réelle — **scénarios couverts par les tests ; passe vision LIVE = post-merge (clé)**

Les 7 cas du mandat sont **exercés** par la recette automatisée (`tests/test_pige_extraction.py`,
extraction mockée mais réaliste) : capture nette (faits + confiances) · **capture partielle → `null`,
pas d'invention** · doublon d'URL (mise à jour proposée) · doublon inter-portail (**fusion** proposée) ·
commune hors périmètre (**rejet motivé, rien en base**) · **baisse de prix** détectée à la re-saisie
(`pige.baisse_prix`) · lien de portail inconnu (accepté et signalé). Le parcours dépôt→extraction→
correction→validation→rattachement→statut `active` est prouvé end-to-end via les endpoints
(`tests/test_pige_api.py`).
La passe **vision LIVE** (composer une image d'annonce réaliste et la faire lire par le VRAI modèle)
exige `ANTHROPIC_API_KEY` (la clé de l'environnement est invalide, cf. VP-003) et se fait **sans visiter
aucun portail** (la doctrine vaut pour l'agent) : c'est la recette d'usage de Vic après merge, comme
prévu au mandat V0 §9.

---

## RECETTE (FIN)
- **Cœur IA vision sans régression** : 38 tests Copilote/IA verts sans modification ✓.
- **Extraction stricte, aucun champ inventé, confiances portées** ✓ · **dédoublonnage + contrôle
  commune opérationnels** ✓ · **coût vision au ledger `ia_budget`** (kind `vision_pige`) ✓.
- **Page admin Radar** complète, mobile, re-vérif enchaînable ✓ (captures 390 + 1440).
- **Le test anti-requêtes-portails de P0 reste VERT** (`tests/test_pige_socle.py` 5/5 ; Radar.tsx
  allowlisté comme affichage) ✓.
- **tsc 0 · build ✓** · **suite au niveau base (worktree `d9611a7a`)** : base 1883 / branche 1896,
  **0 fail** ✓ · **[RADAR-TEST]/démo purgés** (base `pige_biens` = 0) ✓.

Findings : —
