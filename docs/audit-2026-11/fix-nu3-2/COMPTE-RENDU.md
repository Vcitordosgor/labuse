# MANDAT FIX-NU3-2 — Parcours · Copilote · Entrées · Comptes · Accessibilité

**Registre.** Branche `fix/nu3-2`, worktree `~/Desktop/labuse-fix2`, ports réservés 9410/6610.
Corrige les constats des lots **G, H, I, M** de l'audit NU-3 qui relèvent du parcours client, du
Copilote, de la robustesse des entrées, des comptes et de l'accessibilité. **Aucun merge, aucun
accès prod.** Deux autres sessions tournent en parallèle (FIX-NU3-1 : calculs/PDF/outils ; FIX-NU3-3 :
jobs/admin/chaîne de données) — leur périmètre n'est pas touché (voir « Frontières » plus bas).

Décision de Vic appliquée pour le paiement refusé : **7 jours de grâce avec bandeau visible, puis
accès en lecture seule et page de régularisation ; le login reste possible pour régulariser.**

---

## Recette (hook local)

| Vérification | Résultat |
|---|---|
| **Front — `tsc -b`** | **0 erreur** |
| **Front — `vitest run`** | **63 fichiers / 301 tests — tous verts** (node_modules réel `npm ci`) |
| **Back — `pytest -m "not db and not local and not reel and not network"`** | **2813 passés / 0 échec** (48 skips d'env). Deux passes complètes vertes ; une 3ᵉ a fait sauter `test_dashboard2_cloture::test_clients_le_meme_9` une fois (flake **pré-existant** de pollution base partagée : passe en isolement + avec mes tests comptes/facturation ; `licences_actives` non touché par ce diff). |
| **Axe — fiche / Estimer / Copilote** | aria-live + libellés + piège de focus posés (analyse statique + composants ; voir M-A*) |
| **Parcours clavier** | modales piégées + restituées ; champ Estimer nommé ; focus visible Copilote embarqué |

> Les 8 suites vitest qui important `MapView`/maplibre échouaient d'abord « Denied ID …maplibre-gl-worker »
> **uniquement** quand `node_modules` était un lien vers `labuse-main` (restriction `server.fs` de Vite sur
> un chemin hors worktree). Avec un `npm ci` **réel** dans le worktree, les 63 suites passent.

---

## Tableau des trouvailles corrigées

| ID (lot) | Gravité | Fichier(s):ligne | Correctif |
|---|---|---|---|
| **H-M01** | Majeur | `pige/api.py:1555,1759,2121` · `api/documents.py:249` | `surface_hab` borné `Query(gt=0, le=100000)` (inf/énorme → **422**) + `math.isfinite` au cœur `_surface_pour_total` |
| **H-m04** | Mineur | *(idem H-M01)* | surface **négative → 422** (même bornage `gt=0`) |
| **H-D01** | Dette | `api/app.py` (après `_data_error_422`) | `@app.exception_handler(Exception)` : trace serveur journalisée, **500 JSON neutre**, jamais un 500 brut |
| **H-m01** | Mineur | `api/app.py:_check_idu` + appelants (`moteurs.py`, `modules.py`, `_build_fiche`, `parcel_fiche`) | IDU `strip().upper()` → casse/espaces tolérés ; appelants utilisent la valeur normalisée |
| **H-m02** | Mineur | `api/app.py:parcel_fiche` | `source=q_v*` inexistant → **404 « Run inconnu »** (sauf servi/précédent) au lieu d'un repli silencieux |
| **H-D02** | Dette | `api/app.py` (`_auth_guard` + `_est_chemin_admin`) | **fail-safe admin structurel** : toute route au segment `/admin` exige le rôle admin au middleware (routeurs mixtes → dépendance de routeur impossible) ; gardes en ligne conservées |
| **H-D03** | Dette | `models.py:Projet.version` · `api/projets.py` (`_COLS`, `ProjetPatchIn`, `projet_patch`) | **verrou optimiste** : colonne `version`, `409 Conflit` si la version éditée a bougé, incrément sur changement réel |
| **H-M02 / I-CPT-01 / M-P02** | Majeur | `comptes.py` · `facturation.py` · `api/app.py` · `api/onboarding.py` · `App.tsx` | **grâce 7 j** (bandeau) puis **lecture seule** (écritures → 402, sauf régularisation/logout) ; `/moi` sert `acces` + `lien_regularisation` ; login toujours possible |
| **I-CPT-02** | Mineur | `comptes.py:mail_cycle_de_vie_auto` · `facturation.py` | e-mail `resiliation` : **vraie date de fin d'accès** (fin de période payée) pour un abonné payant, plus « prend fin le  » (vide) |
| **I-CPT-03** | Mineur | `api/dashboard.py:_params_licence` | anti-doublon « le le » étendu à `FIN_ESSAI` |
| **I-CPT-04** | Mineur | `api/dashboard.py:_params_licence` | `LIEN_SOUSCRIPTION` → lien d'**invitation** réel (plus `/souscrire`, route morte) |
| **I-CPT-05 / I-TPS-05** | Mineur | `emails.py:maintenance_email` | fenêtre de coupure en français + **« (heure de La Réunion) »** |
| **I-CPT-07** | Dette | `facturation.py` (activation) | pied de facture d'**abonnement** = `config.facture_mention` (293 B / TVA) posé sur le client Stripe (le mode `subscription` ne prend pas `invoice_creation`) |
| **M-P01** | Mineur | `comptes.py` · `facturation.py` (`subscription.deleted`) | résiliation **en fin de période payée** : `acces_fin_at` honoré (comme l'essai), coupure immédiate seulement si pas de période future |
| **M-P03** | Mineur | `facturation.py` (`charge.refunded`) | remboursement **traité** : charge d'abonnement (avec `invoice`) → accès révoqué ; Flash one-shot → rien à révoquer (journalisé) |
| **M-P05** | Dette | `api/onboarding.py:_flash_pied` | pied de la page `/flash` lit `config.facture_mention` (plus « sans TVA » en dur) |
| **I-TPS-01** | Mineur | `frontend/src/lib/format.ts` | `fmtDate/fmtDateNum/fmtDateSitadel/fmtDateSirene` **figent `Indian/Reunion`** (plus de J-1 à l'ouest d'UTC) |
| **I-TPS-02** | Mineur | `api/pre_dossier.py` | ZIP pré-dossier : **toutes** les pièces datées `now_reunion()` (fin du 1980 + heure machine CET) |
| **I-TPS-03** | Mineur | `admin/circuit/*.tsx` · `admin/Cron.tsx` (10 formateurs) | cockpit admin en **heure de La Réunion** |
| **I-TPS-04** | Mineur | `AccueilCopilote.tsx` · `documents/DocumentsView.tsx` | brief Copilote / « généré le » en heure Réunion |
| **G-001** | Majeur | `lib/filters.ts` · `panel/FiltreLabuse.tsx` · `api/app.py:_filtre` | **filtre Risques (PPR/aléa)** sur la carte (Peu importe / Avec / Sans) ; groupe `risques`=`ppr`+`georisque_alea` expandu client **et** serveur (compteur == carte) |
| **G-002** | Mineur | `panel/FiltreLabuse.tsx` | filtre communes : **nom de commune** affiché (CP au survol), comme la carte |
| **G-006** | Majeur | `implantation/moteur.py` | message d'Étude impossible nomme le **stationnement réellement choisi** (plus « aérien » figé en sous-sol) |
| **G-008** | Mineur | `projets/ProjetKanban.tsx` | « 1retenues » → **« 1 retenue »** (pluriel accordé) |
| **G-011** | Majeur | `copilote_v2/outils.py:statut_ppr` | « pas de PPR » **ne nie plus les aléas Géorisques** : la réponse les nomme (mêmes items que la fiche) |
| **G-012** | Mineur | `copilote_v2/outils.py:marche` · `answering.py` (desc. outil) | le Copilote sert le **prix médian par type** (maison/appartement/terrain) quand il existe : exposé depuis `marche_commune_bloc`/`mediane_commune` — **le même point de calcul unique que la fiche commune, l'Estimer et le Radar**. Le tool `marche` lisait `build_marche_commune` (9 lignes, sans médiane par type) → il répondait « pas de segmentation » ; il lit désormais aussi les médianes par type (`prix_median_maison/appartement/terrain` dans `lignes`+`valeurs`) |
| **G-013** | Majeur | `copilote_v2/outils.py:loyer_parcelle` · `answering.py` | loyer d'une parcelle = **OLL de la fiche** (bonne commune par construction), plus le préambule « J'ai compris… » (route déterministe) ni l'étiquette « DHUP (terrain nu) » |
| **G-015** | Majeur | `App.tsx` | réhydratation des filtres depuis le hash : l'effet d'écriture ne **clobbe plus** le hash au 1ᵉʳ rendu (filtres partagés/rechargés conservés) |
| **H-m03** | Mineur | `header/Header.tsx` | barre du haut responsive en fenêtre étroite (recherche `min-w-0 max-w`, « Fiche commune » masquée < 560 px) |
| **I-EXP-02** | Mineur | `DocumentsView.tsx:202-207` · `DocumentsView.tsx:37` · `BilanEcran.tsx:208` · (grep `/financier` front = 0) | **Décision : garder le Financier, un clic ouvre la saisie qui génère** (il exige TVA + programme, donc impossible à produire « nu »). Carte Docs « Bilan » → `generer()` ouvre `BilanEcran` (saisie) ; la bibliothèque régénère par `docBilanUrl(idu, doc_id)` = `/bilan/{idu}.pdf?doc_id=N` (rejoue les saisies, PDF valide, pas de 422). **Aucun lien vers `/financier/{idu}.pdf` nu** dans le front → le 422 « 20/20 » du rapport n'est atteignable par aucun parcours UI. Satisfait sans retrait |
| **M-A01** | Majeur | `styles/index.css` | contrastes AA : `txt-mut`→#879389 (5,41), `txt-off`/`txt-faint`→#7C8A82 (4,79), `.field`→`--txt` (≈10:1) — tous **≥ 4,5:1** mesurés |
| **M-A02** | Majeur | `copilote/CopiloteView.tsx` · `outils/AnalyserAnnonce.tsx` | réponse Copilote (`role=log aria-live`) et résultat Estimer (`role=status aria-live`) **annoncés** |
| **M-A03** | Majeur | `outils/AnalyserAnnonce.tsx` | champ lien : `<label htmlFor>` + erreur `role=alert` liée (`aria-describedby`/`aria-invalid`) |
| **M-A04** | Majeur | `lib/usePiegeFocus.ts` (nouveau) · `DocumentsView.tsx` · `ModulePanel.tsx` · `SourceDrawer.tsx` | **piège de focus + Échap + restitution** généralisés (3 modales/tiroirs), `role=dialog aria-modal` |
| **M-A05** | Mineur | `fiche/Fiche.tsx` | fiche = région nommée (`aria-label`) + IDU `role=heading aria-level=1` |
| **M-A07** | Mineur | `map/MapView.tsx` | bouton recentrer 3D : `aria-label` (plus seulement `title`) |
| **M-A09** | Dette | `copilote/CopiloteEmbarque.tsx` | focus clavier visible (`focus-visible:ring`) sur les champs `outline-none` |
| **M-T04** | Mineur | `outils/AnalyserAnnonce.tsx` | bouton **« Estimer ce bien »** (plus « Analyser l'annonce » sur l'écran « Estimer un bien ») |
| **M-T05** | Mineur | `lib/strings.ts` | CTA d'accueil **« Copilote »** (plus « LABUSE IA ») |
| **M-T06** | Mineur | `copilote_v2/resume_fiche.py` | libellé unique **« Zone PLU »** |
| **M-T07** | Mineur | `outils/M22Programme.tsx` · `outils/EtudeV6.tsx` | stationnement non aérien = **« Sous-sol »** partout |
| **M-T08** | Mineur | `outils/M22Programme.tsx` · `outils/EtudeV6.tsx` | exemple de référence unique **« BW0917 »** |
| **M-T09** | Mineur | `exports/builder.py` | **« Note apporteur »** (plus « Brief apporteur ») |
| **M-T10** | Mineur | `shared/ContactEdit.tsx` | **« E-mail »** (plus « Email ») |
| **M-T11** | Mineur | `radar-extension/background.js` | vouvoiement uniforme (« déposez ») |
| **M-T13** | Mineur | `lib/format.ts:fmtEurCompact` | espace **insécable** avant « M€ »/« k€ » (vérifié U+00A0 à l'octet) |
| **M-T17** | Mineur | `api/ortho.py` · `radar-extension/options.html` | « tableau de bord » (plus « dashboard ») · « Décalage aléatoire max » (plus « Jitter ») |
| **M-T20** | Dette | `fiche/constructibilite.tsx` | « ±30 % » **interpolé** depuis `FOURCHETTE_DEMI_LARGEUR_PCT` |
| **M-T21** | Dette | `emails.py` | accord du pluriel « mouvement(s) » → « mouvement/mouvements » |

---

## Frontières (non traité — hors périmètre ou coordination)

- **M-A06** (sélection parcelle au clavier sur le canevas carte) : **compensé** par l'omnibox ARIA 1.1 (ouvrir une
  fiche reste possible au clavier) — non implémenté (canevas maplibre), consigné.
- **M-A08** (Réglette/Jauge3 portées par la couleur) : résidu mineur, renfort texte majoritaire déjà présent.
- **M-T12 / M-T15 (moteurs) / M-T16 / M-T17-flash** (typographie des gabarits **PDF/Flash** et textes `moteurs.py`) :
  surfaces **PDF** = domaine de **FIX-NU3-1** ; laissées pour éviter conflits de merge et casse des goldens. Les
  surfaces front/API correspondantes (fmtEurCompact, ortho, extension) **sont** corrigées ici. `rarete.py` sert déjà
  le vrai signe moins U+2212 côté client (seul un commentaire porte « -50 »).
- **I-CPT-06, J01–J04, M-J*** (RGPD/self-service/juridique) : hors mandat.
- **I-ADM-*, I-TPS (backend)** : domaine FIX-NU3-3 (jobs/admin) — non touché.

---

## Détail des décisions structurantes

### Paiement refusé → grâce 7 j puis lecture seule (décision Vic)
- Colonnes additives `comptes.paiement_requis_at` (ancre de grâce) et `comptes.acces_fin_at` (fin de période payée),
  posées par le garde-catalogue habituel.
- `session_utilisateur` calcule `acces ∈ {complet, lecture_seule}` et honore `acces_fin_at` (bascule à la requête,
  comme l'essai). Login & lecture toujours ouverts ; **écritures (POST/PUT/PATCH/DELETE) → 402** après la grâce,
  sauf `/onboarding`, `/stripe`, `/facturation`, `/logout`, `/login`, `/moi`.
- `/moi` sert `acces` et `lien_regularisation` (`/onboarding/paiement?t=<pay_token>`). Bandeau App.tsx : ambre
  (grâce) puis corail + bouton « Régulariser » (lecture seule).

### Fail-safe admin (H-D02)
Les routeurs admin sont **mixtes** (routes `/admin/*` **et** routes publiques dans le même `APIRouter`) : une
`dependencies=[Depends(exiger_admin)]` de routeur gaterait aussi le public. Le filet est donc posé au middleware
`_auth_guard`, par segment d'URL `/admin`, **en plus** des gardes `exiger_admin()` en ligne (défense en profondeur,
rien retiré).

---

*FIX-NU3-2 — aucun merge, aucun accès prod. Hook : tsc 0 · vitest 301 · pytest unitaires 2813, tout vert.*
