# RAPPORT M78-quater — Correctifs de recette du Copilote

Branche `feat/m78-copilote`. Recette du mandant sur le bundle à jour. Six défauts corrigés, la
maquette `docs/DA-COPILOTE-PARCOURS.html` comme référence (classes recopiées, données versées).

## #1 — LE RÉCAP-CONFIRMATION EST IMPLÉMENTÉ (priorité absolue) ✅
**Cause racine** : l'interpréteur (`interpreteur.py:_valider_brief`) EXIGEAIT un programme → programme
absent = clarification bloquante « Quel programme visez-vous ? ». Le mandat l'interdit.
- **Le programme n'est JAMAIS bloquant** : absent → `programme = {logements: null, sdp_cible_m2: null}`,
  brief valide, récap affiché. Chercher un terrain sans programme est légitime.
- **Moteur résilient** (le run tolère `sdp_cible_m2 = None`) : `filtre_geometrique` saute le filtre de
  capacité (aucune parcelle écartée pour capacité, seul le garde-fou de plafond s'applique) ;
  `faisabilite` calcule la SDP mais ne l'écarte pas sur une cible inexistante. Le tri championnat P est
  conservé. 2 tests verrouillent ce comportement (`test_copilote_moteurs.py`).
- **Champ libre d'affinage AJOUTÉ** (`RecapConfirmation.tsx`) : « … ou écrivez ce que vous voulez
  ajouter » (Entrée → chip, reste sur l'écran), au-dessus de « Lancer la recherche » pleine largeur.
  Cinq boutons ne couvrent pas tous les besoins — le client écrit le sien.

Preuve bout-en-bout (`/ask` sur la phrase de la recette) : `needs_confirmation:true`,
`programme:{null,null}`, `recap:"J'ai compris : Saint-Paul, ≥ 1000 m², hors PPR rouge…"`. **Captures
parcours A** dans `qa/m78/captures/parcours_a-*/` : accueil → brief → récap → Corriger → récap → Oui →
affinage (champ libre) → Lancer. Le champ libre crée bien la chip « proche des écoles » (06).

## #2 — « VOS DERNIÈRES QUESTIONS » ✅
`AccueilCopilote.tsx` : titre **VOS DERNIÈRES QUESTIONS** (fini « REPRENDRE »), **dédoublonnage** par
question (1re occurrence = plus récente, les missions arrivent déjà triées `updated_at DESC`), **date
relative** « il y a 2 h » (`ilYA()` dans `format.ts`) au lieu du technique « N msg », **4 max +
« Voir tout (N) »**, section **masquée si vide**.

## #3 — Veilles retirées de l'accueil ✅
Bloc VEILLES retiré + carte « Veiller » retirée. **Choix (rapporté)** : la 3ᵉ carte devient
**« Demander »** = le parcours des QUESTIONS DIRECTES (maquette PARCOURS B), qui fonctionne aujourd'hui
(base + web, sinon refus honnête). Les 3 cartes = les 3 parcours : **Chercher · Demander · Vérifier**.
Le mécanisme de veille reste branché côté serveur (intention VEILLE, stockage, endpoints) ; écran dédié
au BACKLOG (dépend du canal notifications).

## #4 — Fuite de vocabulaire interne corrigée ✅
Audit de TOUTES les mentions de source (`outils.py`, `answering.py`, `missions_lourdes.py`) :
- `compter_parcelles` / `fiche_parcelle` : « Recherche à facettes LABUSE (run servi) » /
  « Fiche parcelle LABUSE (run servi) » + `millesime=RUN` → **`source="cadastre"`, `millesime="Etalab
  2026-06"`** (le vrai millésime d'ingestion, cf. `api.app`). Le run interne reste l'argument des points
  de calcul, jamais affiché.
- `marche` : « Marché commune LABUSE (DVF, Sitadel, DHUP — terrain nu M79) » → **« DVF, Sitadel, DHUP
  (terrain nu) »**.
- avis VERIFICATION : « LABUSE ne mesure pas » → « ce calcul ne mesure pas » ; « DVF terrains (marché
  commune) » → « DVF (prix terrain nu par zone) ».
Preuve : « …51 129 parcelles cadastrales **(cadastre, Etalab 2026-06)** ». `res.source`/`res.millesime`
étant le point unique (prose + ligne mono), une seule correction ferme les deux surfaces.

## #5 — Pouces 👍/👎 supprimés ✅
`ReponseInline.tsx` : bloc feedback (états, boutons, commentaire) retiré entièrement ; reste la ligne de
source. L'endpoint `/feedback` reste en place. Feedback futur = lien texte discret (BACKLOG).

## #6 — Re-vérifié sur le bundle à jour ✅
6 exemples tournent à chaque visite · barre jamais verrouillée · en-tête résultats affiche le compte ·
marquage web « ◍ Source : web · [domaine] · consulté le [date] — hors base ». Captures à l'appui.

## Ce que la maquette montre aussi
- **PARCOURS B** : aucune question directe ne déclenche de récap (QUESTION/OUTIL répondent tout de suite,
  vérifié backend) ; refus propriétaire → porte SPF ; refus divisible → répond avec ce qu'on sait, ne
  propose rien. Inchangé, conforme.
- **PARCOURS C** : le récap existe (avis d'achat), 3 chiffres, alerte d'écart ambre, réserve de méthode,
  3 suites. Inchangé, conforme.

## Observation (hors périmètre)
Le rail global de gauche garde une entrée « Veilles » (tiroir socle `toggleVeilles`, antérieur à M78) —
c'est du chrome global, pas l'accueil Copilote. Non touché ; à trancher avec l'écran Veilles dédié.

## Gardes
tsc 0 · vitest 36 · pytest copilote **97** (dont 3 nouveaux : programme non-bloquant + 2 moteurs sans
programme) · golden diff 0 **par construction** (aucune modification du scoring `score_v` ; les moteurs
Copilote ne changent QUE dans la branche `cible=None`, le chemin avec programme est identique octet pour
octet). Échecs préexistants confirmés indépendants (`test_pdf_premium` collection, `test_fiche_core_
sans_bloc_promoteur_lazy` — échoue aussi sans mes changements). **NE PAS MERGER.**

Rappel serveur : mes captures tournaient sur un serveur `:8010` en `LABUSE_DEV_MODE=1` (bruit quota
évité) — à relancer en **mode normal** pour la recette finale.
