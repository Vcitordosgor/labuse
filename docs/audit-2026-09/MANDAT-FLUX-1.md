# MANDAT FLUX-1 — voir la donnée circuler, et la mettre à jour sans rien casser

**Branche : `feat/flux-1`** (depuis `main` après merge de `fix/retours-7`). Bloc commun habituel.
**Origine** : Vic veut **voir** le circuit de la donnée (sources → calcul → écrans), **voir la donnée s'accumuler** (Radar), et comprendre/contrôler ce qui se passe quand une source est mise à jour. Tout ce mandat est **admin seulement** — rien côté client.

**Référence visuelle** : `docs/audit-2026-09/maquette-dashboard-flux.html` (validée par Vic) — bandeau 3 étapes, fourmilière en 3 colonnes, compteur Radar, garde de cohérence, encart « Comment ça marche ».

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

## Le modèle mental que la page doit rendre évident

LABUSE a trois étages et un interrupteur :

1. **Les sources** — 64, chacune avec un millésime (la version chargée).
2. **Le run** — un calcul global qui prend les sources et produit scores, tiers, cascade pour toutes les parcelles. Il porte un nom (aujourd'hui `q_v11_m137`) et il est **figé** une fois calculé.
3. **Les surfaces** — écrans, outils, exports, Copilote. Depuis CONNEXIONS-2, **toutes** lisent « le run courant » par un pointeur unique.
4. **L'interrupteur** — la bascule du run courant. C'est le seul événement qui change ce que voient les clients côté scores.

À côté, **le Radar** est une donnée vivante : les annonces entrent chaque jour sans attendre un run (elles s'affichent tout de suite) et nourrissent le run suivant (prix de référence, écart demandé/acté).

Donc mettre une source à jour, c'est trois gestes : **injecter** (nouveau millésime), **calculer** (nouveau run), **basculer** (le pointeur change). Entre le premier et le troisième, l'app est dans un état intermédiaire assumé : les écrans qui lisent une source brute (couches, chiffres de fiche commune) voient le nouveau millésime, les scores restent sur l'ancien run — et disent « valeurs au JJ/MM » du run. La page doit rendre cet état **visible**, pas le cacher.

---

## F1 — La page « Flux » du dashboard : la fourmilière, vivante

Une page admin qui dessine le circuit réel, **construite depuis les métadonnées** (`data_sources`, `source_veille`, la matrice source → consommateurs de CONNEXIONS-1 M1 rendue exécutable, le registre des outils) — jamais un dessin statique qui dériverait du code.

1. **Quatre colonnes** : Sources → Tables/moteurs (sector_price, scoring/tiers, cascade, capacité, rattachement) → Surfaces (15 outils, fiche, carte, Radar, Projets, Copilote, exports) — et, en tête, le **run courant** avec sa date.
2. **Chaque nœud a un état** : vert (à jour), orange (une version amont existe / plus récent que le run), rouge (en erreur), gris (non surveillé ou manuel). Chaque source affiche son millésime ; chaque surface affiche le run qu'elle lit.
3. **Les liens sont réels** : un clic sur une source surligne tout ce qu'elle alimente ; un clic sur un outil surligne tout ce qu'il lit. C'est la réponse à « qui écoute quoi ».
4. **Une alerte en tête si une surface ne lit pas le run courant** — ça ne doit jamais arriver depuis CONNEXIONS-2 ; si ça arrive, c'est rouge et nommé.
5. Sobre, DA v3, lisible à 64 sources : regroupement par fournisseur, recherche, et la possibilité de replier une colonne. Pas d'animation décorative — de l'état.

## F2 — Le bandeau « Mettre à jour » : Sources → Run → Bascule

En haut de la page Flux, trois étapes avec leur état et leur action. C'est la logistique de mise à jour, rendue évidente.

1. **Sources** : « N sources ont une nouvelle version » → action **Injecter** (celle de SENTINELLE-2 X6, réutilisée). « N sources sont plus récentes que le run courant » — c'est l'indicateur clé de l'état intermédiaire.
2. **Run** : run courant, date, sources et millésimes qu'il a utilisés (le run **enregistre** cette liste à son lancement — si ce n'est pas le cas aujourd'hui, l'ajouter : sans ça on ne peut pas savoir sur quoi un run a été calculé). Action **Lancer un run** : branche le pipeline de scoring existant comme job, avec progression visible et durée estimée. Aucune réécriture du pipeline.
3. **Bascule** : liste des runs terminés ; pour chacun, un **écart avec le run courant** (nombre de parcelles dont le tier change, répartition Priorité/À suivre avant/après) — c'est ce qui permet de basculer en connaissance de cause. Action **Basculer** : met à jour le pointeur unique, **purge tous les caches** recensés en CONNEXIONS-1 A6, journalise (qui, quand, de quel run vers lequel). Refusée si le run n'est pas complet ou n'a pas passé ses contrôles.
4. **Retour arrière** : basculer vers le run précédent est la même action dans l'autre sens. Aucun run n'est supprimé.
5. **Rien n'est automatique** : ni le run, ni la bascule. La sentinelle prévient, Vic injecte, Vic lance, Vic bascule. Un jour peut-être une bascule planifiée — pas dans ce mandat.

## F3 — Voir la donnée s'accumuler : le compteur Radar

Vic veut palper que l'outil d'estimation s'affine avec le temps. Ce ne sont pas les annonces qui rendent l'estimateur précis, ce sont les **rapprochements** : une annonce Radar (prix demandé) reliée plus tard à une vente DVF (prix acté) sur la même parcelle. Chaque paire apprend l'écart réel demandé/acté. La page doit montrer les deux.

1. **Compteurs cumulés**, avec « +N cette semaine » : annonces collectées · annonces rattachées à une parcelle · **paires annonce ↔ vente DVF rapprochées** · communes couvertes · types couverts.
2. **Une courbe dans le temps** pour chacun — il faut donc une table de **relevés quotidiens** (`radar_releves`, un job de fin de journée qui écrit les compteurs du jour). Pas de reconstruction rétroactive inventée : la courbe commence au jour du déploiement, et le dit.
3. **L'écart demandé/acté** médian par type (maison / appartement / terrain), calculé sur les paires, avec le nombre de paires derrière chaque chiffre. C'est **la** mesure de finesse ; elle est honnête : avec 12 paires, elle le dit.
4. Si le rapprochement annonce ↔ DVF n'existe pas encore comme mécanique (vérifier), le construire simplement : même parcelle, vente postérieure à l'annonce dans les 18 mois, type compatible. Un test.
5. Ce bloc apparaît sur la page Flux (colonne Radar) et en tuile sur le Pilotage.

## F4 — La garde de cohérence : « personne n'écoute une ancienne donnée »

CONNEXIONS-1 a vérifié ça en lisant le code. Il faut que ça reste vrai **automatiquement**.

1. Un job quotidien `coherence-run` qui, pour chaque surface recensée, appelle l'endpoint sur une parcelle témoin et vérifie que le run lu est le run courant, et que tier/date de valeur sont identiques d'une surface à l'autre. Réutilise la sonde de santé de CONNEXIONS-2 (lot 7.2) — un contrôle de plus, pas un second système.
2. Résultat sur la page Flux (F1.4) et dans la tuile Santé. Une divergence notifie l'admin.
3. **La bascule exécute ce contrôle immédiatement après avoir changé le pointeur**, et l'affiche : « bascule vers q_v12 : 17 surfaces vérifiées, toutes sur q_v12 ».

## F5 — Comprendre en lisant la page

Un encart replié « Comment ça marche » sur la page Flux, avec le modèle mental ci-dessus en cinq phrases et les quatre mots définis : **source**, **millésime**, **run**, **bascule**. Pour Vic aujourd'hui, pour la personne qui l'aidera demain.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : F2.2 le run enregistrait-il déjà ses sources et millésimes · F2.3 les caches purgés à la bascule (liste) · F3.4 le rapprochement annonce ↔ DVF existait-il, et **combien de paires aujourd'hui** · F4 résultat du premier passage de `coherence-run`. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/flux-1
```
