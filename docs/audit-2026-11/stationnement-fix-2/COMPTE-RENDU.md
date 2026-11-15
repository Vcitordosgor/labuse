# ETUDE-STATIONNEMENT-FIX-2 — compte-rendu

La preuve n'est plus « la citation est présente » mais « le nombre de places calculé est JUSTE ».
Le relecteur avait recalculé 15 zones à la main : 6 rendaient un nombre faux. Elles sont désormais
justes et verrouillées par un banc d'exécution permanent.

## LOT 1 — banc d'exécution (la preuve = le résultat du calcul)

`tests/test_banc_stationnement.py` : 15 zones × (maison T4 120 m² + collectif 20 × T3), valeurs LUES
SUR L'IMAGE de la page officielle, comparées au calcul de `BaremeStationnement.exiger`.

6 écarts trouvés et corrigés :

| Zone | Avant | Après | Cause |
|---|---|---|---|
| Saint-Paul U2c | 40 | 44 | visiteurs 1/5 omis |
| Saint-Louis UA | 50 | 40 (+10 publiques à part) | places publiques comptées comme à dessiner |
| Saint-Leu UD | 40 | 30 | barème collectif par pièces lu comme individuel plat |
| Trois-Bassins UC (maison) | 2 | 1 | arrondi inférieur non appliqué |
| Saint-Joseph U2 | 22 | 20 | « 1/10 » visait l'hébergement CASF, pas l'ordinaire |
| Petite-Île UB (aidé) | 0 | 20 | dispense réservée au LLTS, étendue à tout l'aidé |

Écarts restants sur ces 15 zones : **0**. Banc vert.

## LOT 2 — défauts de fond

- **Plafond national L151-35/36** : c'est un PLAFOND. Il BORNE l'exigence résident (ne la relève jamais)
  et s'applique MÊME sur une ligne dédiée (avant, il court-circuitait la ligne dédiée et pouvait
  remplacer un barème plus favorable). Attaché au barème typé (`plafond_national`), `exiger` retient le
  min et écrit le barème local écarté. Test : `test_plafond_national_ne_fait_que_baisser`.
- **Filtre « logement de fonction seulement »** :
  - ne se déclenche plus quand la zone ouvre un VRAI programme d'habitation (Saint-Louis UZ « 1 logement
    individuel », Saint-Paul U1a quota social) ;
  - suit les renvois vers la zone parente (Le Port 1AUe→Ue, Saint-Denis Uac→Ua héritent la restriction) ;
  - ne refuse l'Étude que si TOUTES les parcelles constructibles sont fonction-only (une seule parcelle
    « fonction » ne condamne plus un projet multi-parcelles).
- **Liste nommée** des 88 zones refusées, avec citation + renvoi :
  `zones-logement-fonction-refusees.md`.

## LOT 3 — plan dessiné

- **Dégagement d'allée mesuré LOCALEMENT** (BW2635 : 13 places « validées » avec 2,25 m parce que le
  contrôle lisait la dimension minimale de la BOÎTE ENGLOBANTE, 5 m). Nouveau `_pincement_allee` :
  ouverture morphologique restreinte au droit des places → une allée pincée sous 5 m devant une place
  échoue, une allée large de 5 m partout réussit. Test :
  `test_degagement_allee_mesure_localement_pas_boite`.

## LOT 4 — document

- **Source UNIQUE de « le barème existe-t-il »** : le drapeau `validee` (le même qui déclenche la
  citation). HT0538/Ud (barème « 1 place / 75 m² de SDP ») était déclaré « absent » (garde-fou) tout en
  affichant sa citation validée page suivante. `_regle_stationnement_courte` décrit désormais le barème
  au m². Test : `test_bareme_existence_source_unique_par_m2_sdp`.
- **Chaque PDF porte la version de calcul** : `_commit_build()` stampe le commit (env `LABUSE_BUILD_COMMIT`
  au déploiement, sinon HEAD) dans la page Hypothèses.

## Livrables

- Banc permanent : `tests/test_banc_stationnement.py` (15 zones + 6 tests ciblés).
- Liste nommée des refus : `zones-logement-fonction-refusees.md` (88 zones).
- 3 Études régénérées APRÈS le dernier commit moteur (stamp `622f9dc7cbed`) :
  `etude_97422000BW2635.pdf` · `etude_97416000HT0538.pdf` · `etude_97404000AD0887.pdf`.

## Reste à traiter (non couvert par ce lot)

Banc étendu aux 212 couples × 4 programmes ; « habitat interdit » motif réel (Le Tampon 2AUa,
Saint-Paul U1pso) ; héritage de barème par renvoi (Saint-Benoît AUa5) ; Le Port aidé +8/1000 m² ;
La Possession seuil 50 m² ; lotissement 0,8 visiteur/lot ; Saint-Pierre haie 1,50 m + voie piétonne
« Non vérifié » ; prospect/implantation « Non vérifié » ; stationnement vélo chiffré ; « mêmes alertes
partout » étendu à l'Étude (zone humide, inondation) ; statut de couverture = contrôles ;
pleine terre / sol perméable / biotope distincts.
