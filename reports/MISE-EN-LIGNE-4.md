# MISE-EN-LIGNE-4 — redéploiement avec openpyxl, et le chronomètre mesuré

**Mandat** : go de Vic, 21/11 au soir (rejoué après l'arrivée effective de la fusion sur
`origin/main` — deux faux départs constatés et rapportés). Décision actée : le garde-fou de la
grille n'est **pas** monté (100 candidats en 100 s → il en faudrait ~150 s, au-delà du délai
API de 120 s) ; la correction passera par le moteur (chantier « capacité maximale », relecture
+ Astra) ; l'affichage « Recherche partielle » est conservé.

## LOT 1 — déploiement : vert, toutes preuves acquises

Précondition : `HEAD = origin/main = a5d53dae3`, arbre propre. `deploy_app.sh labuse-vps` :
**EXIT 0** — et surtout, l'étape venv a installé le lock **puis le selftest (contrôle 5
compris) est passé** : « ✓ jobs selftest : les 41 jobs du registre chargent à blanc » — le
mécanisme neuf a validé en conditions réelles que plus aucun module tiers servi ne manque.

| Preuve | Résultat |
|---|---|
| readyz stable 10 min | **60/60 sondes OK**, 0 erreur de journal depuis le restart |
| Tampon = sha de main | `deploiement.json` = **`a5d53dae32df`** |
| openpyxl importable en prod | **3.1.5** (venv prod, importé) |
| Bilan Excel produit en prod | par `classeur_bilan_bytes` (la fonction de l'endpoint), rapatrié et ouvert : **207 formules**, **valeurs en cache présentes** (terrain 1 703, SDP 600…), ligne « Total produits » là |
| q_v20 intact | manifeste q_v20 / seq 17 ; `score_labuse` = **433 229** |
| Gels préservés | 4 gelés commentés au crontab (calcul-nuit motif registre, purge-runs, radar-cloche, digest) |

## LOT 2a — le chronomètre dans la chaîne du classement : il n'y en a PAS

Balayage de tout le périmètre (`faisabilite/` — résiduel, `cascade/`, `scoring/` — Signal,
Score, scénarios V2, `implantation/`) : **un seul module au chronomètre dans tout le code :
`implantation/moteur.py`** — la grille de l'ÉCRAN Étude (garde-fou 100 s + plafond
déterministe 150 candidats). La chaîne du classement ne l'appelle pas : `faisabilite/` n'importe
d'`implantation` que le chargeur de règles et un libellé de stationnement (vérifié) ; résiduel,
cascade et scénarios V2 n'ont **aucun arrêt au chronomètre interne** — leur résultat ne dépend
pas de la vitesse du serveur. Les seuls chronomètres autour de la chaîne sont **externes et
francs** : le timeout du job runner (calcul-nuit 14 400 s) et la fenêtre 01 h-05 h — dans les
deux cas le job **échoue bruyamment, rien n'est retenu ni promu** (jamais un partiel
silencieux). Conclusion : **le classement q_v25 ne peut pas hériter du problème BW2635.**

## LOT 2b — le problème mesuré : dix terrains, prod contre Mac

Même fonction que l'endpoint, config par défaut, chronométrée (prod après déploiement, Mac au
même commit). Témoins des Études (5) + assiettes étagées 300 → 11 500 m² (5) :

| Terrain | Taille | Prod | Mac | Logements prod/Mac |
|---|---|---|---|---|
| 97408000BI0351 | témoin | 0,2 s · refus amont | 0,1 s · idem | — |
| 97414000DK0208 | témoin | 3,3 s · non aboutie (150/150) | 1,5 s · idem | — |
| 97416000HT0538 | témoin | 13,1 s · complète | 4,6 s · complète | 5 / 5 |
| 97422000AD0887 | témoin | 38,0 s · complète | 9,0 s · complète | 6 / 6 |
| **97422000BW2635** | témoin, 2 003 m² | **101,5 s · PARTIELLE (104/150)** | 29,6 s · complète | **5 / 6 (−1)** |
| 97401000AD0396 | 310 m² | 1,3 s · non aboutie | 1,1 s · idem | — |
| 97401000AD0033 | 760 m² | 17,9 s · complète | 5,3 s · complète | 1 / 1 |
| 97401000AD0144 | 1 491 m² | 51,7 s · complète | 11,9 s · complète | 4 / 4 |
| **97401000AL0189** | 5 008 m² | **103,1 s · PARTIELLE (91/150)** | 43,2 s · complète | **10 / 10 (=)** |
| 97402000AE0005 | 11 533 m² | 0,0 s · refus amont | 0,0 s · idem | — |

**Lecture** : la prod est ~3 à 4× plus lente que le Mac sur ce calcul. **2 terrains sur 10
sortent en « Recherche partielle »** en prod (ceux qui franchissent ~100 s : les assiettes
≥ ~2 000 m² qui ne sont ni refusées ni non-abouties). L'écart de logements est **plus petit que
la partialité** : sur les 2 partielles, **une seule sous-estime (−1 logement, BW2635)** ;
l'autre (AL0189) trouve la même capacité que la grille complète (le meilleur candidat était
dans les 91 premiers). Sur les 6 terrains comparables, **5 sont identiques prod = Mac**.
Matière pour le chantier « capacité maximale » : le coût d'un candidat croît avec l'assiette ;
l'ordre d'exploration fait que le déficit n'apparaît que lorsque les candidats à étages arrivent
tard dans la grille.

## État final

Site déployé sur `a5d53dae3`, stable ; q_v20/seq 17 intacts ; aucune écriture hors le
déploiement lui-même et un classeur témoin dans /tmp (purgé) ; scripts temporaires purgés.
