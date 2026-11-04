# JOHN-TAYLOR-2 — John devient une page, en conversation

**Branche** `feat/john-taylor-2` · worktree `~/Desktop/labuse-john2` · ports 9540/6740 · **Opus**
**Pas de merge. Aucun accès prod.** Date : 2026-11-04 (Réunion +04). DA existante réutilisée.
**Ne touche pas au Tableau de bord** (`TableauDeBord.tsx` : zéro ligne changée — un autre mandat s'en charge).

> **Bilan en une ligne.** John Taylor n'est plus un onglet de la page Données : c'est une **page à part
> entière** du rail admin (« John Taylor », un clic depuis n'importe quelle page), **en conversation** —
> même forme que le Copilote de COPILOTE-4 : à gauche la **liste des conversations** + « + Nouvelle
> conversation », au centre le **fil**, à droite un **volet repliable** (résumé du matin, veille, carnet,
> coût du mois). L'**accueil parle** (« Bonjour Vic. Tout tourne : rien n'attend ta décision » / « Deux
> choses t'attendent »), avec trois suggestions utiles. **Plus jamais d'erreur brute** : un outil ou la base
> qui tombe → John dit en une phrase ce qui a échoué et ce qu'il propose, le détail part au journal.
> L'**enquête** d'une carte s'affiche comme une **question de John**, pas un message de Vic. Réponses
> **lisibles** : chiffres en gras, **sources en étiquettes datées**, **boutons vers l'écran concerné**. Une
> action = une **ligne d'état**. **Historique 90 j**, reprise d'un clic, suppression. **Mobile 390 px** : la
> liste devient un menu (☰). Recette : captures des 3 états + erreur + mobile ; les 10 questions rejouées ;
> **hook vert** (secrets 0 · tsc 0 · vitest 304/304 · build OK · unit 2884/0 · cohérence 6/0 · John 27/0).

---

## Ce qui change — la FORME (le moteur ne bouge pas)

Le **moteur** de John (boucle d'outils Opus, liste fermée d'actions, verrou anti-invention, plafond,
résumé, veille, enquête) est celui de JOHN-TAYLOR-1. Ce mandat **re-présente** John en conversation et
l'**installe comme une page**. Les seuls ajouts backend servent cette forme (historique navigable, accueil
calculé, sources d'une réponse, filet anti-erreur-brute).

### Une page du rail admin (plus un onglet de Données)
- **`AdminView.tsx`** : nouvelle section **`john-taylor`** (libellé « John Taylor », icône ⚓) dans le rail,
  après Contacts. John prend **tout le volet de contenu** (pas d'en-tête générique, pas de cap 1120 px, il
  gère son propre défilement) — une page conversationnelle pleine hauteur, comme le Copilote.
- **`Circuit.tsx`** : l'onglet « John Taylor » de la page Données est **retiré**. La carte
  **« Demander à John »** du Tableau de bord appelle maintenant `store.demanderAJohn(...)` (via la prop
  `onDemanderJohn` qui vit dans `Circuit`, **pas** dans `TableauDeBord`) → bascule sur la page John.
- **`useApp.ts`** (store) : `adminJohnEnquete` + `demanderAJohn(e)` (ouvre la page + pose l'enquête) +
  `clearJohnEnquete()`. `goAdminSection('john-taylor')` suffit pour y aller d'un clic.

### Les trois zones (même patron que COPILOTE-4)
- **Gauche — les conversations** (`JohnSidebar`, dans `JohnTaylor.tsx`) : les conversations du compte, la
  plus récente en tête (titre = la première question abrégée, âge « aujourd'hui / hier / il y a N j »),
  **« + Nouvelle conversation »**, la **suppression** (✕ au survol → confirmation inline), et le **bandeau
  de rétention** en pied (« Conservées 90 jours, supprimables à tout moment »).
- **Centre — le fil** : l'accueil **ou** le fil, + le champ en bas (**Entrée envoie · Maj+Entrée saute une
  ligne**). Messages de Vic à droite (bulle mint), réponses de John à gauche (carte).
- **Droite — le volet repliable** (`VoletInfos`) : **coût du mois**, **résumé du matin**, **veille**
  (étiquettes à millésime), **carnet de bord** (+ validation/rejet des propositions). Bouton
  « Masquer / Afficher le volet ».

### L'accueil qui parle
Calculé **à l'ouverture** (aucun appel modèle) côté serveur (`john/accueil.py`, dans le payload de
`GET /admin/john`) : le **nombre de choses qui attendent une décision** = incidents ouverts + propositions
de carnet + sources de **classe B** avec une nouvelle version à valider (best-effort : une lecture qui rate
compte pour zéro — jamais de fausse alerte). La phrase bascule :
- 0 → « **Bonjour Vic. Tout tourne : rien n'attend ta décision.** »
- 1 → « Bonjour Vic. Une chose t'attend. » · N → « **Bonjour Vic. Deux choses t'attendent.** »

Trois **suggestions** : « Tout est à jour ? », « Qu'est-ce qui a changé depuis hier ? », « Où en est q_v21 ? ».
Cliquer une suggestion démarre la conversation.

### Plus jamais d'erreur brute
Le tour de chat (`chat.repondre`) **enveloppe** la boucle d'outils : si un outil, la base ou le fournisseur
du modèle tombe, John répond **une phrase** qui dit **ce qui a échoué** et **ce qu'il propose** (« Je n'ai
pas pu aboutir : la base n'a pas répondu. Réessaie dans un instant — j'ai mis le détail technique au
journal. »), jamais une trace. Le détail part au **journal serveur** (`log.exception`). Deuxième filet au
niveau des routes (`/admin/john/chat`, `/admin/john/enquete`) : même en cas de pépin avant que le tour
puisse se rattraper, **une phrase, pas un 500**.

### L'enquête = une question de John
Le bouton « Demander à John » d'une carte « ça casse » ouvre la page John ; le fil commence par un **tour de
John** (« Tu m'as demandé de regarder « … ». Je creuse les journaux… », carte à bordure mauve pointillée),
**pas** par une bulle de Vic. La cause et la correction (+ mandat Claude Code en mode « demande du code »)
suivent dans un second tour de John.

### Réponses lisibles
- **Chiffres en gras** (le rendu met en valeur les nombres ET les `**gras**` du modèle — l'anti-invention
  garantit déjà qu'un nombre affiché est sourcé).
- **Sources en étiquettes datées** : les **lectures réelles** du tour (jobs, contrôles, sauvegardes…)
  deviennent des puces « Jobs · 09:12 » (l'heure de lecture). Jamais inventées — tirées des outils
  effectivement appelés.
- **Boutons vers l'écran concerné quand il existe** : « Voir les jobs → » (section `cron`), « Voir le
  Radar → » (`radar`), « Voir les données → » (`donnees`) — rien d'autre (une lecture sans écran dédié, le
  carnet par ex., ne pose pas de bouton).
- **Action = ligne d'état** : une action exécutée s'affiche en ligne d'état (⚙ « Sauvegarde lancée… »), puis
  son résultat en prose. La méta (lectures, boutons, action) est **rangée avec le message** → la reprise
  d'une conversation **rejoue** sources et boutons à l'identique.

### Historique & mobile
- **90 jours** (`john_conversations_jours`, inchangé), purge quotidienne déjà en place. Nouvelles routes
  (cloisonnées au compte, suppression en CASCADE) : `GET /admin/john/conversations`,
  `GET /admin/john/conversations/{id}`, `DELETE /admin/john/conversations/{id}`.
- **390 px** : la colonne des conversations **devient un menu** (☰ → tiroir avec scrim, Échap/clic-dehors
  pour fermer) ; le volet passe aussi en tiroir (ⓘ) ; le fil et le champ s'empilent en une colonne. *(Le
  rail admin 216 px reste celui du shell commun à toutes les pages admin — hors mandat ; la page John,
  elle, est pleinement responsive.)*

---

## RECETTE

| Attendu du mandat | Résultat |
|---|---|
| **Captures des 3 états** (accueil, conversation, enquête) | ✅ `captures/01-accueil.png`, `02-conversation.png`, `04-enquete.png` |
| **Une erreur d'outil simulée rendue en phrase** | ✅ `captures/03-erreur-outil.png` (carte rouge, « Je n'ai pas pu aboutir : la base n'a pas répondu… ») + test `test_john_2::test_erreur_outil_rendue_en_phrase` (jamais la trace brute, « journal » cité) |
| **Les 10 questions de JOHN-TAYLOR-1 rejouées** | ✅ `test_john_1::test_dix_questions_reelles_sourcees` **passe** (10 questions → 10 lectures d'outil, réponses sourcées, trace en base) — inchangé, toujours vert |
| **Mobile 390 px** (la liste devient un menu) | ✅ `captures/05-mobile-accueil.png` (☰/ⓘ, une colonne, suggestions empilées), `06-mobile-tiroir.png` (la liste des conversations en tiroir) |
| **Hook vert** | ✅ secrets **0** · tsc **0** · vitest **304/304** · build **OK** · unit **2884/0** (48 skip) · cohérence **6/0** |
| **Historique** (90 j, reprise, suppression) | ✅ `test_john_2::test_conversations_listees_rouvertes_supprimees` (liste la plus récente en tête, reprise, suppression cloisonnée + CASCADE) |
| **Accueil qui parle** | ✅ `test_john_2::test_accueil_rien_puis_une_chose` (« rien n'attend » ↔ « … t'attend ») |
| **Sources & boutons tirés des lectures** | ✅ `test_john_2::test_chat_rend_sources_et_boutons_depuis_lectures` (puce « Jobs » datée + bouton `cron`, rejoués à la reprise) |
| **Compte-rendu** | ✅ ce fichier |

**Tests John : 27/27** (`test_john_1.py` 23 + `test_john_2.py` 4). **Front : 304/304** (le vieux onglet
2-tests → 3-tests sur la nouvelle page). Les captures sont jouées en direct sur le vrai front (Vite 6740,
Chrome Playwright), réseau en bocal (route interception) : on prouve la **forme réelle** (CSS, layout, flux)
sans backend ni clé API. Driving via `window.__labuse.demanderAJohn` / `goAdminSection` (exposés au hook
d'auto-QA, comme `ouvrirEtude` — aucun effet produit).

### Reproduire les captures
`npm run dev -- --port 6740` puis, depuis `frontend/`, `node captures/john-taylor-2.mjs` (écrit les 6 PNG
dans ce dossier `captures/`, gitignoré comme tous les `**/captures/`).

---

## CE QUI RESTE UN GESTE HUMAIN

1. **Merge** `feat/john-taylor-2 → main` par PR (hors mandat « pas de merge »). Rien n'est actif tant que ce
   n'est pas déployé (la page, les routes d'historique, l'accueil, les sources de réponse).
2. **Mobile du shell admin** : le rail 216 px n'est pas replié sur petit écran — c'est le shell commun à
   toutes les pages admin, hors mandat. La page John, elle, est responsive (☰/ⓘ, tiroirs). À traiter avec le
   shell admin si on veut l'admin pleinement mobile.
3. **Crédit API** (dette JOHN-TAYLOR-1) : le chat et l'enquête consomment Opus ; poser le plafond en prod.

---

## FICHIERS

**Neufs** : `src/labuse/john/accueil.py`, `tests/test_john_2.py`,
`frontend/captures/john-taylor-2.mjs` (gitignoré), `docs/audit-2026-11/john-taylor-2/captures/*.png`
(gitignorés), ce compte-rendu.

**Modifiés** :
- `src/labuse/john/chat.py` — historique navigable (`lister_conversations` / `charger_conversation` /
  `supprimer_conversation`, cloisonné compte, CASCADE), sources & boutons d'une réponse à partir des
  lectures réelles (`_sources_et_boutons`, méta rangée avec le message), filet anti-erreur-brute
  (`_phrase_echec` + enveloppe du tour).
- `src/labuse/api/john.py` — `accueil` dans `GET /admin/john` ; routes d'historique ; filet try/except sur
  `chat` et `enquete` (une phrase, pas un 500).
- `frontend/src/components/admin/circuit/JohnTaylor.tsx` — **réécrit** en page conversationnelle (3 zones +
  accueil + fil lisible + enquête-question + action-ligne-d'état + mobile).
- `frontend/src/components/admin/circuit/JohnTaylor.test.tsx` — refait pour la nouvelle page.
- `frontend/src/components/admin/AdminView.tsx` — section `john-taylor` (rail + rendu pleine page).
- `frontend/src/components/admin/circuit/Circuit.tsx` — onglet John retiré, « Demander à John » → store.
- `frontend/src/store/useApp.ts` — `JohnEnquete`, `adminJohnEnquete`, `demanderAJohn`, `clearJohnEnquete`.
- `frontend/src/lib/api.ts` — `getJohnConversations` / `getJohnConversation` / `deleteJohnConversation`.
- `frontend/src/App.tsx` — `demanderAJohn` / `goAdminSection` exposés au hook d'auto-QA (captures).
