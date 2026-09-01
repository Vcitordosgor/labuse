# MANDAT SENTINELLE-3 — second passage sur les 27 non surveillées

**Branche : `feat/sentinelle-3`** (depuis `main` après merge de `feat/sentinelle-2`). Bloc commun habituel.
**Source** : `docs/audit-2026-09/SENTINELLE-INVENTAIRE.md` — 35 surveillées / 64, 27 non surveillées, 2 doublons couverts.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

## Doctrine — inchangée

La sentinelle surveille et prévient, n'ingère jamais d'elle-même (X6 : clic humain obligatoire). Aucune source d'annonces. Appels one-shot, séquentiels, espacés, UA LABUSE.

**Règle inchangée et non négociable** : une URL n'est inscrite que si elle a été **appelée pour de vrai** et sa réponse lue. SENTINELLE-2 a montré ce que coûte l'inverse — 2 des 6 seeds de SENTINELLE-1 étaient faux faute d'avoir été testés.

**Et une règle nouvelle** : mieux vaut une sonde imparfaite qui détecte un changement qu'aucune sonde. Une source dont on ne peut pas lire le millésime mais dont on peut constater que le fichier a changé **est surveillable** — l'alerte dira « la donnée amont a changé » au lieu de nommer une version. C'est utile et honnête.

---

## Y1 — Les 6 récupérables : retenter

Ces six ont échoué sur des causes potentiellement passagères ou contournables. Priorité absolue du mandat.

1. **DEAL Réunion — PPR, 50 pas géométriques, DEAL WMS** : proxys Lizmap injoignables au moment du test du 01/09. Retenter. Si toujours muets : chercher l'amont réel (les couches DEAL sont souvent republiées sur data.gouv.fr, sur le portail PEIGEO, ou exposées en WFS avec un `GetCapabilities` daté). Un `GetCapabilities` WMS/WFS contient souvent une date ou un numéro de version — c'est une méthode `page` valable. **Les PPR sont une source à fort enjeu** (le risque figure dans les fiches parcelles) : épuiser les pistes avant de renoncer.
2. **Légifrance — ZFANG, FRR** : la page est rendue en JavaScript, aucun millésime lisible, et le « 2067 » capté était un faux positif. Pistes : l'API Légifrance (DILA, авторisation requise — vérifier si un endpoint public de version existe), le flux de publication du Journal officiel, ou le jeu correspondant sur data.gouv.fr. À défaut, surveiller la page en `entete`.

## Y2 — Les hubs : surveiller le catalogue, pas le contenu

Région ODS, Géoplateforme IGN, PEIGEO sont des portails, pas des jeux — d'où l'échec. Mais un portail publie un **catalogue**, et un catalogue change quand un jeu apparaît ou est mis à jour.

Vérifier si chacun expose une API de catalogue (Opendatasoft `/api/explore/v2.1/catalog/datasets`, CSW/GeoNetwork pour Géoplateforme et PEIGEO). Si oui, la sonde compare le **nombre de jeux** ou la date de dernière modification du catalogue, et alerte « le catalogue a évolué ». Utile : c'est ainsi que tu apprends qu'une nouvelle couche exploitable existe.

Si aucune API de catalogue n'est exposée, la source reste non surveillée — mais alors la raison en base devient exacte (« portail sans API de catalogue »), pas « hub ».

## Y3 — Les API de requête : la requête témoin

GPU apicarto (×3), Géorisques live (cavités, mouvements, sites pollués), INPI, recherche-entreprises, OSM (×3). Elles n'ont pas de millésime — mais elles ont un **comportement**.

Pour chacune, essayer une **requête témoin** : une requête figée sur une zone stable de La Réunion, dont on stocke une empreinte de la réponse (nombre d'objets, ou hachage d'un champ stable — pas la réponse entière). La sonde compare l'empreinte au passage précédent ; si elle change, la donnée amont a bougé.

Conditions strictes :
- La requête témoin doit être **légère** (une commune, un rayon court, une limite de résultats) — on ne fait pas travailler un service public pour rien.
- Elle est **identique à chaque passage**, sinon l'empreinte n'a aucun sens.
- Si le service renvoie des résultats non déterministes (ordre variable, champs horodatés), l'empreinte doit porter sur un agrégat stable (un compte), pas sur le contenu brut. Si même un compte est instable, abandonner cette source et le dire.
- Ces sondes portent la méthode `temoin` (nouvelle) et sont clairement distinguées dans le panneau : elles disent « la donnée amont a changé », jamais un numéro de version.

**Ne pas forcer** : une API dont la réponse bouge à chaque appel produirait une alerte quotidienne inutile. Mieux vaut la laisser non surveillée que d'inventer du bruit. Le compte-rendu dit lesquelles ont été écartées pour cette raison.

## Y4 — Les manuelles : rien à faire, mais le dire mieux

Radar/pige, SPANC, fichiers fonciers sous convention, MOBPRO, Office de l'eau : alimentées par Vic, aucun amont public. **Aucune sonde.**

En revanche, ces sources ont une **fraîcheur attendue** que personne ne surveille. Ajouter, pour celles où c'est pertinent, une **échéance de rafraîchissement** (`cadence_attendue_jours`) : au-delà, le panneau et le dashboard signalent « donnée manuelle non rafraîchie depuis N jours ». Ce n'est pas une sonde amont, c'est un rappel — et il ne notifie qu'une fois par dépassement.

Les fichiers fonciers sous convention ont une échéance de convention, pas seulement de donnée : si cette date est connue, la porter aussi.

## Y5 — Bilan et honnêteté du tableau

1. Nouveau bilan chiffré : surveillées / total, ventilé par méthode (`api`, `page`, `entete`, `temoin`, rappel manuel) et par fournisseur.
2. `SENTINELLE-INVENTAIRE.md` est **régénéré** depuis le catalogue (comme en SENTINELLE-2, jamais à la main) et recommité.
3. Toute source restée non surveillée porte une raison **précise et vraie** en base — pas une catégorie fourre-tout. Une raison qui ne dit pas ce qui a été essayé est à réécrire.
4. Le panneau admin distingue visuellement les quatre natures : version détectable · changement détectable (`entete`, `temoin`) · rappel manuel · non surveillable.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : **Y1 sort des 6 récupérables, une par une, avec ce qui a répondu** · Y2 quels hubs exposent une API de catalogue · Y3 lesquelles ont une empreinte stable et lesquelles ont été écartées pour instabilité · **le nouveau total surveillées / 64**. Inventaire régénéré et commité. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/sentinelle-3
```
