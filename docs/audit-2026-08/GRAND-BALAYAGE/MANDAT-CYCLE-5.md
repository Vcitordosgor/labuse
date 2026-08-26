# GRAND BALAYAGE — CYCLE 5 : LES 500 (dernier cycle de la campagne, quel que soit le verdict)
Protocole inchangé (MANDAT.md) : audit seul, aucun fix ; findings GB-034→ ; [GB-TEST] + inventaire de purge ; append + commit PAR LOT ; vérification jusqu'à la cause avant tout finding. Rapport : RAPPORT-CYCLE-5.md. Front :5174, back :8000. Sous-agents parallèles autorisés (patron cycle 4). Budget LLM ≤ 180 appels (LOT Y). PRÉREQUIS : fix/c4-jaunes-tout mergé et serveur redémarré — vérifie au boot (GB-017→033 sont réputés corrigés ; s'ils réapparaissent, c'est une RÉGRESSION, note-la comme telle).
Principe des 500 : génération aléatoire SEEDÉE (note chaque seed dans le rapport pour rejouabilité). Une passe = une vérification individuelle tracée. Le tableau final compte 500 lignes agrégées par lot (détail en annexe CSV dans le dossier).

## LOT U — VÉRITÉ DE MASSE : 200 passes
200 parcelles tirées au sort en SQL, STRATIFIÉES : ~8 par commune (24 communes), en forçant la diversité (tous tiers représentés, U/AU/A/N, bâti/nu, avec/sans servitudes, 5 slivers, 5 multi-polygones, les 2 extrêmes de surface). Pour CHACUNE, via l'API de la fiche : surface == base · zone == base · tier == run servi · SDP résiduelle == parcel_residuel · verdict carte == fiche · millésime affiché == source. 6 vérifications × 200 = la passe est OK si les 6 concordent. TOUT écart = finding avec l'IDU et la grandeur. Livrable annexe : lot-u.csv (idu, commune, 6 verdicts).

## LOT V — FUZZING API : 100 passes
Depuis openapi.json, générer pour CHAQUE endpoint GET une matrice d'entrées hostiles (types faux, bornes, négatifs, énormes, unicode, injections, params en double, encodages %) — 100 requêtes au total réparties sur tous les endpoints, seedées. Invariant unique : JAMAIS un 500, jamais une stacktrace, toujours 2xx/4xx propre. Chaque requête = une passe. Les endpoints d'écriture : mêmes entrées hostiles SANS session → tous 401/403 (inclus dans les 100). Annexe : lot-v.csv (endpoint, payload, code, verdict).

## LOT W — EXPORTS DE MASSE : 50 passes
50 exports tirés au sort (CSV/PDF, tous les types d'export de l'app, périmètres variés dont vides et énormes) — chaque fichier OUVERT et vérifié : lignes == annoncé ou notice de cap (GB-016), en-têtes, accents, dates, aucune valeur « undefined/NaN/None ». Annexe : lot-w.csv.

## LOT X — PARCOURS UI ALÉATOIRES : 60 passes
60 marches aléatoires Playwright seedées (12 pas chacune : ouvrir un outil au hasard, cliquer une parcelle au hasard, filtrer, fermer, naviguer…). Invariants à CHAQUE pas : zéro erreur console · zéro écran blanc · Échap ferme toujours l'overlay courant · le header reste cliquable · retour arrière ne casse pas. Une marche sans violation = une passe OK. Toute violation = finding avec le seed et la séquence exacte (rejouable).

## LOT Y — COPILOTE GÉNÉRATIF : 50 passes (LLM réel ≤ 180 appels)
50 questions générées par gabarits × entités tirées au sort : {compter|prix|délai|patrimoine|verdict parcelle|piscines|permis|comparer} × {24 communes, 10 entreprises, 10 IDU aléatoires} + 10 tournures dégradées (fautes, mélange langues, créole, emojis, question coupée). Invariants : jamais un chiffre faux (spot-check SQL sur 15 réponses) · jamais de JSON brut · badge juste selon la voie · clarification quand ambigu · jamais d'invention sur donnée absente. Chaque question = une passe.

## LOT Z — CHARGE, CONCURRENCE, ENDURANCE : 40 passes
10 passes : la même fiche demandée 10× en parallèle → réponses identiques, latence p95 notée. 10 passes : écritures [GB-TEST] concurrentes (courrier, projet, kanban) 2 threads chacune → jamais de doublon (vérif GB-013 étendue). 10 passes : 10 endpoints chauds sous 50 requêtes rapides chacun → p95 < 3 s ou dégradation propre, zéro 500. 10 passes : mesures d'endurance (RSS backend, connexions pg, taille logs) relevées avant/milieu/fin de cycle → stables.

## LIVRABLE FINAL DE CAMPAGNE
RAPPORT-CYCLE-5.md : tableau 500 passes par lot (OK/KO) + annexes CSV + findings GB-034→ triés + gardées G1-G6 re-vérifiées + inventaire de purge + les seeds. VERDICT DÉFINITIF DE CAMPAGNE : PASSE BLANCHE (zéro 🔴/🟠 nouveau) → la campagne Grand Balayage est close pour de bon ; sinon → liste à fixer puis la campagne est close quand même (les fixes seront vérifiés par leurs tests, pas par un cycle 6). Compte-rendu avec la commande de merge en dernier élément isolé (git merge --no-ff audit/grand-balayage-c5). Pas de merge par CC.
