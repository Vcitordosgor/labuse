# M40 — PHASE 0 · CONSTAT (confrontation GPU vs millésime mairie)

**Branche** `m40-confrontation-gpu-mairie` · base `main` c982f46d (M39 mergé) · **STOP obligatoire.**
**Nature : LECTURE SEULE.** Zéro écriture DB / run / config / src. Seuls fichiers nouveaux : `qa/m40/*`.
Golden, re-mesures M34/M35, SHA256 vigilances M37 : intacts par construction.

Tout ci-dessous est **vérifié sur pièces** (base `labuse`, run `q_v8_calibre`, `spatial_layers`
`plu_gpu_zone` = 5 848 zones, `config/plu_millesimes.yaml` = 24 communes). Le constat central
contredit la présomption du mandat, et c'est ce que la Phase 0 devait attraper.

---

## 1. Ce qui existe vraiment (Train 6 / M32)

- `config/plu_millesimes.yaml` : 24 communes, chacune `{idurba, date_mairie, statut}`. **idurba =
  référence du document MAIRIE** ; statut ∈ {`a_jour`, `annule_partiel`, `opposabilite_en_attente`,
  `rnu`}. Répartition : **20 a_jour · 2 opposabilite_en_attente (Saint-André, Saint-Leu) ·
  1 annule_partiel (Le Port) · 1 rnu (Saint-Philippe)**.
- `_plu_fraicheur(idu)` (`app.py:2039`) sert en fiche un objet `{idurba, horizon=date_mairie, statut,
  libelle, note}` — c'est l'écart de **DATE/STATUT** exposé aujourd'hui, **pas** une confrontation
  de contenus.
- Le zonage servi vient de `spatial_layers.plu_gpu_zone` (GPU), chaque zone portant son propre
  `attrs->>'idurba'` = le document GPU réellement ingéré.

## 2. Y a-t-il matière à confronter les CONTENUS ? — Non, et c'est le constat central

**Confrontation idurba GPU (spatial_layers) vs idurba mairie (config), par commune**
(`qa/m40/confrontation_gpu_mairie_p0.csv`) :

| Résultat | communes |
|---|---|
| **idurba GPU = idurba mairie** (document identique) | **23 / 24** |
| RNU (aucun zonage, honnête) | 1 (Saint-Philippe) |
| GPU sert un document ≠ mairie | **0** |
| résidu multi-idurba (hygiène de données) | 1 (Saint-Joseph) |

**Le GPU n'est PAS en retard sur les mairies au niveau document.** La campagne de ré-extraction
M32 (05/08) a déjà aligné chaque commune sur son document opposable. Détail des cas nommés au mandat :

- **Les 9 ré-extractions M32** (Saint-Louis, Petite-Île, Le Port, Sainte-Suzanne, Les Avirons, La
  Plaine, Sainte-Rose, Salazie, Bras-Panon) : **idurba GPU = idurba mairie** pour toutes → contenu
  déjà réconcilié, rien à opposer.
- **Le Port** (annulation limitée Uppp/Up2, TA 1900330 + CAA 22BX01470) : **correctement reflété** —
  les zones servies sont A/AUc/AUs/N/U, **AUCUN Uppp/Up2** (les zones annulées sont absentes). ✓
- **Saint-André (97409) & Saint-Leu (97413)** — statut `opposabilite_en_attente` : **le GPU HÉBERGE
  bien le document opposable** (97409_20190228 = 142 zones ; 97413_20070226 = 368 zones, ingérées
  2026-06). ⚠ **La note config « AUCUN document GPU en ligne » est FAUSSE sur pièces.** La réalité :
  LABUSE sert le PLU opposable (2019/2007), qui EST sur GPU et **fait foi aujourd'hui** ; c'est la
  RÉVISION en cours qui n'est pas approuvée (donc correctement non servie). Pas de divergence de
  contenu — une note à corriger.
- **Saint-Benoît (97410)** : config `a_jour` 2020 ; seul 97410_PLU_20200206 est ingéré. Les modifs
  n°2/n°3 évoquées ne sont **vérifiables par aucune donnée disponible** (ni GPU, ni source mairie
  exploitable) — voir §4.

## 3. Divergences réelles mesurées — quasi nulles au niveau contenu

- **Saint-Joseph (97412)** : seul cas de **résidu multi-idurba**. 3 zones stale (`97412_PLU_20240320`,
  subtypes A/N) subsistent à côté du document courant (`97412_PLU_20251210`, 343 zones). Elles
  touchent **1 671 parcelles — TOUTES également couvertes par le document courant** (0 servie par le
  seul stale). Vérifié : le subtype stale (A ou N) est **déjà présent dans le document courant** sur
  toutes les parcelles sauf 1 → **redondance sans contradiction de constructibilité**. Hygiène de
  données, pas une divergence GPU-vs-mairie.
- Partout ailleurs : **0 parcelle** servie avec un zonage contredisant le document opposable de la
  mairie. Il n'y a pas de population « à déclasser au vu de la source qui fait foi » — donc **rien
  pour le dossier du geste groupé** côté zonage (contrairement à M39).

**Exposition des statuts non-`a_jour`** (têtes servies, où la mention « vérifier en mairie » a du sens) :

| commune | statut | brûlante+chaude | réserve | lecture |
|---|---|---|---|---|
| Saint-Leu | opposabilite_en_attente | 82 | 369 | 2007 opposable, révision visée S2 2026 |
| Saint-André | opposabilite_en_attente | 30 | 273 | 2019 opposable, révision en cours |
| Le Port | annule_partiel | 25 | 40 | annulation hors zonage résidentiel |
| Saint-Philippe | rnu | 2 | 0 | RNU — aucun PLU (témoin honnêteté) |

## 4. Faisabilité & repli

**La confrontation de CONTENUS GPU-vs-mairie n'est pas faisable et n'a pas de substance
aujourd'hui**, pour deux raisons de fond :
1. **Il n'existe aucune source mairie de GÉOMÉTRIE** au-delà des dates/idurba de la config. On ne
   peut pas opposer parcelle par parcelle un « zonage mairie » à un « zonage GPU » : le seul zonage
   spatial disponible EST le GPU.
2. **Les documents coïncident déjà** (23/24 idurba identiques). Fabriquer une comparaison
   parcelle-à-parcelle produirait 0 divergence — une comparaison sans matière (le mandat l'interdit).

**Repli proposé (le plus utile avec les données réelles) :**
- **(a) Garde de cohérence idurba** — LA confrontation durable et vérifiable : opposer en continu
  `spatial_layers.idurba` (GPU ingéré) à `plu_millesimes.idurba` (référence mairie), par commune.
  Aujourd'hui elle **passe 23/24** et **signale Saint-Joseph** (résidu) ; surtout, elle **attrapera
  le jour où un vrai retard GPU-derrière-mairie apparaîtra** (nouvelle approbation non encore
  publiée au GPU). C'est « la détection de contradictions entre sources » du backlog, cadrée à ce
  qui a de la substance.
- **(b) Corrections config sur pièces** : reformuler la note Saint-André/Saint-Leu (le doc GPU EST
  présent → « révision en cours non encore opposable », pas « aucun document GPU ») ; nettoyer les
  3 zones stale de Saint-Joseph ; réexaminer le `a_jour` de Saint-Benoît (modifs n°2/n°3).
- **(c) Affiner l'exposition fiche** pour les 3 statuts non-`a_jour` : rendre explicite « quelle
  source fait foi » + action « vérifier le règlement en mairie » sur `opposabilite_en_attente`
  (déjà partiellement fait par Train 6 — à formaliser, sans jamais promettre).

## 5. STOP — arbitrages Vic

Le mandat interdit tout changement de tier ; ces arbitrages cadrent la Phase 1.

- **A. Périmètre servi.** Confirmes-tu que la confrontation de contenus GPU-vs-mairie **n'a pas de
  substance** (documents alignés, pas de géométrie mairie) et qu'on bascule sur le **repli (a)+(b)+(c)** ?
- **B. Garde idurba (a).** La retiens-tu comme livrable central (confrontation continue + healthz),
  plutôt qu'une fausse comparaison parcellaire ?
- **C. Corrections config (b).** Feu vert pour corriger la note Saint-André/Saint-Leu, nettoyer le
  résidu Saint-Joseph, et re-statuer Saint-Benoît — **écritures config/data hors scoring, 0 tier** ?
- **D. Saint-Benoît.** Faut-il chercher les modifs n°2/n°3 (hors open-data GPU → portail mairie/DEAL,
  hors périmètre auto) ou consigner l'incertitude en fiche (« modifications possibles — vérifier ») ?

**Ma recommandation : A (repli) · B (garde idurba) · C (corrections) · D (consigner l'incertitude,
ne pas fabriquer).** Aucune parcelle candidate au geste groupé côté zonage — le zonage servi = le
document qui fait foi, pour 23/24 communes.

---

## Annexes
- `qa/m40/confrontation_gpu_mairie_p0.csv` — les 24 communes : idurba mairie vs GPU, statut, match,
  résidu, têtes servies. `gen_confrontation_p0.py`. `_global.txt` (SHA256).
- Aucune écriture servie. Golden / re-mesures / vigilances M37 : non touchés (lecture seule).
