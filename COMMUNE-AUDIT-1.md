# COMMUNE-AUDIT-1 — Inventaire de la fiche commune

**Branche** `feat/commune-audit-1` depuis **main `85ac26a5`**. Lecture seule — aucune correction.
Le rapport sert à écrire le rangement.

Fiche commune = le volet `ContextePanel.tsx` (`[data-contexte-panel]`, 705 lignes), ouvert par le
bouton « Fiche commune » / l'omnibox (`setContexteCommune`). Il lit **trois** requêtes :
`GET /communes/{c}/contexte` (le gros du payload, `_compute_commune_contexte` + cache nocturne
`commune_contexte_cache` rafraîchi live), `motRarete` (`/pipeline-rarete` → l'enveloppe ZAN) et
`motMarcheCommune` (`/moteurs/marche/{c}` → la tendance 12 mois).

---

## Les quatre chiffres en tête

| Indicateur | Valeur | Lecture |
|---|---|---|
| **N cartes** | **19** rendues (20 robinets `fiche_commune_*` déclarés) | Le commentaire code « les 15 cartes » (`app.py:2049`) est **périmé** : SOURCES-1, SOURCES-4 et COUCHES-2 ont ajouté zonage ABC, fiscalité, ORT, AZI/TRI, quartiers IRIS et la carte ZFANG/FRR depuis. |
| **M lignes** | **70** lignes de données rendues dans les 19 cartes | hors sources, prose, portes et boutons. L'en-tête permanent re-sert 4 de ces lignes (terrain U · neuf · SRU · ZAN) en gros. |
| **K données commune du registre absentes** | **37** sur 76 données à la maille commune | dont **22 couches carte** (par nature sur la carte, pas une carte de fiche) et **15 tabulaires**, dont **~13 réellement absentes** de la fiche. |
| **J cellules « à valider »** | **20** sur **456** (19 × 24) | Le mandat cadrait 360 (15 × 24) sur le « 15 » périmé. Réel : **419 réelles · 20 à valider · 17 vides**. |

> **Écart de cadrage assumé.** Le mandat annonce « 15 cartes » et « /360 ». La réalité est **19 cartes
> rendues** adossées à **20 robinets** `fiche_commune_*`. Les nombres ci-dessus et toutes les tables
> comptent la réalité (19 / 456), pas le cadrage périmé.

---

## 1 · Les 15 → 19 cartes, dans l'ordre d'affichage

Trois groupes titrés (`GroupeLabel`), chaque carte est une `LigneCarte` (`<details data-acc>`) — fermée
elle dit l'essentiel (icône · titre · sous-titre · valeur/badge), un clic ouvre le détail. **Deux**
cartes sont **ouvertes par défaut** (`defaultOpen`) : Prix & tendance et Foncier repéré.

### En-tête permanent (au-dessus des groupes, jamais replié)
- **4 chiffres qui décident** : *terrain nu zone U* (€/m²) · *neuf sortie* (€/m²) · *taux LLS SRU* (%, + nb LLS + déficit pts) · *avant épuisement du ZAN* (ans).
- **3 portes** : « Voir ses parcelles → » (vert plein) · « ⊞ Comparer aux 24 » · « ◎ Étude de zone ».
- **Signaux nommés** (`data-fiche-signaux`, règles en constante — n'apparaissent que si vrais).
- **Bandeau RNU** (`data-rnu-bandeau`, si la commune est au Règlement National d'Urbanisme).

### Groupe « Construire ici »

| # | Carte (`data-acc`) | Regroupe | Condition d'apparition | Robinet |
|---|---|---|---|---|
| 1 | Règles d'urbanisme (`regle-plu`) | statut PLU + date + porte « Voir le PLU » | **toujours** | `fiche_commune_regles_urbanisme` |
| 2 | Enveloppe ZAN (`regle-zan`) | budget ZAN restant, rythme conso, horizon d'épuisement | **toujours** (données `motRarete`) | `fiche_commune_zan` |
| 3 | Logement social — SRU (`regle-sru`) | taux LLS, objectif, nb LLS, lecture métier | si `d.sru` | `fiche_commune_sru` |
| 4 | Permis & délais (`construire`) | permis 12 m/5 ans, délai médian, offre engagée, permis dormants | **toujours** | `fiche_commune_permis` |
| 5 | Programme local — PLH (`regle-plh`) | objectif logts/an EPCI, part sociale | si `d.plh` (EPCI a un PLH) | `fiche_commune_plh` |

### Groupe « Le marché »

| # | Carte (`data-acc`) | Regroupe | Condition d'apparition | Robinet |
|---|---|---|---|---|
| 6 | Prix & tendance (`marche`) *(ouvert)* | ancien médian, neuf sortie, tendance 12 m, mutations | **toujours** | `fiche_commune_prix` |
| 7 | Terrain nu (`terrain-nu`) | €/m² terrain nu par zone U / AU + n ventes | si `foncier.prix_terrain_nu.par_zone` | `fiche_commune_terrain_nu` |
| 8 | Annonces — Radar (`annonces`) | biens en vente, prix demandé, écart demandé/acté | si `d.marche_annonces` | `fiche_commune_annonces` |
| 9 | Loyers (`loyer`) | loyer médian €/m² + type | si `d.loyer` | `fiche_commune_loyers` |
| 10 | Zonage logement ABC (`zonage-abc`) | classe A/B/C de la commune | **toujours** (« non déterminée » si absent) | `fiche_commune_zonage_abc` |
| 11 | Taxe foncière (`fiscalite`) | TFPB commune/EPCI, TFPNB commune/EPCI, TEOM + fraîcheur | si `d.fiscalite` | `fiche_commune_fiscalite` |
| 12 | Revitalisation ACV/PVD/ORT (`ort`) | dispositif, condition Denormandie | si `d.ort` **et** `statut ≠ « hors »` | `fiche_commune_ort` |
| 13 | ZFANG / FRR (`zfang-frr`) | régime ZFANG, classement FRR | si `d.zfang_frr` | **AUCUN robinet** ⚠ |

### Groupe « Le territoire »

| # | Carte (`data-acc`) | Regroupe | Condition d'apparition | Robinet |
|---|---|---|---|---|
| 14 | Foncier repéré (`foncier`) *(ouvert)* | parcelles/ha, stock repéré, densifiables, SDP résiduelle | si `d.foncier` | `fiche_commune_foncier` |
| 15 | Zonage (`zonage`) | répartition U/AU/A/N (% de surface) | si `foncier.repartition_zonage` | `fiche_commune_zonage` |
| 16 | Risques (`risques`) | PPR %, mouvement de terrain, CatNat + détail, AZI/TRI, Parc National | **toujours** | `fiche_commune_risques` (+ `fiche_commune_azi_tri` embarqué) |
| 17 | Population & logement (`population`) | habitants/ménages, niveau de vie, logements/vacants, quartiers IRIS, 2 barres | **toujours** | `fiche_commune_population` (+ `fiche_commune_quartiers` embarqué) |
| 18 | Quartiers prioritaires (`qpv`) | QPV, NPNRU + noms | si `qpv.length > 0` **ou** `anru.length > 0` | `fiche_commune_qpv` |
| 19 | Mairie & service urbanisme (`contacts`) | adresse, tél, e-mail, site, annuaire + contacts nommés | si `d.mairie` | `fiche_commune_mairie` |

**Sous la dernière carte** (toujours visible, hors accordéon) : une **grille de 7 outils**
pré-remplis sur la commune (PLU · Permis · Densifier · Radar · Scan patrimoine · Solaire · Étude de
zone · Comparer) + « Voir plus d'outils → », puis le **pied** (date du précalcul nocturne + « aucune
n'entre dans le scoring »).

**Robinets vs cartes.** 20 robinets `fiche_commune_*` sont déclarés. Deux d'entre eux —
`fiche_commune_azi_tri` et `fiche_commune_quartiers` — ne sont **pas** des cartes autonomes mais des
**lignes embarquées** (AZI/TRI dans Risques ; quartiers IRIS dans Population). À l'inverse, la carte
**ZFANG/FRR** est rendue **sans robinet déclaré** (son bloc `zfang_frr` n'a pas de `chiffre` : voir
liste « à ranger »). Net : 18 cartes ↔ robinet 1-pour-1, +1 carte sans robinet, +2 robinets en ligne.

---

## 2 · Carte → lignes (libellé · donnée du registre · source · déclaration)

Légende : **donnée** = id `donnees.py` ; **source** = étiquette servie ; **déclaration** = robinet
`fiche_commune_*` (les cartes commune sont déclarées **dans le code** `registre/robinets.py`, pas en
YAML — les YAML `declarations/fiche/*` concernent la fiche *parcelle*).

### En-tête (4 chiffres)
| Libellé | Donnée | Source |
|---|---|---|
| terrain nu zone U €/m² | `prix_terrain_zone_eur_m2` | DVF terrain nu par zone PLU |
| neuf (sortie) €/m² | `prix_neuf_vefa_acte_eur_m2` | DVF/SITADEL — même run que le comparateur |
| taux LLS SRU % (+ nb LLS, déficit pts) | `taux_lls_pct`, `lls_inventaire_n`, `deficit_sru_pts` | Inventaire SRU (DHUP) |
| avant épuisement du ZAN (ans) | `zan_reste_ha` / `rythme_conso` → horizon | Consommation ENAF Cerema · loi Climat (**estimé**) |

### 1 · Règles d'urbanisme — `fiche_commune_regles_urbanisme` — 2 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Statut PLU (badge) | `statut_plu` | GPU / veille PLU (`veille_plu` + `rnu`) |
| Date de règlement (sous-titre) | `statut_plu.date_reglement` | idem |

### 2 · Enveloppe ZAN — `fiche_commune_zan` — 3 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Budget ZAN restant (estimé) | `zan_reste_ha` | Consommation ENAF Cerema · loi Climat (**estimé**) |
| Rythme de consommation | `rythme_conso_ha_an` | idem |
| Horizon d'épuisement | `horizon_epuisement_ans` (dérivé) | idem |

### 3 · Logement social — SRU — `fiche_commune_sru` — 4 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Taux LLS | `taux_lls_pct` | Inventaire SRU (DHUP) |
| Objectif | `sru.objectif_pct` | idem |
| Nombre de LLS | `lls_inventaire_n` | idem |
| Déficit (pts) | `deficit_sru_pts` (SQL `greatest(obj−taux,0)`) | idem |

### 4 · Permis & délais — `fiche_commune_permis` — 5 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Permis autorisés 12 m (+ 5 ans) | `permis_12m_n` (+ `permis_5a_n`) | SITADEL |
| Délai d'instruction médian | `velocite_delai_median_mois` | m10 |
| Offre engagée (logts/12 m) | `logements_12m` | SITADEL |
| Permis dormants (point mort) | `point_mort_n` | PC caducs (**Estimé**) |

### 5 · Programme local — PLH — `fiche_commune_plh` — 2 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Objectif logts/an | `plh_objectif_logements_an` | PLH (EPCI) |
| Part sociale visée | `plh.part_sociale_pct` | idem |

### 6 · Prix & tendance — `fiche_commune_prix` *(ouvert)* — 4 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Ancien médian (commune entière) | `prix_ancien_median_eur_m2` | DVF — médiane commune entière |
| Neuf (prix de sortie) | `prix_neuf_vefa_acte_eur_m2` | idem |
| **Tendance 12 mois** ⚠ | `motMarcheCommune` `tendance_12m` | DVF — **jamais rendue** (bug `pct` / `delta_pct`, cf. §6) |
| Mutations 12 mois (DVF) | `mutations_12m_n` | DVF |

### 7 · Terrain nu — `fiche_commune_terrain_nu` — 4 lignes
| Libellé | Donnée | Source |
|---|---|---|
| €/m² terrain nu zone U + n ventes | `prix_terrain_zone_eur_m2` (U) | DVF terrain nu par zone PLU |
| €/m² terrain nu zone AU + n ventes | `prix_terrain_zone_eur_m2` (AU) | idem (« zone — » si < 10 ventes) |

### 8 · Annonces — Radar — `fiche_commune_annonces` — 3 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Biens en vente | `annonces_actives_n` | Radar LABUSE |
| Prix demandé médian | `prix_demande_median_eur_m2` | idem |
| Écart demandé / acté | `ecart_demande_acte_pct` | Radar × baromètre DVF (repli phrase si `sous_seuil`) |

### 9 · Loyers — `fiche_commune_loyers` — 1 ligne
| Libellé | Donnée | Source |
|---|---|---|
| Loyer médian (+ type) | `loyer_median_eur_m2` | DHUP — carte des loyers |

### 10 · Zonage logement ABC — `fiche_commune_zonage_abc` — 1 ligne
| Libellé | Donnée | Source |
|---|---|---|
| Classe de la commune (+ millésime) | `zonage_abc_logement` | DHUP — zonage ABC (arrêté 01/08/2014) |

### 11 · Taxe foncière — `fiche_commune_fiscalite` — 5 lignes
| Libellé | Donnée | Source |
|---|---|---|
| TFPB commune | `tfpb_taux_pct` | DGFiP — fichier REI |
| TFPB intercommunalité | `fiscalite.tfpb_epci_pct` | idem |
| TFPNB commune | `tfpnb_taux_pct` | idem |
| TFPNB intercommunalité | `fiscalite.tfpnb_epci_pct` | idem |
| TEOM (taux plein) | `fiscalite.teom_pct` | idem (drapeau « à rafraîchir » si `perime`) |

### 12 · Revitalisation ACV/PVD/ORT — `fiche_commune_ort` — 2 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Dispositif (ACV/PVD/ORT) | `ort_statut` | DGALN — communes ORT |
| Condition Denormandie | `ort.denormandie` | idem |

### 13 · ZFANG / FRR — **sans robinet** — 2 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Régime ZFANG (renforcé/standard) | `zfang_frr.zfang.regime` | `territoire_fiscal` (ZFANG source_ref) |
| Classement FRR (totalité/partie/hors) | `zfang_frr.frr.classement` | `territoire_fiscal` (FRR source_ref) |

### 14 · Foncier repéré — `fiche_commune_foncier` *(ouvert)* — 6 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Parcelles + surface (ha) | `n_parcelles_commune` | Cadastre DGFiP |
| Stock foncier repéré (n + ha promus) | `stock_opportunites` | Classement servi LABUSE |
| Densifiables | `n_densifiables` | analyse LABUSE (Densifier) |
| SDP résiduelle théorique | `densifiables.sdp_residuelle_m2` | idem |

### 15 · Zonage (répartition) — `fiche_commune_zonage` — 4 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Part zone U / AU / A / N (% surface) | `part_zone_U_pct` … `part_zone_N_pct` | Zonage PLU (GPU) |

### 16 · Risques — `fiche_commune_risques` (+ `fiche_commune_azi_tri`) — 6 lignes
| Libellé | Donnée | Source |
|---|---|---|
| PPR (risque naturel) | `ppr_pct` | Géorisques |
| Mouvement de terrain | `risques.mouvement_terrain_pct` | Géorisques |
| Arrêtés CatNat (+ détail 6 max) | `catnat_n`, `catnat_arretes_liste` | GASPAR |
| Inondation (AZI / TRI) | `azi_tri_commune` | GASPAR |
| Aire d'adhésion Parc National | `risques.parc_national` | BD TOPO |

### 17 · Population & logement — `fiche_commune_population` (+ `fiche_commune_quartiers`) — 9 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Habitants · ménages | `habitants_n`, `population.menages` | INSEE Filosofi 2021 |
| Niveau de vie moyen | `population.niveau_vie_moyen_eur` | idem |
| Logements (+ vacants) | `population.logements`, `population.vacants` | INSEE RP |
| Vacance (%) | `vacance_pct` | dérivé (moteur `commune_compteurs`) |
| Par quartier (n IRIS, min/méd/max) | `iris_commune_quartiers` | INSEE RP IRIS 2022 |
| Barre locataires/propriétaires/logés gratuits | `autres_loges_pct` (+ marche) | INSEE RP |
| Barre maisons/appartements | `marche.maisons_pct`, `apparts_pct` | INSEE RP |

### 18 · Quartiers prioritaires — `fiche_commune_qpv` — 2 lignes
| Libellé | Donnée | Source |
|---|---|---|
| QPV (+ noms) | `qpv_n` | ANCT |
| NPNRU | `anru` | ANCT |

### 19 · Mairie & service urbanisme — `fiche_commune_mairie` — 5 lignes
| Libellé | Donnée | Source |
|---|---|---|
| Adresse · Téléphone · E-mail · Site officiel · Annuaire | `mairie_coordonnees` | Annuaire de l'administration |
| Contacts nommés (`ContactsMairie`) | `commune_contacts` | saisie LABUSE (lecture tous comptes) |

**M = 70 lignes** (2+3+4+5+2+4+4+3+1+1+5+2+2+6+4+6+9+2+5). L'en-tête re-sert 4 de ces lignes.

---

## 3 · Ce qui manque — données commune du registre absentes de la fiche

**76** données à la maille commune dans `donnees.py`. **39** sont câblées à un robinet `fiche_commune_*`.
**37 ne le sont dans aucune carte** — réparties ainsi :

**(a) 22 couches carte** (`*_couche` — par nature peintes sur la carte, pas des cartes de fiche) :
`alea_inondation_couche`, `alea_mvt_couche`, `axes_couche`, `bpe_couche`, `bruit_couche`,
`casias_couche`, `cinquante_pas_couche`, `dispositifs_couche`, `dpu_couche`, `ebc_couche`,
`equip_osm_couche`, `er_couche`, `gpu_brut_couche`, `lignes_ht_couche`, `parc_national_couche`,
`ppr_couche`, `rpg_couche`, `sis_couche`, `sup_couche`, `tcsp_couche`, `transport_couche`,
`vefa_couche`, `znieff_couche`. *(NB : `ppr`/`mvt`/`inondation`/`parc_national` sont tout de même
**résumés** en % dans la carte Risques ; la couche elle-même vit sur la carte.)*

**(b) 15 données tabulaires non montrées comme carte** — dont **certaines visibles autrement** :

| Donnée | Libellé | État sur la fiche commune |
|---|---|---|
| `acquisitions_pm_n` | Acquisitions récentes (PM) | **Calculée et présente dans le payload** (`acquisitions_pm`) mais **aucune carte ne la rend** — sortie de la fiche par RETOURS-1 R3 (→ outil Communes). *Donnée servie mais non affichée.* |
| `delai_vente_median_j` | Délai médian de vente (Radar) | **absente** (la carte Annonces montre l'écart, pas le délai de vente) |
| `parc_social_rpls_logements` | Parc social (RPLS) | **absente** de la fiche commune — visible **seulement** sur la fiche parcelle (cf. §4) |
| `comparateur_composite` | Score composite | absente (outil Comparer uniquement) |
| `pression_zan_ha` | Pression ZAN (ENAF consommé) | absente (la fiche montre `rythme_conso`, pas l'ENAF brut) |
| `couverture_commune_pct` | Couverture des sources / commune | absente (page Sources) |
| `n_extraits_plu` | Extraits de règlement | absente (outil PLU) |
| `n_procedures_plu` | Procédures d'urbanisme en cours | absente (outil PLU) |
| `simulplu_resultat` | Simuler un changement | absente (outil PLU simuler) |
| `tranche_prix_vefa` | Prix logement neuf (VEFA) | absente (couche VEFA) |
| `prix_neuf_observe_eur_m2` | Prix du neuf — observé | absente (la fiche montre le neuf **VEFA acté**, pas l'observé) |
| `parcelles_par_zone_n` | Parcelles en zone … | absente (panneau filtres) |
| `n_piscines` | Piscines détectées | **visible** — porté comme compteur de la tuile « Solaire » de la grille d'outils (pas une carte) |
| `permis_5a_n` | Permis 5 ans (SITADEL) | **visible** — rendu en ligne dans la carte Permis (« · N sur 5 ans ») ; sa déclaration vit sous le robinet comparateur, pas `fiche_commune_permis` |

**À ranger en priorité** (données commune absentes qui auraient leur place) : `acquisitions_pm_n`
(déjà dans le payload — la ranger ou la retirer), `delai_vente_median_j`, `parc_social_rpls_logements`
(cf. doublon §4). **Un robinet manque** aussi pour la carte **ZFANG/FRR** (rendue sans `fiche_commune_*`).

---

## 4 · Doublons avec la fiche parcelle

La fiche **parcelle** affiche **41 lignes à la maille commune** (FICHE-AUDIT-1 : 111 affichables =
63 parcelle · **41 commune** · 4 propriétaire · 2 zone · 1 annonce). C'est presque tout le « contexte
commune » ré-affiché sur la parcelle. Croisé à la maille du chiffre :

**Aussi sur la fiche commune (doublons de contexte — présents des deux côtés) :**
`statut_plu` (§1) · `tfpb_taux_pct` + `tfpnb_taux_pct` (§11) · `zonage_abc_logement` (§10) ·
`ort_statut` (§12) · `azi_tri_commune` (§16) · `prix_ancien_median_eur_m2`, `prix_neuf_vefa_acte_eur_m2`,
`mutations_12m_n`, `prix_terrain_zone_eur_m2`, `loyer_median_eur_m2`, `annonces_actives_n`,
`prix_demande_median_eur_m2`, `ecart_demande_acte_pct` (§3/§6/§7/§8/§9) · `iris_commune_quartiers` (§17) ·
dispositifs `qpv_n` / ANRU / ZFANG / FRR (§18/§13). → Le contexte marché + réglementaire + fiscal +
dispositifs de la commune est **redondant** entre les deux fiches (voulu : chaque fiche est autonome).

**Info commune visible SEULEMENT depuis une parcelle (mal rangée) :**

| Donnée | Libellé | Où |
|---|---|---|
| `parc_social_rpls_logements` | Parc social (logements RPLS) | fiche parcelle (Marché) — **jamais** sur la fiche commune, alors que c'est un fait 100 % communal |
| `prix_neuf_observe_eur_m2` | Prix du neuf — observé | fiche parcelle (Constructibilité) — la fiche commune ne montre que le neuf **VEFA acté**, pas l'observé |

**Info commune riche et absente de la parcelle (normal — la commune est chez elle) :** enveloppe ZAN,
SRU détaillé, PLH, permis & délais, foncier repéré / densifiables, répartition de zonage, population &
logement, PPR/CatNat détaillés, mairie. Aucune de celles-ci n'est « mal rangée ».

**Verdict.** Un seul vrai défaut de rangement : **`parc_social_rpls_logements`** (fait communal visible
uniquement depuis une parcelle) — et accessoirement `prix_neuf_observe_eur_m2`.

---

## 5 · Les 24 communes — grille 19 × 24

Rubrique : **● réelle** = carte affichée, valeur concrète, sans réserve du code · **◐ à valider** =
carte affichée mais le code lève une réserve pour cette commune (`sous_seuil` Radar · `< 10` ventes
terrain · `perime` · `document local`/source nulle · non projetable) · **○ vide** = carte non affichée
(condition fausse) ou valeur nulle/« non déterminée ».

| Carte | Bras-P. | Cilaos | Entre-2 | Étang-Salé | Plaine-P. | Possession | Le Port | Le Tampon | Avirons | 3-Bassins | Petite-Île | St-André | St-Benoît | St-Denis | St-Joseph | St-Leu | St-Louis | St-Paul | St-Philippe | St-Pierre | Ste-Marie | Ste-Rose | Ste-Suzanne | Salazie | R/◐/○ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Règles d'urbanisme | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Enveloppe ZAN | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| SRU | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Permis & délais | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| PLH | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Prix & tendance | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Terrain nu | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ◐ | ● | ● | ● | ● | ● | 23/1/0 |
| Annonces Radar | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ● | ◐ | ● | ◐ | ◐ | ◐ | ● | ◐ | ◐ | ● | ◐ | ◐ | ◐ | 5/19/0 |
| Loyers | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Zonage ABC | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Taxe foncière | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Revitalisation | ● | ● | ● | ● | ● | ● | ● | ○ | ● | ● | ● | ● | ● | ○ | ● | ● | ○ | ● | ● | ● | ○ | ● | ○ | ● | 19/0/5 |
| ZFANG/FRR | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Foncier repéré | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Zonage réparti. | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Risques | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Population | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |
| Quartiers prio. | ○ | ○ | ○ | ○ | ○ | ○ | ● | ● | ○ | ○ | ○ | ● | ● | ● | ● | ● | ● | ● | ○ | ● | ● | ○ | ● | ○ | 12/0/12 |
| Mairie | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | 24/0/0 |

Légende colonnes: Bras-P.=Bras-Panon · Cilaos=Cilaos · Entre-2=Entre-Deux · Étang-Salé=L'Étang-Salé · Plaine-P.=La Plaine-des-Palmistes · Possession=La Possession · Le Port=Le Port · Le Tampon=Le Tampon · Avirons=Les Avirons · 3-Bassins=Les Trois-Bassins · Petite-Île=Petite-Île · St-André=Saint-André · St-Benoît=Saint-Benoît · St-Denis=Saint-Denis · St-Joseph=Saint-Joseph · St-Leu=Saint-Leu · St-Louis=Saint-Louis · St-Paul=Saint-Paul · St-Philippe=Saint-Philippe · St-Pierre=Saint-Pierre · Ste-Marie=Sainte-Marie · Ste-Rose=Sainte-Rose · Ste-Suzanne=Sainte-Suzanne · Salazie=Salazie

**Total 19 × 24 = 456 : ● 419 réelles · ◐ 20 à valider · ○ 17 vides.**

Lecture : **17 cartes sur 19 sont pleines sur les 24 communes.** Les seuls creux :
- **Annonces — Radar** : 19 communes `sous_seuil` (couverture Radar mince hors grandes villes) — seules Le Port, Saint-André, Saint-Denis, Saint-Paul, Sainte-Marie ont assez d'annonces.
- **Quartiers prioritaires** : 12 communes sans QPV/ANRU (carte absente = normal, pas un trou de données).
- **Revitalisation ORT** : 5 communes « hors » dispositif (carte absente).
- **Terrain nu** : Saint-Philippe sous le seuil de 10 ventes en zone U (« zone — »).

Réserves **systémiques** (non par-commune, donc non comptées en ◐ mais à savoir) : l'**enveloppe ZAN**
et les **permis dormants** sont **estimés** par construction (étiquette « estimé » / « Estimé » sur les
24) ; la **tendance 12 mois** de la carte Prix est **muette sur les 24** (bug §6).

---

## 6 · Les cachées (visibles après un clic) + anomalies

**Derrière l'accordéon** — 17 cartes sur 19 sont **fermées par défaut** (seules Prix & tendance et
Foncier repéré sont `defaultOpen`). Tout le **détail** d'une carte fermée est caché jusqu'au clic ;
l'essentiel (chiffre-clé) reste porté sur la ligne fermée (`val`). L'état ouvert/fermé est **mémorisé**
par carte (`localStorage` `labuse.fiche.acc`). Contenus qui n'apparaissent qu'ouverts :
- **Risques** : le détail des arrêtés CatNat (péril, dates, code national), la ligne AZI/TRI, le Parc National.
- **Population** : les quartiers IRIS (min/méd/max), les 2 barres (occupation, typologie).
- **SRU** : la lecture métier (encadré couleur).
- **Terrain nu** : le détail par zone U/AU.
- **Mairie** : les **contacts nommés** (`ContactsMairie`, chargés à l'ouverture ; ajout réservé admin).
- **Permis / Foncier / Annonces** : les **passerelles** (« Ouvrir Permis », « Densifier », « Voir les annonces dans le Radar »).

**Toujours visibles (pas derrière un clic)** : l'en-tête 4 chiffres, les signaux, le bandeau RNU, la
grille d'outils, le pied.

**Anomalies relevées (lecture seule — aucune correction) :**
1. **Tendance 12 mois muette.** `ContextePanel.tsx:404` lit `tend['pct']` ; le moteur marché émet
   `delta_pct` (jamais `pct` — vérifié 0/24). Le badge de tendance et la ligne « Tendance 12 mois » de
   la carte Prix **ne s'affichent jamais**. La carte montre ancien/neuf/mutations, la tendance est perdue.
2. **`acquisitions_pm` servie mais jamais rendue.** `_compute_commune_contexte` renvoie
   `acquisitions_pm` dans le payload ; aucune carte de `ContextePanel.tsx` ne la lit (déménagée vers
   l'outil Communes par RETOURS-1 R3). Donnée calculée et transportée pour rien côté fiche.
3. **Commentaire « les 15 cartes » périmé** (`app.py:2049`) — 20 robinets, 19 cartes rendues.
4. **Carte ZFANG/FRR sans robinet** `fiche_commune_*` (seule carte non déclarée au registre).

---

## Les quatre listes courtes

**Absentes** (données commune du registre non rendues, hors 22 couches carte) : `acquisitions_pm_n`
*(servie, non affichée)*, `delai_vente_median_j`, `parc_social_rpls_logements`, `comparateur_composite`,
`pression_zan_ha`, `couverture_commune_pct`, `n_extraits_plu`, `n_procedures_plu`, `simulplu_resultat`,
`tranche_prix_vefa`, `prix_neuf_observe_eur_m2`, `parcelles_par_zone_n`. *(2 « absentes » sont en fait
visibles ailleurs : `n_piscines` = tuile Solaire, `permis_5a_n` = ligne Permis.)*

**Doublons avec la fiche parcelle** : `statut_plu`, `tfpb_taux_pct`, `tfpnb_taux_pct`,
`zonage_abc_logement`, `ort_statut`, `azi_tri_commune`, `prix_ancien_median_eur_m2`,
`prix_neuf_vefa_acte_eur_m2`, `mutations_12m_n`, `prix_terrain_zone_eur_m2`, `loyer_median_eur_m2`,
`annonces_actives_n`, `prix_demande_median_eur_m2`, `ecart_demande_acte_pct`, `iris_commune_quartiers`,
`qpv_n`/ANRU/ZFANG/FRR. **Mal rangé (parcelle seule)** : `parc_social_rpls_logements`, `prix_neuf_observe_eur_m2`.

**À valider** (20 cellules) : **Annonces — Radar** `sous_seuil` sur 19 communes (Bras-Panon, Cilaos,
Entre-Deux, L'Étang-Salé, La Plaine-des-Palmistes, Le Tampon, Les Avirons, Les Trois-Bassins,
Petite-Île, Saint-Benoît, Saint-Joseph, Saint-Leu, Saint-Louis, Saint-Philippe, Saint-Pierre,
Sainte-Rose, Sainte-Suzanne, Salazie) ; **Terrain nu** < 10 ventes zone U (Saint-Philippe).
*(Systémique : ZAN + permis dormants « estimés » sur 24 ; tendance Prix muette sur 24.)*

**Visibles après clic** : détail CatNat + AZI/TRI + Parc National (Risques) · quartiers IRIS + 2 barres
(Population) · lecture SRU · détail terrain U/AU · contacts nommés Mairie · passerelles outils. 17/19
cartes fermées par défaut (Prix & Foncier ouvertes).

---

## Preuve

Deux communes témoins — **Saint-Denis** (grande) et **Cilaos** (petite) — chaque carte capturée dépliée :
`captures/commune-audit/{saint-denis,cilaos}/` (18 cartes chacune + `panel_full.png`). Saint-Denis n'a
pas la carte ORT (`statut = hors`) ; Cilaos n'a pas la carte QPV (0 QPV/ANRU) — les deux cartes
manquantes de l'une sont **présentes et dépliées sur l'autre**, donc **les 19 cartes sont couvertes**.
Script rejouable : `frontend/qa/commune_audit1_cap.mjs` (+ `manifest.json`).

Scripts d'analyse (lecture seule) : `qa/commune_audit1_collect.py` (payloads des 24 communes via
TestClient), `qa/commune_audit1_grid.py` (grille 19 × 24), données figées dans
`qa/commune_audit1_payloads.json`, `qa/commune_audit1_aux.json`, `qa/commune_audit1_grid.json`.

**Aucune correction. Lecture seule. « Ne merge pas. »**
