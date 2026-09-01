# MANDAT SENTINELLE-1 — l'agent de version, généralisé à toutes les sources

**Branche : `feat/sentinelle-1`** (depuis `main` après merge de `fix/connexions-3`). Bloc commun habituel.
**Origine** : `CONNEXIONS-RAPPORT.md` M2 — « agent vérifiant une nouvelle version amont : ABSENT », panneau « Agent de veille des sources » grisé V2 (`admin/Sources.tsx:122`). Seul `sentinelle-dvf-cadastre` (`jobs.py:264`) couvre DVF et cadastre.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

## Doctrine du mandat — à ne pas transgresser

L'agent **surveille et prévient. Il ne télécharge rien, n'ingère rien, ne remplace aucune donnée.** Vic décide de chaque mise à jour. Une sentinelle qui déclenche une ingestion serait une violation directe de « rien n'entre sans validation humaine ».

Il **ne visite jamais un portail d'annonces** — les sources concernées sont les fournisseurs de données publiques (IGN, DGFiP, INSEE, Sitadel, BAN, DHUP…). La liste des sources surveillées exclut explicitement toute source de type annonce.

---

## W1 — La table de veille des sources

Créer `source_veille` : `source_id` (FK `data_sources`) · `url_version` · `methode` · `selecteur` · `cadence_heures` (défaut 24) · `dernier_passage_at` · `dernier_vu` (millésime constaté) · `dernier_statut` (`ok` / `nouvelle_version` / `injoignable` / `illisible`) · `dernier_message` · `actif`.

Une source sans ligne dans cette table n'est simplement pas surveillée — c'est un état normal, pas une erreur.

## W2 — Trois méthodes de détection, pas plus

Le millésime amont se lit de trois façons ; chaque source déclare la sienne dans `methode` :

1. **`api`** — le fournisseur expose un JSON de versions (cas le plus propre, ex. les API de millésimes IGN). `selecteur` = chemin JSON.
2. **`page`** — on lit une page HTML et on en extrait un motif de millésime (`selecteur` = expression régulière, ex. `20\d{2}-S[12]`). Prendre le **plus récent** trouvé, jamais le premier venu.
3. **`entete`** — pas de millésime lisible : on compare `Last-Modified` ou `ETag` du fichier amont à celui du dernier téléchargement. Signale « le fichier amont a changé », sans nommer de version.

Reprendre `sentinelle-dvf-cadastre` (`jobs.py:264`) comme **premier cas d'usage** : il devient une ligne de `source_veille`, pas un job à part. Vérifier qu'il donne le même résultat qu'avant — c'est le test de non-régression du mandat.

## W3 — Le job quotidien

1. Job `sentinelle-sources`, une fois par jour, qui parcourt les lignes `actif=true` dont la cadence est échue.
2. Pour chaque source : appel **one-shot**, timeout court, **aucun retry en boucle**, User-Agent identifiant LABUSE. Les sources sont interrogées **séquentiellement avec un délai** entre deux appels — on ne martèle pas un serveur public.
3. Comparaison au `source_millesime` réellement servi (celui de `data_sources`, cf. Lot 6 de CONNEXIONS-2), pas à une valeur en dur.
4. Écriture du résultat dans `source_veille`. **Aucune écriture dans `data_sources`** : l'état servi ne bouge pas.
5. Une source injoignable ou illisible n'est **pas** une source en erreur : c'est la sentinelle qui a échoué, pas la donnée. Les deux états restent distincts partout.

## W4 — Ce que Vic voit

1. **Notification admin** à la première détection d'une nouvelle version, **dédupliquée** : une notification par source et par millésime constaté, jamais un rappel quotidien. Formulation : « DVF : 2026-S1 est publié — vous servez 2025-S2 ».
2. **Dashboard, tuile Sources** : nombre de sources avec une nouvelle version disponible, lien vers la liste.
3. **Page Sources (admin)** : le panneau « Agent de veille des sources » (`admin/Sources.tsx:122`) sort de son état grisé. Par source : millésime servi · millésime amont · date du dernier passage · statut. Actions : **« Vérifier maintenant »** (lance la sonde sur cette source) et **activer/désactiver** la surveillance.
4. **Rien côté client** : la sentinelle est un outil d'exploitation, elle n'apparaît sur aucun écran abonné.

## W5 — Peupler la table

1. Inventorier les sources de `data_sources` et, pour chacune, chercher si le fournisseur expose une page ou une API de version. Renseigner `url_version`, `methode` et `selecteur` **pour celles où c'est possible sans effort disproportionné**.
2. Les autres restent non surveillées, avec au compte-rendu **la liste et la raison** (pas d'URL stable, millésime non publié, source manuelle…).
3. Ne pas inventer d'URL. Une URL non vérifiée est pire qu'une absence : elle produira un statut `injoignable` permanent qui polluera le tableau.
4. Au compte-rendu : combien de sources surveillées sur combien, ventilées par méthode.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : W2 la reprise de `sentinelle-dvf-cadastre` donne-t-elle le même résultat qu'avant · W5 nombre de sources surveillées / total, ventilation par méthode, et liste des non surveillées avec la raison. Commit par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/sentinelle-1
```
