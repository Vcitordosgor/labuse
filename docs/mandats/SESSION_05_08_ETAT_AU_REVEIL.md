# ÉTAT AU RÉVEIL — session du 05/08/2026, post-M32 mergé (à lire en premier)

> Résumé pour la session neuve : ce qui SERT, ce qui est ACQUIS, ce qui RESTE. Écrit à la clôture
> de M32 (Train 6 — calibration), après bascule gardée, golden repassé, et merge --no-ff sur main.

## Le produit sert normalement — `q_v8_calibre`, basculé M32, conforme
Run servi = **`q_v8_calibre`** (re-scoré SOUS le même label à la bascule M32 ; `config/served_run.txt`
inchangé = point de vérité unique). Tiers servis :
**brûlante 119 · chaude 1041 · à-creuser 29 974 · réserve 2 964 · bâti saturé 29 907 · bâti révélé
4 051 · non-constructible 6 168 · zone fermée 2 804 · AU inconnu 210 · AU fermée 70 · écartée 354 355**
(= 431 663). Golden **117/117** (face DB, ancre AT2542 = brûlante). **Base saine, rien en suspens.**

Filet de rollback : **`q_v8_calibre_pre_m32`** (état pré-M32, 431 663 lignes, intact — renommer en
sens inverse pour revenir). Référence de mesure : **`q_v13_m32_mesure`**. Registre servi
(`served_run_exceptions`, 5 entrées) : AK1442 + AL1154 piscine → a_creuser ; AP0323 / HE0234 / AT0870
documentaires (tier inchangé, motif tracé).

## ACQUIS (mergé / actif)
- **Intégration AU 21 communes — SERVIE.** `build_au_ouverture` (lit `config/calibrage/au_ouverture_
  planchers.yaml`) est le SEUL bon levier. Config corrigée : `defaut: conditionnelle_operation` +
  `"2AU": conditionnelle_etat_tiers` explicite (le bug `defaut: conditionnelle_etat_tiers` déclassait
  les 1AU qui ouvrent par opération — 2000 au lieu de 810). Planchers réels sur Saint-Leu,
  Trois-Bassins, L'Étang-Salé (min_log + densité). **HORS PLU outillé** : Saint-André (opposabilité en
  attente), Saint-Benoît (v2 à venir), Saint-Philippe (RNU).
- **Fraîcheur GPU-vs-mairie — SERVIE en fiche.** `config/plu_millesimes.yaml` (24 communes, idurba +
  date_mairie + statut) ; `_plu_fraicheur(idu)` dans app.py sert `plu_fraicheur` en fiche (horizon =
  date mairie, écart exposé ; Saint-André = étiquette « opposabilité en attente »). Infra millésime
  amont : 4 colonnes `data_sources`, `persist_millesime`, `check_fraicheur` (garde bruyante non
  bloquante), `_fraicheur_couche` structuré dans `modules.py`.
- **SDP bâties révélées — CORRIGÉE (fiche).** `residuel.py` : `emprise_batie` retient la mesure la
  plus grande entre BD TOPO et **CoSIA (`parcel_bati_revele`)** → 8 031 bâties révélées ne s'affichent
  plus « terrain nu » mais « bâtie à ~N % ». Cache isolé du scoring, **0 impact tier** (ces parcelles
  sont déjà déclassées `declasse_bati_revele`).
- **9 ré-extractions PLU (Phase A)** ancrées sur version OPPOSABLE (idurba + date) : Saint-Louis,
  Petite-Île, Le Port (annulation LIMITÉE Uppp/Up2, AU intactes — jugement TA 1900330 + CAA 22BX01470),
  Sainte-Suzanne, Les Avirons, La Plaine, Sainte-Rose, Salazie (densité 20/20/10 levée), Bras-Panon.
  Salazie entièrement outillée (441 servies, 4 têtes, 0 hors-PLU).
- **`scripts/bascule_m32.py`** = geste gardé de référence (rebuild cache AU, archive par renommage,
  re-score sous label, conformité STRICT vs mesure, registre par boucle générique, 6 gardes +
  check_fraicheur, golden régénéré dans le geste via `qa/golden_regen.py`). Bilan : `qa/m32/M32_BASCULE_BILAN.md`.

## RESTE (session neuve, à froid)
- **Dette #14 (double-rail verdict/tier) — MANDAT DÉDIÉ AVANT LE PREMIER CLIENT.** Le moteur verdict
  de fiche (`score_e`) déclasse le bâti marginal en logique pré-M28, désaligné du tier servi. Symptôme :
  **CY0197** servie `brûlante` (bâtie 22 % + divisible R+2, résiduel 194 m², étage 3) mais dont la
  synthèse de fiche affiche `À creuser`. Correction = aligner le verdict sur le **filtre 3 étages**
  (étage 3 divisible = servable → badge « bâtie + division possible », pas de déclassement silencieux).
  Périmètre : TOUS les bâtis marginaux/divisibles.
- **Dette #13 (piscine)** : signal piscine porté au registre parcelle par parcelle (a_creuser), pas
  encore une règle produit. Manquant nommé : couche piscine surfacique + seuil.
- **Site marketing + perf + gelés** (section BACKLOG) : split app/marketing · chiffres post-M32 sur la
  vitrine (source = run servi, jamais figés) · Lighthouse · **MoteurImmo GELÉ** · reco Urbanease ·
  **Saint-Paul référence à déclarer close**.
- **Train 8 — VPS / production** (dernier avant client) : déploiement Caddy + certs + SECRET_KEY,
  licence nominative, Stripe live, vitrine labuse.immo.
- **Vic seul** : réponse mairie Saint-André (opposabilité) → réintégration ; Saint-Benoît modifs n°2/n°3
  → v2 AU ; avocat CGU/CGV.

## Les arrêts de la session (chacun aurait coûté cher)
1. **Mauvais writer AU** — `build_au_statut_batch` (lit `plu_<commune>.yaml`) ≠ `build_au_ouverture`
   (lit `au_ouverture_planchers.yaml`). Deux writers sur `parcel_au_statut` ; le bon levier pour
   l'ouverture = `build_au_ouverture`. Rebuild avec le mauvais → générique montait à tort.
2. **Sur-déclassement 1AU** — `defaut: conditionnelle_etat_tiers` déclassait les 1AU (qui ouvrent par
   opération). Corrigé `conditionnelle_operation` + `"2AU"` explicite. C'est ce que la mesure à blanc
   a attrapé (2000 → 810 en cache, 560 → 210 en tier).
3. **Dry-run avant archive** — conformité `rebuild=False` vérifiée AVANT d'archiver quoi que ce soit
   (0 écart vs mesure) → aucun demi-état possible si la bascule diverge.

## Pièges consignés
- **Golden regen dans le geste** : `qa/golden_regen.py` (pas `golden_check --dump` nu, qui retombe sur
  32 GOLDEN_IDUS et PERD les 84 ancres J3). Garde #6 `check_golden_regenere` refuse une bascule dont
  le golden ne cite pas le run servi.
- **Bascule = re-score SOUS label** (archive par renommage `_pre_<geste>`), conformité STRICT vs la
  mesure ; les SEULS écarts admis = le registre. Tout écart non listé au recompte = rollback.
- **Env** : `/Users/openclaw/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src` (pas de venv local,
  checkout frère `labuse`) ; DB `psql -d labuse` ; API `uvicorn ... --port 8010` avec
  `LABUSE_M28_BADGES=1 LABUSE_SERVED_RUN=q_v8_calibre LABUSE_DEV_MODE=1` ; golden via
  `LABUSE_API_BASE=http://127.0.0.1:8010` = 117/117 ; deck via `qa/dette4/print_pdf.mjs` depuis frontend/.

*Branche : `m32-train6-calibration` (commits a58fc7d bascule + 6ce1d21 clôture), mergée --no-ff sur
main. Gouvernance permanente (régimes [S]/[A]/[M], BACKLOG, fraîcheur amont, un point de calcul unique,
le doute ne profite jamais au classement) en mémoire.*
