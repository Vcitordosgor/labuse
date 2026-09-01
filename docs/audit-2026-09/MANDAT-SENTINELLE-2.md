# MANDAT SENTINELLE-2 — étendre la surveillance au maximum des 64 sources

**Branche : `feat/sentinelle-2`** (depuis `main` après merge de `feat/sentinelle-1`). Bloc commun habituel.
**Origine** : SENTINELLE-1 a livré la mécanique et n'a semé que 6 sources sur 64. Décision Vic : **on veut le maximum de sources surveillées automatiquement.** Ce mandat ne change pas la mécanique, il fait le travail d'enquête source par source.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter.
**Clôture** : `tsc`, build, tests backend et front, puis **commit sur la branche** avant le compte-rendu. Merge = Vic.

## Doctrine — inchangée

La sentinelle **surveille et prévient. Elle n'ingère rien, ne touche jamais `data_sources`.** Aucune source de type annonce. Appels one-shot, séquentiels, espacés, UA LABUSE.

**Et la règle qui commande tout ce mandat : une URL n'est inscrite que si elle a été appelée pour de vrai et que la réponse a été lue.** Une URL plausible mais non testée produit un « injoignable » permanent qui pollue le tableau et fait perdre confiance dans l'outil entier. Mieux vaut 30 sources vraies que 64 déclaratives.

---

## X1 — Inventaire complet, source par source

Produire `docs/audit-2026-09/SENTINELLE-INVENTAIRE.md` : **une ligne par source des 64**, avec fournisseur, millésime servi, et la piste de surveillance envisagée. C'est le plan de travail de X2 ; il reste au dépôt comme trace.

Regrouper d'abord par **fournisseur** : IGN, DGFiP/data.gouv, INSEE, Sitadel/SDES, BAN, DHUP, Etalab, préfecture/DEAL, collectivités. Une même famille partage souvent le même mécanisme de version — trouver la clé d'une famille débloque plusieurs sources d'un coup. C'est le gisement principal.

## X2 — Enquête et vérification réelle

Pour chaque source non encore surveillée, dans l'ordre de préférence :

1. **`api`** — le fournisseur expose un JSON de versions ou de millésimes. Cas idéal, à chercher en premier. Beaucoup de jeux data.gouv.fr exposent des métadonnées de ressources avec date de dernière modification — c'est utilisable pour toute la famille.
2. **`page`** — une page de téléchargement ou de documentation où figure un millésime lisible par motif (`20\d{2}`, `20\d{2}-S[12]`, `20\d{2}T\d`…). Toujours prendre le **plus récent** trouvé.
3. **`entete`** — le fichier amont est joignable : comparer `Last-Modified` / `ETag`. Repli valable pour tout téléchargement direct stable.

**Chaque URL candidate est appelée réellement** avant d'être inscrite. La sonde doit renvoyer `ok` ou `nouvelle_version` — jamais `injoignable` ni `illisible` au moment du semis. Une URL qui échoue n'est pas inscrite : elle va dans la liste des non surveillées avec ce qu'on a essayé.

Cas particuliers à traiter plutôt que d'abandonner :
- **Endpoints de requête sans notion de version** (API interrogée à la demande) : surveiller la page de documentation ou le changelog du service ; à défaut, une requête témoin dont on compare l'en-tête ou un compteur stable.
- **Proxys et miroirs** : remonter à la source d'origine et surveiller celle-ci.
- **Doublons** : une seule ligne de veille pour plusieurs sources dérivées du même fichier amont — l'alerte vaut pour toutes ; le noter dans l'inventaire.
- **Sources alimentées manuellement par Vic** : non surveillables par nature. Les identifier clairement, c'est une réponse valable.

## X3 — Objectif chiffré et honnêteté du tableau

1. **Cible : au moins 30 sources surveillées sur 64**, et davantage si les familles se débloquent. Si la cible n'est pas atteinte, dire précisément pourquoi, famille par famille — pas de contournement en inscrivant des URL douteuses.
2. Le seed reste **idempotent** et préserve `actif` (un réglage manuel de Vic n'est jamais écrasé).
3. Les sources non surveillables gardent un état explicite dans le panneau admin : « non surveillée » avec la raison en infobulle — pas un blanc, pas une fausse erreur.

## X4 — Le tableau reste lisible à 30+ lignes

Le panneau admin de SENTINELLE-1 a été dessiné pour 6 lignes. À 30 ou 40, il faut :
1. **Un tri par défaut utile** : nouvelles versions d'abord, puis erreurs de sonde, puis à jour.
2. **Un filtre** : tout / nouvelle version / sonde en échec / non surveillée.
3. **Regroupement par fournisseur** ou colonne fournisseur triable.
4. La tuile du dashboard donne le nombre de nouvelles versions, inchangée.

## X5 — Ne pas noyer Vic sous les notifications

Avec 30+ sources surveillées, le volume change. La déduplication par (source, millésime) de SENTINELLE-1 est conservée, et :
1. **Un seul résumé quotidien** en cloche quand plusieurs sources ont du nouveau le même jour : « 3 sources ont une nouvelle version », dépliable — pas trois notifications.
2. **Une sonde en échec ne notifie pas** au premier passage : seulement après **3 échecs consécutifs** sur la même source (un serveur public tombe, ça se relève).
3. Le rythme reste quotidien, séquentiel, espacé.

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : **X3.1 nombre final de sources surveillées sur 64, ventilé par méthode et par fournisseur** · la liste des non surveillées avec, pour chacune, ce qui a été essayé · les familles débloquées d'un coup. L'inventaire `SENTINELLE-INVENTAIRE.md` est commité avec le code. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff feat/sentinelle-2
```
