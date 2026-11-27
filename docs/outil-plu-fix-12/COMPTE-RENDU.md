# OUTIL-PLU-FIX-12 — compte-rendu (retouches finales, relecture-plu-9)

Branche `fix/outil-plu-1`. Périmètre : les 2 points « faux » (mineurs) + les 2 réserves de
`~/Desktop/relecture-plu-9.md` (verdict : **OUI, mergeable**). Consigne de charge respectée : tests PLU
**ciblés**, **commit local**, pas de suite complète ni de push. Chiffres : `scripts/plu_fix12_chiffres.py`.

## 1. Décompte du scan corrigé (14 → 15 faux positifs)

Le bilan du compte-rendu FIX-11 écrivait « 1 corrigé + 16 artefacts + **14** faux positifs ». Le scan
`--strict` sort **31 lignes** (Up.10, corrigé, n'y figure plus — il n'en fait donc pas partie). Réel :
**16 artefacts** (97406×14 + 97412×2) + **15 faux positifs** = 31. Corrigé dans
`docs/outil-plu-fix-11/COMPTE-RENDU.md` avec la sortie du script. Aucune ligne n'était sans statut ; seule
l'addition était fausse.

## 2. Test du filet Saint-Pierre resserré

`test_p6_fiche_saint_pierre_ligne_logement_locatif_social` vérifiait `any("place" in c)` — trop lâche.
Aligné sur Saint-Louis : exige désormais **« 1 place »** (un ratio erroné ne passe plus). La donnée servie
était déjà exacte (« 1 place / logement »), le test reste vert. `tests/test_plu_fix10_lot0.py:196`.

## 3. Artefact « lettres espacées » — diagnostiqué, NON corrigé (par sécurité)

- **Cause identifiée.** Le seul PDF porteur est **La Plaine (97406)** : 217 pages qui **concatènent** le
  règlement opposable (p.1-117, texte **propre** : « ARTICLE Ua N ») **et 3 dossiers de modification**
  (p.118-217 : « Modification du PLU… », « Modification n°2 2019 », « Plateau vert »). Le texte justifié de
  ces dossiers est rendu par PyMuPDF avec des espaces **intra-mots** (« TIT RE », « HA UTEUR », « ART ICLE »).
  Balayage des 21 communes : **1/21 seule** a des documents concaténés (97406).
- **Saint-Joseph (97412) est en réalité PROPRE** : le PDF brut donne « ARTICLE AUindicée 2/4/8/12 » sans
  espacement. Ses 2 lignes de scan FIX-11 étaient des **fragments d'en-tête collés** en fin d'extrait
  (« …graphiques.ARTICLE 4 - » p.5), pas des lettres espacées — reclassées.
- **Comptage.** 97406 : 132 extraits de règlement (p.1-117, propres) + **55 extraits** de dossiers
  (p.118+, zone d'artefact). Aucune autre commune concernée.
- **Pourquoi je n'y touche pas** (consigne « si risque pour le reste, ne touche à rien ») :
  1. **Dé-espacer est impossible sans risque** : l'espacement intra-mot est **indiscernable** du texte
     français légitime à mots courts — toute signature regex testée sur-déclenche (60-85 % des extraits de
     toutes les communes). Un retrait d'espaces corromprait des règles valides partout.
  2. **Exclure les pages de dossiers (p.118+) risque de perdre de l'opposable** : ces dossiers sont des
     **modifications** qui **amendent** le règlement (ex. « Modification n°2 2019 » révise ARTICLE UB 7) ;
     déterminer quelle version est opposable exige la métadonnée GPU, pas le seul PDF. C'est un problème de
     **source** (le PDF bundle des pièces non opposables), pas de code d'extraction.
  Effet résiduel : sous le filtre d'une zone de La Plaine, quelques extraits de dossier peuvent apparaître
  **après** l'article propre (doublons/ToC) — cosmétique, aucune valeur de règle faussée. **Avant = après =
  55 extraits** (inchangé).

## 4. La Possession — écart d'édition **résolu** (réingestion de la seule commune 97408)

- **Diagnostic.** La base servait le **texte** extrait du PDF sur disque `97408_reglement_20251217.pdf`
  (déc. 2025) mais estampillé avec l'**idurba/ancre #page** de l'édition active juin 2026
  (`97408_PLU_20260625`). D'où la réserve « texte déc. 2025, ancres juin 2026 ».
- **Quel PDF est le bon ?** L'édition **active au GPU = juin 2026** (`97408_PLU_20260625`). Je l'ai
  téléchargée (HTTP 200) : elle est **octet pour octet identique** au fichier déc. 2025 sur disque
  (md5 `8b3bd9de4c9a3d23f91307c31c457007`, 164 pages, **0 page au texte différent**). Les deux « éditions »
  sont **le même document**.
- **Les pages citées ouvrent-elles le bon passage ?** Oui — pagination identique, donc `#page=N` ouvre le
  bon article dans le PDF juin 2026.
- **Correction.** Réingestion de **la seule commune 97408** depuis le PDF **juin 2026** (désormais sur
  disque sous son nom canonique) : texte, pages, ancres et provenance viennent tous du **même document**
  (`97408_reglement_20260625.pdf`, idurba `97408_PLU_20260625`), 154 extraits. `note_doc` mise à jour
  (l'écart d'édition disparaît ; preuve md5).
- **Vérification.** **10 articles** de La Possession (UA 6/8/9/10/14, UB 8/12, A2/A5, N4) : en-tête **présent
  sur sa `page_debut`** dans le PDF juin 2026, texte conforme — **10/10**.

## Tests (ciblés PLU) & non-régression

- Filet `test_plu_fix10_lot0.py` (19, témoins FIX-10 + tour 11) + `test_plu_cas_valides.py` (34) : **53/53**.
- Non-régression des 8 points de l'audit externe : inchangée (aucune modification de la logique de
  recherche/ingestion ; seul 97408 réingéré depuis un PDF byte-identique).

Commit **local**. Pas de fusion `main`, pas de push (en attente du feu vert).
