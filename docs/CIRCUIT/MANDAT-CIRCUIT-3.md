# MANDAT CIRCUIT-3 — Le filtre : la qualité à l'intérieur de chaque source

Branche : `feat/circuit-3`, worktree `~/Desktop/labuse-audit`, créée depuis `main` si `feat/circuit-2` y est mergée, sinon depuis `feat/circuit-2`.
Dossier : `docs/CIRCUIT/`. Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-3.md`.
Prérequis : CIRCUIT-1 et 2 clos.
Objectif : que l'eau soit analysée avant d'atteindre la pompe. Le circuit sait déjà que les permis viennent de Sitadel 2026-07 ; il doit savoir maintenant si les permis sont complets, posés sur la bonne parcelle, dans des plages plausibles, sans doublons, et si un échantillon vérifié une fois reste juste à chaque nouvelle version. Une eau qui rate son filtre reste en quarantaine et ne se sert pas.

Vocabulaire nouveau : **filtre** = l'ensemble des contrôles joués sur une version d'un réservoir · **contrôle bloquant** = un KO empêche de servir · **contrôle avertissant** = un KO s'affiche mais ne bloque pas · **quarantaine** = la version est ingérée, mesurée, pas servie · **échantillon** = des enregistrements vérifiés une fois contre le producteur, rejoués à chaque version.

---

## Autonomie

Mêmes règles que CIRCUIT-1 et 2 (aucune question, doutes tranchés et écrits, lots sautés plutôt qu'attendus, branche jamais rouge, push par lot, reprise par « continue CIRCUIT-3 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-3.md »). **La liste d'exceptions au registre reste vide sans Vic.** Un seuil de contrôle que CC ne sait pas fixer est posé en `avertissant` avec la valeur observée, jamais en `bloquant` inventé : un filtre trop sévère qui bloque une source saine est pire qu'un filtre qui avertit.

---

## Étape 0

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre, sinon stop. Branche `feat/circuit-3`. Suite verte, nombre noté.
2. Lire les comptes-rendus 1 et 2, `reservoirs.csv` et la table d'impact de `circuit.json` (l'ordre des lots 2 et 3 suit l'impact : DVF 19 robinets, GPU/PLU 13, cadastre, Sitadel, MAJIC, DPE, Géorisques/PPR, SIRENE, BODACC, INPI, BAN, CoSIA, FLAIR, LiDAR, EDF, OSM/TCSP, GTFS, BPE, Filosofi).
3. Relire dans `labuse-recette-ui` et `labuse-scoring` les faits de qualité déjà établis — ils deviennent des contrôles : permis 7 325 sur 10 799 orphelins récupérés par la géométrie, 580 points d'adresse démis, 2 894 sans localisation ; 484 zones d'aléa mouvement de terrain « élevé / très élevé » ingérées en « moyen » ; DPE qui sautait les communes peuplées ; toits LiDAR au seuil de confiance 0,70 avec 0 faux sur 50 ; cadastre d'époque ; ~8 500 permis longtemps invisibles.

---

## Règles

1. **Un réservoir = un filtre déclaré en code**, `src/labuse/filtres/<source>.py`, même forme pour tous : liste de contrôles, chacun avec `id`, `nature` (`completude` · `referentiel` · `rattachement` · `plage` · `doublon` · `geometrie` · `distribution` · `echantillon`), `severite` (`bloquant` · `avertissant`), `seuil`, `mesure()`.
2. **Le filtre se joue sur une version, jamais sur « la table »** : chaque ingestion est étiquetée par sa version ; le filtre mesure cette version ; le résultat est daté et conservé.
3. **Rien n'est servi sans filtre** : pour les données à portée `run`, la pompe refuse de calculer un candidat sur une version en quarantaine ; pour les données à portée `live`, l'ingestion passe par une table d'attente échangée après filtre (lot 4).
4. **Un contrôle ne détruit rien** : la quarantaine garde la version ; Vic peut servir quand même depuis la page, geste journalisé avec « qui » et « pourquoi ».
5. **Les seuils sont des faits, pas des opinions** : chaque seuil est écrit avec la mesure qui l'a fixé (la valeur au 05/09/2026 sur la version servie) ; il se resserre après, jamais avant d'avoir mesuré.
6. Preuve, témoins, tests, commits, rien de mergé : comme les précédents.

---

## Lot 1 — Le cadre

- 1.1 Module `filtres/` : classe `Controle`, `Filtre` par source, exécuteur `labuse filtre jouer <source> [--version V]`, résultats dans `filtre_resultats(source, version, controle, nature, severite, valeur, seuil, verdict, details_json, joue_le)` et verdict de version dans `filtre_versions(source, version, verdict, bloquants_ko, avertissants_ko, joue_le)`.
- 1.2 **Contrôles universels** hérités par tout filtre sans rien écrire : présence des 24 communes (codes INSEE du référentiel `communes`), nombre de lignes de la version dans un couloir autour de la version précédente (avertissant par défaut, ±30 % ; bloquant si 0 ligne), pas de ligne dupliquée sur la clé déclarée, géométries valides et dans l'emprise de La Réunion (si géométrie), dates dans une plage plausible (si date), millésime déclaré.
- 1.3 **Branchement sur la vanne** : Injecter (CIRCUIT-1 lot 5) enchaîne ingestion → filtre → verdict ; la page affiche « filtre : 12 contrôles, 0 KO » ou « 2 bloquants KO, en quarantaine ». Journal `circuit_journal` : geste `filtre`.
- 1.4 **Garde de la pompe** : `labuse pompe calculer` refuse (message nommant la source et les contrôles) si une source à portée `run` a une version servie en quarantaine ; `basculer` aussi.
- 1.5 Test : un filtre qui n'existe pas pour une source à job = test rouge (`filtres/__init__.py` liste toutes les sources de `sources_ingestion.yaml`).

---

## Lot 2 — Les filtres des vingt sources qui pèsent

Un filtre complet par source, dans l'ordre d'impact, chacun avec ses contrôles propres en plus des universels. Attendus minimaux :

- **Cadastre Etalab** : nombre de parcelles par commune dans un couloir (431 663 au total au 05/09), surfaces > 0, IDU uniques, polygones valides ; `geom_simple` reconstruite après filtre OK.
- **Sitadel** : couverture de localisation (part des permis posés sur une parcelle ou un point d'adresse, mesurée aujourd'hui, seuil avertissant en dessous), liste des non localisés servie à la page, aucun permis « approximatif » servi comme point (contrôle de cohérence avec RETOURS-14), numéros de permis uniques, dates DAU cohérentes (autorisation ≤ ouverture ≤ achèvement), distribution des natures de permis stable.
- **DVF** : mutations par commune et par an dans un couloir, prix au m² dans une plage (bloquant si > 90 000 ou ≤ 0), part des mutations sans surface, doublons de disposition, **étiquette Immeuble** posée à l'ingestion pour les ventes multi-lots (EXPORTS-1 a ré-étiqueté 272 mutations : ce contrôle empêche qu'un « appartement 750 m² · 4,5 M€ » revienne), et le **filtre unique des comparables** d'EXPORTS-1 (lot 2) déclaré ici comme contrôle de qualité nommé — les comparables sont une liste, pas un chiffre, leur seul gardien est ce filtre.
- **GPU / PLU** : 24 communes, zones non vides, somme des surfaces de zones ≈ surface communale (avertissant), md5 des règlements identique à la version annoncée, domaine des lettres de zone conforme au référentiel du registre (CIRCUIT-2).
- **MAJIC** : SIREN à 9 chiffres valides (clé de Luhn), doublons propriétaire, part des parcelles rattachées à un propriétaire moral connue.
- **DPE** : communes couvertes vs attendues, dates d'établissement plausibles, classes dans le domaine A-G, taux de passoires par commune stable (avertissant).
- **Géorisques et PPR (DEAL)** : domaines des niveaux d'aléa, distribution par niveau stable — le glissement « élevé → moyen » de RETOURS-13 devient un contrôle bloquant sur la distribution.
- **SIRENE, INPI, BODACC** : établissements actifs par commune dans un couloir, dates, dédoublonnage.
- **BAN** : part des adresses géocodées, coordonnées dans l'emprise.
- **CoSIA, FLAIR, LiDAR HD** : couverture raster ou de tuiles par commune, et pour LiDAR le seuil de confiance 0,70 rejoué sur les 50 toits contrôlés (0 faux attendu).
- **EDF, OSM / TCSP, GTFS, BPE, Filosofi** : comptes dans un couloir, géométries valides, arrêts ou lignes non vides, carreaux dans l'emprise.

Chaque contrôle est écrit avec la valeur mesurée au moment de sa pose. Compte-rendu : tableau source × contrôles, verdict de la version servie aujourd'hui (on s'attend à des avertissants : c'est l'état réel, pas un échec du mandat).

---

## Lot 3 — L'échantillon vérifié contre le producteur

- 3.1 Pour chaque source du lot 2, un échantillon fixe de 20 à 50 enregistrements (choisis parmi les témoins : les 50 parcelles golden, les 24 communes, les 5 clés) dont la valeur attendue est **lue chez le producteur** — le fichier source brut, l'API du producteur, la page officielle — pas dans nos tables. Stocké dans `filtres/echantillons/<source>.json` avec l'origine de chaque attendu (fichier, ligne, URL).
- 3.2 Le contrôle `echantillon` rejoue l'échantillon à chaque version : tout écart entre notre table et l'attendu producteur = KO avertissant, avec les deux valeurs.
- 3.3 Ce qui demande des yeux humains (le rattachement d'un permis à sa parcelle quand l'adresse est ambiguë, la nature d'un toit) est listé dans `docs/CIRCUIT/ECHANTILLONS-A-VALIDER.md` avec la proposition de CC ; l'échantillon vit sans ces lignes jusqu'à validation ; rien n'attend.

---

## Lot 4 — La quarantaine pour les données servies en direct

- 4.1 Depuis le registre, la liste des sources qui alimentent au moins une donnée à portée `live` (elle change dès l'injection). Pour celles-là, l'ingestion écrit dans `<table>__attente`, le filtre se joue dessus, et l'échange (`ALTER TABLE … RENAME`, dans une transaction, avec les index) n'a lieu que sur verdict OK ou sur « servir quand même » de Vic. La version précédente reste sous `<table>__precedente` jusqu'à la prochaine, pour un retour immédiat.
- 4.2 Pour les sources à portée `run` seulement, pas d'échange de table : la garde de la pompe (1.4) suffit, et le compte-rendu le dit source par source.
- 4.3 Retour arrière d'une source : geste sur la page, journalisé.

---

## Lot 5 — Le filtre de nuit et la page

- 5.1 Job wrapper `filtres-sources` (07:05, avant la sonde de cohérence) : rejoue les contrôles avertissants sur les versions servies (dérive dans le temps : une table modifiée par un correctif, un raster remplacé) ; résultats dans les mêmes tables.
- 5.2 Page Circuit : chaque réservoir porte « filtre OK / n KO / non filtré » et, dans la fiche du bas, chaque contrôle avec sa valeur, son seuil, sa date ; les sources avec une version en quarantaine ont une pastille propre dans le bandeau ; « servir quand même » et « revenir à la version précédente » y vivent, journalisés.
- 5.3 Healthz : une version bloquée en quarantaine depuis plus de 7 jours = avertissement.

---

## Lot 6 — SOURCES-1 par la vanne : les sept sources reportées par EXPORTS-1

Les sources du lot 7 d'EXPORTS-1 n'entrent pas par la porte des exports mais par le Circuit : pour chacune, une ligne `data_sources` + seed, une sonde sentinelle (méthode réelle, URL appelée pour de vrai), une cadence, un filtre (ce mandat) et des ids au registre — avant tout affichage.

Ordre imposé, les deux correctifs d'abord parce qu'ils touchent des chiffres déjà servis :
- 6.1 **CatNat** : `catnat_n` est faux (troncature à 10 arrêtés par commune, commande d'ingestion retirée) — réparer l'ingestion, filtre de complétude (nombre d'arrêtés par commune vs source), fuite soldée avec la valeur avant/après sur les 24 communes.
- 6.2 **Taux communaux et départemental de taxe d'aménagement** : source publique (délibérations, base des taux), sondée ; `taxe_amenagement_eur` cesse d'exiger un taux saisi quand le taux public existe ; l'écart entre taux saisi et taux public devient un contrôle.
- 6.3 Puis, en effort S chacune : DPU (périmètres), PEB de Roland-Garros et Pierrefonds, zonage A/B/C, loyers de marché DHUP, coût de construction EPTB 2024 + dataset CDC (remplace la constante d'`engine.py`).
- 6.4 Chaque source ajoutée apparaît sur le Circuit avec son filtre le jour même ; les ids correspondants (déclarés en CIRCUIT-2 lot 1.8) passent de « non calculée — source absente » à servis.

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-3.md · COMPTE-RENDU-CIRCUIT-3.md · ECHANTILLONS-A-VALIDER.md
src/labuse/filtres/ (cadre, contrôles universels, un fichier par source, echantillons/*.json)
tables filtre_resultats, filtre_versions ; tables __attente / __precedente pour les sources live
CLI labuse filtre jouer · job filtres-sources · garde de la pompe · vanne enchaînée
frontend : état du filtre par réservoir, contrôles dans la fiche du bas, quarantaine, servir quand même, retour
tests : un filtre par source à job (rouge sinon), contrôles universels, échange de table, garde de la pompe, échantillons
```

## Définition de fini

- Toute source à job a un filtre ; les vingt sources du lot 2 ont leurs contrôles propres avec seuils mesurés.
- CatNat et les taux de TA corrigés avec avant/après ; les cinq autres sources de SOURCES-1 entrées par la vanne, ou reportées avec la raison.
- Le verdict de chaque version servie aujourd'hui est en base et sur la page.
- Les sources à données live passent par la table d'attente ; une injection en quarantaine ne se sert pas.
- Les échantillons existent pour les vingt sources, avec l'origine producteur de chaque attendu.
- Suite verte, rien mergé, compte-rendu clos.

## Ce qui reste à Vic, après

Lire le tableau des avertissants de la version servie (c'est l'état réel de ses données au jour du mandat), valider `ECHANTILLONS-A-VALIDER.md` avec Stéphanie quand il veut, merger 1 → 2 → 3.

## Interdits

Ceux des mandats précédents, plus : aucun seuil bloquant sans mesure qui le fonde, aucune version détruite par un filtre, aucun échange de table hors transaction.
