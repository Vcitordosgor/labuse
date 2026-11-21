# MISE-EN-LIGNE-3 — les ventes, puis la dépendance manquante

**Mandat** : go de Vic, 21/11 au soir. LOT 1 exécuté sur la prod (le geste du cron, rien
d'autre) ; LOT 2 sur la branche — **rien déployé**, Vic fusionne puis donne le go.

## LOT 1 — ventes : fait, et mon explication d'hier était fausse

`labuse jobs run ingest-dvf` à 20 h 02 (utilisateur labuse, comme le cron) : **ok en 8,1 s** —
refresh **no-op** (aucune nouvelle livraison Etalab : les ventes étaient déjà au **30/06/2026**
partout depuis la recharge du 15/11 ; 31 079 mutations, inchangé) + **médianes de secteur
recalculées** (2 359 lignes, 850 secteurs, `computed_at = 21/11 20 h 02`).

**L'Étude BW2635 reste à 5 logements / 7 places.** Le mandat avait raison de douter : les
médianes du secteur `97422000BW` sont **identiques Mac = prod** (appartement 168 ventes /
2 789 €/m², maison 85/2 480, terrain 18/376) — **mon explication par les médianes était
fausse**. La vraie cause, prouvée par le payload de l'étude (même fonction que l'endpoint,
rejouée des deux côtés et diffée champ à champ) :

- prod : `recherche: {candidats_examines: 100, candidats_prevus: 150, etat: "partielle",
  garde_fou_temps: true}` → le **garde-fou de temps de la grille d'implantation**
  (`etude_grille_garde_fou_s = 100 s`, défaut, non surchargé) **coupe la recherche sur ce
  serveur plus lent** avant d'avoir examiné les candidats R+1 ; le moteur retient le meilleur
  trouvé — R+0, emprise 543 m², 5 logements — et **l'écrit honnêtement à l'écran**
  (« Recherche partielle … la capacité réelle peut être supérieure »).
- Mac (plus rapide) : grille complète → **R+1, 6 logements / 9 places**.

**Ce n'est donc ni une donnée ni un bug : c'est une différence de vitesse machine** sur une
assiette lourde (2 003 m²), bornée par un garde-fou assumé et affichée comme telle. Le même
écart peut toucher d'autres grandes assiettes en prod. Décision pour Vic (pas prise ici) :
monter `LABUSE_ETUDE_GRILLE_GARDE_FOU_S` en prod (ex. 110 s, sous le timeout API de 120 s), ou
accepter le comportement actuel documenté. Nota : le TN LiDAR, les règles et le plafond (16 m)
sont identiques des deux côtés — vérifié dans le diff.

Au passage : les médianes recalculées gardent `millesime_dvf = 2025-12-31` — `dvf-marche` lit
`dvf_mutations_parcelle`, qui n'a aucun écrivain (connu, documenté au plan) ; le libellé
« ventes jusqu'au … » de la page Données ne bougera qu'avec le rebuild de cette table.

## LOT 2 — openpyxl et la question entière

**Inventaire** (balayage AST de `src/labuse`, imports dans les fonctions compris) : **46
modules tiers**. Test de chacun dans le venv de prod (`python -c "import …"`, lecture seule) :
**7 manquants**, qui se classent ainsi :

| Manquant | Verdict |
|---|---|
| **openpyxl** | **SEUL vrai manquant d'un chemin servi** (Bilan Excel `bilan/excel.py`) → ajouté |
| torch, segmentation_models_pytorch | ML only (`ml/`), délibérément jamais en prod (PROPRETE-FIX-0) |
| py7zr | ingestion cadastre historique hors-ligne Mac, jamais servie |
| matplotlib | `implantation/rendu.py` (témoins/archives) — **aucun appelant servi** (vérifié) |
| protocole, scripts | faux positifs de méthode : modules locaux résolus par le CWD `/opt/labuse/app` au runtime (le job verite-permanente les utilise chaque jour) ; `scripts` est déjà couvert par les contrôles 3-4 du selftest |

**Fait sur la branche** :
1. `openpyxl>=3.1` en **dépendance de série** (pyproject, retiré de `[ci]`) **et dans
   `requirements.lock`** (openpyxl==3.1.5 + et-xmlfile==2.0.0 — c'est le lock que
   `deploy_app.sh` installe, le pyproject seul n'aurait rien changé) ; lock revalidé :
   `uv pip install --dry-run` contre le venv testé → « Would make no changes ».
2. **`src/labuse/deps_servies.py`** : la liste déclarée des **40 modules tiers servis** + la
   liste `HORS_PROD` motivée (les 6 exclusions ci-dessus).
3. **Selftest du déploiement étendu (contrôle 5)** : `jobs.selftest()` importe chaque module
   servi — un paquet absent du venv **refuse le déploiement** (le même mécanisme qui bloque
   déjà sur un job non chargeable), au lieu d'un 500 au clic d'un client.
4. **Tests** (`tests/test_deps_servies.py`, 4 verts) dont un **méta-test AST** : tout nouvel
   import tiers non classé (servi ou hors-prod motivé) fait échouer la suite — la liste ne
   peut plus se périmer en silence.

**Sha à fusionner** : voir le commit poussé sur `ops/deploy-groupe-3` (hook vert). Je ne
déploie pas — après fusion par Vic et son go, le déploiement installera openpyxl via le lock
et le selftest vérifiera les 40 imports.
