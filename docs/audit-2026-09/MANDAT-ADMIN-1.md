# MANDAT ADMIN-1 — la refonte du dashboard : une page par question

**Branche : `feat/admin-1`** (depuis `main`). Bloc commun habituel.

**Maquettes validées** (chiffres fictifs, structure de référence) :
- `docs/audit-2026-09/maquette-admin-donnees.html` — page Données (AD2)
- `docs/audit-2026-09/maquette-admin-comptes.html` — page Comptes (AD4)
- `docs/audit-2026-09/maquette-admin-pages.html` — Pilotage (AD5), IA (AD6), Produit (AD7), Courrier (AD8), Radar (AD9), Contacts (AD10), Scan patrimoine (AD3)

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

**Principe** : chaque page répond à UNE question. Données → « mes données sont-elles à jour ? ». Comptes → « que dois-je faire pour ce client ? ». Pilotage → « comment va le produit ? ». On réorganise autour de la question. **Aucune mécanique n'est réécrite** : sentinelle, X6, jobs, mails Brevo, quotas, signalements se REBRANCHENT.

---

## AD1 — Fiche parcelle : couleurs des boutons

« + CRM » en **vert** (contour `--mint`, survol plein vert encre sombre). « + Projet » en **jaune** (contour et texte `--amber`, survol plein ambre encre sombre) — même famille que la chip « Fiche commune ». Largeurs égales, aucun mauve.

## AD2 — Page « Données » : fusion Sources + Cron + Agent de veille + Flux

Maquette A. Les quatre pages deviennent **une**, trois onglets :

1. **Catalogue** : une ligne par source — nom + fournisseur + méthode · millésime **servi** · **amont** (« 2026-S1 disponible » / « identique » / « manuelle (toi) » / « non surveillée » + raison) · dernier passage · fraîcheur (rappels manuels échus en rouge) · actions contextuelles : **Injecter** (X6, si nouvelle version), **Vérifier** (sonde immédiate), **Relancer l'ingestion**, **⏸**. Recherche, chips de filtre, groupement par fournisseur.
2. **Circuit** : la page Flux actuelle (bandeau 3 gestes, fourmilière, compteur Radar, garde de cohérence) déplacée ici telle quelle.
3. **Horloge** : liste réelle des jobs planifiés (nom, ce qu'il fait en une phrase, fréquence, dernier passage, durée, statut, prochain passage) + « Lancer maintenant ». La page Cron vide disparaît, absorbée ici.
4. Bandeau « 3 gestes » condensé en tête, commun aux trois onglets.
5. **Navigation** : le menu admin remplace Sources / Cron / Flux / Agent par « Données ». Anciennes URL redirigées.
6. **Cadence** : sur une ligne surveillée, cadence de sonde éditable (24 h par défaut) — le job ne passant qu'une fois par jour, une cadence inférieure n'a pas d'effet et l'UI le dit ; sur une manuelle, « cadence attendue » = seuil de rappel, infobulle « n'appelle personne : c'est votre rappel ».
7. **Vérité du bouton « Relancer l'ingestion »** : établir ce que fait exactement le bouton actuel (quel job, quelle version, quels effets en base) et faire dire à l'infobulle **exactement ça**, en une phrase. Si le comportement diffère de « recharger la version déjà servie », le compte-rendu le dit.
8. Le pied de page « Qui fait quoi » de la maquette est repris tel quel.

## AD3 — Scan patrimoine : le modèle en deux temps, strict

Problème : une fois CBO choisi, « Ce qu'ils construisent » montre TOUTES les opérations de l'île (2 357) avec filtres commune/catégorie — mélange entre scan du propriétaire et exploration générale.

1. **Propriétaire choisi** → l'onglet ne montre **que ses opérations** : « 14 opérations · 612 logements », carte + liste centrées dessus. **Aucun filtre commune/catégorie/date, aucun total global.** Le champ « se positionner » disparaît de ce mode.
2. **L'exploration générale** (toutes opérations, filtres, totaux) devient un mode séparé : « Explorer toutes les opérations → » accessible depuis l'état 1. On y garde tout l'existant.
3. Libellé : « Ce qu'ils construisent (14) », sous-titre avec la période réelle des permis Sitadel (« construit ou en cours — permis depuis AAAA, données au 30/06/2026 »).
4. Maquette : section 7 de `maquette-admin-pages.html`.

## AD4 — Page « Comptes » : la fiche client

Maquette B, à la lettre :

1. **Création en une ligne** (email, nom optionnel, « Créer & préparer l'invitation » / « ou essai 48 h »). Créer ne poste aucun mail : l'envoi est un geste séparé sur la fiche.
2. **Liste à gauche** : statut coloré, drapeau « ⚑ action en attente » calculé (invitation à envoyer, bienvenue à envoyer, relance J+3 atteinte, dernier rappel J+10 atteint, lien Stripe à envoyer).
3. **Fiche à droite** : en-tête (statut, essai + échéance), carte **« Prochaine action »** avec aperçu + Envoyer, puis le **parcours** en étapes datées.
4. **Renommer les mails partout** (UI, templates, code) : mail 1 → **« Mail de bienvenue »**, mail 2 → **« Relance J+3 »**, mail 3 → **« Dernier rappel J+10 »**. Chaque ligne a « aperçu » (rendu réel du template Brevo avec les variables du compte) avant « Envoyer ».
5. KPI (usage 7 j, dernière connexion, Copilote du jour) et règle de suspension manuelle conservés.
6. L'onboarding « 3 étapes » actuel disparaît. Rien d'automatique de plus : les envois restent des clics.

## AD5 — Pilotage

1. **Retirer la tuile Courrier** (le courrier vit dans sa page).
2. Deux rangées : **À faire** (ambre, cliquable) — sources avec nouvelle version, essais expirant sous 24 h, signalements ouverts, données manuelles en retard. **Santé/traction** (vert) — licences & MRR, garde de cohérence, veilles 7 j, paires annonce ↔ DVF.
3. Les highlights existants sont conservés tels quels en bas.

## AD6 — Page IA

1. **Unités** : « 0,79 ct » devient « 0,79 **centime** / question » avec dessous « 0,51 € ÷ 65 appels ». Plus d'ambiguïté ct/€.
2. « Quota pilote » renommé **« Plafond quotidien par compte »**. Table : compte · consommé/plafond aujourd'hui · 30 j · coût 30 j · plafond **éditable en ligne**. C'est ça, allouer. L'UI précise que le budget € global est côté console Anthropic (lien) ; l'app ne répartit que des appels.
3. **Vérifier en réel** que l'édition prend effet immédiatement sur `/ask` : éditer, poser une question avec un compte témoin, voir le compteur. Résultat au compte-rendu.
4. Le registre surface → modèle (RETOURS-7 Z7) reste sur cette page, sous la table.

## AD7 — Page Produit

1. Usage par outil : sélecteur **7 / 30 / 90 j**, tri par volume, et bloc « **Jamais ouverts sur la période** » en évidence.
2. Retours clients : filtres **par compte** et **par statut**, branchés sur la table signalements unifiée de CONNEXIONS-2 — pas une seconde liste.
3. **Recette réelle du bouton « Signaler »** : envoyer un signalement depuis l'app cliente (compte témoin), le voir arriver ici et dans le compteur Pilotage. Résultat au compte-rendu.

## AD8 — Page Courrier admin

1. **Vue par compte** : filtre compte en tête, chips statut (demande / à déposer / envoyé / répondu / sans réponse — statuts unifiés de CONNEXIONS-2), **« à déposer » par défaut**.
2. Chaque ligne : compte · parcelle/propriétaire · date · statut · **aperçu du courrier réel** · actions **Marquer déposé** / **Marquer envoyé** · lien vers la piste CRM d'origine.
3. Aucun changement de mécanique — même table `courrier_demandes`, mieux présentée.

## AD9 — Radar admin

1. Trois blocs **repliables** : Déposer (dépôt HTML + agence + chemin historique replié) · File d'extraction (badge N) · Re-vérification.
2. Re-vérification **groupée par commune**, tri par ancienneté du dernier contrôle, boutons inchangés, compteur « N vérifiées aujourd'hui ».
3. Le bandeau descriptif se replie après première lecture (état mémorisé).

## AD10 — Contacts de communes

1. Table `commune_contacts` : commune · nom · rôle · téléphone · email · note · ajouté le. **CRUD admin** depuis la page Contacts **et** depuis la fiche commune (bouton « + Ajouter un contact » dans la carte Mairie). Cible : Saint-André → « Mme Gwenaëlle Serveau — resp. PLU, tél, mail ».
2. Les contacts s'affichent dans la carte Mairie de la fiche commune (tous comptes), sous le standard officiel, avec leur rôle.
3. **Refonte de la page Contacts** : recherche en tête, une carte par commune (standard + contacts ajoutés), édition en place. Pas de tableau géant.

## AD12 — La page « Programme » : à quoi sert-elle ?

Vic ne sait pas pourquoi cette page existe. Au compte-rendu : ce qu'elle fait, quel code la sert, qui l'utilise (usage 30 j), et une recommandation en trois lignes — fusionner dans Radar ou Scan, garder, ou retirer du menu. **Aucune suppression dans ce mandat** : Vic tranche.

## AD11 — Vérification : Vic est le seul admin

Requête sur les comptes `role = admin` (ou équivalent). Résultat exact au compte-rendu : combien, lesquels. Si plus d'un, **ne rien changer** — lister et laisser Vic trancher. Ajouter un test qui échoue si un compte non-admin accède à une route admin.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : AD2 les jobs réellement listés dans Horloge · AD2.7 ce que fait vraiment « Relancer l'ingestion » · AD12 rôle et usage de la page Programme · AD6.3 la recette réelle du plafond · AD7.3 la recette réelle du bouton Signaler · AD11 la liste des admins. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/admin-1
```
