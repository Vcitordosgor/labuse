# LICENCES À CONFIRMER — les courriers pour Vic (SOURCES-2 lot 5)

**Objet du lot** : six producteurs servent des données que LABUSE exploite ou veut exploiter
sans qu'une licence de réutilisation COMMERCIALE soit écrite noir sur blanc chez eux. Un
courrier par producteur, une page, qui nomme les couches et demande une réponse écrite.
Rien ici n'écrit en base. Expéditeur suggéré : victor@labuse.immo — LABUSE.

Rappel du droit qui fonde la demande (à garder dans chaque courrier) : les administrations
ont l'obligation d'ouvrir leurs données publiques (livre III du CRPA) ; à défaut de licence
affichée, la réutilisation est libre (art. L.321-1 et suiv.), mais la CONFIRMATION ÉCRITE
protège LABUSE et ses clients.

---

## 1. DEAL Réunion — toutes les couches Lizmap

**À :** DEAL Réunion — Mission connaissance et données, `deal-reunion@developpement-durable.gouv.fr`

Madame, Monsieur,

La société LABUSE (Saint-Denis de La Réunion) édite un service d'analyse foncière à
destination des professionnels de l'immobilier réunionnais. Nous consommons, par vos flux
WFS/WMS officiels (`deal974.lizmap.com`), les couches suivantes :

- aléas littoraux et continentaux, PPR approuvés et TRI, et la couche « état des PAC, PPR,
  PPRL et leur date d'approbation » (projets `01risque` et `02etat_ppr_pac`) ;
- systèmes d'endiguement et zones protégées (projet `03digues`) ;
- zones humides (inventaires 2003/2009/2011/2019), Espaces Naturels Sensibles du Département,
  Ramsar, sites classés et inscrits, réserves naturelles, cours et plans d'eau du domaine
  public fluvial, 50 pas géométriques (projet `deal_reunion`) ;
- cartes de bruit stratégiques (4e échéance).

Votre serveur Lizmap n'affiche pas de licence de réutilisation. Nous vous demandons de bien
vouloir nous **confirmer par écrit** que ces couches sont réutilisables, y compris dans un
cadre commercial, sous Licence Ouverte Etalab 2.0 (ou de nous indiquer la licence
applicable), avec la mention d'attribution que vous souhaitez voir portée.

Nous demandons par la même occasion : la **carte hypsométrique du littoral** (projet
`04tsunami`), aujourd'hui servie en image seule, est-elle disponible en vecteur ?

---

## 2. Conservatoire du littoral

**À :** Conservatoire du littoral — délégation Océan Indien

Madame, Monsieur,

LABUSE sert à ses clients la connaissance des périmètres d'intervention du Conservatoire à
La Réunion (27 sites servis dans notre couche « espaces protégés »). La fiche de vos données
ne porte pas de licence textuelle. Nous vous demandons de bien vouloir **confirmer par
écrit** la licence de réutilisation de vos périmètres (Licence Ouverte 2.0 ?), y compris pour
un usage commercial, et la mention d'attribution attendue.

---

## 3. ONF — forêts publiques

**À :** ONF Réunion, direction régionale

Madame, Monsieur,

LABUSE affiche le régime forestier des parcelles publiques de La Réunion (couche « forêts
publiques », réserve biologique comprise). L'ONF diffuse certaines données sous des
conditions spécifiques. Nous vous demandons de **confirmer par écrit** la licence applicable
aux couches du régime forestier et des réserves biologiques du 974 (BD Forêt/data.gouv), y
compris pour une réutilisation commerciale, et l'attribution attendue.

---

## 4. EDF Réunion (SEI) — réseau électrique

**À :** EDF Réunion — Systèmes Énergétiques Insulaires, open data

Madame, Monsieur,

LABUSE informe ses clients de la proximité du réseau moyenne tension (raccordement). Vos
couches open data (lignes HTA/BT aériennes et souterraines — data.ademe.fr) ne portent pas
de licence explicite chez toutes les rediffusions. Nous vous demandons de **confirmer par
écrit** la licence de vos jeux réseau (HTA/BT aérien et souterrain, postes) et leur
réutilisabilité commerciale, ainsi que l'attribution attendue.

---

## 5. Parc national de La Réunion

**À :** Parc national de La Réunion — pôle SIG (`lizmap.ofb.fr/pnrun`)

Madame, Monsieur,

LABUSE sert le zonage réglementaire du Parc (cœur et aire d'adhésion, couche `PNRun2021`).
La cartothèque OFB/Parc ne porte pas de licence textuelle. Nous vous demandons de
**confirmer par écrit** la licence de réutilisation du zonage (Licence Ouverte 2.0 ?), y
compris pour un usage commercial, et l'attribution attendue.

---

## 6. Région Réunion — trafic RN, DVF Région, potentiel foncier

**À :** Région Réunion — direction des systèmes d'information, portail `data.regionreunion.com`

Madame, Monsieur,

LABUSE consomme trois jeux de votre portail Opendatasoft : les comptages de trafic sur le
réseau routier national (TMJA), le jeu « demandes de valeurs foncières » (utilisé comme
échantillon de contrôle, jamais servi), et le potentiel foncier (indicatif SAR). Le portail
n'affiche pas uniformément la licence par jeu. Nous vous demandons de **confirmer par
écrit**, jeu par jeu, la licence applicable (Licence Ouverte 2.0 ou ODbL) et la possibilité
d'une réutilisation commerciale, avec l'attribution attendue. Nous renouvelons par ailleurs
notre demande de la couche SIG du SAR en vigueur (aucun vecteur public au 13/09/2026).

---

# AUDIT ODbL — ce que LABUSE dérive d'OpenStreetMap

L'ODbL (OpenStreetMap, BANO) autorise l'usage commercial mais impose : (1) l'ATTRIBUTION
« © les contributeurs d'OpenStreetMap », (2) le PARTAGE À L'IDENTIQUE de toute « base
dérivée » redistribuée, (3) la mise à disposition de la dérivée sur demande si elle est
utilisée publiquement (produced work vs derivative database).

| Dérivé LABUSE | Contenu OSM | Redistribuable sous ODbL ? | Verdict |
|---|---|---|---|
| `spatial_layers kind='amenite'` (équipements OSM, Overpass) | oui, direct | OUI — base dérivée, à fournir sous ODbL sur demande | conforme : la source OSM est dite dans la description de couche (layers.ts) et l'attribution « © les contributeurs d'OpenStreetMap » est gravée aux legal_notes du registre |
| `parkings_aper` (parkings loi APER) | oui, direct | OUI — déjà DIT dans legal_notes (« disponible sous ODbL sur demande ») | conforme |
| `tcsp_troncon` / `tcsp_station` / `tcsp_zone` (voies bus en site propre) | tronçons OSM + dérivation LABUSE (stations ≤ 60 m, zone 800 m) | OUI pour les tronçons ; les zones dérivées MÉLANGENT OSM et GTFS (Licence Ouverte) → la base dérivée mixte doit rester fournissable sous ODbL | conforme sous réserve de tenir la dérivée à disposition |
| `pole_echange` (pôles OSM « Sourcé ») | oui, direct | OUI | conforme |
| `transport_arret`/`transport_ligne` (GTFS PAN) | NON (AOM, Licence Ouverte) | n/a | hors ODbL |
| BANO | non utilisé (BAN IGN/Etalab 2.0 seule, vérifié registre) | n/a | hors ODbL |
| `parcel_amenites` (distances au POI le plus proche, consommées par le score) | valeurs CALCULÉES depuis OSM | zone grise classique : des distances agrégées par parcelle sont un « produced work » tant qu'elles ne permettent pas de reconstruire la base OSM ; l'extraction substantielle sous-jacente reste ODbL | conforme en l'état ; ne JAMAIS exporter parcel_amenites en masse sans la marquer ODbL |

**Règle gravée** : tout export en masse d'une table listée « base dérivée » ci-dessus doit
porter la licence ODbL et l'attribution — jamais une redistribution silencieuse sous une
autre licence.

# DVF — la clause qui peut mordre, vérifiée

L'arrêté DVF (art. R112 A-3 LPF) interdit : la **ré-identification** des personnes (croiser
DVF avec d'autres sources pour retrouver le vendeur/l'acquéreur) et l'**indexation** des
données par les moteurs de recherche externes. Vérifié dans l'app le 13/09/2026 :

- DVF est servie **agrégée ou à la parcelle**, jamais nominative (aucun nom dans geo-DVF ;
  LABUSE n'y joint AUCUNE identité de personne physique — les propriétaires PM viennent d'un
  fichier DGFiP distinct qui EXCLUT les personnes physiques) ;
- les pages parcelle sont servies **derrière authentification** (403 à deux comptes gravé,
  COMPTE-2) : aucune page DVF n'est indexable par un moteur externe ;
- les exports (Dossier, Flash, `/export`) sont cloisonnés par compte (garde IDOR, EXPORTS-2)
  et non publiés.

Verdict : **aucun chemin de ré-identification ni d'indexation** dans l'état servi. Point de
vigilance durable : ne jamais créer de page DVF publique non authentifiée, et ne jamais
joindre DVF à une identité de personne physique.
