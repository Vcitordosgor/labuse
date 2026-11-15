# LOT H — carte du code (contre-audit documents) — préparé, à exécuter

> Les 9 points (point 10 = fiche « PLU constructible », DÉJÀ fait en LOT A complément `a84d0d0fa`).
> Parcelles : 97422000BW2635, 97404000AM0838, 97422000AD0887, 97411000IS0448.
> Fichiers partagés avec `fix/chirurgical-docs` (Apporteur, Estimer, Dossier) → changement minimal + à lister pour la fusion.

| # | Gravité | Fichier:ligne | Nature du correctif |
|---|---|---|---|
| 1 | haute | `bilan/excel.py:265-269` (formules résultat/marge/cash-flow) vs `bilan/pdf.py:275-291` (garde sur `r.resultat_net is None`) | L'Excel doit GELER résultat/cash-flow/marge quand un coût requis manque (comme le PDF). Dans le PDF, une taxe sans assiette ne doit pas s'afficher « 0 € · Sourcé ». Test sur les 12 classeurs. |
| 2 | haute | `exports/blocs/apporteur.py:129-149` (`_contraintes` lit `aleas_parcelle_liste`) ; `:405-413` (ICPE/pollution sur `obs_pollution`) | L'Apporteur doit lire LA MÊME liste d'alertes que la fiche (zone humide 100 % AD0887, inondation extrême 85 % BW2635). Ne pas parler d'« ancien site industriel / sol pollué » sur simple proximité ICPE → « installation classée à proximité ». Étendre le test « mêmes alertes partout » à l'Apporteur. |
| 3 | haute | `api/pre_dossier.py:917-932` (`est_ppr_zone`) | PCMI4 IS0448 : ne pas écrire « pas d'exclusion automatique » / « aucune prescription PPR opposable » sur aléa fort quand le Dossier/Gabarit excluent 34 % rouge + 66 % bleue. Parser les % (rouge/bleue) comme le Dossier ; « aucune prescription opposable » SEULEMENT hors de tout zonage PPR. |
| 4 | moyenne | `api/app.py:9276-9281` (`bati_pct` via `surface_terrain_m2`) ; `:9260-9275` (`proprietaire`) | Comparatif IS0448 : bâti 27 % vs 128/959 = 13 % de la fiche → une seule valeur (celle de la fiche). Proprio « particulier » BW2635 vs « non déterminé » du Dossier → même valeur. |
| 5 | moyenne | `api/app.py:5165-5178` (requête RNIC `parcelle_idu = :idu`) + rendu Dossier/fiche | BW2635 : les 2 copros sont aux 4 et 6 rue d'Allemagne, pas sur la parcelle (au 2). Une copro voisine doit s'afficher « à proximité », jamais comme celle de la parcelle (matcher l'adresse/parcelle). |
| 6 | moyenne | `exports/robinet_fiche.py:925-950` ; `exports/blocs/potentiel.py:86-117` (`hauteur_contrainte`) | Dossier AD0887 : « 3,9 m de marge au faîtage » alors que fiche = 3,9 m à l'égout / 6,3 m au faîtage ; même inversion BW2635. Chaque marge doit porter son vrai nom (base de la contrainte). |
| 7 | moyenne | `pige/api.py:2502-2504` (« l'assiette constructible limite… ») | Estimer AM0838 : après refus, n'appelle plus « assiette constructible » les 11 762 m² hors zone rouge d'une parcelle à habitat interdit. Pas de mot « constructible » sur une parcelle non constructible. (Fichier Estimer partagé → minimal + listé.) |
| 8 | moyenne | `exports/etude_faisabilite.py:851-855` ; chercher le relibellé « perméable » → « pleine terre » | AM0838 : Dossier+Étude transforment 25 % de « surface perméable » en 25 % de « pleine terre » (règles de règlement distinctes). Chaque règle garde son nom. |
| 9 | basse | `faisabilite/engine.py:974` (`suffix` si `regime == "exempt"`) | Dossier en zone habitat interdit : ne pas écrire « stationnement non réglementé » quand le règlement fixe des normes pour les AUTRES destinations. |

### À lister seulement (ne pas corriger) :
- Étude de zone : « revenu médian » et « niveau de vie moyen » pour le même chiffre.
- Estimer BW2635 : ventes qui paraissent en double (confirmer/infirmer avec l'identifiant de mutation).

### Méthode de preuve (par point) : régénérer le document de la parcelle concernée dans `~/Desktop/chasse-1/` et citer la phrase corrigée depuis le fichier livré ; test pour le reste. Attention pièges régénération (spawn `__main__`, WeasyPrint, vider `vider_fiche_cache_partage()`, Bilan Excel session-gated).
