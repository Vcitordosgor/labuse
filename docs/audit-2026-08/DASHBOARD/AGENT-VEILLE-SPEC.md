# AGENT DE VEILLE DES SOURCES — SPÉCIFICATION (V2, non implémenté)

> Mandat DASHBOARD-V1 · D6 : la V1 n'implémente PAS cet agent — la table des cadences
> (Sources, calcul « À mettre à jour » automatique) couvre le besoin en attendant. Ce
> document est la spécification d'implémentation pour la V2. Le dashboard affiche un
> panneau grisé qui pointe ici.

## Ce qu'il fait

Un job planifié (cron hebdomadaire, hors chemin critique nocturne) qui interroge chaque
portail AMONT, détecte la publication d'un **nouveau millésime** et **notifie** Vic :
« DVF S2 2026 disponible — lancer l'ingestion ? ». Il ne lance JAMAIS l'ingestion lui-même.

## Ce qu'il surveille, portail par portail

| Portail | Sources couvertes | Méthode de détection |
|---|---|---|
| data.gouv.fr (API datasets) | DVF, BODACC, DPE ADEME, Sitadel/SDES, RNIC, cartofriches | `GET /api/1/datasets/{id}` → `last_modified` + liste des ressources (un fichier nouveau = millésime nouveau) ; comparer au `source_millesime` en base |
| Géoplateforme / IGN | BD TOPO, BD ORTHO (millésimes), RGE ALTI, CoSIA, PCI vecteur | page « actualités » du produit + en-têtes `Last-Modified` des capabilities WMTS/WFS ; les millésimes ortho apparaissent comme nouvelles couches WMTS (`GetCapabilities` diff) |
| Etalab cadastre | Cadastre Etalab (bulk) | index HTTP des dumps (`cadastre.data.gouv.fr/data/…/`) — un répertoire de date nouveau = millésime |
| GPU (géoportail de l'urbanisme) | zonages PLU, SUP, prescriptions | flux WFS `wfs_du` : `GetFeature` COUNT par commune + `Last-Modified` des archives communales ; un delta de count sur une commune = procédure publiée |
| Sudocuh / registre des procédures | états d'avancement PLU | page départementale (HTML stable) : hash de la table 974 ; tout changement = notification avec diff des lignes |
| INSEE | BPE, Filosofi, populations légales | API Melodi / pages produit : numéro de millésime dans les métadonnées |
| ADEME / ODRÉ | DPE (flux continu) | déjà en flux : l'agent vérifie seulement que le flux répond (sentinelle, pas un millésime) |
| Portails ponctuels (DEAL, AGORAH…) | PPR, ZNIEFF, 50 pas, aléas | `Last-Modified`/ETag de l'URL de téléchargement enregistrée dans `data_sources.endpoint_url` ; repli : hash du premier Mo |

Chaque source du catalogue (`data_sources`) porte déjà `endpoint_url`, `source_millesime`,
`prochain_millesime_at` : l'agent lit le catalogue, jamais une liste parallèle.

## Ce qu'il notifie

- `event_log` kind `systeme`, source `Veille sources`, compte NULL (feed admin) + cloche ;
- dédup par (source, millésime détecté) — UNE notification par millésime, jamais une tempête ;
- le message dit : source, millésime détecté, millésime en base, et l'action suggérée
  (« Relancer l'ingestion » si la commande existe au mapping `config/sources_ingestion.yaml`,
  sinon « ingestion manuelle — voir la fiche source ») ;
- tableau de bord : la colonne « Millésime amont » de Sources passe en ambre avec le
  nouveau millésime détecté entre parenthèses.

## Ce qu'il ne fait JAMAIS

- lancer une ingestion (décision humaine, bouton existant) ;
- écrire dans les tables métier (il ne touche que `event_log` + un champ
  `millesime_detecte`/`verifie_le` sur `data_sources`) ;
- scraper au-delà d'une requête légère par portail et par passage (métadonnées, HEAD,
  capabilities — jamais le téléchargement des données) ;
- appeler un LLM (détection 100 % mécanique : dates, hashes, diffs).

## Coût estimé

- ~25 requêtes HTTP légères / passage hebdomadaire (HEAD/JSON/capabilities) — négligeable ;
- développement : ~2-3 jours (drivers de détection par famille de portail + tests contractuels
  sur réponses figées) ; le squelette (catalogue, event_log, dédup, cloche) existe déjà ;
- maintenance : les pages HTML (Sudocuh) sont le seul point fragile — driver isolé,
  échec = notification « portail illisible », jamais un crash.
