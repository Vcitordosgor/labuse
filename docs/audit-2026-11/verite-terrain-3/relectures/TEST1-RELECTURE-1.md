# TEST1-RELECTURE-1 — relecture des 30 premiers cas (ordre alphabétique de permit_id)

Audit VERITE-TERRAIN-3, lecture seule. Entrée : `cohortes/TEST1-NON-60.csv` (permis de logements
réellement accordés, moteur de main = « non constructible »). Détail par cas : `TEST1-RELECTURE-1.csv`.

## Décompte

| Classement | Nombre |
|---|---|
| exception_legale | 18 |
| erreur_labuse | 6 |
| decalage | 6 |
| indetermine | 0 |
| **Total** | **30** |

Répartition des exceptions légales : 14 × STECAL « hameau » Ns de Saint-Benoît (habitat admis
sous condition, N-2 p.42, dépôts 2020-2021 donc avant la caducité ELAN du 31/12/2021),
2 × STECAL Aba de Saint-André (habitat neuf ≤ 120 m² SDP, A2.2 (11) p.106),
2 × logement lié à une exploitation agricole en zone A (Les Avirons A2.2-6 ≤ 150 m² ;
Saint-Benoît A-2/A-3).

Décalages : 2 permis « juste après le millésime » instruits sous l'ancien PLU
(Entre-Deux 24/09/2024, Plaine-des-Palmistes 27/05/2023), 2 lotissement LAMANDIÈRE en zone
affichée A sur un GPU dont les modifications n°2/n°3 ne sont pas intégrées (Saint-Benoît),
2 assiettes réelles différentes de la parcelle jugée (62 m² pour 137 m² habitables ; permis
multi-parcelles jugé parcelle par parcelle).

## Erreurs LABUSE confirmées (6)

### 1. 97440624A0002 — 97406000AD0863 (La Plaine-des-Palmistes, Uc) — risque sur-appliqué
Verdict moteur : « Parcelle couverte par le PPR en zone rouge (inconstructible) — aucune
emprise constructible ». Mesure sur les couches de LABUSE : la zone PPR INTERDICTION (R1)
couvre **9,1 %** de la parcelle ; **90,9 %** est en B3 (PRESCRIPTION, constructible avec
prescriptions) ; l'union des aléas « fort » géorisque ne couvre que 65,5 %. La parcelle
(550,5 m², zone Uc) n'est pas « couverte » par du rouge. Permis de 87 m² accordé le 27/02/2024.
```sql
WITH t AS (SELECT idu, geom_2975 FROM parcels WHERE idu='97406000AD0863')
SELECT z.subtype, z.name,
       round((ST_Area(ST_Intersection(t.geom_2975,z.geom_2975))/ST_Area(t.geom_2975)*100)::numeric,1)
FROM t JOIN spatial_layers z ON z.kind='ppr' AND ST_Intersects(t.geom_2975,z.geom_2975);
-- INTERDICTION « R1 » 9.1 | PRESCRIPTION « B3 » 90.9
```

### 2. 97441021A0161 — 97410000BX0750 (Saint-Benoît, Ua) — trait de côte sur-appliqué
Le moteur calcule 347 m² d'emprise, R+2, puis sert « rédhibitoire » : la parcelle est à 100 %
dans la **bande longue d'évolution du trait de côte** (couche `trait_de_cote/bande_longue`,
taux −0,192 m/an) et `src/labuse/faisabilite/engine.py` (modulation littorale, f = 1 −
littoral_pct, ~lignes 840-848) met le facteur à 0. C'est une bande d'anticipation prospective,
pas une servitude d'interdiction — `cascade_results` la classe d'ailleurs en SOFT_FLAG
(« bande d'anticipation ») et l'aléa PPR est faible. Maison de 67 m² accordée le 27/08/2021
et **achevée** (DAACT 17/07/2025).

### 3. 97440921A0264 — 97409000BI0220 (Saint-André, UB) — règle d'implantation mal calibrée
Le moteur vide la parcelle de 233,6 m² avec des « reculs (3 m) » traités en minimums
obligatoires. Règlement Saint-André 2019 : UB 7 p.27 « **En cas de retrait** de la
construction, la distance […] doit être au moins égale 3 mètres » → le retrait est facultatif,
l'implantation en limite séparative est admise ; UB 6 p.27 : la façade « ne doit pas être
implantée **au-delà** d'une marge de recul de 6 mètres » = recul maximum sur voie, pas un
minimum (citations du règlement officiel portées par `config/plu_destinations/97409_saint_andre.yaml`).
Immeuble de 5 logements (219 m²) accordé le 16/05/2022, achevé (DAACT 23/05/2024). PPR : 100 % B3 prescriptif.

### 4. 9744072500021 — 97407000AL1652 (Le Port, Ub) — règle d'implantation mal calibrée / échec d'assiette
Règlement Le Port (extraits en base) : Ub 4 p.37 (id 2800) « implantées **soit à
l'alignement**, soit avec un recul minimum de 3 mètres » ; Ub 5 p.38 (id 2801) : implantation
« **sur les deux limites séparatives latérales** » obligatoire pour les terrains ≤ 12 m de
largeur sur voie. Le recul nul est donc admis, voire imposé : une parcelle de 166,4 m²
entièrement en Ub n'est pas « exiguë ». Le moteur sert « terrain_exigu »
(cause_moteur `assiette_a_verifier`). Maison de 87 m² accordée le 30/07/2025 (chantier en cours).

### 5. 97440623A0040 — 97406000AD0854 (La Plaine-des-Palmistes, Uc) — échec d'assiette servi comme « non constructible »
Parcelle 425,8 m² à 100 % en Uc, PPR 100 % B3 (prescription), aléa dominant faible (97,4 %) :
aucune contrainte opposable rédhibitoire. Le verdict moteur avoue « la géométrie […] n'a pas
permis d'établir une emprise nette fiable » mais le résultat servi est « non constructible /
terrain_exigu » (défaut pessimiste). Permis de 76 m² accordé le 05/06/2023.

### 6. 97440624A0087 — 97406000AW0822 (La Plaine-des-Palmistes, Ur) — échec d'assiette servi comme « non constructible »
Parcelle de **3 294,1 m²** à 100 % en Ur, PPR 100 % B3, aléa faible 100 %. Même défaut
pessimiste que ci-dessus (cause_moteur `assiette_a_verifier` → cause servie « terrain_exigu ») :
un terrain de 3 300 m² en zone urbaine ne peut pas être exigu. Permis de 53 m² accordé le 16/01/2025.

## Motifs transverses

- **STECAL non modélisés** (16/30) : le moteur réduit la zone à sa famille (N/A → non
  constructible) alors que les règlements admettent l'habitat sous condition (Ns Saint-Benoît,
  Aba Saint-André). Les propres YAML `config/plu_destinations/` documentent ces admissions
  (`statut: sous_condition`) : la donnée existe, le moteur de capacité ne la lit pas. Classé
  exception_legale conformément à la consigne.
- **`assiette_a_verifier` compté comme « non »** (3 des 6 erreurs + 2 décalages voisins) : quand
  la géométrie échoue, le verdict servi est « non constructible » au lieu d'« indéterminé ».
- **Reculs par défaut en zone urbaine dense** (2 erreurs) : les règlements du Port et de
  Saint-André admettent (ou imposent) l'implantation à l'alignement et en limite ; le moteur
  applique un retrait minimal et vide les petites parcelles.
