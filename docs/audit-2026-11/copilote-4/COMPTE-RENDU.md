# COPILOTE-4 — le Copilote devient une conversation

- **Branche** : `feat/copilote-4` · worktree `~/Desktop/labuse-copilote4` · ports 9520 (API) / 6720 (front).
- **Portée** : la **FORME** de l'écran Copilote uniquement. **Pas de merge, aucun accès prod** (merge = geste de Vic).
- **À lire d'abord** : `docs/audit-2026-11/copilote3/COMPTE-RENDU.md` + la maquette validée
  (`Maquette — Copilote en conversation.html`, deux écrans : accueil vide, conversation en cours).

## Règle du mandat, tenue

> **« Ne touche pas au moteur de réponse ni aux verrous anti-invention de COPILOTE-3 : seule la forme change. »**

`answering.py`, `router.py`, `resume_fiche.py`, `outils.py` — **zéro ligne touchée**. Preuve :
- `tests/test_copilote3_verdicts.py` (le filet du mandat COPILOTE-3) : **14 passed** (déterministes), 5 skip
  témoins (base de hook minimale) — à l'identique de COPILOTE-3.
- Les **20 questions** de la recette COPILOTE-3 rejouées contre la base de dev → **réponses identiques en
  fond** (`captures/recette-copilote3-rejouee.txt` : Q01 copro « Oui … 9 lots » RNIC … Q20 « SCI ALOE »
  DGFiP — la table exacte du compte-rendu COPILOTE-3).

Les réponses voyagent par la structure de reply **existante** (`text` + `sources` + `porte`/`carte_filtre`/
`voie`/`document` + `resume_fiche`). COPILOTE-4 ne fait que la **re-présenter**.

## Ce qui change (la forme)

### Une page en deux colonnes
- **Gauche** — `ConversationsSidebar.tsx` (neuf) : les conversations du compte, **les plus récentes en
  haut** (titre = la première question abrégée, servie par `historique._titre` ; ancienneté « aujourd'hui /
  il y a N j »), un **« + Nouvelle conversation »**, la **suppression** d'une conversation (✕ au survol →
  confirmation inline), et le **bandeau de rétention** en pied.
- **Centre** — `CopiloteView.tsx` (réécrit) : l'accueil (vide) **ou** le fil, + le champ en bas.

### L'accueil
« **Bonjour. Sur quoi on travaille ?** » (avatar « C »), une phrase d'explication, **six suggestions** en
grille (sous-ensemble des exemples actuels : parcelle · propriétaire · PLU · procédure · pièges · taxe), et
le champ « **Écrivez comme à un collègue…** ». Les suggestions **disparaissent dès la première question**
(cliquer une suggestion DÉMARRE la conversation — décision de forme, cohérente avec « une conversation »).

### Le fil
- messages de l'utilisateur **à droite** (bulle mauve), ceux du Copilote **à gauche** (carte `ReponseInline`
  inchangée) ;
- **en-tête** : le titre de la conversation (la première question) et, **quand une parcelle est le sujet**,
  son **IDU · commune · zone · surface** — lus de `resume_fiche` (idu, commune, tuiles *Surface* / *Zone
  PLU*) que la réponse PORTE déjà, jamais inventés ; le contexte **suit** (une question de suite — « et si je
  démolis ? », « c'est en copropriété ? » — s'applique à la parcelle du fil sans la répéter, via
  `conversation_id` que le serveur relit) ;
- sous chaque réponse : ses **sources en étiquettes à millésime** (`ReponseInline` : chaque chaîne servie
  devient une puce mono — « PLU Saint-Paul — zone U3c … », « RNIC — répertoire des copropriétés »,
  « politique.pappers.fr » ; **le millésime montré est celui que la source porte, rien d'ajouté**), puis le
  **geste suivant en boutons** (ouvrir la fiche / voir sur la carte / lancer l'outil / éditer un document /
  une voie) — **exactement les champs que la réponse porte** (`porte`, `carte_filtre`, `document`, `voie`,
  `outils_liste`, `surveillance`), jamais inventés ;
- le champ permanent en bas : « **Continuez la conversation…** » + note « *Le Copilote ne dit que ce que les
  données portent…* ».

> Note honnête : sur le résumé « dis-moi tout », la seule source portée est `fiche LABUSE (run servi)`, que
> `ReponseInline` **masque depuis RECETTE-1 (D5)** — donc **pas de puce** sur cette carte (comportement
> d'aujourd'hui, préservé), un bouton « Voir la fiche parcelle complète » l'accompagne. Les puces à
> millésime apparaissent sur les tours à source **externe** (PLU, RNIC, DVF, web…). Les riches puces de la
> maquette (« cadastre · 2026-09 », …) étaient illustratives.

### Conservation & suppression
- **Rétention 30 jours** (était 7), par compte : `config.copilote_v2_retention_jours = 30` (défaut, toujours
  surchargeable à chaud via `app_reglages copilote_retention_jours`). La purge quotidienne
  (`copilote-purge` → `historique.purger`) et le bandeau front lisent la **même** valeur effective.
- **Suppression** d'une conversation : `historique.supprimer()` (cloison lot 6 : compte_id OU sujet de
  session — jamais celle d'un autre ; messages par CASCADE) + route `DELETE /api/copilote-v2/missions/{id}`
  + `copiloteV2MissionSupprimer` au front. Le **pied le dit** : « *Conservées 30 jours, supprimables à tout
  moment…* ».

### Règles transversales
- **aucun défilement horizontal** (`min-w-0`, `break-words`, colonnes `overflow-hidden`) ;
- **Entrée envoie · Maj+Entrée saute une ligne** (textarea unique) ;
- **régions live** : le fil est `role="log" aria-live="polite"` ;
- **mobile 390 px** : la liste des conversations devient un **menu** (bouton ☰ → tiroir avec scrim,
  fermeture par Échap/clic-dehors/✕) ; les suggestions passent en 1 colonne.

## Fichiers touchés

| Fichier | Nature |
|---|---|
| `frontend/src/components/copilote/CopiloteView.tsx` | **réécrit** — coquille deux colonnes + accueil + fil |
| `frontend/src/components/copilote/ConversationsSidebar.tsx` | **neuf** — colonne gauche (liste/neuve/supprimer/rétention/mobile) |
| `frontend/src/components/copilote/ReponseInline.tsx` | sources → **étiquettes à millésime** (puces mono) ; reste inchangé |
| `frontend/src/lib/api.ts` | `copiloteV2MissionSupprimer(id)` |
| `src/labuse/copilote_v2/historique.py` | `supprimer()` (cloisonné, CASCADE) |
| `src/labuse/api/copilote_v2.py` | `DELETE /missions/{id}` |
| `src/labuse/config.py` · `src/labuse/reglages.py` | rétention **30 j** (défaut) |
| `tests/test_copilote_retention_r11.py` | défaut **30** + test de `supprimer()` cloisonné |

*Dette de propreté* : `AccueilCopilote.tsx` (ancien accueil mono-colonne, + le tiroir « brief du matin »
déjà code mort depuis RECETTE-2 D1) n'est **plus importé** — superseded par le nouvel accueil. Laissé en
place (suppression = cleanup ultérieur), comme le veut l'usage du dépôt.

## Recette

- **Captures avant / après** des deux écrans : `captures/avant-accueil.png`, `captures/avant-conversation.png`,
  `captures/apres-accueil.png`, `captures/apres-conversation.png` (+ `conv-main-readable.png`,
  `conv-main-bottom.png` lisibles).
- **Conversation de 4 questions avec contexte qui suit** (live, base de dev, parcelle `97415000CV1186`) :
  en-tête **`97415000CV1186 · Saint-Paul · U · 297 m²`** stable ; « Et si je démolis… » et « C'est en
  copropriété ? » **héritent la parcelle sans la répéter** ; chaque réponse porte **sources + boutons** :
  Q1 bouton *Voir la fiche* ; Q2 puce *PLU Saint-Paul — zone U3c* ; Q3 puce *RNIC*, bouton *Voir la fiche* ;
  Q4 (maire) puce *politique.pappers.fr* (réponse du **moteur inchangé** — web, pas un refus : la maquette
  l'illustrait en refus-voie, le moteur, lui, répond ; non touché par mandat).
- **Sources et boutons présents sur chaque réponse** : vérifié en DOM (puces `[data-source-chip]`, boutons
  `[data-reponse-*]`).
- **20 questions COPILOTE-3 rejouées** → réponses identiques (`captures/recette-copilote3-rejouee.txt`).
- **Mobile 390 px** : `captures/mobile-accueil-390.png` (1 colonne + ☰), `captures/mobile-drawer-390.png`
  (tiroir des conversations).
- **Suppression** prouvée de bout en bout : `DELETE` → `{ok:true}`, conversation + messages (CASCADE) partis
  de la base ; cloison testée (compte A ne supprime pas la conversation de B).

### Hook
- **Front** : `tsc -b` **0 erreur** · `vitest` **301/301** · `vite build` **OK**.
- **Back** (base de dev) : `test_copilote_retention_r11.py` **4 passed** (défaut 30 + purge + suppression
  cloisonnée) ; `test_copilote3_verdicts.py` **14 passed / 5 skip** (verrous intacts).

*Recette jouée le 2026-11-03. Branche `feat/copilote-4`, commit sur la branche. Pas de merge, pas de push,
aucun accès prod. Merge = geste de Vic.*
