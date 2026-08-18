# M117 — refonte DA du Copilote (mauve exclusif à l'IA, 11 gabarits, D5–D10)

Livré le 18/08/2026, d'après `docs/DA-COPILOTE-v2.html` (font foi). Deux chantiers : la migration de
couleur (mint → mauve sur la surface IA) et les six défauts de finition D5–D10 de l'audit M115.
Trois commits sur `feat/m117-da-copilote` (non mergé).

## Phase 1 — migration mint → mauve

Nouveaux tokens de surface IA dans `tailwind.config` : `cp-ia` (#B497F0 = violet), `cp-ia-on/-bg/
-border/-border-on/-dim`, + `cp-warn`/`cp-danger` (cartes refus/erreur). Les ~58 usages de mint sur
la surface IA sont passés au mauve (`cp-ia`) dans les 10 composants Copilote + le formulaire projet
partagé (thémé : mauve dans le Copilote, mint dans Projets). **Exceptions conservées en mint** : les
2 usages du brief du matin (`AccueilCopilote:119` compteur d'événements, `:199` point) — la veille
n'est pas de l'IA. **Grep final** : aucune classe ni hex mint sur la surface IA hors brief.
Contraste : `cp-ia #B497F0` sur fond `cp-ia-bg #100C1C` — lisible, éléments distinguables (M105-B).
La migration précise a évité les faux positifs (noms de tons `'mint'`, clés d'objet) : seules les
CLASSES utilitaires (`bg-mint`, `text-mint`, `mint/x`, `mint-on`) ont migré ; les tons `'mint'`
(Badge/PillStatut) rendent désormais mauve.

## Phase 2 — les 11 gabarits

| # | gabarit | état |
|---|---|---|
| 1 | **Accueil** | REFONDU — six intentions en grille (sous-titres SERVEUR, « {n} outils » = MODULES.length, aucun compte en dur), garanties absorbées sous le titre, brief descendu sous le point d'entrée, « Reprendre » en bas. Les 6 exemples + 3 cartes SUPPRIMÉS. |
| 2 | **Chargement** | migré mauve — 3 points en pulsation, une phrase (`TraitementEnCours`), pas de fausse progression. |
| 3 | **Réponse données** | REFONDU — carte IA, récap M109 en phrase (D7), source du critère « SOURCE · BODACC » (M116 D1), porte cliquable. |
| 4 | **Réponse web (D5)** | REFONDU — ≤ 2 phrases (~150 car.). |
| 5 | **Précision (D10)** | UNIFIÉ — un seul gabarit : carte IA + kicker « PRÉCISION », le champ est le champ PERMANENT du fil (autofocus), plus jamais deux cadres. |
| 6 | **Récap-péage** | migré mauve + D8 (« Nouveau fil » + TTL). Boutons conservés (une action va s'exécuter). |
| 7 | **Run en cours** | migré mauve (Entonnoir / FilInstruction / Resultats — étapes réelles du moteur). |
| 8 | **Refus avec voie (D6)** | REFONDU — carte `warn` + kicker, voie CLIQUABLE (liste des outils, carte…), JAMAIS un champ de réponse dans la carte. |
| 9 | **Critère non applicable** | REFONDU — carte `warn`, l'aveu d'abord (M116 D11 déjà appliqué). |
| 10 | **Erreur** | REFONDU — carte `err`, message honnête (jamais d'identifiant de run), Réessayer sur place. |
| 11 | **Fil expiré (TTL)** | D8 — expiration annoncée sur TOUS les chemins (fil, récap-péage, formulaire projet), fil estompé, reset au message suivant. |
| 12 | **Formulaire projet** | thémé MAUVE dans le Copilote (mint dans Projets) — accent paramétré. |

## Phase 3 — défauts de formulation

- **D5 (web trop long)** : `_deux_phrases` (troncature déterministe ≤ 2 phrases / ~180 car., coupe à
  la 1re clause « X est Y ») + `WEB_SYSTEM` strict + `max_tokens` 300. La gate scénario **repasse à
  6/6** (web len ~150–210).
- **D7 (récap slug)** : le param `sujet` (paraphrase « friches à Cilaos ») RETIRÉ du récap + dédup des
  critères → « J'ai compris : … Cilaos · friche. », chaque information une fois, aucun slug.
- **D9 (web sans contexte)** : le fil est passé au web (`recherche_web(history=…)`) — un enchaînement
  « et à Saint-Pierre ? » se résout, sans réintroduire classify. Cohérent M111 (le modèle résout la
  référence, il ne somme pas). Mesure : le web gardait 0 contexte ; il en a désormais, sans coût de
  latence (classify reste court-circuité).
- Sous-titres d'intention servis par le serveur (`SCENARIOS.sub`).

## Phase 4 — vérification

- **Captures** (`qa/m117/captures.mjs`) : accueil v2, réponse données (carte mauve · récap dédup ·
  SOURCE · BODACC · porte), réponse web courte, refus/voie, précision. Conformes à la maquette.
- **Grep couleur** : aucun mint sur la surface IA hors brief du matin ; le mauve reste cantonné à l'IA.
- **Gate scénario → 6/6** (le cas web est le 6e).
- **Gates** : véracité 33/33 · routeur inchangé · fil 6/6 · facette 11/11 — rien d'assoupli.
- **Golden 0 FAIL** · **suite 1605 passed** · **tsc 0** · **build OK**.
- Les six exemples et les trois cartes ont DISPARU de l'accueil ; rien d'atteignable ne l'est moins
  (les six intentions couvrent les mêmes voies ; le texte libre reste).

## Ce qui reste (honnêteté)

La couleur et les gabarits de réponse (3/4/5/8/9/10/11) + accueil + formulaire projet sont REFONDUS.
Les gabarits **6 (récap-péage)** et **7 (run en cours)** sont **migrés au mauve** mais gardent leur
structure interne existante (RecapConfirmation modes Oui/Corriger/affiner ; Entonnoir/FilInstruction/
Resultats) — pas encore re-tracés au pixel de la maquette (cartes kicker « AVANT DE LANCER » /
progress-steps + run-lines). Le cas D6 « trop de résultats → carte » n'a pas de producteur backend
dédié (le gabarit `warn` + porte est prêt s'il en apparaît un). Les icônes tabler des intentions ne
sont pas ajoutées (pas de librairie d'icônes dans le front ; la grille rend libellé + sous-titre).
