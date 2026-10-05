# CHASSE-3 — chasse sur le build de production, en usage réel

> **Verdict : 8 écarts — 2 FAUX (1 bloquant) · 3 DISCORDANT (1 bloquant) · 2 TROMPEUR ·
> 1 SALE. Pas de jackpot : C3-06 (FAUX bloquant, « Permis dormants » sert une table d'avant
> ORACLE-FIX-1 → ~95 % de fausses cibles à Saint-Pierre) et C3-01 (DISCORDANT bloquant,
> /readyz ment → le healthcheck du prochain déploiement échouera). Le cœur servi, lui, est
> droit : 0 divergence de prix sur 24 communes × tous lecteurs, 6/8 scénarios promoteur
> exacts à la parcelle près, 254/254 écran=papier, 1 355 requêtes sous charge sans une
> anomalie, mobile 0 chiffre perdu, badge public 0 faux, 0 réapparition des écarts corrigés.**

Branche `audit/chasse-3` (base `04819f73` = origin/main du 05/10), worktree
`~/Desktop/labuse-chasse3`, **lecture seule** (seuls `docs/audit-2026-10/CHASSE-3/` et
`scripts/chasse/` écrits). Toute la chasse est jouée contre le **build de prod**
(`npm run build`, servi par l'API du worktree sur `127.0.0.1:6015/socle/`) — jamais Vite.

## Étape 0 — état des lieux
- Arbre propre, base = origin/main du jour, disque 18 Go libres. `npm run build` OK (rolldown).
- Run servi : **13 (q_v16)** ✓ · score q_v16 présent (431 663 lignes parcel_p_score_v2) ✓ ·
  **0 fuite** (sonde cloison) ✓.
- Circuit verrous : **30/32** — G5 CASSÉ (→ écart C3-02), G8 cassé = gel local des horloges,
  connu (DASHBOARD-AUDIT-1), pas un écart neuf.
- `/readyz` : **ready=false en permanence** → écart C3-01 (bloquant déploiement).
- Incident d'environnement (hors app, arbitrage Vic en session) : le boot de l'API exécute
  des `ALTER TABLE … ADD COLUMN IF NOT EXISTS` sur `parcel_residuel_runs`
  (`faisabilite/residuel_runs.py:45`) ; coincé derrière une transaction idle d'une autre
  session, il a figé les lectures ~8-9 min. Non compté comme écart (décision Vic) ; noté ici
  pour l'exploitant : un boot d'API pendant qu'une transaction traîne = gel du service.
- Port 8815 squatté par un process étranger (mll-generator-v2) → chasse jouée sur 6015.
- Copilote **dégradé** (crédits Anthropic épuisés, réponse honnête `degraded:true`) : les
  volets « Copilote » des angles sont joués en charge (endpoint) mais pas en contenu.

## Angle 0 — régression CHASSE-1 + CHASSE-2
`make -C scripts/chasse chasse` rejoué intégralement (dont face_a_face, 718 parcelles,
31 min) : **0 réapparition des écarts corrigés** (C01/C02/C06/C22/C23 de CHASSE-FIX-1,
D04/D05 de CHASSE-FIX-2 absents). Baselines stables : mêmes totaux (CHASSE-2 : 169 écarts
connus, 115 INCOHERENT/54 TOLERABLE), seuls bougent les prix DVF rafraîchis (valeurs, pas
les verdicts). **Une ligne NEUVE** attrapée par le volet déterminisme : le « siège » de la
société propriétaire flappe d'un appel à l'autre → reproduit au calme, écart **C3-08**.

## Angle 1 — usage simultané (10 clients × 10 min)
`python -m scripts.chasse.charge3` → CHARGE.csv + CHARGE_P95.csv. Baseline solo (corps JSON
normalisés, hash) → 10 clients × 10 min sur le mix réel (fiches, enrichment, filtres,
marché, tuiles, PDF, Copilote) avec comparaison des corps EN DIRECT → re-mesure solo.
**1 355 requêtes : 0 corps différent sous charge, 0 dérive post-charge, 0 erreur 5xx,
0 timeout, 0 PDF incomplet servi.** p95 sous charge (10 clients, Mac local) : tuile 0,22 s ·
enrichment 0,21 s · copilote 0,97 s (dégradé) · marché 3,5 s · **fiche 13,7 s (p50 9,1 s)** ·
PDF 22,8 s · **filtre 23,9 s (max 39 s)**. Pas un écart au sens du mandat (chiffres
identiques, zéro erreur) mais la fiche et le filtre se traînent sous 10 clients — à mesurer
sur le VPS avant d'en faire un chantier. Solo au calme : fiche 1,3–2 s (le 12 s observé en
début de session = contention de la régression qui tournait).

## Angle 2 — les questions d'un promoteur (8 scénarios, recalcul SQL)
`python -m scripts.chasse.promoteur3` → PROMOTEUR.csv. Compte = liste = carte sur 8/8
(fixes F2/D05 tiennent), aucune troncature. **6/8 scénarios EXACTS à la parcelle près**
(terrain nu U hors risques 18=18 · capacité ≥10 lgts 1527=1527 · assemblage 1075=1075 ·
dirigeant 70+ 704=704 · public ≥5000 m² 239=239 · bâti sous-densité 1660=1660). Deux FAUX,
même famille (**table dérivée jamais rebâtie après changement de règle**) :
- **C3-06 (bloquant)** : « Permis dormants » — pc_caducs du 08/08, avant ORACLE-FIX-1 →
  à Saint-Pierre ~95 % de fausses cibles (301/316) et ~96 % des vrais dormants ratés (418) ;
  la fiche du témoin CO0833 se contredit elle-même (liste permis « annulé » vs bloc caducité
  « jamais commencé »).
- **C3-07 (moyen)** : « Successions » — instantané du 09/08 antérieur à la doctrine des
  formes patrimoniales (25/09) : SA/SAS servies à tort, SCI 84 ans à 23 parcelles ratée.
Note (pas un écart) : « assemblage » = ≥3 parcelles même SIREN privé SANS contiguïté — règle
documentée et tenue ; 77 % du résultat de Saint-André a de fait ≥1 parcelle contiguë.

## Angle 3 — prix du neuf (VEFA-1) et prix de sortie (PRIX-SORTIE-1)
`python -m scripts.chasse.prix3` → PRIX.csv. Sur les 24 communes :
- **VEFA à l'acte** : contexte commune = comparateur = baromètre = couche carte, partout
  (0 divergence) ; Dossier PDF « Neuf VEFA — commune … VEFA déclaré à l'acte » cohérent.
- **Neuf observé / prix de sortie** : contexte = bloc Marché = faisabilité = prefill
  Financier (= PDF Financier « Prix de vente prévu … prix de sortie NEUF servi »), partout ;
  témoins PRIX-SORTIE-1 tenus (Saint-Denis 4 275, Saint-Pierre 4 258).
- MAIS l'étiquette front du bloc Marché ment : **écart C3-03** (« Prix du neuf VEFA » sur la
  valeur du neuf observé — deux « VEFA » différents dans la même app).
- Négatifs : « prix de sortie » jamais adossé à « ancien »/« revente » dans les PDF joués.
- Le PDF Financier REFUSE explicitement (422 « document_non_etablissable », manques nommés)
  quand le programme n'est pas chiffrable — conforme DOCS-1, jamais un PDF faux silencieux.

## Angle 4 — causes certaines / ignorance + badge « Propriétaire public »
`python -m scripts.chasse.causes3` → CAUSES.csv. Invariant île (431 663 parcelles) :
- cause CERTAINE ⇒ SDP 0 : **163 817/163 817 ✓** · libellés fiche « Non retenue — … » ✓
  (3 témoins × chaque cause) · PDF Dossier §10 cohérent (témoin) ✓.
- cause d'IGNORANCE ⇒ ∅ : **10 778 violations en stock** (SDP=0 au lieu de NULL) → écart
  C3-04 (SALE) ; le scoring classe quand même NC par la cause (10 776/10 778), la fiche
  recalcule juste (null + « Analyse incomplète ») — **2 parcelles fuient en bande « 0 »** →
  écart C3-05 (DISCORDANT).
- 0 sans cause : nommé à la fiche sur l'échantillon (12/12, ex. « Densité autorisée
  atteinte ou dépassée ») ✓.
- Badge public (groupes DGFiP 1,2,3,4,9) : **50 badgées = 0 faux positif · 200 non badgées
  = 0 faux négatif** ✓.

## Angle 5 — l'écran et le papier (40 parcelles × PDF)
`python -m scripts.chasse.ecran_papier3` → ECRAN_PAPIER.csv. 40 parcelles tirées au sort
(stratifiées : 20 SDP chiffrée, 10 cause certaine, 5 ignorance, 5 zéro sans cause),
figures surface/emprise/hauteurs/prix ancien (médiane + n)/prix de sortie :
**254 comparaisons, 0 écart** — y compris format FR (« 1 889 », « 8,2 ») et refus 422
explicites du gabarit/financier. Comparatif (3 témoins : 405/7 398/413 m² écran=PDF) et
Étude de zone (10 170 habitants, 3 548 ménages écran=PDF) cohérents.
Notes de méthode : les « 8 PDF » réels par parcelle sont 4 documents (dossier, financier,
apporteur, gabarit) — argumentaire, dossier-banquier et export sont des **alias 308** vers
financier/dossier (mesuré) ; deux faux écarts de harnais éliminés en route, instructifs :
l'écran n'affiche pas `hauteur_regle_m` (entrée de calcul à l'égout — l'écran montre la
hauteur réglementaire du Gabarit, qui = PDF), et l'emprise « révélée » du mode B
(max BD TOPO/CoSIA) est une notion NOMMÉE par sa source, distincte de l'« Emprise bâtie »
servie (BD TOPO clippé) — cloison COHERENCE-FIX-2 tenue.

## Angle 6 — mobile 390×844
`node scripts/chasse/mobile3.mjs` → MOBILE.csv + captures. 10 fiches + 3 outils : **0 chiffre
perdu ou changé** (les seuls « manquants » mobiles sont les textes du panneau d'accueil
desktop — « 16 outils fonciers », « 1 000 m² » de la suggestion Copilote — pas des données) ;
**0 nombre tronqué** (les ellipses ne coupent que des noms de commune en fin d'adresse,
capture mobile_fiche_97401000AD0069.png : 1 960 m² · Ud3 · 4,1° · SDP 407 m² tous lisibles).
Vérifié au passage : le deep-link `#f=1&idu=…` (la forme que l'app écrit) réhydrate bien la
fiche au rechargement ; la forme nue `#idu=…` ne la rouvre pas mais l'app ne l'émet jamais
(pas un écart).

## Écarts — ECARTS.csv (8)
| id | verdict | gravité | quoi |
|---|---|---|---|
| C3-01 | DISCORDANT | **bloquant** | /readyz « run q_v16 non matérialisé » alors que l'app sert q_v16 (la sonde ignore la résolution cascade D05) → deploy_vps.sh échouera son healthcheck |
| C3-02 | TROMPEUR | moyen | 4 sources vitrine « à jour » sans date de contrôle ni « jamais vérifié » (verrou G5 cassé sur main) |
| C3-03 | TROMPEUR | grave | bloc Marché : « Prix du neuf VEFA (€/m²) » colle sur la valeur du neuf OBSERVÉ (strings.ts:142) — deux « VEFA » différents dans la même app (ex. Saint-Denis 4 275 vs 4 878) |
| C3-04 | SALE | moyen | 10 778 causes d'IGNORANCE stockées SDP=0 au run servi (affichage sauvé par la cause, sauf…) |
| C3-05 | DISCORDANT | faible | …2 parcelles « Analyse incomplète » à la fiche classées bande « 0 » (hauteur_indispo) |
| C3-06 | FAUX | **bloquant** | « Permis dormants » : pc_caducs d'avant ORACLE-FIX-1 → à Saint-Pierre 301/316 servies fausses, 418 vrais dormants ratés ; la fiche du témoin se contredit elle-même |
| C3-07 | FAUX | moyen | « Successions » : instantané du 09/08 antérieur à la doctrine des formes (25/09) — SA/SAS servies, SCI 84 ans/23 parcelles ratée |
| C3-08 | DISCORDANT | moyen | le « siège » de la société propriétaire flappe à chaque appel (LIMIT 1 sans départage) et n'est pas un siège |

C3-06 et C3-07 sont la même famille : **table dérivée jamais rebâtie après un changement de
règle** — le correctif est un rebuild (build_pc_caducs, veille succession), pas du code.

## Ce qui est prouvé juste
- **Prix** (angle 3) : 24 communes × tous les lecteurs — VEFA à l'acte (contexte =
  comparateur = baromètre/Évolution = couche carte = Dossier PDF) et prix de sortie neuf
  servi (bloc Marché = faisabilité = prefill Financier = PDF Financier), **0 divergence de
  valeur** ; témoins PRIX-SORTIE-1 tenus ; « ancien »/« revente » jamais vendus comme prix
  de sortie ; les documents refusent explicitement (422 nommé) plutôt que servir un PDF faux.
- **Filtres** (angle 2) : 6/8 scénarios promoteur EXACTS à la parcelle près contre recalcul
  SQL indépendant ; compte = liste = carte sur 8/8.
- **Écran = papier** (angle 5) : 254/254 comparaisons sur 40 parcelles stratifiées × 4
  documents + comparatif + étude de zone.
- **Charge** (angle 1) : les chiffres ne bougent pas sous 10 clients, 0 5xx, 0 PDF tronqué.
- **Causes** (angle 4) : 163 817 causes certaines toutes à SDP 0 nommée ; libellés fiche
  justes pour toutes les causes ; badge « Propriétaire public » 0 faux positif / 0 faux
  négatif (250 vérifiées) ; les 0 sans cause sont nommés.
- **Mobile** (angle 6) : 0 chiffre perdu/changé/tronqué sur 10 fiches + 3 outils.
- **Régression** (angle 0) : 0 réapparition des écarts CHASSE-FIX-1/2.

## Angles non joués / limites
- **Copilote en contenu** : crédits IA épuisés (réponse dégradée honnête) — ses lectures de
  prix sont vérifiées par le code (il lit le bloc Marché servi) et l'endpoint a tenu la
  charge, mais aucune phrase de Copilote n'a été jugée.
- **Mon harnais de charge tourne sur le Mac d'audit** : les p95 sont des ordres de grandeur,
  pas des SLO (une seule machine, API uvicorn mono-worker).
- Les « 8 PDF » par parcelle n'existent pas : 4 documents réels + 2 multi-cibles (les 3
  autres routes sont des alias 308) — dit à l'angle 5.
- Déterminisme : vérifié via le volet CHASSE-2 (2 appels) + 3 rejeux manuels sur le témoin
  C3-08 ; pas de campagne systématique au-delà.
