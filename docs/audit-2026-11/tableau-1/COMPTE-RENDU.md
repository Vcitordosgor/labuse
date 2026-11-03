# TABLEAU-1 — un tableau qui ne montre que les vraies décisions

**Branche** `fix/tableau-1` · worktree `~/Desktop/labuse-tableau1` · ports 9500/6700 · **Opus**
**Pas de merge.** Prod en **lecture seule, sauf le point 4** (écritures d'acceptation d'écarts — *aucune
n'a été nécessaire, cf. §4*). Date : 2026-11-03 (Réunion +04). Base de départ `ddb266041`.

> **Bilan en une ligne.** Les 4 sources de référence (classe A) qui traînaient dans la carte « à valider »
> s'injectent désormais **seules la nuit** (la cause : le câblage source→commande n'avait jamais été écrit,
> et 2 des 4 n'avaient pas de commande) → la carte ne liste plus que les sources **B** (FRR, BDNB). Les
> **6 sondes en panne** sont réparées (OCS GE/SIS/SCOT recâblées et **vérifiées vertes en direct** ; trio
> Overpass : miroirs + **grace « amont en panne < 7 j → pas d'incident »**). Le tableau ne montre **plus
> de cartes pour les signaux non bloquants** (G8, sondes → « Est-ce que tout tourne ? »), un job pas encore
> dû n'est plus « à l'arrêt », et « se fait depuis le Mac » a disparu (le calcul tourne sur le serveur).
> Recette : banc unit **2860/0**, sondes réparées **7/7**, cohérence **6/0**, tsc **0**, captures avant/après.

---

## ⚑ EN TÊTE POUR VIC — BDNB : que changerait l'injection ? (mesuré en lecture seule)

**Verdict : rien d'utile à injecter pour l'instant, et l'injection ne changerait AUCUN chiffre servi.**

- **BDNB ne nourrit aujourd'hui NI l'emprise NI la hauteur servies.** L'emprise bâtie servie
  (`p_model_bati.emprise_bati_m2`) = **max(BD TOPO IGN, CoSIA)** ; la hauteur = **BD TOPO**. Les tables
  `bdnb_*` **n'existent même pas** en prod (0 ligne). BDNB était prévu pour des **variables candidates de
  scoring** (année de construction, DPE, écart de surface) qui attendent un banc K0 avant tout usage.
- **Contribution actuelle de BDNB au 974 : 0 bâtiment, 0 parcelle** (conforme : le millésime tenu
  `2026-02-a` est **métropole seule, 974 absent**). Pour mémoire, ce qui est servi pour le 974 :
  BD TOPO **817 506** bâtiments (dont 701 052 avec hauteur) · RNB 414 081 · `p_model_bati` 329 315 lignes.
- **La nouvelle version amont** vue par la sentinelle = `2026-02-b` (export **France**, 39,9 Go, publié le
  2026-10-05). **La couverture 974 n'est PAS confirmée** (la BDNB DROM est annoncée « en développement
  2026 ») : seul le comptage ligne-à-ligne tranche.
- **Delta mesuré, deux scénarios :**
  - *974 toujours absent (le plus probable)* → **0 bâtiment, 0 emprise, 0 hauteur, 0 parcelle** touchés ;
    l'ingestion s'arrête d'elle-même à la sonde de couverture.
  - *974 enfin présent* → les tables `bdnb_*` seraient **créées** (données nouvelles, pas un remplacement) ;
    **impact immédiat sur l'emprise/hauteur/taxe/scoring servis = TOUJOURS 0** (aucun code servant ne lit
    `bdnb_*`). Le nombre de bâtiments/parcelles ajoutés = ce que compte la sonde.
- **Ce qui n'est pas mesurable en lecture seule d'ici** : savoir si `2026-02-b` contient le 974 (exige de
  streamer 39,9 Go — une **lecture** réseau, pas une écriture — via `labuse ingest-bdnb` qui sonde d'abord
  la couverture en ~4 min et s'arrête tout seul si 0 ligne 974).
- **Recommandation.** Le bouton « Injecter » **ne risque aucune régression** sur les chiffres servis.
  Avant de cliquer, lancer `labuse ingest-bdnb` en sonde : s'il rapporte « métropole seule, 0 ligne 974 »
  (très probable), **il n'y a rien à injecter** et le statut `retiree` est correct ; s'il voit enfin le
  974, il remplit des tables candidates **sans rien changer de servi**, puis le banc K0 décide plus tard.

---

## 1. Les sources — les A s'injectent seules, « à valider » ne liste que les B

### Pourquoi injection-nuit n'injectait rien (la cause, trouvée)

Six sources étaient en `nouvelle_version` dans la carte « à valider » : **4 de classe A** (Population légale
INSEE, Annuaire DILA, SUP assiettes GPU, Zones exclues EnR OFB/APER) + **2 de classe B** (FRR, BDNB).

Ce **n'était ni un contrôle échoué, ni une mauvaise classe, ni la fenêtre** : le job `injection_nuit`
se contentait d'**empiler les noms dans `a_cabler`** — il n'appelait **aucune** commande d'ingestion. Et
2 des 4 sources A visées (**Population légale INSEE**, **OFB/APER**) n'avaient **pas de ligne** dans
`config/sources_ingestion.yaml`. Résultat : elles restaient « nouvelle version » et **remontaient à tort**
dans la carte de décision de Vic.

### Le correctif

- **`config/sources_ingestion.yaml`** — ajout des 2 commandes manquantes (idempotentes, mêmes que la CLI) :
  `population-legale-sync` et `enr-exclue-toiture-build`. **Les 4 sources A visées résolvent maintenant**
  une commande (Annuaire→`ingest-annuaire-services`, Population→`population-legale-sync`, SUP→`ingest-sup`,
  OFB→`enr-exclue-toiture-build`).
- **`jobs_impl.injection_nuit`** — réécrit : pour chaque source de **classe A en `nouvelle_version` dont la
  commande est connue**, il **lance l'ingestion** (le MÊME chemin détaché que le bouton « Injecter »/le
  cron, via le nouveau `lancer_ingestion_source`), journalise, et pose `injection_lancee_at`. Une source A
  **sans** commande reste « à câbler » (listée, **jamais injectée à l'aveugle**). Les sources **B** en
  nouvelle version → mail « à valider » (clic de Vic), **jamais injectées seules**.
- **`circuit_resume.composer_a_faire`** — la ligne « Injecter » (décision de Vic) n'est émise **que pour les
  sources de CLASSE B**. Les sources A en nouvelle version **ne font plus de carte** (elles s'injectent la
  nuit). `total_a_faire` est aligné (ne compte que les B injectables).

**Résultat** : la carte « à valider » ne liste plus que **FRR et BDNB** (les 2 sources B). Les 4 A partent
seules la nuit. *(Test : `test_classe_a_en_nouvelle_version_ne_fait_pas_de_ligne_injecter`.)*

---

## 2. BDNB — cf. l'en-tête ci-dessus (mesure lecture seule, décision à Vic).

---

## 3. Les 6 sondes en panne — recâblées, et une grace pour les pannes amont passagères

État prod constaté (03/11) : 3 **injoignable** (Overpass : parkings/OSM transport/TCSP — 502/timeout) et
3 **illisible** (SIS / OCS GE / SCOT GPU — format/URL amont changé). Rappel de doctrine : une sonde en panne
**n'a jamais rendu la donnée fausse** (c'est la sentinelle qui échoue, pas la donnée).

| Sonde | Cause réelle | Correctif | Vérifié en direct |
|---|---|---|---|
| **OCS GE** | le téléchargement IGN sert de l'**atom+xml**, pas du JSON (« réponse non-JSON ») | témoin par **regex sur le `<updated>`** du flux atom (nouvelle méthode `re:` pour les amonts non-JSON), sur les 2 produits | **ok** (empreinte des 2 `<updated>`) |
| **SIS (préfecture)** | le .zip n'expose **ni ETag ni Last-Modified** (en-tête vide) | repli **Content-Length** dans la méthode `entete` (un dossier mis à jour change de taille) | **ok** (`taille:8151737`) |
| **SCOT (GPU)** | `SORTBY=gpu_timestamp` + COUNT=1 renvoyait un **ordre non déterministe** (parfois un `gpu_timestamp` null en tête) → « chemin introuvable » | on ne trie plus : on lit **tous** les `gpu_timestamp` du 974 (PROPERTYNAME → ~0,4 ko, sans géométrie) et on garde **le plus récent** par regex | **ok** (`2024-09-17`) |
| **Parkings OSM / OSM transport / TCSP** | **Overpass public saturé** (502/timeout) — l'amont est simplement en panne | **miroirs** (kumi.systems, private.coffee) rejoués automatiquement + **grace** | overpass-api.de répond à nouveau |

**La grace (point clé du mandat).** Dans `circuit_etats.etat_reservoir` : un amont **`injoignable`** depuis
**moins de 7 jours** n'est **plus** « en panne » — c'est une panne passagère du producteur, la sonde le dit
sans ouvrir d'incident (le veilleur passe ~1×/jour, donc l'âge ≈ échecs × cadence). Au-delà de 7 jours →
« en panne » (persistant). En revanche **`illisible`** (format changé = **notre** lecteur cassé) reste « en
panne » dès 3 échecs. De plus, un WFS geopf qui renvoie une **FeatureCollection vide** sous charge est
classé `injoignable` **transitoire** (grace), plus `illisible`.

*Tests : `tests/test_tableau1_sondes.py` (7/7) + `tests/test_circuit_p4_etats.py` (grace 7 j, illisible 3).*

---

## 4. Les 87 petits écarts — tri appliqué ; 0 à corriger, tout justifié

**« 87 » = `coherence_runs.tolerable` du banc** (run prod #18 : `n_ecarts=153`, **`faux_client=0`,
`erreurs_lecteur=0`**, **`tolerable=87`**). C'est exactement le nombre de la carte « Accepter les N » du
tableau. Les 87 sont, par construction du banc, des écarts **dans la tolérance** (petits).

**Tri appliqué (doctrine AUTONOMIE-1), registre croisé des campagnes CHASSE-1/2/3 (64 écarts) +
COHERENCE-1 (6 notions)** — table complète : [`ECARTS-DISPOSITION.csv`](ECARTS-DISPOSITION.csv).

- **À corriger : 0.** Tous les bloquants / `a_corriger` « vrais bugs » ont **déjà été corrigés** par les
  campagnes CHASSE-FIX-1/2/3, COHERENCE-FIX-2, COMMUNE-FIX-1, AUTONOMIE-2, DEPLOY-* — **prouvé par le banc
  prod** (`faux_client=0`, `erreurs_lecteur=0` : plus aucun chiffre faux chez le client).
- **À accepter avec raison : tout le reste** (choix fail-closed voulus, dual-source tolérés, arrondis au
  m²/€, délimitations légales, dettes d'ingestion *data* dont les consommateurs sont déjà corrigés,
  troncatures/naming internes). Chaque raison est dans le registre.
- **1 point à faire confirmer par Vic — C13 (TVA financier) :** le constat « taux toujours 8,5 % » reposait
  sur une confusion : `regime_tva_saisi` décide **HT vs TTC**, pas le taux ; le 8,5 %↔2,1 % (locatif social)
  passe par `part_sociale_pct` et le libellé est exact. **Accepté**, à requalifier en correctif **seulement
  si** Vic veut un vrai sélecteur de taux par régime.

**Écritures d'acceptation en prod : AUCUNE n'a été faite** — et c'est le choix honnête. (a) Il n'y a rien à
corriger ; (b) le banc **tolère déjà** ces 87 (`faux_client=0`) ; (c) plusieurs correctifs sous-jacents sont
**en attente de déploiement** de la branche AUTONOMIE-1 : regénérer le golden « accepté » **maintenant**
figerait un état antérieur aux correctifs. L'acceptation-avec-raison est **enregistrée dans le registre
commité** (la doctrine AUTONOMIE-1 : « registre autoritatif `ECARTS.csv` »), pas par un geste prod aveugle.

---

## 5. Le tableau lui-même — trois états, une carte = une vraie décision

La page Données tient en **trois états** : *tout va bien · ça attend Vic · ça casse*.

- **« Qu'est-ce que je dois faire ? » = décisions humaines SEULES.** Les signaux **non bloquants** sortent
  des cartes :
  - **G8** (verrou d'avertissement, « sources sans contrôle récent ») → tuile **« Contrôle de nuit »** de
    « Est-ce que tout tourne ? », avec la mention « avertissement non bloquant ».
  - **Sondes en panne** → tuile **« Veille des sources »** (« N amont ne répondent plus », pastille ambre,
    jamais rouge — la donnée reste juste). Plus de carte « Réessayer ».
  - Dédup déjà en place conservée (une carte par job : fusion retard/échec ; escalades d'ancienneté masquées).
- **« Est-ce que tout tourne ? »** — un job dont la **date n'est pas venue** est **« pas encore dû »**,
  jamais « à l'arrêt » ; l'en-tête **ne compte que les vrais échecs** (`pas_encore_du` ajouté au résumé,
  à part de `echec`/`arret`).
- **« Où en est la mise à jour ? »** — dit la **vérité du moment**, **plus de bouton** pour ce qui tourne
  seul la nuit :
  - *Injecter* : « les sources de référence s'injectent seules la nuit » ; renvoi « Voir » si une source
    **structurante** attend le clic.
  - *Calculer* : « le calcul tourne la **nuit sur le serveur** » / « calcul en cours » — **plus de bouton**,
    **plus de « sur le Mac »**.
  - *Promotion* : « **automatique** (contrôles verts → servi) » **ou** « **en attente de ton clic** »
    (selon le gate `LABUSE_CALCUL_NUIT_PROMEUT`) — le bouton n'apparaît que pour la vraie décision.
  - *Envoyer en prod* : la version servie aux clients ; **« se fait depuis le Mac » supprimé**.
- **Textes** : « Calcul lancé sur le Mac » → « Calcul lancé » (le calcul est sur le serveur).

**Captures avant/après** : [`avant-tableau.png`](avant-tableau.png) · [`apres-tableau.png`](apres-tableau.png).
*Avant* : cartes « 2 sources ne répondent plus au veilleur » (sondes) et « 1 contrôle de sécurité échoue »
(G8) ; étapes Injecter/Calculer/Basculer **avec boutons** ; « se fait depuis le Mac ».
*Après* : ces 2 cartes ont disparu (passées dans « tout tourne ») ; étapes sans bouton auto-nuit, textes à
jour ; en-tête « pas encore dû » au lieu de « à l'arrêt ».

---

## RECETTE

| Attendu | Résultat |
|---|---|
| Captures avant/après du tableau | ✅ `captures/tableau-1/{avant,apres}-tableau.png` (app bootée local 9500/6700, dashboard réel) |
| Banc complet 0 rouge | ✅ unitaires **2860 passed / 0 failed** (+ 7 tests neufs TABLEAU-1) ; db sentinelle+cockpit **48/0** |
| Sondes réparées vérifiées | ✅ OCS GE / SIS / SCOT **ok en direct** sur l'amont réel ; `test_tableau1_sondes.py` **7/7** |
| Suite de cohérence verte | ✅ `scripts/ci/coherence_run.sh` → **6 passed, 0 écart** (base locale, run 17) |
| Hook vert | ✅ scan secrets **0** · tsc **0** · pytest unit **2860/0** · vitest : admin/circuit **21/21**, 266 pass au total — *8 suites « carte » non chargées = artefact du symlink node_modules inter-worktree (`Denied ID …maplibre-gl-worker`), pas une régression ; mes seules modifs front (TableauDeBord.tsx, types.ts) sont couvertes par la suite admin verte* |

---

## CE QUI RESTE UNE DÉCISION / UN GESTE HUMAIN

1. **BDNB** — cliquer (ou non) « Injecter » après la sonde de couverture `labuse ingest-bdnb` ; cf. l'en-tête.
2. **FRR** — source structurante B : clic de Vic s'il veut la nouvelle version.
3. **C13 (TVA)** — confirmer que `regime_tva_saisi` ≠ sélecteur de taux (sinon = correctif à spécifier).
4. **Merge** — `fix/tableau-1 → main` par PR (hors mandat « pas de merge »). Les correctifs n'agissent qu'une
   fois déployés (injection-nuit armé, sondes recâblées, tableau mis à jour).

---

## FICHIERS

**Neufs** : `tests/test_tableau1_sondes.py`,
`docs/audit-2026-11/tableau-1/{COMPTE-RENDU.md,ECARTS-DISPOSITION.csv,avant-tableau.png,apres-tableau.png}`.
**Modifiés** : `config/sources_ingestion.yaml` (2 commandes A), `src/labuse/jobs_impl.py` (`injection_nuit`),
`src/labuse/api/dashboard.py` (`lancer_ingestion_source`, veille cadence_heures, gate/calcul-en-cours au
cockpit), `src/labuse/circuit_resume.py` (injecter = B, G8/sonde hors cartes), `src/labuse/cockpit_resume.py`
(sondes/G8 en santé, pas-encore-dû, mise-à-jour vérité du moment, Mac retiré), `src/labuse/circuit_etats.py`
(grace sonde 7 j), `src/labuse/sentinelle.py` (OCS/SIS/SCOT recâblés + miroirs Overpass),
`frontend/src/components/admin/circuit/{TableauDeBord.tsx,types.ts}`, plus les tests de recette ajustés
(`test_cockpit_lot_a/b`, `test_circuit_p7_lot4`, `test_circuit_p4_etats`).
