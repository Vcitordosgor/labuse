# RAPPORT M78-bis — Le parcours RECHERCHE refondu : confirmer avant d'instruire

Branche `feat/m78-copilote` (à la suite des phases M78). On INVERSE le flux : le Copilote annonce ce
qu'il a compris, le client valide, PUIS l'instruction part.

## RÈGLE GRAVÉE (§5) — la confirmation est un PÉAGE
Le récap-confirmation ne se justifie QUE quand le coût d'une mauvaise interprétation est élevé : **une
instruction d'une minute (RECHERCHE), un avis d'achat (VERIFICATION)**. Pour tout le reste
(QUESTION, OUTIL, PROJET, VEILLE, refus, hors-sujet), **la réponse immédiate reste la loi** — un péage
systématique tuerait le conversationnel. Vérifié : QUESTION/OUTIL ne déclenchent jamais le récap.

## §1 — Accueil : montrer l'étendue avant la saisie ✅
Pool de **16 exemples** couvrant les 7 intentions (comptage, PLU, patrimoine, délais, RECHERCHE,
PROJET, VERIFICATION, VEILLE, OUTIL, SRU, marché…), beaucoup issus du test de véracité (vérifiés).
**6 en rotation aléatoire** à chaque visite, sous la barre. Un clic remplit la barre, ne lance rien.
Les exemples par carte sont retirés (les cartes gardent titre + description = les archétypes).

## §2 — Récap-confirmation avant toute mission lourde ✅
RECHERCHE et VERIFICATION uniquement. `recap.py` interprète SANS lancer (`interpreter_brief`) →
- **a)** récap en une phrase (« J'ai compris : … C'est bien ça ? ») + **Oui, c'est ça** / **Corriger**.
- **b)** Corriger → chips éditables (✕ retire → ré-interprète) + réécriture libre → retour au récap.
- **c)** Oui → affinage optionnel : suggestions cliquables tirées des **facettes réelles** du brief
  (surface, zone U/AU, hors ABF, budget) + **Lancer la recherche**. Chaque suggestion ajoute une chip
  et reste sur l'écran ; Lancer part avec ce qui est là.
- **d)** La clarification du routeur ALIMENTE le récap (pas de double question) — clarification COURTE :
  2-3 communes ACTIVES (dépôts de permis récents) + « Toute l'île », **jamais 24**.
- Le récap validé RESTE en tête pendant l'instruction et sur les résultats (`data-recap-confirme`).
- Backend : `answer(confirme)` — VERIFICATION produit l'avis après validation ; RECHERCHE lancée par le
  front sur « Lancer » (run M26-A).

### Complément (constaté à l'écran) ✅
L'écran « PRÉCISION NÉCESSAIRE » (clarification pleine page, **24 chips de communes**, barre verrouillée
« EN ATTENTE ») est **SUPPRIMÉ** — remplacé, pas cumulé. (1) La barre principale n'est **jamais
verrouillée** (`readOnly` retiré). (2) La clarification est une **bulle du récap** (≤ 4 suggestions).
(3) **Aucune étape « en attente »** n'est affichée avant le lancement (bloc `enAttente` retiré, tests
d'état 3 obsolètes supprimés).

## §3 — L'en-tête des résultats dit le compte ✅
Avant le héros : « **N restituées** sur M retenues — les autres sont classées derrière le rang N. »
(`data-resultats-compte`). L'information principale vit en tête.

## §4 — « Voir sur la carte » : CHANTIER (rapporté, pas bricolé)
Le mandat autorise : « si ça demande un chantier, le dire au rapport plutôt que le bricoler. » **C'est
le cas.** Constat technique :
- Le **panneau-liste de gauche du socle est FILTRE-DRIVEN** (`/filtre` + `FiltreCriteres`). Il n'existe
  **aucun mécanisme pour y injecter une liste d'IDU arbitraire** (la shortlist exacte du Copilote).
- Le pont IA→socle existant (`useApplySearch`) est **filtre-based** : il rejouerait les critères du
  brief comme filtres (résultat APPROXIMATIF), pas la shortlist EXACTE que le mandat exige (« charge
  exactement les N parcelles restituées »).
- Les surlignages carte (`iaRestitution`, `moduleMap.idus`) sont des overlays ; leur calque `module-hl`
  est vraisemblablement masqué hors contexte module (`setView` remet `module=null`). Pas un pont propre
  vers le panneau-liste.
- **« Mes vues » (M52) — CONSTAT CORRIGÉ (validé Vic)** : elle **EXISTE** (table `saved_searches`,
  endpoints `/events/searches`, barre de filtres, [M52-L5] mergé). Mon premier constat « introuvable »
  était FAUX (mauvais termes de recherche). MAIS elle stocke un `filtersToHash` (un FILTRE nommé), pas
  une liste d'IDU → à ÉTENDRE pour une shortlist d'IDU nommée.

**Mandat candidat écrit au BACKLOG (validé Vic, PAS lancé)** avec ses 2 exigences : (1) source de liste
par IDU explicite **coexistant** avec le filtre-driven (le socle affiche SOIT un filtre SOIT une liste
arbitraire, sans que l'un casse l'autre) ; (2) recherche NOMMÉE durable = étendre « Mes vues » aux listes
d'IDU. **En attendant : PAS de bouton carte mort** — action LIVE « Ouvrir la fiche » sur le héros (ouvre
la fiche de la 1ʳᵉ parcelle) + lignes cliquables. Rien qui promette la carte.

## Tests
- Routeur : QUESTION/OUTIL ne déclenchent JAMAIS le récap (vérifié backend).
- Parcours récap → corriger → récap → oui → affiner → lancer (vérifié : le récap porte les critères ;
  le run est lancé avec le brief final).
- Accueil : 6 exemples affichés, tous cliquables, aucun ne lance (`data-accueil-ex`).
- §4 : non livré (chantier) — pas de test carte.

## Gardes
tsc 0 · vitest 36 · build vert · pytest copilote 26 · golden 119/119 (backend inchangé côté scoring).
**NE PAS MERGER.**
