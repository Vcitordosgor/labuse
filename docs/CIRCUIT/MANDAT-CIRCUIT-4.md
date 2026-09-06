# MANDAT CIRCUIT-4 — La règle : chaque calcul adossé à sa référence

Branche : `feat/circuit-4`, worktree `~/Desktop/labuse-audit`, créée depuis `main` si `feat/circuit-page` y est mergée, sinon depuis `feat/circuit-page`.
Dossier : `docs/CIRCUIT/`. Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-4.md`.
Prérequis : CIRCUIT-1, 2, 3 et P (la page en trois onglets) clos. Tout calcul vit dans `registre/moteurs/` (CIRCUIT-1 lot 2) : l'inventaire des maths, c'est la liste de ces fonctions.
Objectif : que le circuit ne vérifie plus seulement que tout le monde dit la même chose que le moteur, mais que le moteur dit la même chose que la règle. Pour chaque calcul : la formule telle qu'elle est codée, la référence qui la fonde (article, barème, méthode) ou le choix LABUSE assumé, un exemple calculé indépendamment et épinglé en test, et un verdict visible sur le circuit.

Vocabulaire nouveau : **règle** = la référence externe qui fonde un calcul · **classe d'une donnée** : `regle_externe` (une loi, un code, un barème, un arrêté la définit) · `methode_standard` (une méthode statistique ou technique reconnue) · `choix_labuse` (une définition à nous, assumée) · `modele` (le scoring : pas de formule officielle, une validation) · **exemple témoin** = un calcul refait à la main, hors du moteur, sur une clé connue.

---

## Autonomie

Mêmes règles (aucune question, doutes écrits, lots sautés plutôt qu'attendus, branche jamais rouge, push par lot, reprise par « continue CIRCUIT-4 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-4.md »). **Une limite propre à ce mandat : un écart entre la formule codée et un texte de loi n'est jamais corrigé en autonomie.** Lire un article reste un jugement humain ; CC constate, documente, propose, et laisse la formule en place. Seules les erreurs d'arithmétique pure (unité fausse, division inversée, arrondi qui change un résultat) sont corrigées, avec test, et listées à part.

---

## Étape 0

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre, sinon stop. Branche `feat/circuit-4`. Suite verte, nombre noté.
2. Lire les comptes-rendus 1 à 3, `registre/donnees.py`, `registre/moteurs/`, et les références déjà connues dans la doc : loi 2025-1129 du 26/11/2025 (art. L151-36 : stationnement allégé, 800 m à vol d'oiseau d'une station TCSP, 1 place par logement, 0,5 pour le logement social), CDAC au-delà de 1 000 m² (L752-1), décret ZFANG 2026-421, calibration des 23 règlements PLU + Saint-Philippe au RNU, la méthode du prix de secteur (médiane, 5 % d'extrêmes exclus, segments type × période, rayon adaptatif), la méthode « même type de bien, seuil 30 » pour affiché vs acté, le modèle m36-l2f-2026 et ses métriques.

---

## Règles

1. **Un calcul = une fiche de règle**, `src/labuse/regles/<donnee_id>.py` : `formule_codee` (en français et en notation mathématique, écrite depuis le code, pas depuis la doc), `entrees`, `classe`, `reference` (titre, article ou section, URL, version ou date du texte, extrait), `verdict`, `exemple_temoin`, `valide_par` (`cc` · `vic` · `stephanie` · `en_attente`), `verifie_le`.
2. **Pas de verdict « conforme » sans extrait** : la référence doit être un passage réellement lu, cité, daté. Sans passage, le verdict est « référence introuvable », jamais « conforme ».
3. **Un exemple témoin est calculé hors du moteur** : un script indépendant dans `tests/regles/` refait le calcul depuis les entrées brutes avec la formule de la référence ; il ne réutilise aucune fonction du moteur. C'est la seule garde qui attrape une dérive de formule.
4. **Une donnée `modele` n'a pas de règle** : sa justesse est le backtest et le golden, déjà en place ; la fiche de règle le dit, avec les métriques du run servi.
5. **Un choix LABUSE est écrit, pas caché** : la fiche dit pourquoi ce dénominateur, cette fenêtre, ce seuil, et depuis quand.
6. Preuve, témoins, tests, commits, rien de mergé : comme les précédents.

---

## Lot 1 — L'inventaire des calculs

- 1.1 Depuis `registre/moteurs/`, la liste exhaustive des fonctions qui calculent (tout ce qui n'est pas passe-plat), avec leurs opérations (somme, ratio, médiane, seuil, intersection géométrique, tranche) — `docs/CIRCUIT/CALCULS-INVENTAIRE.md`, une ligne par fonction : donnée(s) servie(s), opérations, entrées, classe proposée.
- 1.2 Classement par classe. Ordre de traitement : `regle_externe` d'abord (c'est là que se joue la responsabilité), puis `methode_standard`, puis `choix_labuse`, puis `modele`.
- 1.3 Garde : un test refuse toute fonction de `registre/moteurs/` sans fiche de règle (`regles/__init__.py` liste les deux côtés).

---

## Lot 2 — Les règles externes

Attendus minimaux, chacun avec extrait daté et exemple témoin :

- **SDP résiduelle et constructibilité** : définition de la surface de plancher (Code de l'urbanisme, art. R111-22) ; emprise au sol, hauteur, reculs, CES et coefficients lus dans le règlement de la zone (GPU, calibration des 23 PLU ; Saint-Philippe au RNU : règles nationales) ; la formule du résiduel pose ces règles dans l'ordre du règlement ; exemple sur BW0917 et sur une parcelle en zone U de chaque commune calibrée.
- **Taxe d'aménagement** : base (surface taxable, art. L331-10 s.), valeur forfaitaire de l'année en vigueur (arrêté annuel), taux communal et départemental (délibérations, source déclarée par commune), abattements et exonérations appliqués ; exemple sur un projet témoin par commune.
- **Stationnement allégé (TCSP)** : L151-36 tel qu'issu de la loi 2025-1129 — rayon 800 m à vol d'oiseau, plafonds 1 et 0,5 ; la couche et la fiche appliquent la même règle.
- **CDAC** : seuil 1 000 m² (L752-1), nature des surfaces comptées.
- **Littoral et 50 pas géométriques** : articles applicables, bande, exceptions.
- **ZFANG / FRR** : décret 2026-421, périmètres et effets affichés.
- **Permis (Sitadel)** : définitions SDES des logements autorisés, commencés, annulés ; fenêtre « 24 mois glissants » et « point mort » comparées aux définitions officielles, écart écrit si LABUSE s'en écarte (alors classe `choix_labuse` explicite).
- **DPE** : classes A-G et seuils de l'arrêté du 31/03/2021, passoires F-G.
- **PPR** : niveaux d'aléa et prescriptions tels que les règlements DEAL les définissent ; domaine des classes.
- **DVF** : définitions DGFiP (mutation, disposition, nature, prix) et exclusions appliquées.
- **Population, équipements, carreaux** : définitions INSEE (Filosofi 200 m, BPE).

**L'agent « règle »** (Claude + recherche web, surface `agent_regle` dans `SURFACES`, même façade que l'agent source de CIRCUIT-1) va lire Légifrance, service-public, impots.gouv, ADEME, INSEE, la DEAL, et ramène l'extrait, l'URL, la date de version ; anti-invention identique ; pages en JavaScript notées `introuvable, navigateur nécessaire`. Chaque fiche de règle porte l'extrait ramené.

Verdicts : `conforme`, `ecart` (avec le passage en face et la différence), `reference_introuvable`, `partiel` (une partie de la règle non implémentée, dite). Les écarts vont dans `docs/CIRCUIT/REGLES-ECARTS.md`.

---

## Lot 3 — Les méthodes standard et les choix LABUSE

- 3.1 **Méthodes** : prix de secteur (médiane, exclusion des 5 % d'extrêmes, segments type × période, rayon adaptatif), affiché vs acté (même type, seuil 30), isochrones (moteur et profil), rayon d'étude de zone, parts et taux (dénominateurs) — chaque fiche cite la méthode (source statistique ou technique) et son exemple témoin refait à la main.
- 3.2 **Choix LABUSE** : pour chaque donnée sans référence externe (paliers, seuils de « potentiel », fenêtres, exclusions), la fiche écrit la définition, le pourquoi (s'il est documenté quelque part : mandats, comptes-rendus, décisions de Vic dans `docs/`), la date et l'auteur ; `valide_par = en_attente` pour ce que CC ne trouve pas justifié — la liste va dans `docs/CIRCUIT/CHOIX-LABUSE.md` pour Vic, sans rien bloquer.
- 3.3 **Modèle** : la fiche du scoring et des paliers renvoie aux métriques du run servi (backtest, PR-AUC, calibration, stabilité de classement) et au golden ; pas de règle inventée.

---

## Lot 4 — Les exemples témoins épinglés

- 4.1 Pour chaque fiche `conforme` ou `choix_labuse` : un test `tests/regles/test_<donnee>.py` qui recalcule la donnée sur une clé témoin **avec une implémentation indépendante** (lecture des entrées brutes, application de la formule de la référence, comparaison au moteur à la tolérance déclarée).
- 4.2 Pour chaque fiche `ecart` : le même test, marqué `xfail` avec le motif et le lien vers `REGLES-ECARTS.md` — il passera au vert le jour où Vic tranche et que la formule change.
- 4.3 Les tests de règle sont rangés dans la suite normale ; ils s'exécutent au `pytest` de chaque mandat futur. Objectif : au moins un exemple témoin par fonction de calcul.

---

## Lot 5 — La règle sur le circuit

- 5.1 Le registre porte pour chaque donnée `classe`, `reference`, `verdict`, `verifie_le`, `valide_par` ; `labuse registre sync` les met en base.
- 5.2 Page de détail d'un robinet (CIRCUIT-P, `Detail.tsx`) et tiroir de traçage : badge par donnée — conforme (mint), écart (rouge), référence introuvable (ambre), choix LABUSE (gris, avec la définition), modèle (mauve, avec ses métriques) — et le lien vers l'extrait de référence.
- 5.3 Résumé (CIRCUIT-P, `circuit_resume.py`) : lignes « n écarts à la règle » (à corriger) et « n choix LABUSE à confirmer » (à décider), chacune menant aux robinets concernés.
- 5.4 Job wrapper `regles-references` mensuel, désactivé par défaut : renvoie les agents « règle » sur les références datées de plus de six mois (un texte peut changer) et signale toute version nouvelle.

---

## Lot 6 — Les erreurs d'arithmétique pure

Ce que CC a le droit de corriger seul : une unité (m² pour ha), un arrondi qui change une classe, une division inversée, un signe, un seuil comparé strictement au lieu de largement quand la référence est claire. Chaque correction : avant/après sur les témoins, test, et une ligne dans `docs/CIRCUIT/CORRECTIONS-ARITHMETIQUE.md`. Tout le reste attend Vic.

---

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-4.md · COMPTE-RENDU-CIRCUIT-4.md
docs/CIRCUIT/CALCULS-INVENTAIRE.md · REGLES-ECARTS.md · CHOIX-LABUSE.md · CORRECTIONS-ARITHMETIQUE.md
src/labuse/regles/ (une fiche par donnée calculée) · registre étendu (classe, référence, verdict)
agent « règle » (surface agent_regle) · job regles-references (désactivé)
tests/regles/ : une implémentation indépendante par calcul, xfail motivés pour les écarts
frontend : badges de règle, extraits de référence, pastilles du bandeau
```

## Définition de fini

- Chaque fonction de `registre/moteurs/` a sa fiche de règle et son exemple témoin indépendant ; la garde du lot 1.3 passe.
- Chaque règle externe a un extrait daté ou porte « référence introuvable » avec ce qui a été tenté.
- `REGLES-ECARTS.md` et `CHOIX-LABUSE.md` sont complets et lisibles sans le code : une ligne par décision attendue, avec l'impact (robinets touchés, exemple chiffré).
- Aucun écart à la loi corrigé en autonomie ; les corrections d'arithmétique pure sont listées avec test.
- Suite verte, rien mergé.

## Ce qui reste à Vic, après

C'est le seul mandat des quatre qui lui rend une vraie décision : trancher `REGLES-ECARTS.md` avec Stéphanie (chaque ligne : la formule codée, le texte, l'écart, la proposition) et confirmer ou corriger `CHOIX-LABUSE.md`. Puis merger 1 → 2 → 3 → 4, et les `xfail` se lèvent au fil des arbitrages.

## Interdits

Ceux des mandats précédents, plus : aucun verdict « conforme » sans extrait, aucune correction de formule fondée sur une lecture de la loi sans Vic, aucun exemple témoin qui réutilise le moteur qu'il est censé vérifier.
