# M22 — LES TROIS EXPORTS QUE PERSONNE NE FAIT · RAPPORT FINAL

Mandat autonome, base `main` 8feea8b (M12→M21 mergées). **CC ne merge pas** — 5 branches
poussées, non mergées. Golden 116/116 par lot (`LABUSE_DEV_MODE=1`, instance locale :8022),
jamais réparé. Modèle P gelé (aucun lot ne touche au scoring). Filet : tag `avant-m22`
(posé par Vic sur e11f920 = main + audit préparatoire ; constaté en place, non déplacé).
L'audit `docs/mandats/M22_AUDIT_PREPARATOIRE.md` a fait foi (branche `docs/m22-audit-preparatoire`).

## 0. Branches et ordre de merge

| Lot | Branche | Commit | Basée sur |
|---|---|---|---|
| 0 briques | `refactor/m22-0-briques` | c1368ca | main |
| A foncier max | `feat/m22-a-foncier-max` | 1d20896 | 0 |
| B lettre zonage | `feat/m22-b-lettre-zonage` | 20a2a34 | 0 |
| C argumentaire | `feat/m22-c-argumentaire` | e5f22ae | A |
| D potentiel | `feat/m22-d-potentiel` | abc9516 | C |

**Ordre de merge Vic (`--no-ff`) : 0 → A → B → C → D** — conforme au mandat. B est basée
sur 0 (elle n'a pas besoin de A) ; C sur A ; D sur C. **Conflit attendu UNIQUE et trivial :
`app.py`** au merge de C après B (B ajoute l'import/include `lettre_zonage` près de
`banquier`, C ajoute `argumentaire` près de `carnet` — zones distinctes, résolution
évidente ; D ajoute `potentiel` juste sous `argumentaire`, dans C's sillage).

## 1. Preuves par lot

### LOT 0 — Briques communes (`refactor/m22-0-briques`)
- `api/briques_pdf.py` : CSS print, helpers Sourcé/Estimé/€, `collect()`, carte IGN,
  sections cover/identite/faisabilite/bilan/comparables/risques, `render_pdf()` — extraits
  de `banquier.py` (543 l. → le Banquier ne garde que libellé, synthèse IA, endpoints+cache).
- **PDF Banquier avant/après : 6 pages PIXEL-IDENTIQUES à 150 dpi** (`qa/m22/0/` :
  2 PDF + `diff_pdf.py` rejouable + rendus p1 ; synthèse IA neutralisée pour le déterminisme,
  harnais auto-validé par un run-à-run identique).
- Tests banquier adaptés au module partagé (mêmes garde-fous) : 42/42 ciblés.

### LOT A — Inversion de la calculette (`feat/m22-a-foncier-max`)
- `compute_calculette(mode="achat_max")` : le prix d'achat max **EST** la charge foncière
  supportable — identité arithmétique, aucun second moteur ; le mode ajoute la dérivation
  ligne à ligne (`steps`, du prix de sortie DVF au foncier) et l'**écart de négociation
  demandé − max** (`demande_moins_max_eur`, `sens` = surcout/marge : champs auto-porteurs,
  pas de signe ambigu). Réponse historique STRICTEMENT inchangée en mode `charge`.
- `POST /faisabilite/{idu}/charge` : champ `mode`. UI fiche : bascule segmentée discrète
  « Charge supportable / Prix d'achat max » dans la calculette du tiroir Faisabilité.
- **Preuves `qa/m22/a/`** : 97415000ET1659 (CF +3,22 M€, prix fiable) — JSON forward vs
  inverse **identiques**, capture UI des 2 modes, écart rendu en clair :
  « prix demandé 4,0 M€ − prix d'achat max 3,2 M€ = **surcoût de 782 k€ (+20 %)** ».
- Tests +4 (identité, dérivation, sens de l'écart, prix insuffisant → pas de faux chiffre).

### LOT B — Lettre de vérification de zonage (`feat/m22-b-lettre-zonage`)
- `api/lettre_zonage.py`, `GET /lettre-zonage/{idu}.pdf`, 3 pages sur briques.
- **Règle d'or codée ET testée : une règle sans article ne s'imprime pas.** `a_verifier` →
  « à vérifier — règlement ambigu » ; zone non calibrée → repli honnête GPU ; servitudes =
  couches EN BASE uniquement (« ne vaut pas état exhaustif » / « ne vaut pas absence »).
- Accès : bouton discret dans le tiroir « Règles d'urbanisme » — **la barre M20 reste à
  7 tuiles** (le diff ne la touche pas).
- **Preuves `qa/m22/b/`** : BV1193 (U6c, simple) et DK1169 (AU2h+N, 10 risques dont PPR,
  ABF — servitudes multiples), PDF + rendus + capture bouton. Tests 8/8.

### LOT C — Argumentaire de négociation (`feat/m22-c-argumentaire`)
- `api/argumentaire.py`, `GET /argumentaire/{idu}.pdf?prix_demande_eur&cout_construction_m2&marge_frais_pct`
  (défauts = calculette M15-C2), 6 pages : synthèse (écart en clair) · marché DVF (fiabilité
  affichée telle quelle, neuf/ancien) · faisabilité (articles) · réductions de CAPACITÉ ·
  bilan à rebours ligne à ligne (trace M22-A) · vigilance qualitative · sources.
- **Doctrines Vic codées ET testées** : le mot « décote » n'apparaît nulle part ; les
  modulations sont des réductions de capacité (la doctrine est énoncée DANS le document) ;
  la section vigilance ne contient AUCUN € ; ton neutre (« pour tout acquéreur »),
  montrable au vendeur.
- UI : lien discret sous la calculette en mode « Prix d'achat max », mêmes hypothèses.
- **Preuves `qa/m22/c/`** : ET1659 avec prix demandé 4 M€ > max (écart +782 k€/+20 % rendu
  p.1 et p.4) et sans prix demandé. Tests 6/6.

### LOT D — Rapport de potentiel (`feat/m22-d-potentiel`) — CONDITIONNEL
- **Condition constatée NON remplie** : aucune trace de validation de la revue visuelle des
  20 cartes O12 par Vic (`docs/mandats/O12_DIVISION_OR_REVUE.PDF` en attente, OUTILS_SUITE
  §O12). Conformément au mandat : le rapport sort **SANS divisibilité chiffrée**, encadré
  « Analyse de divisibilité : disponible sur étude complémentaire » (aucun chiffre — testé),
  **`EXPOSE` reste False** (non touché — testé).
- `api/potentiel.py`, `GET /rapport-potentiel/{idu}.pdf` (IDU seul), 5 pages accessibles :
  3 verdicts (Extension / Division / Points d'attention) · extension = SDP autorisée −
  existante = restante (`residuel.py`), incertitude dite (« ESTIMATION sur la base d'un
  bâti de N niveau(x) » quand la hauteur manque — à Saint-Paul le LiDAR fournit la hauteur
  réelle, bannière absente à juste titre ; le rendu du caveat est verrouillé par test) ·
  avant compromis · marché · limites (ni avis de valeur, ni arpentage).
- **Interdits testés** : aucune identité de propriétaire ; aucune valorisation € de la division.
- **Preuves `qa/m22/d/`** : AC0197 (cas type : ~1 059 m² restants) et BN1253
  (« Pas de potentiel d'extension identifié » — un résultat honnête est un résultat).
  Tests 7/7.

## 2. Textes des encadrés de limites (relecture Vic)

**Lettre de zonage (encadré §5)** :
> Cette lettre reflète les documents d'urbanisme tels que numérisés à la date d'édition.
> Elle ne constitue pas un certificat d'urbanisme au sens de l'art. L.410-1 du code de
> l'urbanisme, seul opposable. La taille minimale de lot n'est pas une donnée modélisée :
> non vérifiée.

**Lettre — pied de page** :
> Lettre de vérification de zonage établie à partir des documents d'urbanisme tels que
> numérisés (GPU / PLU calibré LABUSE) — ne constitue pas un certificat d'urbanisme
> (art. L.410-1 du code de l'urbanisme). À vérifier en mairie.

**Argumentaire — pied de page** :
> Argumentaire de négociation établi à partir de données publiques (cadastre, DVF, PLU) et
> des hypothèses saisies — estimation indicative, ni un prix ni une promesse ; ne vaut pas
> conseil. À vérifier par l'acquéreur et ses conseils.

**Argumentaire — phrase de synthèse (gabarit)** :
> Au regard des règles applicables (zone X) et du marché observé (N ventes DVF, fiabilité F),
> la charge foncière supportable — ce que l'opération peut payer le terrain — s'établit
> entre X et Y € (médiane Z, selon les hypothèses de coût et de marge rappelées en partie 5).

**Rapport de potentiel (encadré §6)** :
> Ce rapport n'est ni un avis de valeur, ni un document d'arpentage, ni un certificat
> d'urbanisme. Les surfaces constructibles sont des indications issues des règles numérisées
> et du bâti cartographié ; lorsque la hauteur du bâti n'est pas connue, la surface existante
> est une estimation — c'est alors écrit en clair. Aucune valorisation en euros d'une
> division n'est avancée.

**Rapport de potentiel — encadré division (O12 fermé)** :
> Analyse de divisibilité : disponible sur étude complémentaire. La faisabilité d'une
> division (taille minimale éventuelle, accès et façade du lot, reculs, servitudes) relève
> d'une étude réglementaire et d'un géomètre-expert — aucun chiffre n'est avancé ici.

## 3. Où brancher les quotas (rapport seul, rien de codé)

Modèle existant : `api/dossier.py:77-111` — `plans.acces("dossier_parcelle")` (403 avec
`plans.refus(...)` explicite, M21-C) + décompte `usage_compteurs` (Essentiel 20/mois,
Intégral illimité). Les 3 nouveaux endpoints sont aujourd'hui **sans gate** (même statut que
l'export fiche). Branchement proposé, à arbitrer :
- `lettre_zonage_pdf`, `argumentaire_pdf`, `rapport_potentiel_pdf` : ajouter le même couple
  `plans.acces(...)` + compteur, soit sous la clé `dossier_parcelle` (mutualisé), soit sous
  une clé produit par export si la tarification à l'unité (modèle Flash 79 €) est retenue —
  la tarification est HORS mandat M22.

## 4. Non fait / bloqué / à savoir

- **LOT E (vérif sur main)** : à dérouler APRÈS merge Vic — reboot, régénération des 4 PDF
  (Banquier inclus), golden, non-régression du tiroir Faisabilité (la calculette a changé).
- **Divisibilité chiffrée (LOT D)** : conditionnée à la revue Vic des 20 cartes O12 ;
  le jour venu → commit dédié `EXPOSE=True` + compte-rendu en docs/ + section chiffrée
  (« indicateurs favorables à une division », jamais une division de droit).
- **Bannière « ESTIMATION » du LOT D** : non déclenchable sur les parcelles de preuve
  (LiDAR Saint-Paul = hauteurs réelles) — rendu verrouillé par test unitaire.
- **Argumentaire — libellé de zone** : `zone_resolue` verbeuse (renvois « AU2c → règles de
  U2c (…) ») tronquée au code dans la phrase de synthèse ; le détail vit en partie 3.
- **⚠ Sessions concurrentes dans le même working tree** (à signaler à Vic) : pendant M22,
  deux autres sessions ont travaillé dans le dépôt local. (1) `docs/scoring-spec` : mon
  commit LOT 0 a atterri sur cette branche (HEAD déplacé sous mes pieds) → réparé par
  cherry-pick (c1368ca), `docs/scoring-spec` restituée à b9439b7 (= son état poussé), la
  branche `refactor/m22-0-briques` a été re-poussée correcte. (2) Mandat « M-RENOUV »
  (`feat/renouv-a-segment`) : a stashé mes modifs LOT C en cours (message de stash
  explicite) → récupérées par `git stash pop`, rien de perdu. Mes commits portent une
  garde `[ branche == attendue ]` depuis l'incident. **Recommandation : un seul mandat
  actif par clone, ou des clones séparés.**
- Échecs pytest préexistants sur main (inchangés par M22) : 9 × `test_front_reliquats` +
  `test_auth::test_local_par_defaut_tout_ouvert` (flaky en suite complète uniquement).
- Pièges rejoués : URL DB `postgresql+psycopg://` (psycopg3) ; `qa/node_modules` = symlink
  local vers `frontend/node_modules` (non commité) pour Playwright.

## 5. Chiffres de fin

- Suite sur la chaîne D (0+A+C+D) : **1143 verts**, 10 échecs = les mêmes que main.
- Golden : **116/116 à chaque lot** (0, A, B, C, D).
- tsc 0 · build front OK (lots A, B, C ; D sans front).
- 25 tests neufs (4 bilan inverse, 8 lettre, 6 argumentaire, 7 potentiel) + banquier adapté.
