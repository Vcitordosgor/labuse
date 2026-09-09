# RECETTE-2 — deuxième tour de recette (08/09/2026)

**Branche** `feat/recette-2` (depuis `feat/recette-1`) · worktree `~/Desktop/labuse-recette2` · rien mergé, aucune bascule, aucun rescoring.
**Run servi** : q_v14 (vérifié : `runs.current()` = q_v14, install editable + worktree `main` promus le 08/09 18:56 ; le manifeste local de ce worktree était périmé — aligné pour la recette, non commité).
**Méthode** : chaque point constaté dans Chrome via Playwright MCP (front `:5180` → API `:8022`, recette2). Preuves dans `docs/audit-2026-09/RECETTE-2-preuves/`.

## ⚠ Alerte à Vic (bloquant produit, hors code)
**S1 — le service IA est réellement coupé faute de crédits sur le compte Anthropic.** L'appel renvoie `400 — "Your credit balance is too low"` (clé valide). Je ne peux pas recharger le compte. Toutes les surfaces IA (Copilote, Synthèse, Poser une question) resteront en message honnête jusqu'à recharge. Tout le reste du mandat est fait.

---

## Tableau des 30 points

| # | État | Constaté au navigateur | Preuve |
|---|------|------------------------|--------|
| **S1** | Corrigé (message) + **action Vic** | Cause = compte Anthropic sans crédit. Le Copilote affiche le message honnête « solde de crédits épuisé — recharger le compte », plus « réessayez ». | `ai/core.py:83`, `copilote_v2/answering.py:41` · `s1-copilote-honnete.png` |
| **S2** | Corrigé | Le questionnaire s'arrêtait sur « enregistré » sans ouvrir le PDF. Bouton « Ouvrir le document Financier » ajouté → PDF 200 servi de bout en bout. | `FinancierQuestionnaire.tsx:66` |
| **S3** | Corrigé | 24 → 20 questions (4 retirées : type stationnement, prix déjà refusé, commission d'apporteur, apport). Libellés en français clair, fin du jargon. | `financier_questionnaire.py` · `s3-questionnaire-e1.png` |
| **S4** | Non reproduit | La carte de l'île + étiquettes de communes s'affiche par défaut (2 rechargements), parcelles au zoom/clic. Aucun gating dans MapView. | `s4-accueil-loaded.png`, `s4-reload.png` |
| **S5** | Corrigé | Nom de PM fonctionne (CBO/SCI → Scan patrimoine). Un nom de PP ne peut rien renvoyer (non-open-data). « commune » et « projet » retirés des formats. | `header/Header.tsx:233` · `s5-cbo.png` |
| **S6** | Corrigé | Cause = `count(*)` sur `parcel_p_score_v2` (4,3 M lignes) recalculé à chaque fiche (~2,1 s). Mémoïsé par run. Fiche 2,8 s → 0,79 s (880 ms réseau). | `verdict_servi.py:65` |
| **S7** | Corrigé (maquette à valider) | Section « Qui vous envoie ce brief » retirée ; date d'émission remontée en tête. Coup d'œil enrichi (Potentiel, Contraintes, Prix de secteur). PDF 4 pages. | `blocs/apporteur.py` · `s7-apporteur.png` · `maquette-apporteur.html` |
| **S8** | Corrigé | Un champ vide ne s'imprime plus jamais : commune/surface absente → segment retiré, phrase reformulée. Vérifié sur parcelle résolue ET non résolue (« votre parcelle ZZ 9999 » — zéro tiret). | `ModulePanel.tsx` (remplirGabaritCourrier) |
| **S9** | Répondu | Voir ci-dessous. | — |
| **S10** | Corrigé | Infobulles au survol retirées partout sauf contrôles carte (Legend, MapToolbar) et pastilles « i » icône-seule. Garde jsdom (Playwright ne déclenche pas les events React du portal). | `Tip.tsx`, `Tip.test.tsx` |
| **S11** | Corrigé (rendu à l'œil) | Voile gris retiré : opacité UNIFORME (0,72) en mode analyse, palier porté par la couleur. Vérifié dans le module servi (ancien voile retiré) ; rendu WebGL zoomé à confirmer à l'œil (cf. R36). | `MapView.tsx` (OPINION_OPACITY) |
| **S12** | Rien à faire | Écran 1 de l'analyse conservé. | — |
| **S13** | Corrigé | Texte « Info classement » réécrit pour q_v14 (train ≤2023, cal 2024, test 2025, isotonique par segment, signaux q_v14). Vérifié dans le module servi (q_v8 absent, q_v14 présent). | `lib/strings.ts:291` |
| **S14** | Répondu | Reproduit : l'adressage fonctionne (cache complet 257 340). Le tri `surface` de la vue factuelle remonte les emprises géantes (jusqu'à 28 M m²) non adressées (2/200). Voie « Demander à LABUSE » (rang) : 19/30 adressées. | — |
| **S15** | Corrigé | Cause profonde : `.hover-fill` = fond en DÉGRADÉ qui ne peint pas sur un `<tr>` ; texte en encre sombre sans aplat → « vert absent ». Fix CSS `tr.hover-fill:hover > td`. Ligne survolée verte. | `styles/index.css` · `s15-densifier-hover.png` |
| **S16** | Corrigé | Description de la carte 💧 Piscines raccourcie → 2 lignes comme Ensoleillement (même hauteur 80,9 px). | `ProspectionSolaire.tsx` · `s16-piscine-apres.png` |
| **S17** | Corrigé | Flèches d'accordéon : fermé → droite (▸, -rotate-90), ouvert → bas (▾). Deux chevrons SVG corrigés. Vérifié (fermé -rotate-90, ouvert sans rotation). | `ChevronSection.tsx`, `FiltreLabuse.tsx:200` |
| **S18** | Répondu (oui) | La fiche lit bien q_v14 : `score_v2.rang_total = 428 239` = exactement le compte classé q_v14. | — |
| **S19** | Répondu | Voir ci-dessous. | — |
| **S20** | Répondu | Voir ci-dessous. | — |
| **S21** | Répondu (oui) | Le n° de demande = `rang_compte` propre au compte (row_number par compte) — 1→16 pour ce compte, distinct du PK global (id 45 → rang 16). Vérifié en lecture (envoi réel non déclenché, à raison). | `courrier.py:201` |
| **S22** | Répondu (oui) | Projets triés `updated_at DESC` (plus récent d'abord). | `api/projets.py:632` |
| **S23** | Répondu (proposition) | Voir ci-dessous — liste proposée, NON appliquée. | — |
| **S24** | Non reproduit | 5 emplacements de nom de projet vérifiés au survol, tous lisibles (liste Projets = encre sur vert, dropdown fiche = encre sur ambre, CRM = mint conservé, suggestion = encre sur mint). | `s24-projet-hover.png` |
| **S25** | Corrigé | « Filtrer par thème » : liseré vert, survol vert (hover-fill), flèche ▾ ouverte / ▸ fermée. Vérifié. | `SourcesPage.tsx:257` |
| **S26** | Corrigé | Producteur (col 3) renvoyé en rangée 2 par l'auto-placement (après le ↗ col 4) → forcé rangée 1 (`md:row-start-1`). Nom + producteur alignés (grille passe de 2 rangées à 1). | `SourcesPage.tsx:97` · `s25-s26-apres.png` |
| **S27** | Corrigé | Point final de l'accroche solaire retiré. Vérifié. | `registry.ts:118` |
| **S28** | Corrigé/Vérifié | « Poser une question » ouvre le Copilote intégré à la fiche (data-ia-tete inline, contexte parcelle) — pas de page à part. | `s28-poser-question.png` |
| **S29** | Vérifié | « Synthèse IA » produit une vraie synthèse de la fiche (dérivée déterministe des données) ; couche LLM enrichie « non servie » à cause de S1. | `s29-synthese-ia.png` |
| **S30** | Répondu (proposition) | Voir ci-dessous — sans coder. | — |

---

## Réponses écrites

### S9 — Résumé vs Dossier
Le **Dossier** = document complet, 10 sections (identité, zonage, potentiel, risques, marché, réseaux, autour, commune, bilan, sources). Le **Résumé** reprend les MÊMES données en **sélection courte, présentation compacte (3 pages)** : zone, sur place, propriétaire, prix d'achat, potentiel, capacité, aléas, prix, viabilisation, dispositifs, taxe — et renvoie explicitement au Dossier (version complète) et au Financier (bilan chiffré). Il a **remplacé l'export brut de la fiche** (retiré au lot 8 d'EXPORTS-2).
**Il n'est pas redondant** : c'est la « carte de visite » d'une parcelle — l'essentiel en un coup d'œil, à joindre à un premier contact, là où le Dossier est l'exhaustif. **Recommandation : le conserver.** Sa seule faiblesse est le recouvrement de données avec le Dossier ; si Vic préfère un seul document, c'est le Résumé qui saute (le Dossier est le socle). **Décision laissée à Vic.**

### S19 — Sources SOURCES-1 orphelines dans la fiche, sous q_v14
Vérifié en base : ces sources SONT ingérées dans `spatial_layers` — `dpf` (281), `zone_humide` (3 122), `ens` (84, ≈ espaces naturels), `dpu` (202). **`rpg` n'existe PAS comme kind** (pas de couche dédiée ; contenu proche dans `ocs_ge`). **`peb` = 0 ligne** (retiré à raison, un couvert-vide serait un faux RAS).
**Réponse : NON, elles n'apparaissent toujours pas dans le bloc « Servitudes invisibles / Pièges » de la fiche** — parce que le dictionnaire `_KINDS` (`api/servitudes.py:28`) ne les liste pas. Le changement de cascade servie (q_v13_sources1) est **orthogonal** : il concerne le SCORING, pas l'affichage des couches (qui vivent dans `spatial_layers`, indépendant du run). Elles apparaissent en revanche sur la CARTE (couches). Les remonter dans la fiche = exactement l'objet de **S23**.

### S20 — La fiche est-elle au mieux de ce qu'elle peut être ?
La fiche est riche et honnête (chaque chiffre sourcé, absences dites). Ce qui manquerait, avec les données disponibles :
1. **Servitudes/pièges incomplets** — DPU, DPF (ravines/reculs), zones humides, ENS ingérés mais non remontés dans le bloc « Servitudes invisibles » (cf. S19/S23). C'est le gisement le plus net.
2. **PEB (bruit aérien)** — non ingéré (0 ligne) ; à dire « non couvert », déjà le cas.
3. **RPG (parcellaire agricole)** — pas de couche dédiée ; l'usage agricole n'est visible que via `ocs_ge`.
4. **Adresse** — présente pour ~60 % des parcelles (les grandes emprises naturelles n'en ont pas) ; c'est une limite de la source, pas de la fiche.
5. **Enrichissement IA** — la synthèse et le Q&A dépendent de S1 (crédits) ; couche déterministe déjà servie.
Hors ces points, la fiche exploite bien les sources. La priorité d'amélioration = **S23** (remonter les 4 kinds servitudes déjà en base).

### S23 — Extension de `_KINDS` (proposition, NON appliquée)
`_KINDS` (`api/servitudes.py:28`) liste aujourd'hui : sup, cinquante_pas, bruit_route, sol_pollue, trait_de_cote, zonage_assainissement, znieff. **Kinds à ajouter (présents en base, donc pas de faux RAS)** :

| kind | lignes | libellé proposé | vigilance |
|------|-------:|-----------------|-----------|
| `dpu` | 202 | Droit de préemption urbain (DPU) | la commune peut préempter une vente |
| `dpf` | 281 | Domaine public fluvial — ravine / recul | recul de construction imposé |
| `zone_humide` | 3 122 | Zone humide (inventaire) | remblai/drainage encadrés (loi sur l'eau) |
| `ens` | 84 | Espace naturel sensible (ENS) | droit de préemption départemental, protection |

**ER / EBC** : déjà servis en fiche via le bloc « Signaux » (prescriptions `plu_gpu_prescription`, badges EBC/ER) — pas dans `_KINDS`, à laisser tel quel OU rapatrier pour l'unicité (décision Vic). **PEB** : rester en « non couvert » (0 ligne). **RPG** : pas de kind → rien à remonter.
**Non appliqué — attend l'accord de Vic** (le bloc servitudes pilote une décision d'achat, chaque libellé doit être arbitré).

### S30 — Segmentation du listing du mode analyse (proposition, sans coder)
Ce qui existe aujourd'hui : le listing (`ResultsSection`) est **une liste plate triée par rang**, chaque carte portant des badges (palier, raison, état du bien, événement, cluster, veille, type de propriétaire). Il n'y a **aucun regroupement** — je ne trouve pas de convention antérieure écrite ; « segmenter par type » reste à cadrer.
**Proposition (à valider, sans coder)** — segmenter par **palier** (le « type » de classement, vocabulaire PALIERS-1), dans l'ordre décroissant d'intérêt :
- **Priorité** (p ≥ 0,20) — en tête, dépliée.
- **À suivre** (0,10–0,20) — dépliée.
- **Sans signal** — repliée par défaut (compteur seul, dépliable).
- **Écartée** — repliée, séparée visuellement (terre éteinte), n'apparaît qu'au « voir pourquoi ».
Chaque en-tête de segment = libellé + compteur + définition (réutiliser `defTiers`, source unique). En option, un **second axe** dans chaque segment (chips filtrantes, non des sous-listes) : bâti / nu, PM / PP, événement, veille succession — les dimensions déjà portées par les badges. Le tri reste par rang à l'intérieur d'un segment.
Bénéfice : on lit d'abord les 114 Priorité + 631 À suivre (le gisement actionnable) sans les 280 658 « sans signal » qui noient la vue. **Aucune ligne de code écrite ; en attente de l'arbitrage de Vic sur l'axe (palier seul, ou palier × type).**

---

## Vérifications techniques
- Front : `tsc` 0 · `vitest` **198/198** (dont gardes neuves `Tip.test.tsx`, S8 dans `CourrierService.test.tsx`, S7 dans `test_exports2_lot6`).
- Back : tests ciblés verts (exports2, verdict, answering, RETOURS-12-A1 IA).
- 5 commits de code (Lot 1 `ded8e89f`, Lot 2 `019f3419`, Lot 3 `5214f1c6`, Lot 4 `4ac7fd36`, Lot 6 `efa5b850`) ; Lot 5 (S18–S23) = vérifications/réponses, sans code. Rien mergé, aucune bascule, aucun rescoring.
