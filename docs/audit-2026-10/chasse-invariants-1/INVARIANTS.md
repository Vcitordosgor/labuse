# INVARIANTS — CHASSE-INVARIANTS-1

Une ligne par règle vérifiée sur l'île servie (q_v18 / run_seq 15, 434 582 parcelles).
Colonnes : domaine · règle (FR) · parcelles passées · violations (→ E-xx dans `ECARTS.md`).
Les requêtes/scripts rejouables sont dans chaque `domaine-N.md`. **97 invariants, 12 domaines.**

| dom | # | règle | passées | violations |
|---|---|---|---|---|
| 1 | géom valide / SRID / non-nulle | toute géométrie servie est valide, au bon SRID, non nulle | 434 582 | 0 |
| 1 | centroïde dans parcelle | le centroïde stocké tombe DANS la géométrie | 434 582 | **9 792 → E-07** |
| 1 | bâti ≤ dessin (amont) | emprise bâtie ≤ dessin de la parcelle | 292 056 | **20 243 → E-08** |
| 1 | disparue hors calcul | une parcelle disparue n'alimente aucun calcul servi | 1 353 disp. | 0 (résiduel/score) |
| 1 | surface du run présente | `surface_terrain_m2` présente et > 0 par ligne servie | 433 229 | **433 229 → E-09** |
| 1 | surface incertaine tracée | écart contenance↔dessin > ×2 ⇒ basculé « surface incertaine » | 433 201 | 0 (1 593 tracées) |
| 1 | une commune par INSEE | préfixe INSEE ↔ 1 seule commune | 434 582 | 0 |
| 1 | surface jamais ≤ 0 | aucune surface servie nulle ou négative | 433 229 | 0 |
| 1 | ratios bornés | `taux_emprise`/`pct_potentiel` ∈ [0;100], sdp ≥ 0 | 433 229 | **61 599 + 64 293 → E-01** |
| 2 | une zone par idu | `parcel_zone_plu` : 1 zone/idu, aucun champ NULL | 434 582 | 0 |
| 2 | zone fiche = zone carte | même source (dominante surface), fiche et carte s'accordent | 427 419 | 0 (mais cf E-02) |
| 2 | RNU Saint-Philippe | aucune zone U/AU PLU servie à Saint-Philippe | 4 180 | 0 |
| 2 | parts bizone ≤ 100 % | les parts d'une parcelle ne somment jamais > 100 % | 1 404 (éch.) | 0 |
| 2 | non-validée ne sert pas | aucune feuille PLU `propose` chiffrée n'alimente une SDP | 2 071 zones | 0 |
| 2 | gabarit borné | emprise ∈ [0;100] %, niveaux sous faîtage, fam ↔ lib | 2 071 + 427 419 | 0 |
| 2 | SDP ⇒ zone reconnue | SDP positive ⇒ une zone PLU à la carte | 193 394 | **1 380 → E-02** |
| 3 | pas de 0/NULL muet | `sdp=0` sans cause ⇒ bâti saturé ; cause ⇒ pas de SDP positive | 433 229 | 0 |
| 3 | couverture score 100 % | toute parcelle vivante porte un score q_v18 | 433 229 | 0 |
| 3 | bande ⇔ score | 0⇔score 0, NC⇔score NULL⇔non_calculable (5 miroirs) | 433 229 | 0 |
| 3 | NC ⇒ cause | `non_calculable` ⇒ cause présente | 16 583 | 0 |
| 3 | bâti résiduel cohérent | bâtie + résiduelle = max, résiduelle ∈ [0;max] | 292 056 | 0 |
| 3 | borne physique SDP | SDP résiduelle ≤ terrain × 20 | 193 394 | 0 (max ×3,14) |
| 3 | moteur SDP ≤ emprise×niv | recompute indépendant de la capacité | 120 (éch.) | 0 |
| 3 | score reproductible | recompute == stocké, déterministe | 500 (éch.) | 0 |
| 3 | barème monotone | SDP ↑ ⇒ points ↑ à faisabilité égale | sweep | 0 |
| 3 | bande A servable | bande A ⇒ score>0, SDP>0, non disparue, non NC | 6 207 | 0 |
| 3 | A ⇏ exclusion dure | bande A sans `cascade_exclue` | 6 207 | **607 → E-10** |
| 4 | PPR rouge ≥50 % ⇒ exclu | union(INTERDICTION) ≥50 % ⇒ HARD_EXCLUDE ⇒ rouge déduit | 2 196 (224 géom.) | **224 → E-03** |
| 4 | fiche = score sur PPR | fiche « rédhibitoire » ⇒ score/SDP ne peuvent être > 0 | 224 | **30 → E-11** |
| 4 | servitude sourcée | aucun risque/servitude servi sans `data_source_id` | 434 582 | 0 |
| 4 | SDP>0 rouge = PPR-partiel | HARD_EXCLUDE rouge + SDP>0 ⇒ rouge < 100 % (découpe) | 105 298 | 0 |
| 4 | hors-rouge ≤ contenance | aire servie hors rouge ≤ contenance | (construction) | 0 |
| 5 | identité comptable | `marge = charge − prix` à l'euro | 150 179 | 0 |
| 5 | non-estimable sans chiffre | une ligne non estimable ne porte aucun chiffre | 132 108 | 0 |
| 5 | estimable complète | une ligne estimable a tous ses champs | 150 179 | 0 |
| 5 | mention « estimé » | toute estimation porte « estim » (libellé + détail) | 282 287 | 0 |
| 5 | run servi partout | toutes les lignes `score_e` portent q_v18 | 282 287 | 0 |
| 5 | €/m² plausible | prix terrain implicite dans une fourchette par commune | 150 179 | 0 |
| 5 | médianes DVF plausibles | médianes sectorielles bornées par type | 2 359 | 0 |
| 5 | fenêtre DVF ancrée | « N ans » ancré sur `max(date_mutation)`, pas `CURRENT_DATE` | 29 566 | **−1 068 → E-04** |
| 5 | marge lisible | marge estimée d'un ordre de grandeur de promotion | 150 179 | **(M€) → E-15** |
| 6 | SIREN Luhn | tout SIREN 9 chiffres respecte la clé de Luhn | 158 k+ distincts | 0 |
| 6 | pseudo-SIREN connus | seuls les « U… » DGFiP échappent (jamais affichés) | — | 0 |
| 6 | cessée ≠ active | société état C jamais servie « active » | 551 | 0 |
| 6 | enrichissement borné | `etat ∈ {A,C,NULL}`, `maj` pas dans le futur | 9 730 | 0 |
| 6 | âge aîné cohérent | âge dirigeant aîné servi ∈ [18;110] | 7 725 | **5 → E-05** |
| 6 | âge propension cohérent | `age_max_dirigeant` ∈ [18;110] | 8 311 | **5 → E-05** |
| 6 | succession ⇒ seuil | succession à venir ⇒ âge ≥70 ∨ SCI dormante | 6 256 | 0 |
| 6 | âge succession borné | `dirigeant_age` de la veille ∈ [18;110] | 6 249 | **1 → E-06** |
| 6 | lien idu↔PM unique/sourcé | lien unique, PM toujours sourcée+datée | 82 701 | 0 servies |
| 7 | PC caduc rattaché | tout PC caduc ⇒ parcelle existante | 4 822 | 0 |
| 7 | permis idu ⇒ parcelle | permis servi par idu ⇒ parcelle existante | 50 809 | 0 servi |
| 7 | permis pas dans le futur | aucune date permis > aujourd'hui | 50 809 | 0 |
| 7 | BODACC pas dans le futur | aucune date annonce/parution future | 16 170 | 0 |
| 7 | clôture pas future | aucune clôture BODACC future servie | 14 078 | 0 (N-01) |
| 7 | DPE pas dans le futur | aucune date DPE / année constr. future | 1 123 | 0 |
| 7 | DPE servi rattaché | DPE servi ⇒ parcelle existante | 1 100 | 0 |
| 7 | DPE adresse valide | rattachement BAN/adresse, INSEE connu | 1 100 | 0 |
| 7 | étiquette DPE légale | étiquette ∈ A–G | 1 123 | 0 |
| 7 | BODACC ⇒ société connue | toute entrée BODACC servie résout une dénomination | 177 | 0 |
| 7 | caducité datée | `pc_annee ≤ caduc_depuis ≤ 2026`, octrois>0 | 4 822 | 0 |
| 7 | identifiants uniques | `permit_id`/`numero_dpe` uniques | 51 932 | 0 |
| 7 | inversion dépôt notée | dépôt > autorisation ⇒ note servie (jamais muet) | 50 809 | 0 (7 754 notés, N-02) |
| 8 | 24 communes partout | 24 communes présentes, 0 commune NULL | 434 582 | 0 |
| 8 | somme = île | `sum(communes.parcelles)` = parc vivant total | 433 229 | 0 |
| 8 | commune = SQL vivant | `/communes[c].parcelles` = compte SQL vivant (24) | 433 229 | 0 |
| 8 | évaluées/chaudes = SQL | `.evaluees`/`.chaudes` = recompte q_v18 (24) | 24 com. | 0 |
| 8 | /stats partitionne | tiers et bandes somment au total | 432 350 | 0 |
| 8 | additivité stats | `sum(/stats par commune)` = /stats île | 432 350 | 0 |
| 8 | /stats.total = SQL | total île = recompte base servie | 432 350 | 0 |
| 8 | écart /communes vs /stats | 879 = exactement les slivers vivants <2 m² | 879 | 0 |
| 8 | filtre = cardinal | `/filtre.compte=total=/stats.total`=SQL | île | 0 |
| 8 | idus = compte | `len(idus)` = compte quand non tronqué | 30 (éch.) | 0 |
| 8 | fiche commune cohérente | `n_parcelles`, INSEE, stock, zonage concordants | 24 com. | **surface_ha → E-12** |
| 9 | pas de date future | aucune date de source > aujourd'hui | 157 | 0 |
| 9 | pas de millésime futur | aucun `source_millesime` année 2027+ | 157 | 0 |
| 9 | run cohérent partout | manifeste = residuel = mvt = score = cascade | 5 pointeurs | 0 |
| 9 | vue résiduel = run servi | `parcel_residuel` lit le run servi, effectif = score | 433 229 | 0 |
| 9 | règle dérivée à jour | pc_caducs/veille portent la version de règle du code | 2 tables | 0 |
| 9 | millésime = producteur | `/sources` = `source_millesime` (producteur unique) | 99 | 0 |
| 9 | millésime ≤ max table | Sitadel/DVF ne prétendent pas plus que leur max réel | 80 k | 0 (N-04) |
| 10 | Copilote n'invente rien | aucun chiffre/source absent des données servies ; refus propres | 30 questions | 0 |
| 11 | idu invalide ⇏ 500 | idu malformé/inexistant ⇒ 404 propre | 17 var. | 0 |
| 11 | commune inconnue ⇏ 500 | commune bidon/unicode/SQLi ⇒ pas de 500 | 5 var. | 0 |
| 11 | liste extrême ⇏ 500 | limit/offset/bbox/source absurdes ⇒ pas de 500 ni fausse donnée | 11 var. | 0 |
| 11 | filtre/stats extrême ⇏ 500 | valeurs hors-sens ⇒ pas de 500 | 6 var. | 0 |
| 11 | recherche ⇏ 500 | vide/SQLi/unicode/2000 car. ⇒ pas de 500 ni fuite | 7 var. | 0 |
| 11 | tuile hors grille ⇏ 500 | tuile MVT hors zoom/emprise ⇒ 204/vide | 8 var. | **2 → E-14** |
| 11 | aucun affichage sale | pas de « NaN/None/undefined » ni négatif impossible en 2xx | 6 payloads | 0 |
| 12 | taxe = CGI (10 cas) | taxe servie = reconstruite du CGI (10 cas de référence) | 10 | 0 |
| 12 | taxe = CGI (500 parc.) | assiette + total = recalcul CGI au centime (3 profils) | 1 500 | 0 |
| 12 | commune a un taux | toute parcelle ⇒ commune avec taux communal sourcé | 434 582 | 0 |
| 12 | emprise constructible | = min(zone_implantation, emprise_sol_max) [règle PLU] | 300 | 0 |
| 12 | chaîne faisabilité | bâtie = constructible×0,45 ; niv = round(H/3) ; SDP = bâtie×niv | 300 (+2 004) | 0 réelles |
| 12 | taux ⇏ impossible | aucun taux d'occupation > 100 % servable | 433 229 | **61 599 → E-01** |
| 12 | SDP résiduelle ≥ 0 | invariant dur | 433 229 | 0 |
| 12 | sous-densité cohérente | `sous_densite` cohérent avec le taux AFFICHÉ | 433 229 | **1 148 → E-13** |
| 12 | bilan = Excel (10 jeux) | bilan servi = modèle promoteur (CA/HT/postes/marge) | 10 | 0 |

**Bilan : 97 invariants · ~2,2 M lignes-parcelles passées au crible · 15 violations actives (6 FAUX-CLIENT, 7 INCOHERENT, 2 ROBUSTESSE) + 5 anomalies source neutralisées · 82/97 invariants au vert.**
