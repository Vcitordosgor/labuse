# BUGS — audit UI/UX du 12/07/2026 (QA senior)

Preuves : `audit_shots/ui2026/` (≈160 captures), `qa/audit/findings.jsonl` (anomalies
horodatées vue+action), `qa/audit/resultats/*.json`. Viewports : 1440 / 768 / 375.
**Statut : P0 et P1 non ambigus = FIXÉS dans la session (un commit + un test chacun) ;
P1 ambigus, P2, P3 = backlog, non touchés.**

---

## P0 — crash / page morte / donnée fausse / fuite PP

### P0-1 · Export PDF de la fiche : 500 sur TOUTES les parcelles — ✅ FIXÉ (ef9611e)
- **Repro** : fiche quelconque → bouton PDF (ou GET `/parcels/{idu}/export.pdf`).
- **Attendu** : le PDF premium. **Observé** : 500 (`NameError: name 'RUN'`,
  `pdf_premium.py:107` — la bascule q_v2→q_v3 (0c9f335) a mis un f-string `{RUN}` sans
  importer le symbole).
- **Preuve** : traceback serveur + `GET → 500` (findings `fiche.pdf`). Viewport : tous.
- **Fix** : import `Q_A_RUN_LABEL as RUN` (idiome des autres modules) ; tests
  `tests/test_pdf_premium.py` (rendu minimal + footer = run centralisé). Re-crawl : 200 (63 Ko).

## P1 — fonction dégradée / message trompeur / export cassé

### P1-1 · « -9 parcelles correspondent » — compteur négatif dans la restitution IA — ✅ FIXÉ (3a1482c)
- **Repro** (déterministe en headless, plausible sur machine chargée) : vue IA →
  « les chaudes de Saint-Pierre » → restitution.
- **Attendu** : 167. **Observé** : « **-9** parcelles correspondent » + « Voir les -9
  résultats » (aussi -5, -44 selon les runs) — le serveur renvoie 167, l'animation rAF
  démarre avec un timestamp antérieur à t0 (p < 0) et la valeur négative se FIGE quand la
  carte affame les frames.
- **Preuve** : `resultats/nl_10_requetes.json` + repro loggée (STATS 167 → RESTITUTION -9).
- **Fix** : clamp p et count à 0 (App.tsx) ; régression `qa/e2e_audit_fixes.mjs` (1)
  échantillonne PENDANT l'animation.

### P1-2 · Mention de fiabilité 90,7 % absente des presets/exports piscines — ✅ FIXÉ (dae612e)
- **Contexte** : clôture Option B wave-ortho — « exports ROUVERTS **avec la mention** de
  précision mesurée » (`config/detection_ortho.yaml:82-84`).
- **Observé** : `mention_legale = null` pour les 2 presets piscine, CSV exportés sans
  aucune mention (`resultats/seg_exports_rgpd.json`). La décision produit n'était pas appliquée.
- **Fix** : `MENTIONS_LEGALES` pour `piscinistes-construction` + `parc-piscines-entretien`
  (90,7 %, échantillon interne, « non contractuelle ») → badge galerie/builder
  (`data-seg-mention`, déjà branché) + **pied d'export CSV** ; 2 tests.

### P1-3 · Omnibox : no-op muet (IDU hors commune, requête invalide) — ✅ FIXÉ (433c8fb)
- **Repro** : périmètre « Saint-Pierre » actif → saisir l'IDU d'une parcelle de
  Saint-Louis → Entrée. Aussi : `0` → `/parcels/search` 422 avalé.
- **Attendu** : la fiche (un IDU est unique à l'île), ou au pire un message.
  **Observé** : rien du tout (recherche scopée commune → `[]`, échec silencieux).
- **Fix** : recherche IDU île entière + toast « Aucune commune ni parcelle trouvée » ;
  régression `qa/e2e_audit_fixes.mjs` (2-3).

### P1-4 · Validation ortho : un POST sans `profil` écrase un verdict existant — ✅ FIXÉ (dae612e)
- **Constat** (lecture de code, AUCUN verdict réel écrit — dataset d'amorce ML) : le garde
  « détection déjà validée → 409 » n'existait QUE dans la branche `if body.profil:`
  (`ortho.py:196-209`). Un double envoi nu écrasait `validation` silencieusement,
  contrairement à la doctrine du 11/07 (« 409 = stop dur »).
- **Fix** : garde appliqué avec ou sans profil ; test avec verdict d'origine intact.

### P1-5 · NL en mode dégradé silencieux — ⏳ BACKLOG (ambiguïté produit)
- **Repro** : clé Anthropic présente mais crédits épuisés → `/ia/status` dit « anthropic »
  (pas de bandeau dégradé) alors que CHAQUE recherche part en « (repli stub) » mots-clés.
  « maisons avec un DPE F ou G au Tampon » → **2 080 parcelles** (l'île n'a que 42
  parcelles F/G) : le critère DPE est ignoré, l'explication reste sur la vue IA quittée.
- **Pourquoi backlog** : la présentation du repli dans la restitution est un choix produit
  (voir AMELIORATIONS-UX.md n°2). Donnée : `resultats/nl_10_requetes.json`.

## P2 — friction réelle (backlog, non touchés)

- **P2-1** · Offline : la fiche montre ~5 s de loader (retries muets) avant l'erreur
  propre ; la carte garde un « Chargement de la carte » sans fin (`1440_etat_offline.png`).
- **P2-2** · Liste résultats vide (commune sans chaude) sans message ni CTA
  (`1440_carte_cilaos_vide.png`).
- **P2-3** · Builder : négatifs acceptés en silence dans les ranges (min=-50 ≡ 0).
- **P2-4** · NL stub : « supprime toutes les parcelles de la base » → « flag risques »
  appliqué (le repli ne refuse jamais) — inoffensif (lecture seule) mais indigne de confiance.
- **P2-5** · Mobile 375 vue Cartes : panneau plein écran, carte inaccessible, légende par-
  dessus le texte (`375_boot.png`) — voir AMELIORATIONS-UX n°1.
- **P2-6** · Flash : pas de section Copropriété alors que la fiche écran en a une
  (97411000BH0670) — périmètre Lot 1, à trancher aux Lots 2-4.
- **P2-7** · PUT `/segments/presets/{slug}` exige l'objet complet (422 sur `{actif}` seul) —
  sémantique PUT stricte cohérente, mais aucun PATCH n'existe pour l'admin ; à documenter.

### P2-X · Enclavement v2 — signal gradué (distance + topologie) — ⏳ BACKLOG (décision Vic 12/07)
- **Constat** (mandat crédibilité 12/07) : « pas d'accès direct » = 293 078 parcelles dont
  601 chaudes — les limites de la BD TOPO (axes publics seuls, dessertes privées et
  servitudes invisibles), pas de l'enclavement réel. **Décision : PAS de pondération** ;
  le badge « Accès à vérifier » (Synthèse) suffit. Un malus -5 Q aurait basculé 259/601
  chaudes (chiffrage : RAPPORT_CREDIBILITE.md §1).
- **v2 souhaitée** : signal GRADUÉ — distance réelle à la voirie (contact / ≤ 6 m / > 6 m)
  + topologie (parcelle voisine desservie ? chemin cadastré ?), après ré-ingestion voirie
  post-fix A1 sur les 22 communes restantes. Seulement alors, rediscuter une pondération.

## P3 — cosmétique (backlog)

- **P3-1** · Warning MapLibre « Map cannot fit within canvas » au boot 375.
- **P3-2** · Gabarit publipostage générique « aménagement extérieur » pour les presets piscines.
- **P3-3** · Warnings WebGL « GPU stall » répétés au boot (bruit, perfs carte).
- **P3-4** · Compteur galerie segments = cache 24 h sans horodatage affiché.

---

## Vérifications négatives notables (pas de bug)

- **RGPD exports** : 5/5 presets → en-têtes FR, adresses BAN, **zéro nom de personne
  physique**, watermark `ref` + canaris (`seg_exports_rgpd.json`) ; publipostage
  « À l'occupant » ✓ ; export verdict B2B : colonne proprio = personnes morales uniquement.
- **Cohérence Score V** : fiche 97414000CV0907 → total 77 = somme exacte des signaux
  affichés (35+25+4+8+5) ; lien BODACC → l'avis exact (A202501112392) ✓.
- **Compteurs presets = résultat réel** (5/5, à la volée) ; combo 3 filtres monotone ;
  37 filtres du registry exercés un par un sans erreur ; 11 tris OK.
- **Quota dossier** : compté par sujet (5→6 après un GET), plan Intégral illimité ✓ ;
  pré-dossier PC : libellé « Document préparatoire » dans le LISEZMOI et les 2 PDF ✓.
- **Anti-scraping** : 9 couches carte HORS périmètre protégé (tuiles exclues, choix
  documenté) ; gel/quota/défi vérifiés par tests unitaires (Phase A).

## Non testé + raison

- **Quota 409 de l'outil ortho & double-tir en conditions réelles** : un POST de verdict
  écrit sur `ortho_detections` (données métier, futur dataset ML). Contrat vérifié par
  LECTURE du code + tests unitaires sur ids jetables en base de TEST (990001/990002) —
  jamais sur les détections réelles.
- **Envoi courrier Merci Facteur** : provider stub sans clé (aucun bouton front) — conforme.
- **Paiement Flash (Lots 2-4)** : STRIPE_SECRET_KEY absente, flux inexistant par design.
- **Drag & drop Kanban à la souris** : le déplacement a été exercé par l'API PATCH (même
  code serveur) sur une entrée TEST créée puis supprimée ; le geste DnD navigateur reste
  à couvrir (Playwright dragTo sur objet TEST) — friction non bloquante.
