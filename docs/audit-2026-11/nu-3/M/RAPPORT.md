# MANDAT AUDIT-NU-3 — Lot M : Textes, juridique, prix, accessibilité, aide

**Registre.** Audit **LECTURE SEULE** joué le 2026-11-01. Branche `audit/nu-3-m`, worktree
`~/Desktop/labuse-nu3-m`, ports réservés **9340/6540**, run servi `q_v20`, base Mac `labuse`
(434 582 parcelles, == prod données, SRID 2975, PostGIS). **Aucune écriture base, aucun correctif,
aucun commit applicatif, aucun merge, aucun accès prod.** Deux autres lots (G, N) tournaient en
parallèle sur le même Postgres — jamais coupé.

> **Méthode et limite assumée.** Le périmètre de ce lot (textes, juridique, prix, aide) est
> **autoritatif au niveau du code** : chaque constat est ancré sur un `fichier:ligne` lu et vérifié.
> Le code fait foi — les chaînes servies, les routes légales, la machine à états de facturation et
> les gardes Stripe se lisent sans booter. **L'application n'a PAS été bootée** pour ce lot (lots G/N
> actifs, navigateur MCP partagé, base partagée) : en conséquence **l'audit axe dynamique écran par
> écran et le parcours VoiceOver réel N'ONT PAS été joués** — c'est la limite explicite de ce lot,
> comme pour NU-3-N. L'accessibilité est donc traitée en **analyse statique des composants**
> (ARIA, rôles, gestion du focus, régions live, sémantique) **+ contrastes de la DA sombre MESURÉS**
> au ratio WCAG depuis les tokens de `frontend/src/styles/index.css` (seule mesure de contraste
> possible sans rendu, et la plus rigoureuse : elle calcule le ratio exact). Les captures écran
> n'ont pas été produites (pas de rendu) ; tout est reproductible par lecture du code cité.
>
> Cinq sous-audits forkés (un par pilier) ont balayé le code en lecture seule ; les constats les plus
> graves (fuite RGPD, sources de prix, clé de tri du classement, labels de champ, collision de nom
> produit) ont été **re-vérifiés à la main** et sont annotés comme tels.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Scénarios joués** | **~5 balayages de code exhaustifs** (textes front/back/PDF/mails/extension ; couche juridique CGV+RGPD+sous-traitants ; chaîne prix/Stripe/webhooks/cycle de vie ; aide/onboarding/tooltips confrontés au code calculant ; a11y statique des 3 écrans cibles fiche/Estimer/Copilote + coque) + **1 table de contrastes mesurée** (18 teintes de texte × 5 fonds de la DA sombre, 90 ratios WCAG) + ~12 vérifications manuelles ciblées (`proprietaire_type.libelle_proprietaire`, `_cle_classement`, `.field`, labels Estimer, `fmtEur`/`fmtEurCompact`, footer Flash TVA, redirections légales). |
| **Bloquant** | **2** |
| **Majeur** | **10** |
| **Mineur** | **24** |
| **Dette** | **15** |

**Verdict de synthèse.** Le soin apporté aux **textes** et à l'**aide** est réel et entretenu :
formateurs centralisés (`fmtEur`/`fmtM2`, `registre_fmt`) avec espace insécable, zéro `TODO`/`lorem`/clé
brute en surface client, couche de tooltips méthodologiques dense et **honnête** (disclaimers PPR
« pas un certificat », estimation « ordre de grandeur », médiane par type). De même la **mécanique de
prix** est bien architecturée : source unique `config.py → offres.py → /api/offres`, **aucun 349/79
codé en dur** dans une chaîne servie, et une **garde `_garde_coherence_prix` qui refuse de facturer**
si le prix Stripe diverge de l'affiché — le vrai rempart anti-dérive. **Le danger n'est pas
l'arithmétique des prix ni l'orthographe : il est juridique et, secondairement, de cohérence.** Le
point de rupture est unique et grave : **l'app est une machine à traiter les données personnelles de
propriétaires tiers** (patronymes de successions/indivisions affichés en clair, historiques,
adressage de courrier), mais la seule politique livrée ne parle que du client-utilisateur, le détail
de confidentialité est **déporté hors dépôt** (301 vers `labuse.immo`), et la fuite de noms de
particuliers (ex-NU-D-017) **est toujours vivante** dans `proprietaire_type.py`. Viennent ensuite des
confusions de **vocabulaire** (une même SDP résiduelle nommée « restante » ou « résiduelle » jusque
dans un même PDF ; le Flash titré « Étude de faisabilité »), une **contradiction d'aide sur la notion
phare** (le classement décrit comme « probabilité de vente » alors qu'il trie par qualité foncière),
des **contrastes DA sombre sous le seuil AA** sur le texte de champ et le texte secondaire, et une
**accessibilité dégradée** (pas de région live sur la réponse Copilote ni le résultat Estimer, champ
Estimer sans libellé, modales sans piège de focus). **Aucun onboarding** n'existe.

---

## Pilier 1 — TEXTES

### NU-3-M-T01 — MAJEUR — Une même SDP résiduelle nommée « restante » OU « résiduelle » dans toute l'app, jusque dans un même PDF
- **Où** : `frontend/src/components/fiche/Fiche.tsx:1215,1390` (« SDP restante ») vs `frontend/src/components/outils/Blocs.tsx:132` et `frontend/src/components/compare/ComparePanel.tsx:96` (« SDP résiduelle », même champ `sdp_residuelle_m2`) ; PDF `src/labuse/exports/blocs/annonce.py:176,188` + `exports/miroir.py:1103` (« SDP restante ») vs `exports/blocs/comparatif.py:134,140` + `miroir.py:1275` (« SDP résiduelle ») ; Copilote `src/labuse/copilote_v2/resume_fiche.py:34` (« SDP restante (bâti conservé) ») vs `:253` (« SDP résiduelle »).
- **Affiché** : « SDP restante » / « SDP résiduelle ».
- **Juste/problème** : c'est le MÊME potentiel résiduel constructible (`sdp_residuelle_m2`), nommé de deux façons selon l'écran — parfois dans le **même document** (`miroir.py`) et la **même surface** (tuile Copilote vs réponse). Contredit frontalement la doctrine SDP-UNIQUE-1 « un mot par notion ». (« SDP maximale / consommée / existante » sont des notions distinctes volontaires — ne pas confondre : seul le couple restante↔résiduelle désigne la MÊME grandeur.)
- **Repro** : Fiche §Potentiel vs Comparer/Blocs vs PDF Comparatif vs réponse Copilote.
- **Proposition** : un seul libellé pour `sdp_residuelle_m2` dans tout le produit (le `resume_fiche.py:34` « SDP restante (bâti conservé) » est le plus explicite) ; test de cohérence de libellé dans `tests/coherence/`.

### NU-3-M-T02 — MAJEUR — Le rapport Flash (79 €) se sous-titre « Étude de faisabilité », nom d'un produit distinct
- **Où** : `src/labuse/flash/templates/rapport.html.j2:24` (sous-titre de garde « Étude de faisabilité indicative d'une parcelle ») vs `src/labuse/exports/etude_faisabilite.py:478` (« `<h1>Étude de faisabilité — {commune}` »), le document dédié 8 pages.
- **Affiché** : Flash → « Étude de faisabilité indicative d'une parcelle » ; produit premium → « Étude de faisabilité — … ».
- **Juste/problème** : deux produits à prix et profondeur différents portent le même nom de famille. Le qualificatif « indicative » atténue, mais un acheteur Flash peut croire recevoir l'Étude de faisabilité complète ; risque commercial/contractuel (le Flash est vendu « document d'aide à la décision », pas une étude).
- **Repro** : page de garde PDF Flash vs page de garde PDF Étude de faisabilité.
- **Proposition** : donner au Flash un sous-titre propre (« Pré-analyse d'une parcelle », « Aperçu LABUSE ») qui ne réemploie pas « Étude de faisabilité ».

### NU-3-M-T03 — MINEUR — « Info classement » et les libellés de tri : voir NU-3-M-H01 (la contradiction d'aide sur la notion phare est traitée au pilier Aide)

### NU-3-M-T04 — MINEUR — Outil « Estimer un bien », bouton d'action « Analyser l'annonce » sur le même écran
- **Où** : `frontend/src/components/outils/AnalyserAnnonce.tsx:535` (titre « Estimer un bien ») vs `:562` (bouton primaire « Analyser l'annonce ») ; sous-titre de garde d'entrée lien « Un lien d'annonce » `:551`.
- **Affiché** : titre « Estimer un bien » · bouton « Analyser l'annonce ».
- **Juste/problème** : renommage RECETTE-4 propagé au titre mais pas à l'action — deux noms pour le même geste, même écran. Survit aussi « Analyser une annonce » + « scrapé » dans la sonde admin `src/labuse/sonde_circuit.py:600` (anglicisme + ancien nom).
- **Repro** : Outils → Estimer un bien → entrée LIEN.
- **Proposition** : bouton « Estimer » (ou « Estimer ce bien ») ; nettoyer la sonde.

### NU-3-M-T05 — MINEUR — Le Copilote appelé « LABUSE IA » sur le CTA d'accueil, « Copilote » partout ailleurs
- **Où** : `frontend/src/lib/strings.ts:62` (`decouvrir: 'LABUSE IA'`) vs `frontend/src/components/Rail.tsx:98` (« Copilote »), `LeftPanel.tsx:344` (« Demander au Copilote »), `AccueilCopilote.tsx:130` (« COPILOTE »).
- **Affiché** : « LABUSE IA » vs « Copilote ».
- **Juste/problème** : même fonctionnalité, deux noms sur le parcours d'entrée.
- **Repro** : Accueil (2ᵉ bouton mauve) → vue Copilote.
- **Proposition** : « Copilote » partout ; réserver « IA » à la mention de nature (surface mauve).

### NU-3-M-T06 — MINEUR — « Zone » vs « Zone PLU » pour le même champ (Copilote)
- **Où** : `src/labuse/copilote_v2/resume_fiche.py:30` (« Zone ») vs `:249` (« Zone PLU »), champ `zone_plu_famille`.
- **Juste/problème** : même fait, deux libellés sur la même surface. **Proposition** : « Zone PLU » partout.

### NU-3-M-T07 — MINEUR — Stationnement : « En ouvrage » (Assemblage) vs « Sous-sol 1 niveau » (Étude)
- **Où** : `frontend/src/components/outils/M22Programme.tsx:309,592` (`label:'En ouvrage'`) vs `frontend/src/components/outils/EtudeV6.tsx:1109` (`['sous_sol','Sous-sol 1 niveau']`).
- **Juste/problème** : même notion (stationnement non aérien) nommée différemment entre deux outils voisins. **Proposition** : harmoniser la nomenclature de stationnement.

### NU-3-M-T08 — MINEUR — Exemple de « référence » parcelle incohérent entre champs
- **Où** : `frontend/src/components/ParcelInput.tsx:133` (+8 autres « (BW0917) ») vs `EtudeV6.tsx:847` (« (ex. 97404000AW0099) », IDU 14 car.) vs `M22Programme.tsx:521` (« (AW0451) »).
- **Juste/problème** : même champ, trois exemples ; EtudeV6 donne la forme longue là où les autres donnent la forme courte. **Proposition** : un seul exemple canonique.

### NU-3-M-T09 — MINEUR — Document « Apporteur » titré « Brief apporteur » dans le PDF (+ anglicisme)
- **Où** : `src/labuse/exports/builder.py:71` (« Brief apporteur ») vs libellé écran « Apporteur » / pied « apporteur d'affaires » (`builder.py:97`).
- **Juste/problème** : double nommage écran/PDF + anglicisme « Brief ». **Proposition** : « Note apporteur » écran et PDF.

### NU-3-M-T10 — MINEUR — « Email » / « E-mail » / « mail » — trois graphies (admin)
- **Où** : `frontend/src/components/shared/ContactEdit.tsx:35` (« Email » non accentué), `admin/AdminView.tsx:140` (« E-mail »), `admin/Licences.tsx:92` (« mail de bienvenue »).
- **Juste/problème** : trois graphies d'un même objet, « Email » anglicisé. **Proposition** : « E-mail » (ou « courriel ») partout.

### NU-3-M-T11 — MINEUR — Tutoiement vs vouvoiement pour la même consigne (extension)
- **Où** : `outils/radar-extension/background.js:726` (« Déposez à la main… ») vs `:728` (« …dépose à la main »).
- **Juste/problème** : deux registres pour la même consigne d'échec, vus côte à côte (ligne d'état + notification). **Proposition** : vouvoiement uniforme.

### NU-3-M-T12 — MINEUR — Flash et blocs PDF « Estimer » retombent sur l'espace sécable (U+0020) avant `:` `%` `€`
- **Où** : `src/labuse/flash/templates/rapport.html.j2` (nombreux « mot : », « n % ») ; `src/labuse/exports/blocs/annonce.py:36,40` + `comparatif.py:88` (`{…} €`, octet 0x20) vs la norme `src/labuse/exports/registre_fmt.py:20,24,28` (U+00A0).
- **Affiché** : « 8,5 % », « 400 000 € » exposés à la césure nombre↔unité.
- **Juste/problème** : deux conventions typographiques chez un même éditeur ; les formateurs généraux (`fmtEur`/`fmtM2`, `registre_fmt`) utilisent bien l'insécable — le défaut est **localisé** au Flash et à des blocs PDF ré-implémentés. **Proposition** : insécable (idéalement l'insécable fine U+202F) dans ces gabarits.

### NU-3-M-T13 — MINEUR — `fmtEurCompact` casse la règle insécable que `fmtEur` respecte
- **Où** : `frontend/src/lib/format.ts:21` (`fmtEur` → NBSP U+00A0 avant `€`, conforme) vs `:30-31` (`fmtEurCompact` → **espace ordinaire** avant « M€ » / « k€ »). *(vérifié à l'octet par hexdump.)*
- **Affiché** : « 450 k€ », « 2,4 M€ » sur cartes/badges exposés à la césure « 2,4 ⏎ M€ ».
- **Juste/problème** : le commentaire ligne 19 promet « espace insécable avant € » ; le format compact ne le tient pas. **Proposition** : NBSP (ou U+202F) dans `fmtEurCompact` aussi.

### NU-3-M-T14 — MINEUR — Littéraux `%` manuels avec espace sécable (front)
- **Où** : `frontend/src/lib/fourchette.ts:18,20,24` (« ±30 % », « 27 % »), `components/outils/blocB.tsx:178` (« ±44 % »), `lib/layers.ts:153,155`, `components/outils/Blocs.tsx:33-38` (« ≥ 1 000 m² »).
- **Juste/problème** : `format.ts` promet l'insécable ; ces littéraux manuels utilisent 0x20. **Proposition** : passer par les formateurs ou insécable explicite.

### NU-3-M-T15 — MINEUR — Signe « moins » incohérent sur l'abattement ZAN −50 %
- **Où** : `src/labuse/api/rarete.py:14,31` (vrai « − » U+2212) vs `rarete.py:74` et `moteurs.py:607…655` (tiret-trait « - »).
- **Juste/problème** : même règle, deux glyphes (« −50 % » vs « -50 % »). **Proposition** : U+2212 partout pour un nombre négatif.

### NU-3-M-T16 — MINEUR — Apostrophe courbe/droite mélangées
- **Où** : `src/labuse/flash/templates/rapport.html.j2:228` (U+2019 isolée parmi des droites) ; `src/labuse/api/moteurs.py:148,152` (« toute l'île » courbe à côté de « d'analogie » droite) ; front `primitives.tsx:334`, `EtudeV6.tsx:353` (droites dans une app majoritairement courbe).
- **Juste/problème** : rendu incohérent de l'apostrophe. **Proposition** : apostrophe typographique U+2019 partout.

### NU-3-M-T17 — MINEUR — Anglicismes résiduels en surface client
- **Où** : `src/labuse/flash/templates/rapport.html.j2:416` (« **Vélocité administrative** », calque de *velocity*, alors que le sous-titre dit déjà « Délai médian d'instruction ») ; `src/labuse/api/ortho.py:48` (champ `source` client : « Source ortho désactivée au **dashboard** ») ; `outils/radar-extension/options.html:41` (« **Jitter** max (minutes) »).
- **Juste/problème** : termes non usuels/jargon exposés. **Proposition** : « Délais d'instruction » / « tableau de bord » / « Décalage aléatoire max ».

### NU-3-M-T18 — MINEUR — Fonction de recette « Tester l'alarme » livrée dans le popup de PROD (extension)
- **Où** : `outils/radar-extension/popup.html:20` (+ `popup.js:40-53`, `background.js type:"test-alarm"`).
- **Affiché** : lien « Tester l'alarme (+2 min) », `title` « Recette : programme l'alarme dans 2 minutes… ».
- **Juste/problème** : outil de QA (le mot « Recette » est interne) visible/cliquable par tout client. **Proposition** : masquer derrière un flag dev.

### NU-3-M-T19 — DETTE — Jeton technique et abréviations en libellé (extension)
- **Où** : `outils/radar-extension/options.html:32` (« Jeton (**X-Radar-Token**) ») ; `background.js:702,710` (« LBC **nouv** 3, **relec** 12, **conf** 1 »).
- **Juste/problème** : nom d'en-tête HTTP et jargon abrégé non explicités. **Proposition** : libellé humain, en-tête masqué.

### NU-3-M-T20 — DETTE — « fourchette ±30 % » figée en dur, découplée de la constante
- **Où** : `frontend/src/components/fiche/constructibilite.tsx:904` (« fourchette ±30 % » en clair) vs `frontend/src/lib/fourchette.ts:14` (`FOURCHETTE_DEMI_LARGEUR_PCT`, qui se commente lui-même « les deux DOIVENT rester synchrones »).
- **Juste/problème** : contradiction latente si la constante bouge sans toucher le texte. **Proposition** : interpoler la constante dans le texte.

### NU-3-M-T21 — DETTE — Chaînes/contenus morts shippables
- **Où** : `frontend/src/lib/strings.ts` clé `ventDeclassees` (« N faible », rendue nulle part) ; `src/labuse/emails.py:197` (HTML « {total} **mouvement(s)** » parenthésé vs `:47` texte qui accorde le pluriel) ; `src/labuse/gabarit/fixtures.py:81` (reculs/emprises/hauteurs de démo « 5 m / 3 m / 40 % » — à confirmer non exposées client via `api/gabarit.py:23`).
- **Juste/problème** : code mort/incohérences latentes. **Proposition** : supprimer les morts, accorder le pluriel HTML, vérifier le point d'entrée Gabarit démo.

---

## Pilier 2 — JURIDIQUE

> Correctif de cadrage : contrairement à une première lecture (« aucune page légale dans le front »),
> le légal vit **côté serveur** dans `src/labuse/api/onboarding.py` (HTML rendu) : **les CGV existent et
> sont servies** à `/cgv` (`onboarding.py:690`), avec clause boussole « pré-analyse indicative, pas un
> conseil » (art. 2), sans engagement (art. 5), preuve d'acceptation horodatée (`cgv_version` +
> `cgv_acceptees_at`, `comptes.py:104,341`) côté abonnement ET Flash (`facturation.py:167`). En
> revanche `/mentions-legales` et `/confidentialite` **redirigent (301) hors dépôt** — voir J03.

### NU-3-M-J01 — BLOQUANT — Aucune base légale ni information pour le traitement des données personnelles de propriétaires tiers (art. 14 RGPD)
- **Où** : CGV art. 8 « Données personnelles (RGPD) » `src/labuse/api/onboarding.py:777-783`.
- **Constat** : l'art. 8 n'énumère QUE les données du **client-utilisateur** (email, nom du compte, journal de connexion, facturation Stripe). Aucune mention des **personnes physiques tierces** dont l'app traite et affiche les données.
- **Contradiction** : l'app affiche et traite des données personnelles de propriétaires non-clients — noms via `proprietaire_type.libelle_proprietaire` (`src/labuse/proprietaire_type.py:134-141`), `owner_name` servi en fiche (`src/labuse/api/enrichment.py:382,384`), historique de propriété, et surtout **adressage de courrier nominatif** (`src/labuse/courrier.py`, sous-traitant postal). Ces personnes ne sont ni informées (art. 14), ni couvertes par une base légale (art. 6), ni par une durée de conservation.
- **Impact** : cœur de métier (prospection foncière) reposant sur un traitement de données de tiers **sans cadre RGPD** — exposition CNIL majeure. Non déployable en conformité tel quel.
- **Proposition** (pas de rédaction ici) : établir base légale (intérêt légitime + balance), information art. 14 (mention dans les exports/courriers listant la source et les droits), durée de conservation, et registre des traitements.

### NU-3-M-J02 — BLOQUANT — Fuite de patronymes de particuliers via successions/indivisions (ex-NU-D-017, toujours vivant)
- **Où** : `src/labuse/proprietaire_type.py:134-138` (`libelle_proprietaire`) et `:166-168` (`classify_dgfip` → `owner_name = nom`). *(re-vérifié à la main.)*
- **Affiché vs juste** : le code se dit « personnes morales uniquement » (`proprietaire_historique.py:10`, `ProprietaireHistorique.tsx:5`, `blocs.py:11`) et son **propre commentaire** l.104-105 affirme « une succession/indivision N'EST PAS une personne morale ». Pourtant, pour une tête « Succession »/« Indivision », `libelle_proprietaire` ne retire QUE le mot de tête (`re.sub("^(succession|indivision|…)\s+", "", nom)`) et **conserve le patronyme**, puis renvoie `« Succession — DUPONT Jean »`. `owner_name` reçoit la dénomination complète. Ces libellés sont servis en clair dans la fiche, le Dossier, le Comparatif, le Courrier et le Copilote (`proprietaire_type.py:102-105`).
- **Contradiction** : la purge RGPD livrée (`rgpd_dirigeants.py`) ne couvre QUE la nationalité des dirigeants de PM et le `raw` RNE — elle ne touche jamais `parcelle_personne_morale.denomination` des successions/indivisions.
- **Impact** : diffusion de noms de personnes physiques identifiables (héritiers, indivisaires) à des clients commerciaux — manquement RGPD direct. Le constat NU-D-017 reste **non corrigé**.
- **Proposition** : masquer/agréger le patronyme pour les têtes succession/indivision (« Succession (plusieurs héritiers) ») comme pour les personnes physiques, ou le traiter sous base légale + information explicites.

### NU-3-M-J03 — MAJEUR — Mentions légales & politique de confidentialité hors dépôt + sous-traitants réels non nommés
- **Où** : redirections 301 `src/labuse/api/onboarding.py:806-813` (`/mentions-legales` → `https://labuse.immo/mentions-legales/`, `/confidentialite` → idem) ; renvoi « Politique complète » `onboarding.py:783` ; CGV art. 8 `onboarding.py:782`.
- **Constat** : la **source de vérité du légal** (mentions, politique de confidentialité, liste des sous-traitants, finalités) est **hors du dépôt auditable** — son contenu réel est invérifiable ici et peut diverger du comportement de l'app. L'art. 8 ne nomme que « Stripe (paiement), hébergeur (UE), service d'acheminement des e-mails (SMTP) ». Or l'app utilise **Brevo** comme sous-traitant d'emailing (`src/labuse/brevo.py:1-14`, templates 4-19) et **Merci Facteur PRO** comme sous-traitant d'envoi postal nominatif (`src/labuse/courrier.py`) — aucun nommé.
- **Impact** : obligation de transparence sur les sous-traitants (art. 13-14) potentiellement non remplie ; audit légal impossible depuis le produit déployé.
- **Proposition** : nommer explicitement Brevo et Merci Facteur dans l'art. 8 ; a minima servir la politique de confidentialité depuis l'app (versionnée) plutôt qu'en redirection externe.

### NU-3-M-J04 — MAJEUR — Pas de parcours self-service de droit d'accès / effacement (art. 15/17)
- **Où** : `effacer_compte_rgpd` existe (`src/labuse/comptes.py:797`, cascade FK + anonymisation audit robuste) mais n'est appelée QUE par la CLI (`src/labuse/cli.py:4524-4527`). Aucun endpoint API/écran. Aucune route d'export des données non plus.
- **Constat/contradiction** : la CGV art. 8 (`onboarding.py:781`) promet « droit d'accès, de rectification et d'effacement : contact@labuse.immo » (donc un email manuel) et l'art. 7 (`onboarding.py:772`) dit « il peut en demander l'export » — sans endpoint d'export existant.
- **Impact** : conformité « sur papier » dépendante d'un geste admin manuel ; risque de délai hors 1 mois (art. 12) à l'échelle. Acceptable à très petite échelle, à outiller avant croissance.
- **Proposition** : endpoint self-service d'export + demande d'effacement déclenchant `effacer_compte_rgpd`.

### NU-3-M-J05 — MINEUR — Durées de conservation partielles, nulles sur le stock de données tierces
- **Où** : purges TTL réelles pour notifications 90 j (`src/labuse/api/events.py:186,292`), Copilote 7 j (`config.py:340`), contexte 10 min (`config.py:342`) ; CGV art. 8 annonce « la vie du compte, puis effacement sous 30 jours » (`onboarding.py:780`).
- **Constat** : la seule durée annoncée ne concerne que l'utilisateur ; les **données de propriétaires tiers** (`parcelle_personne_morale`, `owner_enrichment`) n'ont **aucune durée déclarée ni appliquée** — elles vivent indéfiniment.
- **Impact** : pas de limitation de conservation pour le vrai stock personnel (art. 5-1-e). **Proposition** : durée + purge pour les données tierces.

### NU-3-M-J06 — MINEUR — Absence de bandeau cookies : CONFORME en l'état (à confirmer sur la vitrine)
- **Où** : aucun bandeau/consentement dans `frontend/` ; cookie unique fonctionnel `labuse_session` HMAC httpOnly SameSite=Lax (`src/labuse/api/auth.py:6-7,28`). Grep analytics/Sentry/gtag/matomo/plausible/posthog = **néant**.
- **Constat** : aucun traceur → aucun consentement requis (cookie strictement nécessaire, exempté) — **c'est correct**. Noté pour mémoire ; à vérifier que le site vitrine `labuse.immo` (hors dépôt) n'ajoute pas de traceur sans bandeau.
- **Impact** : nul côté app ; dette documentaire seulement.

### NU-3-M-J07 — DETTE — Preuve d'acceptation CGV solide (bon point, par contraste)
- **Où** : `comptes.py:104,330-344` (utilisateurs : `cgv_version` + `cgv_acceptees_at` horodatés, audit) ; `facturation.py:167-196` (`flash_commandes` : `cgv_version`/`cgv_accepte_at`) ; case obligatoire avant paiement (`onboarding.py:376`).
- **Constat** : le consentement **contractuel** est bien recueilli et consigné (version + horodatage), côté abonnement ET Flash. Noté comme dette car cette rigueur sur le contractuel **souligne par contraste** l'absence totale de base/preuve pour le traitement des données TIERS (J01/J02).

---

## Pilier 3 — PRIX ET PAIEMENT

> Socle solide. Source unique `config.py:196` `integral_prix_eur_mois=349` / `:199` `flash_price_eur=79`
> → `offres.py` → `/api/offres` ; **aucun 349/79 codé en dur dans une chaîne servie** (toutes les
> occurrences sont config, commentaires, ou le CLI de provisionnement qui lit lui-même
> `offre_*()["eur"]*100`). Cohérence écran↔Stripe **doublement garantie** : `provisionner()` pose
> `unit_amount = eur*100` (`facturation.py:56-68`) ET `_garde_coherence_prix` (`facturation.py:73-88`)
> **refuse de facturer** si le prix Stripe diverge de l'affiché. TVA/franchise 293 B affichée de façon
> cohérente aux points de vente (pied Flash, CGV art. 4, pied facture Stripe). **Aucun bloquant** :
> aucun montant erroné, aucun sur-octroi silencieux non divulgué. Les risques résiduels sont des
> **mismatches accès↔facturation dépendant de gestes manuels Stripe**.

**Tableau des prix affichés** (tous lus de la source, sauf le pied Flash TVA en dur) :

| Emplacement | Valeur | Codé en dur ? | = 349/79 ? |
|---|---|---|---|
| `config.py:196/199` (source) | 349 / 79 | source de vérité | ✅ |
| `/api/offres`, front (`api.ts`, `Licences.tsx`) | via offres.py | lu serveur | ✅ |
| Invitation / bascule paiement (`onboarding.py:352,467…`) | `{eur_mois} €` | lu `offre_integral()` | ✅ 349 |
| CGV art. 4 (`onboarding.py:740-742`) | 349 / 79 / 30 j | lu offres.py | ✅ |
| Page /flash (`onboarding.py:1071,1085`) | `{eur} €` | lu `offre_flash()` | ✅ 79 |
| Checkout Stripe Intégral/Flash (`facturation.py:134,181`) | `eur*100` + garde cohérence | lu offres.py | ✅ |
| Pied facture Stripe (`config.py:306`) | mention 293 B | config | n/a (TVA) |
| **Pied HTML Flash** (`onboarding.py:280`) | « sans TVA à ajouter » | **codé en dur** (ne lit pas `facture_mention`) | voir P05 |
| E-mails Brevo (templates 4-19) | aucun param prix | corps **hors dépôt** | non auditable (P04) |

### NU-3-M-P01 — MINEUR — Résiliation en cours de mois : coupure immédiate possible, contraire aux CGV
- **Où** : `src/labuse/facturation.py:496-501` (`customer.subscription.deleted → suspendre_compte`) + `comptes.py:752-757` (`suspendre_compte` passe `statut='suspendu'` ET `DELETE FROM sessions_auth` sur-le-champ).
- **Comportement** : les CGV art. 5 (`onboarding.py:755-761`) promettent « la résiliation prend effet à la fin de la période mensuelle en cours … accès maintenu jusqu'au terme de la période déjà payée ». Mais `subscription.deleted` **coupe l'accès immédiatement**.
- **Juste/attendu** : pour tenir la promesse, la résiliation doit utiliser `cancel_at_period_end=true` côté Stripe (le webhook `deleted` ne partant alors qu'à la fin de période). Aucun endpoint self-service ni billing portal : la résiliation passe **100 % par un geste manuel de Vic** — le respect de la CGV dépend donc entièrement de CE geste, non garanti par le code.
- **Repro** : client résilie le jour 3 d'un mois payé ; si Vic supprime la souscription immédiatement → accès coupé jour 3 alors que le mois est dû et promis. **Proposition** : documenter/forcer `cancel_at_period_end`.

### NU-3-M-P02 — MINEUR — `paiement_requis` conserve l'accès payant intégral (période de grâce divulguée)
- **Où** : `comptes.py:456` et `:466` — `paiement_requis` **absent des deux listes de coupure** → `session_utilisateur` reste valide. *(re-vérifié à la main.)*
- **Comportement** : après `invoice.payment_failed` (`facturation.py:468-471`) le compte passe `paiement_requis` mais garde l'accès complet pendant les relances Stripe. L'utilisateur voit un **bandeau** d'avertissement (`frontend/src/App.tsx:527-531`, « le dernier prélèvement n'a pas abouti … l'accès sera suspendu sans régularisation »).
- **Juste/attendu** : c'est une **période de grâce intentionnelle et documentée** (commentaire `comptes.py:463-465`), pas un sur-octroi silencieux — conforme au connu NU-3-H M02. À confirmer par Vic que la durée (pilotée par les relances Stripe, pas par l'app) est bornée.
- **Repro** : carte expire, paiement échoue jour 1 → accès complet jusqu'à ce que Stripe épuise ses relances et supprime la souscription.

### NU-3-M-P03 — MINEUR — Aucun traitement du remboursement (`charge.refunded`)
- **Où** : `facturation.py:381-508` (`traiter_webhook` ne gère que `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`). Grep `refund` = 0 hit hors prose CGV.
- **Comportement** : les CGV promettent un remboursement si le rapport Flash échoue (`onboarding.py:753`) et pour la période non servie (`onboarding.py:763`). Un remboursement émis dans Stripe est purement comptable, **ne révoque aucun accès** in-app.
- **Juste/attendu** : acceptable pour le Flash (one-shot, rien à révoquer) ; pour l'Intégral, un remboursement Stripe **non accompagné** d'une suppression de souscription laisse l'accès `actif`. En pratique les deux vont ensemble → effet limité, **DETTE plutôt que faille**. **Proposition** : documenter la procédure (toujours annuler la souscription en remboursant l'Intégral).

### NU-3-M-P04 — DETTE — Corps des e-mails transactionnels non auditable (prix/TVA hors dépôt)
- **Où** : `src/labuse/brevo.py:44-95` (templates 4-19 référencés par ID ; corps HTML chez Brevo). Les mails `flash_pret`, `relance_carte`, `resiliation`, etc. **ne reçoivent aucun paramètre de prix** → le code ne peut pas injecter un prix divergent.
- **Risque** : si un rédacteur a figé « 349 € »/« 79 € » ou une mention TVA EN DUR dans un template Brevo, cela dériverait silencieusement à un changement de prix/régime. **Proposition** : revue manuelle Brevo + `verifier_templates()`.

### NU-3-M-P05 — DETTE — Pied Flash « sans TVA à ajouter » codé en dur : mentira au jour de l'assujettissement TVA
- **Où** : `src/labuse/api/onboarding.py:278-280` (`_FLASH_PIED` : « Prix total, sans TVA à ajouter — TVA non applicable, article 293 B du CGI ») — **ne lit pas** `config.facture_mention`. *(re-vérifié à la main.)*
- **Contexte** : `config.py:303-306` **avertit** que le MRR dépassera le seuil de franchise 293 B « dans l'année ». Le jour de la bascule, Vic changera `facture_mention` → la facture Stripe suivra, mais la page `/flash` continuera d'afficher « sans TVA à ajouter — art. 293 B » (texte en dur).
- **Proposition** : faire lire `facture_mention` au pied Flash (source unique de la mention fiscale).

---

## Pilier 4 — ACCESSIBILITÉ

### Contrastes de la DA sombre — MESURÉS (ratio WCAG, tokens `index.css`)

Tout le texte LABUSE est inférieur à 18,66 px gras / 24 px → **seuil AA = 4,5:1** (aucun exempté « grand texte »). Ratios calculés texte × fond (fonds : `bg-0 #0A0C0B`, `bg-1 #0C0F0D`, `bg-2 #111614`, `bg-stat #141A17`, `bg-3 #161C19`) :

| Token texte (hex) | sur bg-0 | sur bg-2 | sur bg-3 | verdict AA |
|---|---|---|---|---|
| `txt-hi #E8EFEA` | 16,8 | 15,6 | 14,8 | ✅ |
| `txt #B8C4BC` | 10,9 | 10,2 | 9,6 | ✅ |
| `txt-dim #8A968F` | 6,4 | 6,0 | 5,6 | ✅ |
| **`txt-mut #6B776F`** | **4,20** | **3,91** | **3,70** | **❌ échoue partout** |
| **`txt-off #5E6B64`** | **3,52** | **3,28** | **3,10** | **❌ échoue partout** |
| **`txt-faint #4E5A53`** | **2,72** | **2,53** | **2,40** | **❌ échoue (loin)** |
| `txt-ghost #3E4A44` | 2,12 | 1,97 | 1,87 | ❌ (décoratif) |
| `lab #7C8A82` | 5,43 | 5,06 | 4,79 | ✅ (juste) |
| `#97A39B` (seg/p-off) | 7,50 | 6,99 | 6,61 | ✅ |
| `mint #4ADE80` | 11,3 | 10,5 | 9,9 | ✅ |
| `coral #E2726A` | 6,4 | 6,0 | 5,6 | ✅ |
| `amber #E0A94F` | 9,3 | 8,7 | 8,2 | ✅ |

Jetons teintés sur leur fond : `amber` sur `amber-bg` 7,5 ✅ · `coral` sur `coral-bg` 5,5 ✅ · `mint` sur `mint-bg` 8,9 ✅ · texte encre `#071009` sur aplat `mint` (survol plein) 11,1 ✅. Les surfaces colorées et le texte principal sont **largement conformes** ; le problème est **les trois niveaux de texte sombre**.

### NU-3-M-A01 — MAJEUR — Texte de champ et texte secondaire sous le seuil AA 4,5:1
- **Où** : `.field { color:var(--txt-off) }` (`frontend/src/styles/index.css:299`) → **texte saisi dans les champs à 3,28:1** sur `bg-2`. `--txt-mut` (3,70–4,20:1) porte le sous-texte des lignes (`.gr-s` l.91, `.po-s` l.564, sous-titres de tooltips), `--txt-faint` (2,40–2,72:1) porte `.legal` (mentions légales 9 px !, l.315), `.stat-s`, `.chev`, `.stat-v.vide`.
- **Défaut** : la valeur tapée dans un champ, une partie du texte secondaire omniprésent et **le texte légal** sont sous 4,5:1 (le légal est à ~2,5:1, très loin).
- **WCAG** : 1.4.3 (contraste minimum).
- **Repro** : lire une valeur saisie dans un champ sur `bg-2` ; lire un `.stat-s`/`.legal`. **Proposition** : relever `.field` à `--txt` (10:1), `--txt-mut`→cible ≥ 4,5 (ex. `#7C8A82`/`--lab`), et surtout `.legal` qui doit rester lisible.

### NU-3-M-A02 — MAJEUR — Copilote et Estimer : les résultats asynchrones ne sont pas des régions live
- **Où** : Copilote `frontend/src/components/copilote/CopiloteView.tsx:161` (`<div data-fil>`), `ReponseInline.tsx:102-109` — grep `aria-live`/`role=status`/`role=log` sur `components/copilote/*` = **0**. Estimer `frontend/src/components/outils/AnalyserAnnonce.tsx:183-268` (bloc estimation) et `:377-410` (prix vs marché) : résultat dans un `<section>` ordinaire. *(re-vérifié à la main : 0 région live côté Copilote.)*
- **Défaut** : quand la réponse Copilote arrive (ou le rapport Estimer se construit), **rien n'est annoncé** au lecteur d'écran — seul l'indicateur de chargement (`role=status`) parle, puis silence sur le contenu utile.
- **WCAG** : 4.1.3 (messages d'état).
- **Repro** : VoiceOver/NVDA, poser une question au Copilote → « cherche votre réponse… » puis plus rien ; coller un lien dans Estimer → le rapport apparaît en silence. **Proposition** : `role="status"`/`aria-live="polite"` sur le conteneur de réponse Copilote et sur le bloc résultat Estimer.

### NU-3-M-A03 — MAJEUR — Estimer : champ « lien d'annonce » sans libellé programmatique, erreur non liée
- **Où** : `AnalyserAnnonce.tsx:551-564` — l'`<input>` n'a qu'un `<p>` adjacent « Un lien d'annonce » (non associé) + un `placeholder` comme libellé ; aucun `<label htmlFor>`/`aria-label`/`aria-labelledby`. L'erreur (`:564`) est un `<p class="text-coral">` sibling, sans `aria-describedby`/`aria-invalid`/`role="alert"`. *(re-vérifié à la main.)*
- **Défaut** : placeholder-as-label (disparaît à la saisie) ; l'erreur n'est ni annoncée ni rattachée au champ. (Note : le champ « Surface habitable » `:226` a, lui, un vrai `<label htmlFor>` — correct, donc le patron existe.)
- **WCAG** : 4.1.2 / 3.3.2 / 3.3.1.
- **Repro** : VoiceOver sur le champ lien → « zone d'édition » sans nom ; coller un lien invalide → message rouge muet. **Proposition** : `<label>` associé + `aria-invalid`/`role="alert"` sur l'erreur.

### NU-3-M-A04 — MAJEUR — Modales/drawers sans piège de focus ni restitution
- **Où** : `frontend/src/components/documents/DocumentsView.tsx:229-236` (`role="dialog" aria-modal="true"` mais rien d'autre), `components/outils/ModulePanel.tsx:409-411` (tiroir Permis : ni rôle, ni trap, ni Esc), `components/fiche/SourceDrawer.tsx:26-37` (Esc OK mais pas de `role=dialog`, pas de piège, pas de focus initial/restitution). Le patron correct existe (`AccueilCopilote.tsx:89-105`, piège + restitution) mais n'est pas généralisé.
- **Défaut** : focus reste derrière la modale, Tab en sort, et à la fermeture le focus n'est pas rendu au déclencheur.
- **WCAG** : 2.1.2 (pas de piège inverse) / 2.4.3 (ordre de focus).
- **Repro** : ouvrir « Dossier » (Docs) au clavier → Tab circule derrière ; fermer le drawer Permis → focus perdu en haut du document. **Proposition** : généraliser le hook de piège de focus de `AccueilCopilote`.

### NU-3-M-A05 — MINEUR — Fiche : pas de landmark `<main>` ni de hiérarchie de titres
- **Où** : aucun `<main>`/`role="main"` dans `components/` ; `fiche/Fiche.tsx:898-900` (identité parcelle = `<div>/<span>`, pas de `<h1>`) ; `fiche/primitives.tsx:119-123` (titres de section = `<div class="t-title">` dans un `<button>`, pas de `<h2>`). *(re-vérifié : le Rail a bien `<nav>`+`aria-current`, Copilote/Projets ont un `<h1>`.)*
- **Défaut** : l'écran central n'a ni point de repère principal ni titre ; « aller au contenu » et « lister les titres » du lecteur d'écran ne trouvent rien.
- **WCAG** : 1.3.1 / 2.4.1 / 2.4.6. **Proposition** : `<main>` autour du contenu, `<h1>` sur l'IDU/adresse, titres de tiroir en `<h2>`.

### NU-3-M-A06 — MINEUR — Carte : sélection de parcelle au clic souris uniquement
- **Où** : `components/map/MapView.tsx:1066-1079` (`m.on('click', layerId, …)`), aucun équivalent clavier sur le canvas.
- **Atténuation** : chemin clavier robuste via l'omnibox `AddressAutocomplete` (combobox ARIA 1.1 complet) et `ParcelInput` → ouvrir une fiche reste possible au clavier.
- **WCAG** : 2.1.1 (partiellement compensé). **Repro** : au clavier seul, impossible de cliquer une parcelle sur la carte.

### NU-3-M-A07 — MINEUR — Bouton recentrer 3D annoncé par `title` seul
- **Où** : `MapView.tsx:447` (bouton recentrer `◎` : `title` sans `aria-label`), alors que `BoutonCarte` `:452-463` utilise bien `aria-label={title}`. **WCAG** : 4.1.2. **Proposition** : `aria-label` explicite.

### NU-3-M-A08 — MINEUR — Signaux portés par la couleur (renfort texte majoritaire, deux résidus)
- **Où** : majoritairement **OK** (niveau d'aléa écrit « niveau {intensité} » `fiche/risques.tsx:77` ; PPR « zone bleue » = Badge ambre AVEC texte `:87` ; `CasesEtat` ✓/?/✕ avec glyphe ; pastille lu/non-lu `Header.tsx:337` = `role="img" aria-label` corrigé NU-F-039). Résidus : `fiche/formes.tsx` `Reglette` (`:208-210`, repère commune vs secteur distingués par couleur/forme sans libellé d'état propre) et remplissage de `Jauge3` (`:110-124`, intensité héritée du texte voisin seulement).
- **WCAG** : 1.4.1. **Repro** : en nuances de gris, la position « secteur vs commune » de la Réglette se lit mal.

### NU-3-M-A09 — DETTE — `outline-none` sans focus-visible de remplacement (Copilote embarqué) + `role=status` imbriqué dans un bouton
- **Où** : `copilote/CopiloteEmbarque.tsx:54,79,98` (`outline-none` sans `focus:border`/`focus-visible` — la plupart des autres champs ont `focus:border-mint`) ; `AnalyserAnnonce.tsx:253,562` (`<Chargement role=status>` imbriqué dans un `<button>` → région live dans un contrôle, annonce ambiguë).
- **WCAG** : 2.4.7 / 4.1.2. **Proposition** : bordure de focus visible ; sortir le `role=status` du bouton.

> **Synthèse a11y.** Base de primitives étonnamment mûre (omnibox combobox ARIA 1.1, tooltips `Tip`
> focusables+Esc, accordéons en vrais `<button aria-expanded>`, `<select>` natifs, `prefers-reduced-motion`
> respecté, indicateur de chargement unique `role=status`, nav `<nav>`+`aria-current`, un piège de focus
> exemplaire). Deux faiblesses systémiques : **(1) pas de région live sur les contenus asynchrones cœur
> de métier** (réponse Copilote, résultat Estimer se construisent en silence) et **(2) gestion de focus
> des modales non généralisée**. Un utilisateur clavier seul PEUT : ouvrir une fiche (via omnibox, pas via
> carte), lancer Estimer (dégradé : champ sans nom, erreurs/résultat muets), interroger le Copilote
> (dégradé : réponse non vocalisée). **Aucun blocage dur, mais 3 parcours sur 3 dégradés pour un lecteur
> d'écran, surtout faute d'`aria-live`.** L'audit axe dynamique et VoiceOver réel restent à jouer sur une
> instance bootée (limite de ce lot).

---

## Pilier 5 — AIDE ET ONBOARDING

### NU-3-M-H01 — MAJEUR — L'aide décrit le classement comme « probabilité de vente » alors que le tri est qualité-foncière d'abord (deux surfaces d'aide se contredisent)
- **Où** : modale « Info classement » `frontend/src/lib/strings.ts:363-390` (`algo.corps`, titre `algo.titre` « Comment LABUSE classe les parcelles », montée depuis `components/panel/LeftPanel.tsx:46`) + libellés de tri `strings.ts:198` (`tri.rang: 'Probabilité de vente sous 1 an'`), `:210` (`tri.rangTip`) ; comportement réel `src/labuse/scoring/score_labuse_combine.py:1-12` et `:153-159` (`_cle_classement`). *(re-vérifié à la main.)*
- **Dit** : « Ce que mesure le classement : Une seule chose : la probabilité qu'une parcelle change de main à court terme. Pas sa valeur, pas sa beauté — sa probabilité de vente. » et `rangTip` « le classement LABUSE — la probabilité de vente sous 1 an … les ex æquo départagés par la qualité du terrain ».
- **Fait réellement** : la clé de tri est **lexicographique `(BANDE_RANG, −signal_p, −sdp, idu)`** — **la bande de qualité foncière (A>B>C>D>NC) D'ABORD**, le Signal (probabilité) ne départageant QU'À l'intérieur d'une bande (le docstring l.8-11 l'affirme : « d'abord la BANDE … puis le Signal À L'INTÉRIEUR de la bande »). C'est **l'inverse** de ce que dit le tip.
- **Écart** : faux/contradictoire. L'autre panneau d'aide `comprendre.classement` (`strings.ts:315`, « La bande dit le potentiel constructible RÉEL ») et les libellés de bande (`lib/status.ts:119-125`, « Excellente — le meilleur potentiel constructible ») disent **juste** — ce sont « Info classement » + `tri.rang`/`rangTip` qui inversent qualité et probabilité.
- **Repro** : ouvrir « Info classement » (panneau résultats) vs « Comprendre l'analyse » vs survol de l'en-tête de tri. **Proposition** : réécrire `algo.corps`/`tri.rang`/`rangTip` pour dire « tri par potentiel constructible (bande), départage par probabilité de vente » — aligné sur `_cle_classement`.

### NU-3-M-H02 — MAJEUR — Infobulle comparateur : « appartements priorisés » décrit une méthode supprimée par FIX-FINAL-1
- **Où** : `frontend/src/components/outils/blocB.tsx:173` (tip de la colonne `prix_ancien`) ; comportement réel `src/labuse/marche_service.py:139-152`.
- **Dit** : « ⚠ La FICHE d'une commune affiche un prix LOCAL (secteur autour de la parcelle centrale, **appartements priorisés**) — plus fin, souvent inférieur ».
- **Fait réellement** : depuis FIX-FINAL-1 (NU-A-002), le « prix de l'ancien » de tête est servi par `sector_price(…, type_prioritaire=tp)` où `tp` est **la nature réelle de la dernière mutation DVF** (maison OU appartement) ; le commentaire `marche_service.py:139-143` dit explicitement « plus jamais un prix d'appartement servi en tête d'un dossier de maison ». **Il n'y a plus de priorisation appartement.**
- **Écart** : périmé — l'aide décrit la méthode d'avant le correctif qui l'a supprimée. **Proposition** : réécrire le tip (« prix du secteur, par type du bien »).

### NU-3-M-H03 — MINEUR — Badge « copro — hors du classement foncier par défaut » : exclusion inconditionnelle, pas « par défaut »
- **Où** : `frontend/src/components/fiche/ScoreV2Block.tsx:97` vs réel `src/labuse/scoring/p_v2/statuts.py` (exclusion `~df["copro"]`, fraction=null).
- **Dit/fait** : « par défaut » suggère une conditionnalité ; une copropriété est exclue **inconditionnellement** (aucun réglage ne la ré-inclut). De plus le badge vit sous l'en-tête « Probabilité de vente sous 1 an » tout en parlant du classement « foncier ».
- **Écart** : vague/trompeur. **Proposition** : « hors univers de classement (copropriété) ».

### NU-3-M-H04 — MINEUR — Infobulle « Loyers (OLL) » ne dit pas que la maille est la ZONE, pas la commune
- **Où** : `frontend/src/components/fiche/marche.tsx:273` ; réel `src/labuse/ingestion/oll_loyers.py:186-211` (`oll_parcelle`, jointure `spatial_layers kind='iris_insee'` → zone OLL ; repli zone agglomération pour les 8 communes multi-zones).
- **Dit/fait** : le tip affiche « Maison X · appart. Y €/m² » sans dire que c'est une médiane de **zone OLL** (6 zones couvrent l'île) — laisse croire à une granularité communale/locale.
- **Nuance** : le tip est gardé par `loyers_oll?.disponible` → il ne s'affiche jamais faux, il **manque juste la maille**. (Contexte PROD-VERIF-1 : OLL non résolu EN PROD, `iris_insee` 0/344.)
- **Écart** : incomplet. **Proposition** : nommer la zone OLL dans le tip.

### NU-3-M-H05 — MINEUR — Valeur du terrain : fourchette ±30 % présentée comme « incertitude mesurée » (marge forfaitaire)
- **Où** : `frontend/src/components/fiche/marche.tsx:154-158` (tip « Méthode de la valeur » + commentaire « incertitude mesurée (backtest VERITE-TERRAIN-2) ») ; source `lib/fourchette.ts` (`fourchette()` applique **±30 % constant**).
- **Dit/fait** : la fourchette est un ±30 % **uniforme** appliqué à tout terrain, pas une dispersion propre à l'échantillon de la parcelle — contrairement à l'outil Estimer qui calibre ±% par bien via IQR (`AnalyserAnnonce.tsx:220`, « Précision mesurée sur les ventes 2025 »).
- **Écart** : vague — « incertitude mesurée » survend une marge forfaitaire. **Proposition** : « fourchette indicative ±30 % » (sans « mesurée »).

### NU-3-M-H06 — DETTE — Aucun onboarding ni visite guidée de première utilisation
- **Où** : balayage `frontend/src/components` + `App.tsx` → aucun composant tour/walkthrough/first-run/« Bienvenue » (`LogoIntro.tsx` n'est qu'une animation ; `introDejaVue` `:199` ne garde qu'elle). Seul dispositif d'accueil : l'écran Copilote (`AccueilCopilote.tsx:23-34`, 10 exemples cliquables **tous mappés à de vraies capacités**) + l'avis IA permanent (`AvisIA.tsx`).
- **Écart** : aide à la découverte manquante pour une app à 40+ outils — pas de parcours guidé, pas d'états vides didactiques généralisés, pas de modale de première connexion. **Proposition** : au minimum un état vide didactique sur la fiche/les outils ; idéalement une courte visite.

### NU-3-M-H07 — DETTE — Bloc de preuve « 99,99 % » (rattachement BAN) défini mais jamais rendu
- **Où** : `frontend/src/lib/strings.ts:275-306` (`preuve`, « 99,99 % » en dur `:284`) ; aucun composant ne référence `CLIENT.preuve` (grep applicatif = 0).
- **Écart** : contenu d'aide orphelin (chiffre interne figé) ; s'il était rendu un jour, le « 99,99 % » serait à re-sourcer. **Proposition** : supprimer ou re-sourcer avant tout rendu.

> **Synthèse aide.** Pas de véritable onboarding ; la découverte repose sur l'accueil Copilote et sur une
> **couche très dense de tooltips méthodologiques**, dans l'ensemble **honnête et à jour** (taxe, baromètre
> VEFA/ancien/terrain, SDP « bâti conservé » R+1 supposé, PPR rouge « pas un certificat », aléas =
> intersection géométrique, succession = signal non confirmé, neuf ≤ 3 ans, médiane par type) : les
> correctifs récents (PPR-UNIQUE-1, ESTIMER-2, FIX-FINAL-1, COPILOTE-3) ont propagé jusqu'aux textes
> d'aide. Le point noir n'est pas un mensonge isolé mais **la contradiction entre deux surfaces d'aide sur
> LA notion centrale** (classement = probabilité de vente vs potentiel constructible — c'est le second qui
> est juste), plus un tip comparateur resté collé à une méthode d'avant correctif.

---

## Récapitulatif des trouvailles

| ID | Gravité | Pilier | Titre court |
|---|---|---|---|
| NU-3-M-J01 | **BLOQUANT** | Juridique | Données de propriétaires tiers sans base légale ni information (art. 14) |
| NU-3-M-J02 | **BLOQUANT** | Juridique | Fuite de patronymes successions/indivisions (`proprietaire_type.py:136`) |
| NU-3-M-T01 | MAJEUR | Textes | SDP « restante » vs « résiduelle » (même grandeur) |
| NU-3-M-T02 | MAJEUR | Textes | Flash sous-titré « Étude de faisabilité » (collision produit) |
| NU-3-M-J03 | MAJEUR | Juridique | Légal hors dépôt (301) + sous-traitants (Brevo, Merci Facteur) non nommés |
| NU-3-M-J04 | MAJEUR | Juridique | Pas de self-service accès/effacement (CLI only) |
| NU-3-M-A01 | MAJEUR | A11y | Contrastes DA : `.field` 3,28:1, `txt-mut`/`txt-faint` < AA |
| NU-3-M-A02 | MAJEUR | A11y | Copilote & Estimer : résultats sans `aria-live` |
| NU-3-M-A03 | MAJEUR | A11y | Estimer : champ lien sans libellé, erreur non liée |
| NU-3-M-A04 | MAJEUR | A11y | Modales/drawers sans piège de focus |
| NU-3-M-H01 | MAJEUR | Aide | Classement décrit « probabilité de vente » vs tri qualité-d'abord |
| NU-3-M-H02 | MAJEUR | Aide | Tip comparateur « appartements priorisés » périmé |
| NU-3-M-T04…T18, P01…P03, J05/J06, A05…A08, H03…H05 | MINEUR | (24) | voir détail ci-dessus |
| NU-3-M-T19…T21, P04/P05, J07, A09, H06/H07 | DETTE | (15) | voir détail ci-dessus |

**Fil rouge.** Les prix sont justes et bien gardés, les textes propres et l'aide honnête à l'unité : le
danger de ce lot n'est ni l'orthographe ni l'arithmétique, c'est **le juridique** (traitement non encadré
des données personnelles de tiers, fuite de patronymes toujours vivante, légal déporté hors dépôt) et,
en second rang, **la cohérence** (un même objet nommé de deux façons, une notion phare décrite à
contre-sens par l'aide) et **l'accessibilité** (contrastes sombres sous le seuil, parcours lecteur
d'écran dégradés faute de régions live). Deux bloquants, tous deux RGPD.
