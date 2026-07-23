# LA GRANDE PASSE FINALE — chasse des reliquats avant bascule live

**Branche `tech/chasse-finale` (base `main` a4074d7 = app actuelle : post-vague UI + audit paiement A-E + embellissement E). Mode nuit autonome. Rien mergé, rien en prod. Vic lit, tranche ce qui attend, puis merge.**

Méthode : trois inspecteurs en parallèle (tunnel serveur / front React / finitions transverses),
puis triage. Je **répare en autonomie** le certain (une seule bonne réponse, aucune dimension
esthétique) — un commit `[FIX-x]` chacun, vérifié (tsc + tests) ; je **liste pour Vic** tout ce qui
exige un jugement. Verts en fin de passe : **golden 116/116, suite 1125/0**.

---

## 🔴 0. BLOQUANTS (à lire en premier)

| # | Sujet | État |
|---|---|---|
| B1 | **CGV citaient un sous-traitant RGPD fictif « Resend »** (emails transactionnels) alors qu'aucun email auto n'existe — contredit les mentions légales de la même app. Donnée légale fausse sur un écran qui touche l'argent. | ✅ **CORRIGÉ [FIX-1]** (+ bump cgv_version 2026-07-23) |
| B2 | **`/mentions-legales` affiche le placeholder `[À COMPLÉTER par Vic — adresse officielle EI + SIREN]`.** Mentions légales sans SIREN/adresse = lacune légale avant vente. | 🟠 **ATTEND VIC** (donnée que seul Vic possède ; bloquant *commercial*, pas technique) |
| B3 | **Hero d'accueil : « 431 663 parcelles » codé en dur** (`LeftPanel.tsx:98`), présenté comme un fait client. Devient faux si la couverture change ; non sourcé. | 🟠 **ATTEND VIC** (le corriger proprement = injecter le compte réel via l'API — pas un correctif trivial ; arbitrage : chiffre dynamique vs constante sourcée) |

Aucun 500 / écran blanc / fuite inter-comptes trouvé. L'ErrorBoundary, les états 429/erreur et
`/healthz`·`/healthz/crons` sont propres (aucune fuite de secret — vérifié).

---

## ✅ 1. Corrigé en autonomie (`[FIX-x]`) — 5 commits, chacun rejetable seul

| Fix | Fichier(s) | Avant → Après | Gravité | Vérifié |
|---|---|---|---|---|
| **FIX-1** | `onboarding.py` (CGV art. 8) + `config.py` | « Stripe, **Resend (emails transactionnels)**, hébergeur » → « Stripe, hébergeur (UE). Aucun email automatique » ; `cgv_version` → `2026-07-23` | **majeur** | tests conformité/comptes/factu 13/0 ; live : 0 occurrence Resend, v2026-07-23 |
| **FIX-2** | `onboarding.py` (Flash) | `inputmode="latin"` (valeur HTML invalide, ignorée) → `inputmode="text"` (champ IDU) | mineur | live : `inputmode="text"` |
| **FIX-3** | `coffre_ui.py` (`page()`) | **aucun favicon** sur ~20 surfaces d'entrée → `<link rel=icon>` 32/16 px (assets de marque déjà servis) | mineur | live : liens présents, `/socle/favicon-32.png` → 200 |
| **FIX-4** | `Fiche.tsx` (bloc Potentiel) | `{fo.surface_plancher_m2} m²` brut (×4) → `fmtM2(...)` (LOI-3 : séparateur fr + ha au-delà d'1 ha) | moyen | `tsc -b` 0 |
| **FIX-5** | `App.tsx`, `Loading.tsx` | hex arbitraires dupliquant un token exact : `text-[#06130C]`→`text-mint-ink`, `[#B497F0]`→`violet` (×4) | mineur | `tsc -b` 0 ; rendu pixel-identique |

**Note atlas avant/après** : ces correctifs sont **délibérément à faible empreinte visuelle** —
FIX-5 est pixel-identique (même hex, juste le nom du token) ; FIX-3 = icône d'onglet ; FIX-1 = une
ligne de texte légal ; FIX-2 = invisible (attribut clavier). Le seul delta visible est **FIX-4**
(« 12 345 m² » / « 1,2 ha » au lieu de « 12345 m² »). Un atlas capté montrerait des images
identiques pour FIX-3/5 ; le diff git est la meilleure preuve. Pas de capture superflue générée.

---

## 🟠 2. Attend Vic — défauts de jugement (NON touchés : structure / visuel / arbitrage / doute)

### Bloc 1 — tunnel argent (surfaces serveur)
1. **Page 404 hors design system** (`app.py` `_NOT_FOUND_HTML`) : couleurs en dur (`#060A08`…) au
   lieu des tokens `coffre_ui`, et fond `#060A08` **divergent** du `--bg` officiel `#050706`.
   *Reco :* router la 404 via `coffre_ui.page()` (une seule source de dessin). → structure.
2. **Champ « Identifiant » = email, wording tiraillé** : label « Identifiant », `type=text` /
   `autocomplete=username`, placeholder `vous@cabinet.re`, et le message d'erreur de login dit
   « vérifiez votre **email** ». *Reco :* trancher — soit « Email » + `type=email` partout, soit
   « Identifiant » assumé (y compris le message d'erreur). Je n'ai pas corrigé un demi-côté car le
   commentaire du code réserve ce champ au futur backend d'identité → **arbitrage produit**.
3. **Wordmark « LA BUSE » (porte) vs « LABUSE » partout ailleurs** (`auth.py:167`). Logotype assumé
   (le nom = l'oiseau) ou incohérence ? → choix de marque.
4. **Casse des titres d'onglet non uniforme** (`LABUSE — invitation` vs `LABUSE — Connexion`, ~24
   chaînes). *Reco :* capitale initiale partout. → style global à appliquer en lot.
5. **Classes CSS synonymes `.sub` / `.sous`** (même style) employées au hasard dans `onboarding.py`.
   Hygiène, zéro impact visuel. *Reco :* garder `.sub`.
6. **Wording « paiement à venir » après clic « Payer »** quand Stripe indisponible (repli honnête).
   Le client a cliqué payer sans payer — formulation à valider.
7. **Route `POST /reset-demande` orpheline** (aucun émetteur depuis « zéro email auto ») —
   `onboarding.py:192`. *Reco :* supprimer route + entrée `_PUBLIC`, ou documenter si réemploi futur.

### Bloc 2 — cœur produit (front React) · *couverture agent : 38/38 fichiers .tsx*
8. **Surface parcelle sans séparateur** côté serveur Flash (« 12500 m² ») : le codebase est
   **incohérent** (serveur `banquier.py` `:.0f` sans séparateur ; front `fmtM2`/`fr-FR` avec espace)
   → pas « une seule bonne réponse ». *Reco :* aligner le serveur sur la locale fr du front.
9. **Hex en dur dans des maps de couleurs en objets `style`** (pas des className swappables) :
   `ProjetKanban.tsx:40-43`, `ContextePanel.tsx:11-17` (SRU_META), `ViabilisationBlock.tsx:14-17`,
   `GestionnairesBlock.tsx:15`, `SourcesPage.tsx` (STATUS_DOT/BADGE_META), `ModulePanel.tsx` /
   `moteurs.tsx` (rColor/tColor appliqués en `style`). Certaines valeurs **sont** des tokens
   (`#5CE6A1`=mint…), d'autres **non** (`#E6B15C`, `#8FD9B6`, palette data-viz `#7DE8E0`…). *Reco :*
   centraliser dans `lib/status.ts` + appliquer par className OU assumer les hex data-viz hors token.
   → refonte className-vs-style + décision sur la palette data-viz.
10. **`toLocaleString`/`toLocaleDateString` inline** au lieu des helpers `lib/format.ts` (LOI-3) —
    répandu (`SourcesPage`, `ContextePanel`, `blocB` qui n'importe aucun helper, `SegmentsPage`,
    `ResultsSection`…). **Rendu déjà correct** (fr-FR) donc pas un défaut visible ; dette de
    convention, source de dérive future. *Reco :* passe de refactor dédiée (batchable).
11. **Boutons icône-seul sans `aria-label`** (`ContextePanel:82`, `SegmentsPage:112/138/268`,
    `ProjetKanban:309-311`, `TimeMachine:147`, `moteurs:390`, `MapToolbar:117`). **La plupart ont
    déjà un `title`** (= nom accessible de repli), donc l'écart réel est mineur ; le seul vraiment
    nu (`+` de `moteurs`) est de l'outillage **admin**. *Reco :* ajouter `aria-label` = le `title`,
    en lot. Non touché pour éviter d'étiqueter à tort de l'admin non tracé.
12. **Clés React = index de tableau sur des listes filtrables** (`ModulePanel:284/325/614`,
    `PermitsProximityBlock:31`, `ScoreV2Block:116`, `ViabilisationBlock:42`) alors qu'un id stable
    existe (`permit_id`, `idu`). Recyclage d'état DOM possible au changement de filtre. → moyen.
13. **Libellés divergents entre écrans** : `CONTRAINTE_LABEL` (« hors zone à risque (PPR) » vs
    « hors PPR ») + `TYPE_LABEL` recopié dans 3 fichiers. *Reco :* centraliser `lib/labels.ts`.
14. **Code d'état de permis brut affiché** (`ModulePanel.tsx:326/328`, « état {code} ») — le commentaire
    du code reconnaît « codes non documentés ». Jargon qui fuit. *Non corrigé :* le remplacer par un
    libellé (« Permis accordé… ») **suppose** un sens des codes qu'on ne connaît pas → **jugement**.
15. **Divers signalés** : `ErrorBoundary:22`/`Fiche:1062` montrent `error.message` brut (peut fuir
    de l'anglais) ; vignettes score `ParcoursTinder:209` sans unité (`/100`, `%`) ; `prompt()`/
    `confirm()` natifs dans l'admin segments ; cibles tactiles 36 px (`MapToolbar h-9 w-9`)/28 px
    (chips) < 44 px ; `#2FE0A0` (vert logo, **NON**-token assumé — ne pas rabattre sur `mint`) ;
    « NON contiguë » en capitales (`moteurs:115`) — emphase possiblement voulue.

### Bloc 3 — marges
16. Vus sains : états vides, 404 (texte propre), `annule` bien relu par `flash_page`, redirections
    Stripe (`success_url`/`cancel_url`) toutes vers des routes réelles — **aucun lien de paiement mort.**

---

## 👁️ 3. Écrans que Vic doit regarder à l'œil (priorité ressenti)

1. **`/mentions-legales`** — remplacer le placeholder SIREN/adresse (B2) : bloquant vente.
2. **Accueil (hero LeftPanel)** — trancher le « 431 663 » (B3) : chiffre figé vs sourcé.
3. **Porte `/login`** — wordmark « LA BUSE » vs « LABUSE » (item 3) + wording du message d'erreur (item 2).
4. **Fiche → onglet Potentiel** — vérifier le rendu des surfaces après FIX-4 (« 1,2 ha » attendu au-delà d'1 ha de SDP).
5. **Écran de bascule Checkout / retour** — relire le wording « paiement à venir » (item 6).
6. **Page 404** — décider si on la rattache au design system (item 1).

---

## 🩺 4. Santé & vérifications finales

- **Golden : 116/116 PASS, 0 FAIL** (après tous les fixes).
- **Suite : 1125 passed, 18 skipped, 0 failed** (skips environnementaux : base applicative / QA distante).
- **Front : `tsc -b` exit 0** après FIX-4/5.
- **Smoke live (serveur de branche :8011)** : CGV sans Resend + v2026-07-23, favicons servis (200),
  `inputmode="text"`, routes publiques du tunnel toutes 200 (login 302 = auth désactivée en local, normal).
- `/healthz`+`/healthz/crons` : aucune fuite de secret. Aucun `console.log`/`print`/`TODO`/`lorem`
  user-facing (2 `console.error` MapLibre légitimes). Prix 349 €/79 € cohérents partout.

---

## Curseur de reprise (si session neuve)

- Branche `tech/chasse-finale`, base `main` a4074d7. Faits : **FIX-1..5** (voir §1).
- Serveur de branche relançable : `LABUSE_DEV_MODE=1 uvicorn labuse.api.app:app --port 8011`
  (`LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`, `PROJ_DATA=…/labusedb/share/proj`).
- **Reste de valeur (tout listé §2, certain mais batché/à trancher)** : aria-labels en lot (item 11),
  clés React stables (12), centralisation libellés (13), maps hex→status.ts (9), LOI-3 toLocaleString (10).
  Rien de bloquant technique n'y demeure. Bloc 2/3 : inspection **statique** faite (38/38 tsx) ;
  parcours **cliqués live** non faits (auth requise + dist à rebuild) — à couvrir si Vic le souhaite.
- **Rien mergé, rien en prod. Vic tranche §0-B2/B3 + §2, puis merge.**
