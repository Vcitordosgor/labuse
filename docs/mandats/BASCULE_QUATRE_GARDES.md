# Le vrai livrable de la bascule v8 : QUATRE gardes qu'un script de bascule doit avoir

> **Note de méthode (Vic, 30/07/2026).** La bascule `q_v7_defisc → q_v8_calibre` a échoué quatre
> fois avant de tourner — chaque échec a révélé une garde MANQUANTE. Ces quatre gardes sont ce
> qu'un script de bascule doit savoir faire **avant de toucher un run servi**. C'est le livrable
> durable de cette séquence, au-delà du run lui-même.

## Les quatre gardes (chacune tirée d'un échec réel)

### 1. COMPLÉTUDE — prouver que le run est entier avant de se déclarer terminé
- **Échec** : la 1ʳᵉ bascule a produit `parcel_p_score_v2` (scores) SANS la cascade `dryrun_*`, et
  s'est déclarée finie → golden en échec massif. Un run incomplet est **plus dangereux** qu'un run
  qui échoue : l'échec s'arrête et se voit, l'incomplétude ne se révèle qu'au golden, après coup.
- **Garde** : `verify_completude(target, attendu)` compte CHAQUE table clé-run (scores P + cascade
  evaluations + cascade results + matrice + snapshot) vs l'attendu ; au premier manque →
  `RunIncompletError` (échec BRUYANT). Le run n'est PAS déclaré servable tant qu'il n'est pas prouvé
  entier. (Réf. 7e principe de méthode.)

### 2. ESPACE DISQUE — estimer le besoin et refuser de démarrer sans la marge
- **Échec** : le job a tourné ~20 % (plusieurs heures) puis est mort sur `No space left on device`.
  Un job long qui meurt à mi-course sur disque plein est une garde manquante au même titre que la
  complétude.
- **Garde** : `check_disque()` estime le besoin restant (tranches q_v7 − déjà écrit q_v8), mesure le
  disponible = **libre OS + espace RÉUTILISABLE** (FSM via `pg_freespacemap`, exact ; repli
  `n_dead_tup`), et **refuse de démarrer** si le débordement OS (`besoin − FSM`) dépasse le libre ×
  marge. Modèle juste : le FSM absorbe les écritures (réutilisation d'espace mort sans grossir le
  fichier), seul le débordement touche l'OS. Flag `--skip-disk-check` en connaissance de cause.

### 3. JOURNALISATION DE PROGRESSION — savoir où en est un job de plusieurs heures
- **Échec** : le script n'affichait rien pendant la re-passe cascade → il a fallu interroger la base
  à la main pour savoir l'avancement, et deviner que le job était mort (compteur figé).
- **Garde** : une ligne par commune TERMINÉE — **heure (HH:MM:SS), commune, compte cumulé, ETA**.
  L'état d'un job long doit être lisible sans requête manuelle.

### 4. CODE D'APPLICATION SUR `main` — scorer avec le code servi, pas un working tree divergent
- **Échec (classe, cf. leçons antérieures)** : trois désynchronisations `origin/main` en une journée
  — du code/des runs qui existaient sans être atteignables, ou l'inverse. Un run servi doit être
  produit par le code qui est SUR main (mergé, poussé), pas par un working tree local divergent,
  sinon le run servi et le code servi « racontent deux mondes ».
- **Garde** : avant de matérialiser un run servi, vérifier que la branche est à jour avec
  `origin/main` (ou que le correctif est mergé), et pousser en fin de bascule. (Réf. règle
  [git-push-fin-mandat] : commit + push toujours, merge jamais côté agent.)

## Pourquoi c'est le livrable
Le run `q_v8_calibre` est un résultat ponctuel ; ces quatre gardes sont **réutilisables pour toute
bascule future** (v9, re-calibrages, migrations de la chaîne servie). Une bascule qui touche un run
servi sans les quatre expose le produit à un état incohérent SILENCIEUX — la pire des pannes pour un
produit dont l'argument central est « chaque chiffre est vérifiable ». Les gardes 1, 2, 3 sont
implémentées dans `scripts/bascule_v8_calibre.py` ; la garde 4 est une discipline de séquencement
(vérif main + push) à intégrer au protocole de bascule.

*Séquence : bascule v8, 29-30/07/2026. Quatre échecs → quatre gardes : KeyError (câblage),
débordement varchar, run incomplet, disque plein — les deux derniers ont nommé les gardes 1 et 2 ;
la journalisation et la vérif-main complètent le quatuor.*
