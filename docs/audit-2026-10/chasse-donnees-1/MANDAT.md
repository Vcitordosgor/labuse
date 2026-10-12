# MANDAT-CHASSE-DONNEES-1 — la bonne donnée, au bon endroit, la même partout

Rédigé le 12/10/2026. Modèle : Opus (deux sessions si besoin, le rapport est repris là où il s'arrête). Branche `audit/chasse-donnees-1` depuis main, worktree `~/Desktop/labuse-chasse-donnees`, ports 8740/5940. **Lecture seule : aucun correctif, aucune écriture en base, aucun run.** À lancer après le déploiement de q_v18, sur le local (qui fait foi) puis en comparaison avec la prod.

## Ce que cherche Vic

Une information = une source = une valeur, servie à l'identique partout où elle apparaît. Trois façons d'échouer, et ce mandat les chasse toutes :

1. **Fausse** : la valeur ne correspond pas à la source officielle.
2. **Divergente** : la même information n'a pas la même valeur selon l'endroit (fiche, carte, filtre, outil, fiche commune, Dossier, Flash, Copilote, Radar, veille, mail, API partenaire, dashboard), ou la même source est lue par plusieurs chemins qui ne donnent pas le même résultat.
3. **Mal placée** : la valeur est juste mais son étiquette ment (unité, rayon, période, millésime, contenance vs dessin, HT), ou un zéro remplace une absence.

Une chasse qui revient vide est un bon résultat : elle se prouve, elle ne se déclare pas.

## Règles

- **Étape 0** : `pwd`, branche, arbre propre. Base locale servant q_v18 (vérifier `served_run.txt`).
- Ne pas refaire les chasses passées (COHERENCE-AUDIT-1, ORACLE-1, CHASSE-1/2, CONNEXIONS-1, FRONT-CHIFFRES) : les lire, reprendre leur banc `scripts/coherence` et leurs oracles, et **chasser ce qu'elles n'ont pas couvert**. Toute reprise d'un écart déjà connu doit dire s'il a été corrigé ou non.
- Chaque écart est **reproductible** : requête SQL ou appel d'API, parcelle ou commune témoin, valeur A, valeur B, source, fichier:ligne des deux chemins.
- Pas de correctif, pas de refonte suggérée : un écart, une cause, une preuve. Les corrections viendront dans CHASSE-DONNEES-FIX-1.
- Le banc doit être **rejouable** par une seule commande (`scripts/coherence/...`), pour devenir la garde automatique.

## Lot A — l'inventaire de lignée (le socle, à faire avant tout)

Pour **chaque information servie au client** (chiffre, libellé, date, statut, badge, couleur de carte), une ligne dans `LIGNEE.csv` :

`notion · source amont · table(s) · moteur/calcul (fichier:fonction) · lecteurs (chaque surface qui l'affiche, fichier:ligne) · étiquette affichée · unité · millésime affiché · comment l'absence est rendue`

Méthode : partir des payloads d'API (fiche, communes, outils, filtres, tuiles, exports, flash, copilote, partners, radar, veille, mails Brevo, dashboard) et des rendus front/PDF, pas d'une liste a priori. Objectif : 100 % des informations, pas les 286 notions du banc existant. Signaler dans une colonne : `lecteurs = 1` (pas de divergence possible) ou `≥ 2` (à comparer en Lot C).

Et l'inverse, `SOURCES-LECTEURS.csv` : pour chaque table de source, **tous** les chemins de code qui la lisent, avec leurs filtres et paramètres (rayon, période, seuil, exclusions). Deux chemins pour la même notion avec des paramètres différents = écart « divergence latente », même si aucune parcelle témoin ne la révèle.

## Lot B — les témoins

40 parcelles choisies **pour mettre la donnée en difficulté**, pas au hasard : nouvelle parcelle du cadastre d'octobre · parcelle disparue (ouverte depuis un projet) · surface incertaine (DV0285) · contenance ≠ dessin de plus de 5 % (CW0658) · sans contenance · à cheval sur deux zones PLU · zone AU fermée · zone rouge partielle (AK0804) · PPR multiple · Saint-Philippe (RNU) · GPU dépublié (Saint-André, Saint-Leu) · propriétaire SCI avec dirigeant · propriétaire absent · copropriété · parcelle avec permis annulé · avec vente DVF récente et multi-parcelles · dans un QPV · en ORT · littoral · sans adresse BAN · bâti dense · terrain nu · parcelle suivie par une veille · parcelle en CRM · parcelle d'un Flash test. Plus les 24 communes.

Chaque témoin est listé avec la raison de son choix.

## Lot C — même donnée, même valeur partout

Pour chaque témoin et chaque notion à `lecteurs ≥ 2` : relever la valeur sur **chaque** lecteur au même instant (API, propriétés de tuile, compteur de filtre, outil, fiche commune, Dossier PDF et Flash PDF extraits en texte, Copilote sur question déterministe, Radar, veille, mail rendu, API partenaire, dashboard). Matrice `notion × lecteur` par témoin. Toute différence = écart, y compris d'arrondi, d'unité, de millésime ou de libellé.

Agrégats : total d'une fiche commune = somme des parcelles ; compteur d'un filtre = longueur de la liste = chiffre des stats ; carte (tuiles) = run servi = fiche. Les 24 communes, pas un échantillon.

## Lot D — la vérité face à la source

Pour 20 notions au moins (et pas seulement celles d'ORACLE-1) : la valeur servie contre la source officielle lue aujourd'hui (cadastre IGN, GPU, Géorisques, fichier DVF Etalab, Sitadel, SIRENE/RNE, BAN, INSEE, DPE ADEME, BODACC), sur les 40 témoins. Les règles PLU affichées relues dans le règlement pour 10 zones non couvertes par ORACLE-1.

Et la fraîcheur : chaque millésime affiché (fiche, Sources, pied de PDF) = date maximale réelle dans la table.

## Lot E — étiquettes et absences

Pour chaque notion : l'étiquette dit-elle exactement ce qui est calculé (rayon réel, période réelle, unité, contenance vs dessin, « estimé » quand c'est estimé, source nommée) ? Une absence est-elle rendue comme une absence (« non renseigné », « sous seuil ») et jamais comme 0, 0 %, « aucun » ? Relever tout chiffre codé en dur dans le front hors registre apparu depuis FRONT-CHIFFRES-2.

## Lot F — local contre prod (après le déploiement)

Les 40 témoins rejoués sur app.labuse.immo et en local : même valeur partout. Tout écart local/prod est un écart de déploiement, à part dans le rapport.

## Livrables

`docs/audit-2026-10/chasse-donnees-1/` : `LIGNEE.csv`, `SOURCES-LECTEURS.csv`, `TEMOINS.md`, `ECARTS.md` (une ligne par écart : notion · gravité · témoin · valeur A / valeur B / source · cause · fichier:ligne · reproduction), `RAPPORT.md` (5 lignes de verdict en tête), banc rejouable étendu.

Gravité : **FAUX-CLIENT** (valeur fausse servie) · **DIVERGENT** (deux valeurs pour une notion) · **LATENT** (deux chemins, pas encore de témoin qui diverge) · **ÉTIQUETTE** · **ABSENCE** · **FRAÎCHEUR**.

Un commit par lot. Ne merge pas.
