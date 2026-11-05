# NU5-F — Accessibilité, mobile/tablette & mise en page

**5/11/2026 · branche `audit/nu5-f` · worktree `~/Desktop/labuse-nu5f` · ports 9780 (API) / 6980 (vite) ·
Opus · LECTURE SEULE (aucune correction) · base locale `labuse` q_v20 · prod ni touchée ni sondée.**

Périmètre du mandat : chaque page client et chaque outil sur **téléphone (390)** et **tablette (768)**,
portrait et paysage ; **clavier seul** ; **lecteur d'écran (VoiceOver)** ; **contrastes/lisibilité WCAG 2.2 AA** ;
**zoom 200 %** ; **mouvement réduit** ; **réseau lent (3G)**. Livrable : grille page × critère, trouvailles
classées, harnais automatique à 390 px.

---

## 0. Le fait qui domine tout l'axe mobile

**L'application REFUSE délibérément de s'ouvrir sur téléphone et tablette.** Au chargement,
`main.tsx::_rendre()` appelle `lib/appareil.ts::estAppareilMobile()` et, si vrai, monte **uniquement**
`<EcranOrdinateur/>` (« LABUSE est disponible sur ordinateur. Ouvrez app.labuse.immo depuis votre
ordinateur. ») — **ni l'App, ni l'admin, aucune autre page**. C'est une décision produit assumée
(commentaire `CHARGEMENT-1 point 6` : « LABUSE est un outil de bureau »).

Le verrou se déclenche si **un seul** critère est vrai : UA mobile (Android/iPhone/iPad/Mobile/Tablet),
iPad déguisé en Mac (MacIntel + tactile), pointeur principal tactile (`pointer: coarse`),
**ou largeur d'écran physique `window.screen.width` < 1 024 px**.

Vérifié **empiriquement** (harnais, descripteurs Playwright `devices`, et calcul direct du prédicat) :

| Appareil | Verrouillé ? |
|---|---|
| iPhone 12/13 (390, portrait **et** paysage) | ✅ oui → écran ordinateur |
| Pixel 7 (412) | ✅ oui |
| Tablette Android (800) | ✅ oui |
| iPad Pro portrait (1024, tactile+MacIntel) | ✅ oui |
| iPad gen 7 (810) | ✅ oui |
| Fenêtre de **bureau rétrécie** à 390 (écran physique 1440) | ❌ non → app rendue |

> **Conséquence pour le mandat** : sur un **vrai** téléphone ou une **vraie** tablette, en portrait comme
> en paysage, **aucune page client ni aucun outil n'est accessible**. Tous les critères « 390/768 au doigt,
> clavier virtuel, carte au doigt, PDF ouvrables… » sont donc **sans objet (N/A) par conception**. NU5-F ne
> peut pas certifier le mobile : il n'existe pas.

**Nuance utile pour la correction.** Le prédicat lit `window.screen.width` (écran **physique**), pas la
fenêtre : une fenêtre de bureau simplement rétrécie n'est **pas** bloquée. En rendant l'app ainsi, on
constate qu'**elle sait déjà se replier** : **0 débordement horizontal** sur les 7 vues à 390 px — et même à
**320 px** (cf. §3). Le code porte des points de rupture `md:`, des tiroirs, un rail qui se réduit en
colonne d'icônes, un hamburger Copilote. **La capacité responsive EXISTE mais est condamnée par le verrou.**
Lever le verrou serait donc peu risqué côté mise en page — mais exposerait alors les défauts d'accessibilité
ci-dessous (aujourd'hui ils ne frappent que l'utilisateur de bureau, le seul réel).

### L'écran-ordinateur lui-même (`EcranOrdinateur.tsx`)
Propre sur la DA (fond nuit, menthe), **contraste OK** (texte `txt-hi`/`mint` sur `bg-0`), lien `Contact`
mailto focusable au clavier. Réserves mineures : **pas de repère `main` ni de `h1`** (le message est un
`<p>`, pas un titre ; `RunNonConfigure` voisin a pourtant `role="alert"`) — un lecteur d'écran atterrit sur
du texte générique. Impact faible (c'est un cul-de-sac d'une phrase).

---

## 1. Méthode (rejouable, lecture seule)

- Backend `labuse.api.app:app` sur `:9780` (venv `~/Desktop/labuse/.venv`, `PYTHONPATH=src`, rôle PG
  `openclaw`, base `labuse`, `env=local` → **auth désactivée**, donc app complète sans session). Vite sur
  `:6980` (`LABUSE_API_DEV=http://127.0.0.1:9780`), base servie `/socle/`.
- Pilotage **Playwright** : verrou prouvé par `devices` (vrai iPhone/iPad) ; app rendue en rétrécissant la
  fenêtre (écran physique 1440 → non verrouillé). Mesures par `evaluate` : débordement, tailles de cibles,
  repères, visibilité du focus (marche clavier armée par un vrai `Tab`), régions live, noms accessibles.
- **axe-core 4** injecté dans la page (WCAG 2.0/2.1/2.2 A+AA, violations) sur chaque vue × {390, 1440}.
- **Contraste** calculé **déterministiquement** depuis la palette réelle (`tailwind.config.js` +
  `config/brand_colors.json`) — ratios WCAG sur fonds `bg-0 #0A0C0B` et carte `#111614`.
- Harnais versionné : `harness/audit_a11y.mjs` (+ `resultats.json`, la passe du 5/11). Captures dans `captures/`.

Surfaces couvertes : rail (Carte, Outils, Docs, Copilote, Radar, Projets, CRM, Sources, Admin), en-tête
(omnibox, Fiche commune, Signaler, notifications, compte), **Fiche parcelle** (`97416000EI1048`, 11 tiroirs),
carte MapLibre, écran-ordinateur. Cartographie des pages/outils/overlays établie par lecture de code
(`App.tsx`, `Rail.tsx`, `registry.ts` — 16 outils, ~12 familles d'overlays/modales).

---

## 2. Grille page × critère

Légende : **V** conforme · **O** réserve/partiel · **R** défaut net · **na** sans objet.
« Mobile réel » = sur vrai téléphone/tablette. « Repli ≤390 » = app rendue en fenêtre rétrécie.

| Surface | Mobile réel 390/768 | Repli ≤390 (débord.) | Cibles ≥44/≥24 | Clavier | Lecteur d'écran / structure | Contraste AA | Mvt réduit | 3G / chargement |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Écran-ordinateur** (seul écran mobile réel) | na¹ | V | V | V | O² | V | V | V |
| Carte + overlays | na¹ | V | **R**³ | V | O⁴ | **R**⁵ | V | O⁹ |
| Fiche parcelle (11 tiroirs) | na¹ | V | O | V | O⁶ | **R**⁵ | V | O⁹ |
| Copilote | na¹ | V | O | O⁷ | O⁸ | **R**⁵ | V | O⁹ |
| Docs | na¹ | V | **R**³ | V | O¹⁰ | **R**⁵ | V | O⁹ |
| Radar / Marché | na¹ | V | O | V | O | **R**⁵ | V | O⁹ |
| Projets | na¹ | V | O | V | O⁴ | **R**⁵ | V | O⁹ |
| CRM (Kanban) | na¹ | V | **R**³ | O | **R**¹¹ | **R**⁵ | V | O⁹ |
| Sources | na¹ | V | O | V | O⁴ | **R**⁵ | V | O⁹ |
| Outils (16, menu) | na¹ | V | O | V | O | **R**⁵ | V | O⁹ |

Notes : ¹ bloqué par le verrou (§0). ² pas de `main`/`h1` sur l'écran-ordinateur. ³ beaucoup de cibles
< 24 px (marqueurs communes 21 px ; Docs 405/423 ctrl < 44 px ; CRM 188 ctrl < 24 px). ⁴ **pas de `main`,
pas de `h1` sur la Carte** (vue d'atterrissage), pas de lien d'évitement. ⁵ axe `color-contrast` *serious*
sur **toutes** les vues (Docs 24 nœuds, Projets 12 à 1440 px) + calcul palette (§Contraste). ⁶ Fiche : titre
`role="heading"` au lieu de `<h1>` ; tiroirs avec `aria-expanded` (bien) ; pas de `main`. ⁷ **focus invisible
sur le composeur** Copilote (bordure menthe permanente, rien ne change au focus). ⁸ région live `role="log"
aria-live` **présente dans le code** mais montée seulement quand le fil est actif. ⁹ squelettes Suspense +
`Loading` `role="status" aria-live` présents (non éprouvés sous throttle 3G réel). ¹⁰ Docs : **6 `<th>` sans
`scope`**. ¹¹ CRM : **`nested-interactive` × 187** (contrôles focalisables imbriqués), pas de `h1`, pas de `main`.

---

## 3. Trouvailles classées

### CONSTAT STRUCTURANT — mobile/tablette indisponible par conception
Voir §0. Pas un bug : décision produit documentée. **Mais** il rend le mandat mobile sans objet et masque
une capacité responsive réelle (repli propre jusqu'à 320 px). À porter à la synthèse : décider si LABUSE
**assume** le bureau-seul (alors le mandat mobile tombe) ou veut ouvrir le mobile (alors les MAJEUR ci-dessous
deviennent bloquants pour le mobile aussi).

### MAJEUR

- **F1 — Contraste insuffisant, généralisé (WCAG 1.4.3 AA).** axe lève `color-contrast` *serious* sur **les 7
  vues**, aux deux tailles (Docs **24** nœuds à 1440 px, Projets **12**, Radar 5, CRM/ Sources/Carte 2–3 ;
  bouton **Signaler** systématique). Cause racine confirmée par le calcul de palette : les **bas étages de
  l'échelle de texte** passent sous le seuil AA 4,5:1 sur le fond principal `#0A0C0B` :

  | Jeton | Hex | Ratio /bg-0 | Verdict |
  |---|---|---:|---|
  | `txt-mut` (sous-titre, très utilisé) | #6B776F | **4,20** | ❌ < 4,5 (texte normal) |
  | `txt-off` | #5E6B64 | **3,52** | ❌ < 4,5 |
  | `txt-faint` | #4E5A53 | **2,72** | ❌ < 3 (sous le plancher non-texte) |
  | `txt-ghost` | #3E4A44 | **2,12** | ❌ < 3 |
  | `cp-faint` (Copilote) | #57655E | **3,20** | ❌ < 4,5 |
  | `st-exclue` (libellé statut) | #6B7A72 | **4,35** | ❌ < 4,5 |

  (En vert : `txt-hi`, `txt`, `lab`, `txt-dim`, menthe, ambre, corail, bleu, violet, iris, statuts
  chaude/surveiller/creuser/écartée — tous ≥ 4,5.) Les étages fautifs portent sous-titres, horodatages,
  libellés secondaires. *Correction par cause : remonter la luminance de `txt-mut`/`txt-off`/`cp-faint` (les
  plus bas servent surtout bordures/désactivé — vérifier au cas par cas qu'ils ne portent pas de texte lisible).*

- **F2 — CRM : `nested-interactive` × 187 (WCAG 4.1.2).** Le Kanban CRM imbrique des contrôles focalisables
  dans d'autres contrôles focalisables (carte-bouton contenant des boutons) : un lecteur d'écran et la
  navigation clavier s'y perdent (ordre et annonce imprévisibles). S'ajoutent **188 cibles < 24 px**, **pas de
  `h1`**, **pas de `main`**. La vue la plus dégradée de l'app côté accessibilité.

- **F3 — Cibles tactiles sous le minimum (WCAG 2.2 §2.5.8 AA = 24 px ; cible mandat = 44 px).** Généralisé :
  icône de recherche 20×20, compte 32×32, notifications 36×36, **marqueurs communes 21 px**, Docs 405/423
  contrôles < 44 px, CRM 188 < 24 px. axe `target-size` *serious* (Carte 8, CRM 11–16). Cohérent avec un
  dessin « souris » — et l'une des raisons invoquées pour verrouiller le mobile.

### MOYEN

- **F4 — Label-in-name (WCAG 2.5.3) sur toutes les vues.** axe `label-content-name-mismatch` *serious* partout :
  le bouton **Notifications** affiche « 99+ » mais se nomme « Notifications » ; le bouton de **fond de plan**
  affiche « Sombre »/« 3D » mais se nomme « Fond de plan » ; le **logo** idem. La commande vocale (« clique
  99+ ») échoue. *Correction : inclure le texte visible dans le nom accessible.*

- **F5 — Repères & titres incohérents (WCAG 1.3.1 / 2.4.1 / 2.4.6).** **Aucun lien d'évitement** nulle part ;
  `<main>` **présent uniquement sur Copilote** (absent sur Carte, Docs, Radar, Projets, CRM, Sources) ;
  **`<h1>` absent sur la Carte (atterrissage) et le CRM** (présent ailleurs) ; la Fiche fabrique son titre
  avec `role="heading" aria-level=1` au lieu d'un `<h1>` (`Fiche.tsx:903`). Un utilisateur clavier/AT doit
  retraverser rail + en-tête à chaque fois, sans point d'entrée au contenu.

- **F6 — Focus clavier invisible sur le composeur Copilote (WCAG 2.4.7).** Le `textarea` a une **bordure
  menthe permanente** (état de repos) ; au focus, outline absent, bordure et ombre inchangées → **rien ne
  distingue le focus**. L'anneau global a été retiré volontairement (`index.css:403`), donc tout contrôle en
  `outline-none` sans style `focus-visible` local devient invisible au clavier (aussi `Ia.tsx:35`,
  `CopiloteView.tsx:187`). Sur les champs de formulaire, le seul indice est un **léger changement de couleur
  de bordure** (menthe) — minimal. *Le rail (`:158`) et les contrôles MapLibre (`:378`) ont, eux, un bon
  anneau ; les composants de base `Bouton`/`Case`/`Chip` aussi : le socle est bon, les exceptions trahissent.*

- **F7 — « Mode clair » inexistant.** Le mandat demande clair **et** sombre ; l'app est **sombre uniquement**
  (`colorScheme: normal`, pas de bascule de thème ; seul le **fond de carte** a un « Clair »). Critère mandat
  non tenu (ou à acter comme hors-périmètre produit).

### MINEUR

- **F8 — Docs : 6 `<th>` sans `scope`, aucune `<caption>` (WCAG 1.3.1).** Les tableaux (Analyser une annonce,
  Marché, admin) n'associent pas en-têtes↔cellules de façon fiable pour l'AT.
- **F9 — Omnibox : pas de libellé persistant.** Nom accessible dérivé du **seul placeholder** (« Rechercher :
  IDU, SIREN… ») ; pas d'`aria-label` ni de `<label>`. axe ne le bloque pas (le placeholder sert de nom
  calculé) mais le placeholder **disparaît à la saisie** (WCAG 3.3.2 / 1.3.1, bonne pratique).
- **F10 — Carte : `role="region"` nommé « Map » (anglais) dans une app française**, générique. Clavier OK
  (`tabindex=0`, MapLibre gère pan/zoom clavier).
- **F11 — Copilote 390 : grappe d'en-tête débordante de ~28 px**, rognée par le parent (`overflow-hidden`,
  donc pas de scroll) mais un contrôle peut être coupé ; le composeur bas chevauche la dernière suggestion.

### FORCES (confirmées)

- **Repli de mise en page sain** : **0 débordement horizontal** sur les 7 vues à 390 px **et à 320 px**
  (WCAG 1.4.10 reflow) ; rail→colonne d'icônes, panneaux qui se replient, hamburger Copilote, composeur fixé en bas.
- **Mouvement réduit : coupe-circuit global** (`index.css:357`) — **vérifié en direct** : sous
  `prefers-reduced-motion: reduce`, toutes les durées de transition/animation tombent à ~0. Exemplaire.
- **Focus visible sur tout le socle** : marche clavier sur 42 contrôles du shell → **0 focus invisible**
  (rail, en-tête, panneau, carte, marqueurs) ; ordre de tabulation **logique** (rail → en-tête → panneau →
  carte → communes). `Échap` ferme panneaux/tiroirs/modales (vérifié en code sur la plupart des overlays).
- **Régions live présentes** : Copilote (`CopiloteView.tsx:229`) et John (`JohnTaylor.tsx:418`) en
  `role="log" aria-live="polite"` — montées avec le fil actif.
- **Fiche** : tiroirs en `aria-expanded` (15), copie IDU, navigation accordéon propre.
- `lang="fr"` correct (WCAG 3.1.1) ; polices auto-hébergées (pas de Google Fonts) ; champs de formulaire
  majoritairement nommés (0 input sans nom détecté hors omnibox) ; **états de chargement** (squelettes
  Suspense + `Loading role=status`) présents par conception.

---

## 4. Harnais

`harness/audit_a11y.mjs` (Playwright + axe-core) — rejouable, **sort ≠ 0 si échec dur** :
1. **Verrou mobile** : contextes vrais iPhone 13 / iPad gen7 → assert `data-ecran-ordinateur` présent &
   app non montée (✅ les deux).
2. **App rendue** : 7 vues × {390, 1440} → axe WCAG 2.2 AA, débordement horizontal, cibles < 24/< 44 px,
   repères (`main`/`h1`/skip/`th[scope]`), régions live.

Passe du 5/11/2026 (`harness/resultats.json`) : **14 pages mesurées, 0 débordement horizontal, 32 échecs
durs uniques** (tous axe *serious* : `color-contrast`, `label-content-name-mismatch`, + CRM
`nested-interactive`/`target-size`). Prérequis & lancement : `harness/README.md`.

Captures : `captures/01-desktop-1440-carte.png`, `02-390-carte.png`, `03-390-copilote.png` — **non
versionnées** (le dépôt ignore `docs/audit-*/**/*.png`, `.gitignore:197`) ; regénérables en relançant le
harnais + Playwright. La preuve versionnée et rejouable est `harness/resultats.json`.

---

## 5. Pour la synthèse NU-5 → correction par cause

1. **Trancher le mobile** : bureau-seul assumé (le mandat mobile tombe) **ou** ouverture (alors F1–F3
   deviennent bloquants pour le mobile). Le repli propre jusqu'à 320 px montre que l'ouverture est surtout un
   travail d'accessibilité, pas de mise en page.
2. **Contraste (F1)** à la source : remonter `txt-mut`/`txt-off`/`cp-faint` dans la palette (un seul endroit,
   `tailwind.config.js` + `:root`), re-mesurer avec le harnais.
3. **CRM (F2)** : déchevêtrer les contrôles imbriqués (187) — plus gros chantier a11y isolé.
4. **Cibles (F3)** : plancher 24 px (AA) a minima, 44 px visé, sur contrôles et marqueurs.
5. **Repères/labels (F4–F6, F9)** : lien d'évitement + `main`/`h1` par vue ; nom accessible = texte visible ;
   anneau de focus sur le composeur et les `outline-none` orphelins ; libellé persistant d'omnibox.

**Verdict NU5-F : des défauts MAJEUR existent** (contraste généralisé, CRM imbriqué, cibles) — ils frappent
l'utilisateur de bureau, le seul réel aujourd'hui. Le mobile/tablette, lui, **n'est pas auditable : il est
fermé par conception**. Rien de ce qui précède n'a modifié le code ni la prod.
