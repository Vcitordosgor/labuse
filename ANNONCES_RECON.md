# ANNONCES_RECON — terrains à vendre · La Réunion (974)

*Spike de reconnaissance (appels réels). Aucun connecteur construit, aucune logique
cascade/scoring touchée. Règle absolue respectée : **Leboncoin / SeLoger / PAP non
sollicités** (CGU interdisent le scraping), et aucune source n'est contournée.*

## Méthode & limites honnêtes

- Tests par `curl`/`urllib` réels depuis le conteneur, comme le spike sources géo.
- Signal CGU léger via `robots.txt` + licence des jeux open data (≠ avis juridique).
- **Limite du spike** : le proxy sortant du conteneur a renvoyé **503 / DNS échoué**
  sur `immobilier-etat.gouv.fr`, `vigifoncier.fr/.re` et `safer-reunion.com`. Ce n'est
  **pas** une preuve que ces sources sont fermées — juste qu'elles sont **non concluantes
  depuis cet environnement**. À re-tester depuis un réseau direct.

## Récapitulatif

| Source | Ce que c'est | Testé (réel) | Couvre 974 | Géo / cadastre | Réutilisation | Classe |
|---|---|---|---|---|---|---|
| **data.gouv.fr** (API datasets) | open data national | ✅ 200 JSON | filtre 974 = **0** pour vente/foncier/domaine/cessions | — | Licence Ouverte | **Aucune annonce « à vendre »** |
| **data.regionreunion.com** (ODS, 275 jeux) | open data régional | ✅ 200 JSON | oui | DVF a le cadastre | ouverte | **Que des transactions (DVF) + potentiel-foncier** — pas d'annonces |
| **immonot** (notaires) | annonces de ventes | ✅ robots 200 (permissif) | oui (notaires 974) | adresse, parfois réf. parcelle | **CGU restrictives** ; flux XML **partenaire** (membres) | ⛔ Fermé sauf accord |
| **SAFER proprietes-rurales** | annonces foncier rural | ✅ robots 200 | réseau SAFER (974 = SAFER Réunion) | adresse/commune | CGU ; SAFER = service public | ⛔ Fermé sauf partenariat |
| **Vigifoncier (SAFER)** | **notifications de ventes (DIA)** | ❔ 503 via proxy | oui (SAFER Réunion) | **référence cadastrale** (DIA) | **convention/abonnement pro** | ✅ **Légal via convention** (la meilleure piste) |
| **immobilier-etat.gouv.fr** / DNID `encheres-domaine` | cessions de l'État | ❔ 503 via proxy | national (peu de 974) | adresse | public, mais portail JS, **API ouverte non trouvée** | ❔ Non concluant |
| **agorastore.fr** (collectivités) | ventes d'actifs publics | ✅ 200 (SPA Nuxt, back `auctelia`) | national | adresse | CGU opérateur, **pas d'API ouverte documentée** | ⛔ Opérateur/CGU |
| **licitor / enchères judiciaires** | annonces légales de ventes | ✅ site répond | national | adresse | CGU opérateur | ⛔ Opérateur/CGU |
| **Leboncoin / SeLoger / PAP** | annonces | 🚫 **non sollicités** | — | — | **scraping interdit** | 🚫 Exclu par la règle |
| **EPF Réunion / DIA communales** | acquisitions/cessions publiques, préemptions | ⬜ non testé | 974 | cadastre (DIA) | open data **potentiel** / partenaire | ⬜ Piste à creuser |

## Détail des constats (chiffrés)

- **Open data = transactions, pas des offres.** `data.gouv` filtré sur le département **974**
  renvoie **0** dataset pour *vente immobilière / foncier / domaine / cessions*. Le portail
  **ODS de la Région** (275 jeux) ne contient, côté foncier, que **DVF** (`demande-de-valeurs-foncierespublic`,
  des **transactions** déjà intégrées à LA BUSE) et **potentiel-foncier** (les îlots, déjà utilisés).
  Aucun jeu « annonces » / « cessions » / « terrains à vendre ».
- **Les offres « à vendre » vivent sur des portails à CGU.** `immonot` (notaires) et
  `proprietes-rurales` (SAFER) ont un `robots.txt` permissif **mais** robots ≠ droit de
  réutilisation : republier/industrialiser leurs annonces exige un **accord** (immonot
  propose un **flux XML partenaire** ; SAFER fonctionne par **convention**).
- **Vigifoncier** (SAFER) est l'outil pro de référence : il **notifie les ventes foncières
  (DIA)** avec **référence cadastrale** — donc directement rattachable à une parcelle.
  C'est un **service partenaire/abonnement**, pas de l'open data. Non joignable depuis ce
  spike (503 proxy), mais sa nature est documentée et connue.
- **Secteur public** (État via `immobilier-etat.gouv.fr`/DNID, collectivités via `agorastore`,
  enchères judiciaires via `licitor`) : ventes **légalement publiques**, mais portails **JS
  sans API ouverte trouvée**, volumes 974 faibles, et réutilisation encadrée par chaque
  opérateur. `agorastore` est une SPA adossée à `api.auctelia.com` (API privée opérateur).

## Verdict franc

- **Pour des « terrains à vendre » au 974 en OPEN DATA, sans accord : NON.** Ça n'existe pas.
  Ni `data.gouv` (974 = 0), ni le portail régional (que des transactions). Tout ce qui est
  *réellement à vendre* est sur des portails à CGU (notaires, SAFER, opérateurs) ou interdits
  (Leboncoin/SeLoger/PAP).
- **Au moins une voie LÉGALE et rattachable à la parcelle existe — via PARTENARIAT :**
  **Vigifoncier / SAFER** (le meilleur : DIA = **référence cadastrale** = rattachement *exact*
  à `parcels.idu`), à défaut le **flux partenaire immonot** (notaires, géocodable par adresse).
- **Le secteur public** (État/collectivités/judiciaire) est légalement exploitable mais
  **éclaté, faible volume au 974, sans API ouverte** → ingestion lourde, intérêt marginal.

**Conclusion : on ne construit PAS de connecteur sur de l'open data inexistant ni sur du
CGU-interdit.** Si l'objectif est un flux propre de terrains à vendre rattachés à la parcelle,
la bonne cible est une **convention SAFER/Vigifoncier**. Sans cet accord, la voie honnête est
de **rester sur l'existant** (DVF = ce qui s'est vendu et à quel prix + potentiel-foncier)
comme proxy « marché », sans prétendre couvrir les offres en cours.

## Si on obtient un accès propre — intégration proposée (sans coder)

Le cœur de l'intérêt : **faire passer chaque annonce dans la cascade existante** pour la
**qualifier** (verdict + double score), sans toucher au moteur.

1. **Nouvelle source déclarée** dans `data_sources` (nom, licence/convention, fiabilité), +
   une table `annonces` (idu rattaché, prix, surface, date, type, url, source_id, raw_payload,
   `rattachement` = `cadastre|adresse`).
2. **Normalisation** d'une annonce → **résolution vers une parcelle** :
   - **réf. cadastrale** (Vigifoncier/DIA) → reconstruction de l'**IDU 14 car.** → jointure
     directe sur `parcels.idu` (rattachement **exact**) ;
   - sinon **adresse** → géocodage **BAN/api-adresse** → point → `ST_Contains` PostGIS sur
     `parcels` → parcelle candidate (rattachement **approximatif**, tracé comme tel).
3. **Qualification = la cascade telle quelle** : on appelle `evaluate_parcels` sur la parcelle
   rattachée → on obtient **verdict + complétude + opportunité**. L'annonce devient un signal
   à très forte valeur : *« ce terrain est officiellement à vendre **ET** la cascade dit
   opportunité 78 / complétude 62 »*. Tri possible des annonces par score.
4. **Veille** : une nouvelle annonce sur une parcelle suivie (Kanban) ou bien notée peut
   remonter comme **signal** (réutilise la mécanique veille existante) — sans coder ici.
5. **Garde-fous CGU/RGPD** : ne stocker/afficher que ce que la convention autorise ; pas de
   nominatif ; conserver `source` + `url` + licence pour la traçabilité ; respecter les
   quotas/flux du partenaire.

*Option (hors scope, à valider plus tard) :* exposer « mis en vente » comme un `bonus_key`
config-driven (au même titre que `permis_sitadel_recent_proximite`) pour que la mise en vente
**remonte** le score d'opportunité. À ne faire **que** sur décision — on ne touche pas au
scoring maintenant.

## Pistes à creuser (non testées dans ce spike)

- **EPFR (Établissement Public Foncier de La Réunion)** — acquisitions/cessions publiques ;
  possible open data ou partenariat.
- **DIA open data communales** — quelques communes publient leurs déclarations d'intention
  d'aliéner (ventes en cours, **avec cadastre**). À sonder commune par commune au 974.
- **Re-tester depuis un réseau direct** `immobilier-etat.gouv.fr` et `vigifoncier` (503 ici =
  limite du proxy, pas verdict).

---

*À toi de décider : GO sur une démarche partenaire SAFER/Vigifoncier, ou on capitalise sur
l'existant (DVF + potentiel-foncier) sans connecteur d'annonces. Je n'ai rien codé.*
