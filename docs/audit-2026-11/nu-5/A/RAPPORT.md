# NU5-A — Audit des outils du menu « Outils », parcelle par parcelle

**Mandat** : chaque outil réel du menu Outils, éprouvé sur 20 parcelles choisies pour piéger,
réparties sur ≥ 10 communes. On vérifie, pour chaque outil × parcelle : qu'il ne plante pas et
dit quand il ne peut pas répondre ; sa cohérence avec la fiche (surface, zone, SDP, risques, prix,
propriétaire, au même chiffre près) ; sa logique métier ; les cas-limites de saisie ; et le libellé
(promet-il plus que le calcul ne fait ?).

**Cadre** : branche `audit/nu5-a`, worktree `~/Desktop/labuse-nu5a`, backend local port **9730**
(`env=local`, auth désactivée), front 6930. **Lecture seule — aucune écriture, aucune correction.**
Base locale `labuse` (run servi **q_v20**, rôle `openclaw`). Prod jamais touchée. Date 2026-11-05.
Modèle Opus 4.8.

**Verdict d'ensemble** : sur **260 appels outil × parcelle** (13 appels par parcelle) + une passe de
cas-limites + les outils de niveau commune, **aucun plantage, aucun 500, aucun fait inventé, aucun
chiffre faux présenté comme sûr**. Matrice : **186 vert · 25 orange · 0 rouge · 9 n/a**.
Les 25 oranges sont **concentrés sur deux outils** (Gabarit, Estimer un bien) et **un seul axe** :
ils ne tiennent pas compte de la **constructibilité / destination** de la parcelle. Plus une série de
cas-limites de saisie non bornés sur **Taxe d'aménagement** (contraste net avec la Calculette, elle
strictement bornée).

---

## Étape 0 — Les outils réels du menu Outils

Le menu (`frontend/src/components/outils/registry.ts`) rend 16 cartes visibles, dans un ordre figé.
Chaque outil : nom affiché, entrée, endpoint HTTP réel, calcul back, et l'écran de la fiche qui
reprend ses chiffres. (Les clés `hidden` = résolvants sans carte : Calculette foncière M23, Mon
secteur S1, Étude de faisabilité M22, Veille promoteurs S3, etc.)

| # | Outil (clé) | Entrée | Endpoint(s) | Calcul back (fichier) | Écran fiche qui reprend les chiffres |
|---|---|---|---|---|---|
| 1 | **PLU** (`plu`, O13) | commune / recherche texte | `GET /modules/plu-annuaire/{communes,search,pack/{insee}}` | `plu_ingest.search_reglement`, `commune.etat_corpus_plu` | §PLU (zone + procédure) |
| 2 | **Permis** (`permis`, M03 ; dormants M04) | commune / idu | `GET /modules/permis`, `/modules/promesses`, `/modules/parcelle-permis?idu=` | `modules.py:permis/promesses/parcelle_permis` | §Permis (200 m), signal viabilité |
| 3 | **Communes** (`communes`, O6 ; Évolution M18) | commune | `GET /communes`, `/communes/{c}/acquisitions-pm`, `/radar/marche` | `app.py:commune_acquisitions_pm`, `proprietaire_historique` | §Dynamique (acquisitions PM) |
| 4 | **Scan patrimoine** (`patrimoine`, M02) | société / SIREN / adresse | `GET /modules/patrimoine?siren=`, `/modules/patrimoine/search?q=` | `modules.py:patrimoine` (SELECT MAJIC) | §Propriétaire (SIREN, inverse) |
| 5 | **Assemblage** (`assemblage`, M16) | 2–8 idus | `POST /moteurs/assemblage {idus:[…]}` | `moteurs.py:assemblage` + `assemblage.aggregate_assiette` | §Assemblage (partenaire), SDP/tier |
| 6 | **Comparer des parcelles** (`comparer`, A8) | 2–3 idus | `GET /compare?idus=a,b,c` | `app.py:compare` → `_fiche_servie`/`fiche_payload` | toute la fiche (surface, zone, SDP, prix) |
| 7 | **Pièges et risques** (`risques`, M10) | idu | `GET /servitudes-invisibles/{idu}` | `servitudes.py:contraintes_parcelle` + `aleas_parcelle` | §Pièges & risques, §Aléas (MÊME fonction) |
| 8 | **Étude de zone** (`etude-zone`, M27) | idu/point/géom + rayon | `POST /outils/etude-zone` | `app.py:_calcul_etude_zone`, `zone/etude_de_zone.py` | §Autour de cette parcelle |
| 9 | **Estimer un bien** (`analyser-annonce`, N1) | adresse→idu / lien Leboncoin | `GET /radar/annonce/estimation/{idu}`, `POST /radar/annonce/analyser` | `pige/api.py:estimation_annonce` | §Marché (médiane €/m²), dernière mutation DVF |
| 10 | **Remonter le temps** (`temps`, M08) | idu | `GET /moteurs/parcellaire-epoque/{idu}`, `/parcels/{idu}/geojson` | `moteurs.py:parcellaire_epoque` ; lien ortho `enrichment.remonter_le_temps` | (pas de chiffre ; géom + lien IGN) |
| 11 | **Gabarit réglementaire** (`gabarit`, M24) | idu | `GET /outils/gabarit/{idu}` | `gabarit/builder.py` → `gabarit/engine.py:compute_gabarit` | §Constructibilité (hauteur, emprise, enveloppe) |
| 12 | **Taxe d'aménagement** (`taxe-amenagement`, K3) | idu + saisies | `GET /outils/taxe-amenagement`, `…/prefill?idu=`, `…/config` | `taxe_amenagement.calculer / taux_parcelle` | §Financier (taux), §Constructibilité (SDP) |
| 13 | **Prospection solaire** (`prospection-solaire`, M26) | commune + filtres / idu | `GET /modules/prospection-solaire`, `…/parcelle/{idu}` | table figée `parcel_solar` (PVGIS, gelée 11/07/2026) | (indépendant ; pas de reprise fiche) |
| 14 | **Blocs fonciers** (`blocs-fonciers`, M29) | commune + filtres | `GET /modules/blocs`, `/modules/blocs/{id}` | table pré-calculée `parcel_blocs` (contiguïté au batch) | SDP agrégée (même source) |
| 15 | **Successions à venir** (`successions`, M28) | commune + filtres | `GET /modules/successions` | `modules.py:_calcul_successions` sur `parcel_veille_succession` | tag veille succession (Score V) |
| 16 | **Courrier propriétaire** (`courriers`, M09) | idu + corps + destinataires | `GET /courrier/statut`, `POST /courrier/demande`, `…/composer`, `…/pdf` | `courrier.py` (CRUD + provider) | (idu → propriétaire, comme Patrimoine) |

Résolvants cachés éprouvés aussi : **Calculette foncière** `POST /modules/faisabilite/{idu}/charge`
(`bilan.py:compute_calculette`), **Étude de faisabilité** `POST /modules/etude/parcelles` + `/modules/etude`
(`modules.py` + moteur implantation, clé body = `idus`).

**Fiche de référence** : `GET /parcels/{idu}` → `app.py:_fiche_servie`/`_q_v2_fiche`. Champs servis
confrontés : `surface_terrain_m2` (servie = contenance), `surface_dessin_m2`, `etat_bien`,
`potentiel_a_batir.{zone_lib,zone_fam,constructible,rien_a_batir,sdp_restante_m2,motif}`,
`aleas.liste[]` (PPR rouge/bleu + aléas par niveau, % parcelle), `taxe_amenagement.taux_communal_pct`,
`terrain.pente_moy_deg`, `coproprietes[]`, `proprietaire_moral.{denomination,siren}`,
`prix_ancien.{median,fiable}`. **Doctrine LABUSE confirmée : le front ne recalcule rien ; chaque
outil et la fiche lisent le même robinet.**

---

## Les 20 parcelles-pièges (16 communes)

Sélection par SQL (`harnais/select_parcelles.py`, preuves `preuves/candidats.json`), choix figé dans
`preuves/choix.json`. Communes distinctes : Saint-Pierre, Saint-Louis, Le Tampon, Entre-Deux,
Saint-Benoît, L'Étang-Salé, Le Port, Saint-Paul, Saint-Leu, Saint-Philippe, Saint-Denis,
Saint-Joseph, Sainte-Marie, Salazie, Sainte-Suzanne, Cilaos = **16**.

| Piège | idu | Commune | Preuve (base q_v20 / fiche) |
|---|---|---|---|
| Nue en zone U | `97416000EI1048` | Saint-Pierre | Ud, emprise 0, SDP résiduelle 4 043 m², `etat_bien=nu` |
| Bâtie et saturée | `97414000CT1094` | Saint-Louis | UD, emprise 100 %, SDP résiduelle 0, `etat_bien=bati_max` |
| Bâtie, reste constructible | `97422000EH0128` | Le Tampon | Uc, emprise 41 %, SDP résiduelle 600 m², `bati_encore` |
| Pente forte | `97403000AV0009` | Entre-Deux | pente moy. **65,8°**, terrassement lourd, PPR rouge 100 % |
| À cheval sur 2 zones PLU | `97410000AY0201` | Saint-Benoît | recoupe A + Acor (gabarit multizone) |
| À cheval sur 2 communes | `97404000AC0006` | L'Étang-Salé | sur la limite communale (dist 0,00 m de Les Avirons) |
| Zone rouge partielle | `97407000AV0337` | Le Port | PPR rouge sur ~60 % ; zone Uem |
| Zone bleue | `97415000AB0316` | Saint-Paul | PPR bleue sur ~100 % |
| Minuscule (<100 m²) | `97413000DD1338` | Saint-Leu | contenance **6 m²** |
| Géante (>5 ha) | `97417000BN0004` | Saint-Philippe | **27 506 974 m²** (≈ 2 751 ha), zone PLU nulle |
| Copropriété | `97411000ES0054` | Saint-Denis | RNIC « LES TOURTEREAUX », 860 lots |
| Littoral (50 pas) | `97412000BW0702` | Saint-Joseph | bande des 50 pas géométriques, Nli + EBC |
| AU ouverte | `97415000HN0015` | Saint-Paul | AU1est, `classe=conditionnelle_operation` |
| AU fermée | `97410000AD0552` | Saint-Benoît | AUp1, `classe=declasse_au_fermee` |
| Zone A | `97418000AI0533` | Sainte-Marie | A, 29 990 m² |
| Zone N | `97421000BE0062` | Salazie | Npnr, 29 996 m² |
| Sans adresse | `97407000BB0009` | Le Port | aucune ligne `parcel_adresse` ; Uc |
| Sans propriétaire connu | `97420000BE0704` | Sainte-Suzanne | aucune personne morale (particulier/non nominatif) |
| Sans vente dans le voisinage | `97424000AR0021` | Cilaos | aucune mutation DVF rattachée ; N, cirque isolé |
| Monument historique | `97418000BD0016` | Sainte-Marie | abords de MH (SUP AC1), PPR rouge 100 % |

---

## Matrice outil × parcelle

Verdict : **V** = répond + cohérent fiche/métier · **O** = répond mais réserve (cohérence, libellé
ou logique) · **R** = plante / invente / chiffre faux présenté comme sûr · **–** = non applicable.
Colonnes = les outils qui s'appliquent à **une** parcelle (les outils de niveau commune — PLU,
Communes, Permis radar, Blocs, Successions, Courrier — sont éprouvés à part, §« Outils de niveau
commune »). CSV complet : `preuves/matrice.csv`.

| Parcelle (piège) | Risques | Gabarit | Taxe | Estimer | Solaire | Temps | Permis | Comparer | Ét.zone | Calcul. | Patrim. |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| nue zone U | V | V | V | V | V | V | V | V | V | V | V |
| bâtie saturée | V | V | V | V | V | V | V | V | V | V | – |
| bâtie + reste constructible | V | V | V | V | V | V | V | V | V | V | – |
| pente forte | V | **O** | V | **O** | V | V | V | V | V | V | – |
| 2 zones PLU | V | **O** | V | V | V | V | V | V | V | V | – |
| 2 communes | V | **O** | V | **O** | V | V | V | V | V | V | – |
| zone rouge partielle | V | **O** | V | **O** | V | V | V | V | V | V | V |
| zone bleue | V | **O** | V | **O** | V | V | V | V | V | V | – |
| minuscule <100 m² | V | V | V | **O** | V | V | V | V | V | V | V |
| géante >5 ha | V | **O** | V | **O** | V | V | V | V | V | V | V |
| copropriété | V | V | V | V | V | V | V | V | V | V | – |
| littoral 50 pas | V | **O** | V | **O** | V | V | V | V | V | V | V |
| AU ouverte | V | **O** | V | **O** | V | V | V | V | V | V | V |
| AU fermée | V | **O** | V | V | V | V | V | V | V | V | V |
| zone A | V | **O** | V | **O** | V | V | V | V | V | V | – |
| zone N | V | **O** | V | **O** | V | V | V | V | V | V | V |
| sans adresse | V | V | V | V | V | V | V | V | V | V | V |
| sans propriétaire connu | V | V | V | V | V | V | V | V | V | V | – |
| sans vente voisinage | V | **O** | V | **O** | V | V | V | V | V | V | V |
| monument historique | V | **O** | V | **O** | V | V | V | V | V | V | V |

**Totaux : V = 186 · O = 25 · R = 0 · n/a = 9.** Les oranges tombent dans **Gabarit** (13) et
**Estimer** (12), toujours sur des parcelles **inconstructibles / non bâties**. Assemblage n'a pas
de colonne (il exige ≥ 2 parcelles) : éprouvé en §cas-limites.

---

## Trouvailles, classées par gravité

### 🔴 ROUGE — aucune
Aucun outil ne plante, n'invente un fait, ni ne renvoie un chiffre faux présenté comme fiable. Les
réserves ci-dessous sont des défauts de cohérence ou de libellé, jamais des faussetés servies.

### 🟠 ORANGE

**O1 — Gabarit dessine une enveloppe constructible là où la fiche dit « Rien à bâtir ».**
Parcelle `97407000AV0337` (Le Port, zone **Uem**) : la fiche sert
`potentiel_a_batir = {constructible:false, rien_a_batir:true, motif:"Habitat interdit dans cette zone",
sdp_restante_m2:0}`. Le Gabarit, lui, renvoie `status:"ok"`, **zoneImplantationM2 = 763 m²**,
hauteur 18 m, et des `appliedRules` géométriques (reculs, emprise, hauteur, **exclusion** PPR). Le
moteur intègre les règles **géométriques** mais **pas la règle de destination** (habitat interdit),
que la fiche porte. `nonIntegratedRules` ne la signale pas ; `coverage.risques=false` est une réserve
faible. Un promoteur lisant « 763 m² implantables, R+5 » dans l'outil « Gabarit réglementaire » alors
que la zone interdit l'habitat ferait une erreur coûteuse. Le libellé front « où et jusqu'où une
construction peut s'implanter, **selon les règles réglementaires intégrées et sourcées** » surévalue
ce qui est réellement intégré. *C'est la trouvaille la plus sérieuse.*

**O2 — Gabarit : « Calcul incomplet — donnée réglementaire manquante » pour des parcelles
DÉFINITIVEMENT inconstructibles.** Sur ≥ 10 parcelles (N, A, AU fermée, PPR rouge 100 % : pente_forte,
deux_zones, deux_communes, ppr_bleue, littoral, au_ouverte, zone_A, zone_N, sans_vente, monument,
géante), le Gabarit renvoie `status:"incomplete"` + le message front *« le calcul reprendra dès que la
donnée manquante sera disponible »*. Ce message suggère une **attente de donnée**, pas une
**interdiction**. Pour une parcelle en zone N ou PPR rouge à 100 %, le verdict juste est
« inconstructible », pas « on vous le dira plus tard ». (À noter côté positif : pour zone_A, le champ
`raccordement.multizone` détecte bien le partage `A 70,7 % / N 29,3 %`.)

**O3 — Estimer un bien : prix « bâti » servi, fiabilité Moyenne/Élevée, sur des parcelles non bâties
ou inconstructibles — sans signaler la non-constructibilité.** Exemples : pente_forte (N, PPR rouge
100 %) → 3 289 €/m² « bâti », n=87, **fiabilité Moyenne** ; monument (N, PPR rouge 100 %) → 1 925 €/m²
« bâti », **fiabilité Élevée** ; littoral (Nli, EBC) → 2 922 €/m² ; géante (forêt 2 751 ha) → 2 682 €/m²
« bâti » (fiabilité Limitée, au moins). L'estimation est un **comparateur de secteur** honnête en soi,
mais l'outil s'appelle « Estimer un bien » et étiquette `type_comparateur="bati"` pour des parcelles
qui ne portent aucun bâti et ne peuvent rien recevoir. `valeur_indicative=null` limite la casse (pas
de valeur totale calculée), mais le €/m² « bâti » + la fiabilité induisent en erreur. L'estimation ne
lit pas la constructibilité de la parcelle.

**O4 — Taxe d'aménagement : calcul direct sans borne de saisie → résultats absurdes ou négatifs.**
`GET /outils/taxe-amenagement` accepte (statut 200, aucun avertissement) : `surface_taxable_m2=1e9`
→ **66,9 Md€** ; `taux_communal_pct=-5` → **taxe NÉGATIVE −2 230 €** ; `taux_communal_pct=9999`
→ 8,9 M€. Une surface négative est bien ramenée à 0, mais rien ne borne la surface par le haut ni les
taux (le taux est d'ordinaire pré-rempli public, mais l'override n'a aucune validation). **Contraste
net avec la Calculette foncière**, elle **strictement bornée** (voir V-ci-dessous).

**O5 — Comparer : abandon silencieux d'idu invalides/surnuméraires, doublons rendus tels quels.**
`GET /compare?idus=…` : un idu introuvable est **retiré sans message** (`count` baisse), un mélange
valide+bidon renvoie seulement le valide, 4 idus sont **plafonnés à 3 en silence**, et 4 fois le même
idu renvoie **3 lignes identiques** (pas de dédoublonnage). Jamais d'erreur : l'utilisateur voit une
table plus courte sans savoir pourquoi.

**O6 — Étude de zone : rayon invalide silencieusement ignoré.** `rayon_km` = −1, 0 ou 999 → statut 200,
`zone_disponible:true`, `rayon_km:null` : repli silencieux sur l'isochrone par défaut. L'utilisateur
qui demande « 999 km » obtient un isochrone de 10 min sans en être informé (`idu` introuvable, lui,
est franc : 404 « parcelle introuvable ou sans géométrie »).

### 🟢 VERT — robustesse et cohérence confirmées (points forts)

- **0 plantage / 0 erreur 500** sur 260 appels outil×parcelle (13 × 20) + cas-limites + niveau commune.
  Tous les codes = 200 (sauf refus volontaires : Assemblage 422 « ≥ 2 parcelles », Comparer/idu absent,
  Patrimoine « ignoré » quand pas de personne morale).
- **Cohérence SURFACE au m² près** : Gabarit, Comparer, Taxe-prefill, Estimation et Assemblage lisent
  tous la **surface servie** (`surface_terrain_m2` = contenance), identique à la fiche, y compris quand
  contenance ≠ dessin (2 zones : 8 275 partout ; minuscule : 6 partout ; géante : 27 506 974 partout).
- **Cohérence ZONE** : `comparer.zone` et `taxe-prefill.zone_plu` = `fiche.zone_lib` sur les 20.
- **Cohérence SDP** : `taxe-prefill.sdp_gabarit_m2` = `fiche.sdp_restante_m2` = `comparer.sdp_residuelle_m2`
  (nue 4 043 ; bâtie-reste 600 ; sans-proprio 1 455). **Aucune SDP supérieure à ce que le PLU permet**
  n'a été détectée (COS ≈ 1,35 pour la nue Ud, sous le plafond CES 60 % × R+5).
- **Cohérence RISQUES** : `/servitudes-invisibles` ≡ `fiche.aleas` au pourcentage près (PPR rouge/bleu %,
  aléas par niveau). Ex. bâtie-saturée : rouge 62 %, bleue 38 %, mvt moyen 100 % — identiques des deux
  côtés. Monument : **« Abords de Monument historique — avis ABF — Périmètre des abords »** bien listé
  (et `solaire.abf=true`). Littoral : **« 50 pas géométriques (bande littorale) »** bien listé.
- **Assemblage** vérifie la **contiguïté** (`ST_DWithin` 0,5 m) avant de sommer : 2 parcelles non
  contiguës → `contigu:false`, parcelle isolée **flaguée**, `gain_pct:-100`, note « accords,
  propriétaires et faisabilité restent à vérifier ». Exige ≥ 2 (422) ; idu absent → 404 « 1 parcelle(s)
  trouvée(s) sur 2 ». **N'additionne jamais des parcelles non contiguës sans le dire.**
- **Estimer** est honnête quand il manque des comparables : sans-adresse → `median:null` +
  « Pas assez de ventes de terrain nu comparables dans le secteur ». **SSRF-safe** : lien hors
  Leboncoin / vide / texte → `{ok:false, erreur:"url_invalide"}`, aucun fetch tenté.
- **Calculette foncière** : bornes **strictes** (422) sur coût ≤ 0 / négatif / énorme, marge < 0 / > 60,
  prix < 0, virgule décimale, texte dans un champ numérique. `calculable:false` propre quand capacité
  ou DVF manquent (pente, 2 zones, géante, littoral…).
- **Prospection solaire** : filtres absurdes (potentiel 1e7, proba 500 %, piscine < 0) → 0 résultat
  sans planter ; commune inexistante → 0 ; données « gelées au 11/07/2026 » annoncées.
- **Cas extrêmes de taille** : minuscule 6 m² → Gabarit `zoneImplantationM2 = 0` (correct),
  `calculable:false` ; géante 2 751 ha / zone nulle → tous les outils répondent, estimation « Limitée »,
  aucun plantage, 14 servitudes correctement listées (réserve biologique, DPF ravine…).
- **Successions** (niveau commune) : libellé « approche une succession », **jamais « en succession »** ;
  signal = âge dirigeant ≥ 70 ou SCI dormante, « ni décès ni mise en vente ».
- **Sans adresse / sans propriétaire / sans vente** : tous les outils répondent ; Patrimoine
  honnêtement indisponible sans personne morale ; estimation « Limitée » ou « indisponible ».
- **À cheval sur 2 communes** : la parcelle est mono-commune par construction cadastrale (aucune
  parcelle ne chevauche réellement une limite) ; tous les outils l'attribuent de façon cohérente à
  L'Étang-Salé, **sans jamais la mélanger** avec Les Avirons.
- **Remonter le temps** : FeatureCollection valide, **vide + source citée** quand la filiation
  d'époque manque (aucune invention). *Réserve de couverture : vide sur les 20 — la couche
  « parcellaire d'époque » (DFI/DGFiP) est peu peuplée ; le lien ortho IGN, lui, reste la fonction
  phare de l'outil.*

---

## Cas-limites de saisie (synthèse)

Preuve brute : `preuves/edge.json` (`harnais/edge_cases.py`).

| Outil | Champ | vide | 0 | négatif | très grand | décimale | texte | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Calculette** | cout, marge, vrd, prix | défauts secteur | **422** | **422** | **422** | virgule→**422** | **422** | 🟢 bornes strictes |
| **Taxe** | surface_taxable_m2 | ∅ (incomplet) | 0 € | ramené à 0 | **66,9 Md€** | OK | — | 🟠 pas de borne haute |
| **Taxe** | taux_communal_pct (override) | — | — | **−2 230 €** | **8,9 M€** | — | — | 🟠 taux négatif accepté |
| **Solaire** | potentiel/proba/piscine | — | — | ignoré (sain) | 0 résultat | — | — | 🟢 sain |
| **Assemblage** | idus | 422 | — | — | — | — | — | 🟢 ≥ 2 exigé |
| **Assemblage** | idu bidon | 404 clair | — | — | — | — | — | 🟢 |
| **Assemblage** | 2 non contiguës | `contigu:false` + isolées | — | — | — | — | — | 🟢 flagué |
| **Comparer** | idus | count 0 | — | — | cap 3 **silencieux** | — | — | 🟠 drop silencieux |
| **Estimer** | url | url_invalide | — | — | — | — | url_invalide | 🟢 SSRF-safe |
| **Étude de zone** | rayon_km | — | ignoré | ignoré | ignoré (999) | — | — | 🟠 repli muet |
| **Étude de zone** | idu | — | — | — | — | — | — | 404 clair 🟢 |

---

## Le harnais (rejouable)

Tout est dans `docs/audit-2026-11/nu-5/A/harnais/` ; les sorties brutes dans `preuves/`.

1. **`select_parcelles.py`** — requêtes SQL (une connexion/transaction isolée par critère, `statement_timeout`)
   qui trouvent les candidats des 20 pièges ; détection PPR par la fonction servie `labuse_ppr_couleur`,
   littoral par `spatial_layers.kind='cinquante_pas'`, monument par SUP `ac1`, 2-communes par distance au
   polygone `mvt_communes`. → `preuves/candidats.json`.
2. **`preuves/choix.json`** — les 20 idus figés + la preuve de chaque piège.
3. **`harness.py`** — appelle, pour chaque parcelle, la **fiche** (`GET /parcels/{idu}`) comme référence
   puis **tous les endpoints outils réels** (HTTP, port 9730), enregistre statut + ms + JSON. Variable
   `ONLY=` pour rejouer un sous-ensemble (mode fusion). → `preuves/resultats.json`.
4. **`edge_cases.py`** — passe de cas-limites de saisie (vide/0/négatif/énorme/virgule/texte) par outil.
   → `preuves/edge.json`.
   - **`resume_preuves.py`** — extrait COMPACT de `resultats.json` (brut ~7 Mio, non versionné car
     rejouable et bloqué par le hook > 2 Mio) → `preuves/resultats_resume.json` (60 Ko, versionné) :
     par parcelle × outil, statut + champs clés sur lesquels s'appuie ce rapport.
5. **`analyse.py`** — aplanit `resultats.json` en tableau lisible parcelle × outil avec l'écart à la fiche.
6. **`matrice.py`** — applique les règles de verdict (documentées en tête) → `preuves/matrice.csv` +
   l'affichage V/O/R.

**Rejeu** (backend local lancé sur 9730, `env=local`) :
```bash
PYTHONPATH=src .venv/bin/python -m uvicorn labuse.api.app:app --host 127.0.0.1 --port 9730 &
PYTHONPATH=src .venv/bin/python docs/audit-2026-11/nu-5/A/harnais/select_parcelles.py
BASE=http://127.0.0.1:9730 PYTHONPATH=src .venv/bin/python docs/audit-2026-11/nu-5/A/harnais/harness.py
BASE=http://127.0.0.1:9730 PYTHONPATH=src .venv/bin/python docs/audit-2026-11/nu-5/A/harnais/edge_cases.py
PYTHONPATH=src .venv/bin/python docs/audit-2026-11/nu-5/A/harnais/matrice.py
```
**Pièges de poste rencontrés (notés pour le prochain)** : (a) le venv est `~/Desktop/labuse/.venv`
(`PYTHONPATH=src`, rôle PG `openclaw`, base `labuse`) ; (b) `/readyz` peut rester **503**
(`schéma=ÉCHEC(verrou/ensure_schema)` si un ancien verrou d'avis traîne) **sans** empêcher les
endpoints de servir — tester un vrai endpoint, pas `/readyz` ; (c) un backend lancé en `nohup … &`
détaché se fait **SIGTERM** quand la tâche parente se termine → le lancer **au premier plan** d'une
tâche de fond persistante ; (d) les requêtes PostGIS `ST_Intersection/ST_Union` sur tout `parcels`
doivent être **bornées par commune** sous peine de timeout (GEOS InterruptedException).

---

## Portée et limites

- **Lecture seule** : aucune écriture en base, aucune correction de code, prod jamais touchée.
- Les outils de **niveau commune/portefeuille** (PLU annuaire, Communes, Permis radar, Blocs,
  Successions, Courrier, Étude de faisabilité) sont éprouvés en **fumée** (tous 200 + structure saine)
  et par leur **facette parcelle** quand elle existe (permis 200 m, patrimoine par SIREN, acquisitions
  PM par commune) ; ils ne sont pas dans la matrice parcelle car ils ne prennent pas un idu unique.
- La **cohérence prix** est bornée par la disponibilité DVF ; on a vérifié le comportement « pas de
  comparable » (honnête) et « bâti sur inconstructible » (O3), pas la justesse absolue de chaque médiane
  (hors périmètre NU5-A, cf. NU-4-C).
- L'« à cheval sur 2 communes » n'existe pas au cadastre (parcelles mono-commune) : le piège a été joué
  sur une parcelle **à la limite** (dist 0,00 m), ce qui teste bien l'attribution de bord.

## Pour qui veut corriger (hors mandat, pistes)
O1/O2 : faire porter au Gabarit le verdict de **destination** (habitat interdit, zone non ouverte) et
distinguer « inconstructible » de « donnée manquante ». O3 : gater l'estimation « bâti » sur la
constructibilité / présence de bâti, ou afficher la réserve. O4 : borner `surface_taxable_m2` et
refuser les taux négatifs côté `taxe-amenagement` comme le fait déjà la Calculette. O5/O6 : renvoyer
un message quand un idu est ignoré / un rayon invalide est remplacé.
