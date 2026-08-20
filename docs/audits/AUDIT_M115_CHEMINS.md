# M115 — audit des chemins du Copilote, avant la refonte DA

Audit PUR (aucune correction, aucun changement visuel). Cartographie du Copilote sur main (M113) —
les 6 chips, leurs chemins nominaux, dégradés et conversationnels — pour que la refonte
`docs/DA-COPILOTE-v1.html` se pose sur des chemins qui tiennent. Preuve reproductible via
`qa/m115/audit_*.py` (rejoue `answer()` et dump la réponse exacte). Fait le 18/08/2026.

Méthode : chaque cas est une DEMANDE exacte → RÉPONSE exacte servie par `answer()` (+ chrono).
Rien n'est corrigé — Vic arbitre ce qu'on répare avant de repeindre.

---

# PARTIE 1 — LES DÉFAUTS (par gravité)

## A. Ce qui TROMPE

### D1 — La source citée ne correspond pas à la donnée qui répond
Un comptage par CRITÈRE crédite toujours « cadastre », même quand le critère vient d'ailleurs.
- **Demande** (chip données) : « Combien de parcelles en procédure judiciaire à Saint-Denis ? »
- **Réponse** : « À Saint-Denis, 126 parcelles présentent un signal de procédure judiciaire
  (BODACC). **(Source : cadastre, Etalab 2026-06)** » · `sources=['cadastre']`
- **Preuve du biais** : la maquette DA (§2) attend pour CE cas « SOURCE · **BODACC** — INGÉRÉ LE
  16/08/2026 ». Le signal « procédure judiciaire » vient de BODACC ; « défiscalisation » d'un
  référentiel fiscal ; « permis » de Sitadel — mais la réponse crédite le cadastre dans tous les cas.
- **Cause** : `src/labuse/copilote_v2/outils.py:168` — `compter_parcelles` renvoie toujours
  `source="cadastre", millesime=CADASTRE_MILLESIME`, quel que soit le critère filtrant.
- **Gravité** : TROMPE — la provenance affichée n'est pas celle de la donnée qui fonde le chiffre.

## B. Ce qui BLOQUE

### D2 — Une question de données à qui il manque juste la commune est REFUSÉE
- **Demande** (chip données) : « combien de parcelles »
- **Réponse** : « Je n'ai pas d'outil dédié pour cette demande. LABUSE couvre les données
  foncières et de marché : parcelles (comptage, surface, zonage, verdict)… » · `refus=aucun_outil`
- **Attendu** : une PRÉCISION « sur quelle commune ? » (la maquette §4 montre exactement ce
  gabarit pour un paramètre manquant). Ici le sélecteur ne trouve pas d'outil faute de commune et
  bascule en refus, au lieu de demander le paramètre.
- **Cause** : `answering.py:493` (`refus == "aucun_outil"` → `_sans_outil`) ; le sélecteur
  (`_select_tool`) renvoie `aucun_outil` quand la commune manque, aucune branche ne réclame le
  paramètre pour un comptage.
- **Gravité** : BLOQUE — une demande légitime meurt en refus au lieu d'une question.

### D3 — Un PROJET en texte libre n'ouvre PAS le formulaire (contredit M113)
- **Demande** (texte libre, sans chip) : « je veux monter une opération immobilière »
- **Réponse** : `clarification=true` · « Pouvez-vous préciser : lieu (commune), nombre de logements
  visés, budget d'achat, et type d'opération ? » — **pas** de `projet_form`.
- **Attendu (M113 Phase 3)** : « le Copilote ne crée plus jamais un projet sans passage par le
  formulaire » et « intent PROJET (chip OU texte libre) ouvre le formulaire, prérempli ». Le chip
  « projet » ouvre bien `projet_form` (même vide) ; le texte libre vague, lui, retombe sur l'ancienne
  clarification-texte.
- **Cause** : `answering.py:478` — le court-circuit `if route.clarification and intent not in
  ("HORS_SUJET","RECHERCHE","VERIFICATION")` intercepte AVANT la branche PROJET (`:534`→`:538`
  `_projet_form`). Un PROJET que le routeur juge vague ne parvient jamais au formulaire.
- **Gravité** : BLOQUE / INCOHÉRENT — deux comportements pour la même intention selon le chemin.

### D4 — Le chip « Ouvrir un outil » sur une demande vague REFUSE au lieu de proposer la liste
- **Demande** (chip outil) : « ouvre un outil »
- **Réponse** : « Je n'ai pas d'outil dédié pour cette demande… » · `refus=aucun_outil`
- **Attendu** : le sous-titre de la maquette dit « 28 outils d'analyse » — le chip devrait mener à
  un choix parmi les outils, pas refuser. Aucune voie n'est proposée.
- **Cause** : `answering.py:493`→`_sans_outil` ; aucun chemin « lister/choisir un outil ».
- **Gravité** : BLOQUE — l'intention explicite « ouvrir un outil » n'aboutit sur rien d'ouvrable.

## C. Ce qui MANQUE

### D5 — La réponse web est trop longue (contexte superflu)
- **Demande** (chip web) : « Qui est le maire de La Possession ? »
- **Réponse** (334 car.) : « Le maire de La Possession est **Erick Fontaine**, élu au second tour des
  élections municipales du 22 mars 2026 avec 50,35 % des voix et officiellement installé le 27 mars
  2026 (31 votes pour, 4 blancs). Il succède à Vanessa Miranville, qui assurait ce mandat depuis
  2020. »
- **Attendu (DA §3 + WEB_SYSTEM)** : « Court par construction : le fait, la source, la date. Pas de
  paragraphe d'enrobage. » (la maquette : « Le maire de La Possession est **Vanessa Miranville**. »)
  Malgré `WEB_SYSTEM` (« UNE à DEUX phrases… aucun contexte superflu », `outils.py`), le modèle sert
  50,35 %, 31 votes, 4 blancs, la succession depuis 2020.
- **Preuve reproductible** : idem « qui est le maire de Cilaos » → 2 phrases chargées (Phase 3.1).
- **Gravité** : MANQUE — gabarit non conforme (verbeux).

### D6 — Un refus ne propose pas de voie cliquable
- **Demandes** : « combien de parcelles » (D2), « ouvre un outil » (D4), « quelle est la météo… »
- **Réponse** : le gabarit refus liste ce que LABUSE COUVRE (texte), mais `porte=None`.
- **Cause** : `answering.py:776` — `_sans_outil(...) return _reply(txt, intent, refus="aucun_outil",
  porte=None)`. Le texte décrit le périmètre ; il n'est pas actionnable.
- **Attendu (M112)** : « un refus utile propose une voie ». Ici la voie est décrite, jamais cliquable.
- **Gravité** : MANQUE.

### D7 — Le récap M109 (« J'ai compris… ») est redondant et sent le slug
- **Exemples servis** :
  - « J'ai compris : répondre à votre question — Cilaos · **friches à Cilaos** · friche. »
  - « …Saint-Denis · **parcelles procédure judiciaire Saint-Denis** · procédure judiciaire (BODACC). »
- **Constat** : la commune et le critère sont répétés 2–3 fois ; « parcelles procédure judiciaire
  Saint-Denis » se lit comme un identifiant interne, pas une phrase.
- **Cause** : `answering.py:258` concatène `_compris_fr(route.params)` (« Cilaos ») + `criteres_appliques`
  (les `criteres_labels` de `compter_parcelles`, qui re-portent commune + critère).
- **Attendu** : « aucun jargon servi » — la maquette montre une phrase nette « J'ai compris :
  Saint-Denis · parcelles sous procédure judiciaire. »
- **Gravité** : MANQUE (soin).

### D8 — « Nouveau fil » et l'annonce du TTL sont absents sur certains écrans
- **Constat** : `data-fil-nouveau` (`CopiloteView.tsx:312`) et le minuteur d'expiration
  (`CopiloteView.tsx:174` — `if (fil.length === 0 || filExpire) return`) sont conditionnés à
  `fil.length > 0`. Or le **récap-péage RECHERCHE** (chip parcelle) et le **formulaire projet**
  n'alimentent pas `fil` (ils passent par `recap` / `projet_form`). Sur ces deux écrans : pas de
  bouton « Nouveau fil », pas d'annonce de TTL.
- **Gravité** : MANQUE — présence incohérente d'une promesse d'écran.

### D9 — Le chip « web » est sans contexte conversationnel
- **Constat** : le chip web court-circuite `classify` (M113) ; un tour web ne voit NI l'historique
  NI les paramètres. Un enchaînement « et à Saint-Pierre ? » après une question web ne peut pas
  fonctionner (aucune continuation possible). La rupture de sujet « tient » trivialement (il n'y a
  aucun contexte à rompre), mais aucune reprise non plus.
- **Preuve** : Phase 3.1 web — la réponse ignore `prior_params` (par construction).
- **Gravité** : MANQUE — limitation assumée du court-circuit, à décider pour la refonte.

### D10 — Le gabarit de PRÉCISION diffère selon le chemin
- **Chip parcelle** : `clarification_recap = {question, options, champ:"communes"}` → carte PRÉCISION
  avec champ dédié (DA §4).
- **Chip surveillance** : `clarification=true` + texte « Sur quelle commune veiller… ? » → pas de
  carte, la réponse se donne dans le champ permanent du fil.
- **Constat** : deux mécanismes pour le même besoin (« il manque un paramètre »). Le champ existe
  dans les deux cas, mais la STRUCTURE d'écran diffère.
- **Gravité** : MANQUE — incohérence de gabarit (Phase 1.3).

### D11 — Le critère non applicable sert d'abord le compte non filtré
- **Demande** (chip données) : « combien de parcelles avec une charge foncière supérieure à
  200 €/m² à Saint-Paul »
- **Réponse** : « **51129** (cadastre · Etalab 2026-06). ⚠️ Le critère « charge foncière > 200 €/m² »
  n'est pas encore interrogeable ici… » · `criteres_non_appliques=['charge foncière…']`
- **Constat** : le filet M109 est bien là (phrase, aucun bouton — conforme). MAIS le grand nombre
  51 129 (TOUTES les parcelles de Saint-Paul) mène la phrase avant l'avertissement : un lecteur
  pressé peut le prendre pour la réponse. La `carte_filtre` servie a `filtres:{}` (toutes les
  parcelles), sans mention du critère tombé dans le libellé.
- **Gravité** : borderline (par conception M109) — à surveiller au repaint.

## Chemins VÉRIFIÉS SAINS (pas de défaut)

- **Le zéro n'est pas une absence** : « Combien de parcelles à événement rouge à Cilaos ? » →
  « **Aucune parcelle** à événement rouge n'est recensée à Cilaos (cadastre Etalab 2026-06). » —
  zéro explicite et sourcé. ✓
- **Le filet M109** s'affiche en phrase, sans bouton (D11). ✓
- **La rupture de sujet** tient sur les chemins qui passent par `classify` (données, parcelle) :
  T2 « friches à Cilaos » après T1 « ≥ 20000 m² à Saint-Paul » n'hérite pas de `surface_min`. ✓
- **Le préremplissage projet depuis un texte vide** est gracieux : « créer » → `projet_form
  {prefill:{}}`, le formulaire s'ouvre vide, aucun plantage. ✓
- **L'échec** : modèle/API en panne → `ERREUR_INFRA` (« service d'analyse indisponible ») + garde
  générale `/ask` (M102) — jamais un 500 nu. Observé lors de l'épuisement de crédits API. ✓
- **Le surveillance nominal** : `answer()` sert « Pose de la veille… » (transitoire), l'endpoint
  `copilote_v2.py:55` `_executer_veille` sert le message final « Veille posée : … ». ✓

## Chrono par chemin (base M113 disponible)

| chip | demande | chrono |
|---|---|---|
| données | procédure judiciaire Saint-Denis | ~8,8 s |
| parcelle | terrains Saint-Leu 15 log (récap) | ~8,8–13 s |
| projet | 12 lots Bras-Panon (form) | ~1,2 s |
| web | maire La Possession | ~8–13 s |
| surveillance | permis Saint-Paul | ~2,4 s |
| outil | baromètre | ~1,9 s |

Les chemins qui gardent `_select_tool` + `_formuler` sur sonnet (données, parcelle, web) restent à
~8–13 s ; ceux qui n'ont ni sélection ni formulation (projet, outil, surveillance) sont à 1–2 s. Le
chip « données » ne gagne pas la latence espérée — il force l'intent mais garde sélection+formulation.

---

# PARTIE 2 — L'INVENTAIRE (plan de la refonte DA)

## 2.1 Les gabarits d'écran existants (≈ 11)

1. **Accueil** (`AccueilCopilote.tsx`) — hero + 6 chips « Que souhaitez-vous faire ? » + composer +
   brief du matin + « Vos dernières questions » + 6 exemples fixes + 3 cartes + bandeau garanties.
2. **Réponse inline** (`ReponseInline.tsx`) — QUESTION / OUTIL / web / données : `text` + phrase
   récap M109 (`compris`) + porte(s) (`porte` / `carte_filtre` / `surveillance` / `document`) + `sources`.
3. **Récap-péage** (`RecapConfirmation.tsx`, mode `recap`) — RECHERCHE/VERIFICATION : `recap` +
   `chips` + `suggestions` + boutons « Oui, c'est ça » / « Corriger » / « Lancer ».
4. **Précision — carte** (`RecapConfirmation.tsx`, `clarification_recap`) : question + options + champ.
5. **Précision — champ de fil** (`CopiloteView.tsx`, `clarification=true`) : réponse dans le champ
   permanent du fil. (= D10, deux gabarits pour le même besoin.)
6. **Refus** (`ReponseInline.tsx`, `refus`) — 5 motifs : `hors_sujet`, `aucun_outil`,
   `proprietaire_pp`, `projection`, `web_rien_trouve`.
7. **Erreur** (`ERREUR_INFRA` / tour `echec` du fil).
8. **Chargement** (`TraitementEnCours` / `dispatching`).
9. **Fil** (`CopiloteView.tsx`) — tour par tour, champ de réponse permanent, « Nouveau fil » (D8).
10. **Formulaire projet** (`ParcoursProjet.tsx`) — parcours guidé 5 étapes (refondu M114).
11. **Run de mission lourde** (`Entonnoir` / `FilInstruction` / `Resultats` / `BlocLivrable`) — l'UI
    d'instruction RECHERCHE (entonnoir, fil des moteurs, résultats, note d'opportunité, état vide).

La maquette DA n'en dessine que 4 (accueil, réponse données, réponse web, précision) : les 7 autres
gabarits (récap-péage, refus, erreur, chargement, fil, projet, run) sont à traiter pour ne pas
repeindre à moitié.

## 2.2 Couleur — le mint servi sur la surface IA (doctrine : mauve à l'IA)

Le token IA de la maquette est `--ia: #A78BFA` (mauve) ; le token courant est `--violet/--cp-violet:
#B497F0`. Doctrine de la refonte : le mint `#4ADE80` ne reste QUE sur le brief du matin (veille).

- **Mint LÉGITIME (brief du matin / veille)** — à garder : `AccueilCopilote.tsx:134` (point du
  brief), `:165` (compteur d'événements du panneau brief).
- **Mint sur des éléments IA — à migrer vers le mauve (≈ 58 occurrences)** — les plus visibles :
  - `AccueilCopilote.tsx:120` « instruit » (h1), `:206` chip scénario sélectionné, `:227` bouton
    Envoyer, `:264` badge « recherche ».
  - `RecapConfirmation.tsx:37` label « Précision », `:55` bouton Répondre, `:120` bouton Lancer,
    `:130/:134` carte récap + bouton « Oui ».
  - `CopiloteView.tsx:383/:388` bandeaux, `:403` bouton Instruire, `:408` point de statut, `:519`
    bouton relance.
  - `ReponseInline.tsx:40/:42` bouton et bordure de réponse.
  - `Entonnoir.tsx:51/:56/:57/:68/:72`, `FilInstruction.tsx:13/:43`, `Resultats.tsx:81/:89/:95`,
    `ui.tsx:10/:27/:48/:53` (badges/pills/étiquettes « sourcé »).
- **Mauve déjà en place (IA) — conforme** (≈ 25) : `CopiloteView.tsx:39/:326/:350/:353`,
  `ReponseInline.tsx:39/:42`, `ui.tsx:49/:53/:68/:72-74`, `BlocLivrable.tsx:16/:24/:28`,
  `FilInstruction.tsx:15`, `CopiloteEmbarque.tsx:55/:58/:64/:74/:75/:81`.

Détail exhaustif fichier:ligne : voir la passe couleur en annexe de ce mandat (agent d'inventaire).
Note : `--violet` courant (`#B497F0`) ≠ `--ia` maquette (`#A78BFA`) — trancher le token final.

## 2.3 Les textes servis (pour n'en oublier aucun à la refonte)

~200 chaînes recensées. Points d'entrée :
- **Accroches** : `AccueilCopilote.tsx:120-123` (h1 « Dites ce que vous cherchez. Le Copilote
  instruit. » + tagline « Une parcelle instruite en une minute — N sources, chaque chiffre daté »).
- **Placeholders** (14) : composer `:224`, réponse fil `CopiloteView.tsx:349`, précision
  `RecapConfirmation.tsx:52` « Votre réponse… », embarqué `CopiloteEmbarque.tsx:78/97`, projet
  `ParcoursProjet.tsx` (nom/commune/programme/budget/critères).
- **Chips (serveur)** : `answering.py:298-311` — 6 × (libellé + placeholder). NB : la maquette ajoute
  un **sous-titre** par chip (« Compter, filtrer, croiser », « 28 outils d'analyse »…) que le serveur
  ne fournit pas encore.
- **Labels de section** : `:198` « Que souhaitez-vous faire ? », `:258` « VOS DERNIÈRES QUESTIONS ».
- **Aide/serment** : `:234` « Écrivez librement — ou choisissez… », `CopiloteView.tsx:319`
  annonce d'expiration, `:409` « Moteurs déterministes journalisés ».
- **Garanties (pied)** : `AccueilCopilote.tsx:293-295` (3 lignes) — la DA §1 les ABSORBE sous le titre.
- **Refus/erreur (serveur)** : `answering.py` HORS_SUJET/ERREUR_INFRA/REFUS_PP/REFUS_PROJECTION,
  `_COUVRE`, web « rien trouvé » ; `missions_lourdes.py` veille/vérification ; `outils.py` commune
  non reconnue.
- Inventaire complet (~200) : voir la passe texte en annexe (agent d'inventaire).

## 2.4 Ce qui est en dur (vs dérivé)

**Bonne nouvelle — déjà dérivé** (la DA « compte de sources calculé, jamais en dur » est tenue) :
- Compte de **sources** : `AccueilCopilote.tsx:101` `chiffres?.sources` ← `/api/accueil/chiffres`
  (`accueil.py`, `SELECT count(*) FROM data_sources…`). Pas de « 55 » en dur.
- Compte d'**outils** : `LeftPanel.tsx:438` `${MODULES.length}` ← `outils/registry.ts` (28). Pas de
  « 28 » en dur.
- **Chips** : servis par `GET /api/copilote-v2/scenarios` (aucune copie en dur au front).
- **Parcelles / communes** : `AccueilChiffres` / `/communes` (dérivés).

**Réellement en dur (mineur)** : `AccueilCopilote.tsx:108/269` — `slice(0, 4)` / `length > 4` (nombre
de « dernières questions » avant « voir tout ») ; `:182` `.slice(0, 4)` (communes du brief). Magies « 4 ».

**À prévoir pour la DA** : les **sous-titres de chips** (maquette) n'existent pas dans le registre
serveur (`SCENARIOS` n'a que `libelle` + `placeholder`) — à ajouter côté serveur si on les veut
dérivés/servis, pas en dur au front.

---

## Synthèse pour l'arbitrage

Avant de repeindre : **D1** (source qui trompe) et **D2/D3/D4** (chemins qui bloquent au lieu de
demander/ouvrir) méritent une décision — ce sont des fissures sous la peinture. **D5–D10** (verbeux,
refus sans voie, récap slug, présence incohérente de « Nouveau fil »/TTL, gabarit précision double)
sont des manques de finition que la refonte peut absorber. La couleur (§2.2) et les sous-titres de
chips (§2.3) sont le gros du travail de repaint. Aucune correction n'a été faite — Vic tranche.
