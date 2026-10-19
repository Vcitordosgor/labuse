# CHASSE-DOCS-1 — chasse aux écarts sur la catégorie Docs et les outils parcelle

**Modèle** Opus · **lecture seule** (aucune correction, aucun merge) · **branche** `audit/chasse-docs-1` depuis `origin/main` (`43733e0a`) · **worktree** `~/Desktop/labuse-chasse-docs` · **ports** API 8830 / front 6030.
**Run servi** `q_v19` · cascade `q_v19_sources` · `residuel_run_seq 16` (promu le 19/10/2026, `config/served_manifest.json`) · base Mac `postgresql:///labuse` (socket `openclaw`).
**Date** 2026-10-19.

---

## Résumé

**17 écarts retenus, 0 bredouille.** La chasse ne revient pas les mains vides : l'alignement des *valeurs chiffrées* d'un lecteur à l'autre est **solide** (surface = contenance partout, TA et taxe foncière recalculées à la main au centime, prix/zone/hauteur/CES cohérents), mais la couche **texte & présentation** des documents porte plusieurs défauts, dont deux qui atteignent directement le client.

| Gravité | Nombre | Écarts |
|---|---|---|
| **FAUX-CLIENT** | 2 | E-02, E-04 |
| **incohérence** | 7 | E-01, E-03, E-05, E-06, E-07, E-08, E-09 |
| **erreur** | 4 | E-10, E-11, E-13, E-16 |
| **doublon** | 1 | E-17 |
| **cosmétique** | 3 | E-12, E-14, E-15 |

### Les 5 pires

1. **E-02 — un dict Python brut dans le Dossier client.** §Sols de `97416000DY0106` imprime `CASIAS : {'nom': 'Sucrerie Casernes', 'subtype': 'casias', 'statut': 'En arrêt', 'distance_m': 44, 'sur_place': False, 'fiche_risque': 'https://…'}`. Donnée technique crue (dict, `False`, URL) servie telle quelle.
2. **E-04 — l'Étude de faisabilité ne se livre pas, en silence.** `POST /modules/etude` et `/modules/etude/pdf` dépassent 60–200 s sur grande parcelle (`97415000EV0324`, 41 009 m²) → `HTTP 000 timeout`, pas une erreur propre. Le moteur reste lent même sur une petite parcelle (3 279 m²) avec un objectif ≠ défaut (> 200 s).
3. **E-05 — le Dossier dit « non constructible », l'Étude vend 350 m².** `97416000DY0106` (à cheval N 54 % / Ud 46 %) : le Dossier §10 affirme « saturée · densité dépassée > 300 % » **et** « surface de plancher non calculable (zone non constructible) », tandis que Comparer et l'Étude servent « Ud · R+4 · 350 m² constructible ».
4. **E-01 — la mixité sociale se contredit dans la même section.** §Urbanisme affiche « seuil 1 800 m² » + « quota 30 % » (sourcés) **et**, trois lignes plus bas, « Mixité sociale : seuils de la zone non renseignés à ce jour ». (3/10 parcelles.)
5. **E-03 — courrier « À l'occupant » à un propriétaire pourtant nommé.** Le Dossier nomme « Personne morale — COMMUNE DE SAINT-BENOIT (SIREN …) » ; le Courrier adresse « À l'occupant » à l'adresse de la mairie. (4/10 parcelles, toutes à propriétaire public connu.)

### Ce qui est JUSTE (vérifié, pas un écart)

- **Surface = contenance cadastrale** partout (fiche / Comparer / Gabarit / Taxe), le dessin `ST_Area` reste discret (CONTENANCE-1 respecté).
- **Taxe d'aménagement recalculée à la main = endpoint** : 120 m² RP à Saint-Paul → 4 683 € (3 122 communal + 1 561 départemental, assiette 62 440 €), au centime.
- **Taxe foncière = source REI** : `commune_rei` 97415 = 41,77 / 16,00 / 30,91 · 97401 = 29,55 / 17,91 / 38,27 · 97416 = 44,18 / 17,91 / 24,26, byte-identiques à la fiche.
- **« SDP du scénario »** dans l'Étude de faisabilité — jamais « SDP maximale réglementaire » (règle IMPLANTATION-4 LOT C tenue ; le « SDP maximale réglementaire » du **Comparatif** est, lui, correct : Comparer ≠ Étude).
- **L'ancien moteur de capacité a disparu** du Dossier / Comparatif / fiche : partout « Nombre de logements → voir l'Étude de faisabilité » (IMPLANTATION-4 LOT B tenu).
- **Comparables DVF** = carte grisée « bientôt » (non cliquable) — conforme au mandat, non forcée.
- **Densifier** = retiré du produit (DENSIFIER-PLI, plié dans le filtre Capacité) — aucun résidu trouvé dans les outils.
- **Prix** : métriques distinctes et bien étiquetées (Comparatif « Prix bâti (section cadastrale) 3 804 €/m² » vs fiche « prix ancien médian 3 811 €/m² · 24 ventes < 500 m ») — pas un écart.

---

## Méthode

- **API** servie localement (`uvicorn labuse.api.app:app --port 8830`), front non requis (tout en JSON / PDF).
- **Collecte** : `scripts/coherence/_chasse_docs_collecte.py` — pour chaque IDU, archive sous `docs/audit-2026-10/chasse-docs/<idu>/` : `fiche.json`, les 9 documents Docs (Dossier, Bilan modèle, Apporteur, Pré-dossier PC, Gabarit, Comparatif, Étude de zone, Étude de faisabilité, + Comparables DVF = grisé), les outils parcelle (Pièges & risques, Taxe, Prospection solaire, Gabarit, PLU par parcelle, Permis, Comparer, Remonter le temps, Courrier aperçu ; **Densifier retiré du produit**), et le `pdftotext -layout` de chaque PDF.
- **Analyse** : `scripts/coherence/_chasse_docs_analyse.py` (tableau notion × lecteur) + relecture des `pdftotext` + relecture du code source pour la cause.
- **Banc rejouable** : `scripts/coherence/chasse_docs.py` (17 gardes, 1 par écart, 0 ECART attendu après correction).

### Échantillon (10 parcelles)

| # | IDU | Commune | Profil | Rôle |
|---|-----|---------|--------|------|
| 1 | 97415000BO0852 | Saint-Paul | bâtie saturée, U1a | témoin |
| 2 | 97401000AD0554 | Les Avirons | nue Ud3 | témoin |
| 3 | 97416000DY0106 | Saint-Pierre | N bâtie (à cheval N/Ud) | témoin |
| 4 | 97411000AV0110 | Saint-Denis | à cheval Uh/N | témoin |
| 5 | 97410000AN0347 | Saint-Benoît | PM commune | témoin |
| 6 | 97411000BZ1065 | Saint-Denis | — | témoin |
| 7 | 97415000BW0102 | Saint-Paul | à cheval U6c/A/N | témoin |
| 8 | 97416000CZ0678 | Saint-Pierre | **PPR rouge partielle (39 %)** | choix CC |
| 9 | 97415000EV0324 | Saint-Paul | **AU fermée (AU2c conditionnelle)**, 41 009 m² | choix CC |
| 10 | 97411000DS0186 | Saint-Denis | **> 2 ha (20 001 m², Ui)** | choix CC |

---

## Angle A — même valeur partout (notion × lecteur)

Tableau notion × lecteur construit sur les lecteurs structurés (fiche, Comparer, Gabarit outil, Taxe, faisabilité) + relecture PDF. **L'alignement des valeurs chiffrées est bon**, les divergences apparentes sont pour l'essentiel des **métriques distinctes bien séparées** ou des **choix de référence légitimes** :

| Notion | Verdict | Détail |
|---|---|---|
| Surface (contenance) | ✅ cohérent | fiche.contenance = Comparer.surface_m2 = Taxe.surface_terrain = Gabarit.surfaceParcelleM2 (quand mono-zone). À cheval : le Gabarit calcule sur la **portion de zone** (champ nommé `surfaceParcelleM2`, légèrement trompeur — noté). |
| Zone + parts | ⚠ E-09 | `zone_parts` identiques partout ; mais `faisabilité.capacite.zone` nomme la zone **constructible** (Ud) tandis que fiche/Comparer nomment la **dominante** (N). |
| Hauteur max | ✅ | fiche « 16 m faîtage · 12 m égout », Gabarit = faîtage, faisabilité = égout — deux références, toutes deux justes. |
| CES / emprise | ✅ | fiche « 40 % » = Comparer 40 % = Gabarit (plafond m² dérivé). |
| Reculs | ✅ | fiche = seul lecteur chiffré (3 m), cohérent avec le Dossier. |
| SDP | ⚠ mineur | faisabilité/Comparer = SDP **max** ; Taxe `sdp_gabarit_m2` pré-remplit en réalité la SDP **résiduelle** (ex. BZ1065 : 212 vs 35 ; DS0186 : 27 001 vs 22 769) — notions différentes, étiquetage à clarifier. |
| Prix + fourchette | ✅ | fiche.prix_ancien.median = faisabilité.marche.median ; Comparer.prix_secteur_bati = métrique **distincte et étiquetée**. |
| Nb ventes + rayon | ✅ | fiche.prix_ancien.n/radius = faisabilité.marche.n/radius. |
| Taxe foncière + libellé | ✅ | fiche.fiscalite = `commune_rei` (vérifié main, angle E). |
| Taxe d'aménagement | ✅ | fiche.taxe_amenagement.taux = Taxe.taux_communal_pct. |
| Aléas + % PPR | ✅ | fiche.aleas = Pièges & risques (même fonction `aleas_parcelle`). Caractère rédhibitoire gradué par seuil de couverture (`servitudes.py`, `_risque_seuils`) — **principiel, pas un écart**. |
| Propriétaire | ⚠ E-03 | type cohérent, mais le **Courrier** ne nomme pas une PM connue (voir E-03). |

(La fonction `nb aléas` ≠ `nb servitudes` : fiche.aleas.n compte les aléas PPR/Géorisques, Pièges & risques `n` compte les servitudes — notions différentes, pas un écart.)

---

## Angle B — doublons

- **E-17** — Gabarit (`97401000AD0554`, `97411000AV0110`) : le bloc-source « BD TOPO® … / adjacence cadastre » est réimprimé à l'identique sous « Limites séparatives » **et** sous « Recul voie », avec le libellé « **BD TOPO BD TOPO®** » redoublé.
- Les autres répétitions (pieds de page, disclaimer légal, millésime PPR par ligne de risque) sont de la pagination/attribution légitime — **RAS**.
- Entre documents : l'Apporteur ne refait **aucune** valeur du Dossier avec un chiffre différent (surface, zone, bâti, propriétaire concordent) — la seule divergence Apporteur↔Dossier est de **format** (voir E-15 et milliers non espacés).

---

## Angle C — erreurs

- **E-02** (FAUX-CLIENT) — dict Python brut (§Sols CASIAS), `97416000DY0106`.
- **E-10** (erreur) — Étude de zone : « Emplois salariés » **sans nombre** alors que la donnée est servie (`emplois.postes_min 11 730 … postes_max 24 210`). 9/9 études de zone.
- **E-11** (erreur) — équipement affiché « (0 m) » = géocodage manquant imprimé en distance nulle (`97415000EV0324` « Santé : …GINGN (0 m) », `97415000BW0102`).
- **E-13** (erreur) — permis Sitadel en **dates ISO brutes** (« déposé 2024-01-01 ») + jour placeholder « 01-01 » (fausse précision ; Sitadel ne publie que l'année de dépôt).
- **E-16** (erreur) — Apporteur `97410000AN0347` : « 6 parcelles voisines … » mais la liste est **tronquée à 4 + « … »** dans un champ de données.
- **E-06** (incohérence) — Dossier §10 `97415000BO0852` : « saturée, SDP déjà consommée » + « Marge SDP non calculée » + « Marge de surélévation 0,6 m » (trois affirmations incompatibles).
- **E-07** (incohérence) — Gabarit `97411000AV0110` : « terrain exigu · Zone d'implantation 0 m² » **et** « Plafond d'emprise 114,7 m² · Hauteur 7,0 m » (gabarit chiffré sur un terrain déclaré non retenu).
- Format non français (**cosmétique**) : **E-12** Gabarit « Emprise maximale : 40.0 » (point décimal, sans « % »), **E-14** Étude de zone « chiffre d'affaires.. » (double point), **E-15** Apporteur « …97411000AV0110et le numéro » (espace manquant). Famille non bancée mais réelle : point décimal dans Dossier/Comparatif (« 1.9 m », « 1.5 places », « 4.5 m », « 0.91 ≥ 0.5 »), pourcentages collés (« 40% », « 8% »), milliers non espacés (« 1800 », « 1000 », « 1037 », « 1003/2338/1308 ») — incohérents avec les « 1 003 m² » correctement espacés ailleurs dans le même document.
- **« Nombre de logements » de l'ancien moteur** imprimé hors Étude de faisabilité : **RAS** (remplacé partout par « voir l'Étude de faisabilité »).
- Candidat non retenu : Comparatif `97415000BW0102` « Charge foncière -59 €/m² » (valeur négative imprimée) — possiblement voulu (chiffre brut d'un comparatif indicatif), à trancher par Vic.

---

## Angle D — mise à jour (Bilan + Étude), sur 2 parcelles

**Mécanique de fraîcheur comprise.** La bibliothèque « Mes documents » (`documents_bibliotheque.py:113 lister`) calcule l'état `a_jour` ssi **tous les millésimes de sources** figés à la génération valent encore ceux du jour. L'état « Sources modifiées depuis » reflète donc **les données publiques, pas les hypothèses du client**.

- **Bilan (`97415000BO0852`)** — `POST /bilan/{idu}/calcul`, prix de vente 4 000 → 4 800 €/m² : `ca_ht` 294 736 → 353 684 (= ×1,2, proportionnel). Le Bilan **recalcule en continu** depuis ses seules saisies ; le Dossier/Gabarit/fiche n'en dépendent pas (générés depuis les données servies + PLU) → **seul le Bilan change**. ✅
- **Étude (`97416000CZ0678`)** — objectif par défaut `equilibre` : scénario A barre R+6, T2 42 / T3 30 / T4 12, SHAB 4 008 m². Le ré-calcul avec `objectif=plus_logements` **n'a pas abouti sous 200 s** (même sur cette petite parcelle de 3 279 m²) → voir **E-04** (le moteur d'implantation est le goulet). L'indépendance inter-documents est néanmoins avérée par lecture du code (`EtudeIn` n'alimente que l'Étude).
- **« Sources modifiées depuis »** : changer une hypothèse de Bilan ou un scénario d'Étude **ne fait pas** basculer le badge (par construction — il suit les millésimes de sources). Ce n'est pas un bug, mais un **écart d'attente** : un client qui a changé ses hypothèses ne voit aucun signal distinguant l'ancien document du nouveau. À documenter côté produit (non compté dans les 17).

---

## Angle E — vérité à la main, sur 3 parcelles

Recalcul depuis la règle officielle citée, sans recours aux anciens audits :

- **TA (`97415000BO0852`, Saint-Paul)** — CGI art. 1635 quater, valeur forfaitaire 2026 hors-IdF = **892 €/m²**, abattement 50 % sur les 100 premiers m² d'une résidence principale. Projet 120 m², 1 logement RP : assiette = (100 × 892 × 0,5) + (20 × 892) = **62 440 €** ; part communale 5 % = 3 122 € ; part départementale 2,5 % = 1 561 € ; **total 4 683 €** = endpoint, exact.
- **Taxe foncière (3 communes)** — fiche vs source REI (`commune_rei`) : 97415 = 41,77 / 16,00 / 30,91 ; 97401 = 29,55 / 17,91 / 38,27 ; 97416 = 44,18 / 17,91 / 24,26 — **identiques**.
- **Hauteur / CES / reculs (`97415000BO0852`)** — fiche « 16 m faîtage · 12 m égout » (Art. 10.2 p. 24), « emprise non réglementée » (absent), « recul limites 3 m » (Art. 7.2 p. 21), « pleine terre 10 % » (Art. 13.1 p. 35) ; valeurs **citées avec article + page**, cohérentes entre fiche / Gabarit / faisabilité / Dossier (modulo faîtage vs égout). La confrontation au texte GPU parcelle-à-parcelle a déjà été menée par VERITE-TERRAIN-2 (99 %) et n'est pas rejouée ici.

---

## Tableau des écarts

| id | parcelle(s) | notion | lecteur A = valeur | lecteur B = valeur | gravité | cause présumée |
|---|---|---|---|---|---|---|
| **E-01** | BO0852, AN0347, EV0324 (3/10) | mixité sociale | §Urbanisme « seuil 1 800 / quota 30 % » | §Urbanisme « seuils de la zone non renseignés à ce jour » | incohérence | `declarations/fiche/reste_a_declarer.yaml:120` (phrase d'absence de `mixite_clause` nie des seuils présents) |
| **E-02** | DY0106 | §Sols (CASIAS) | fiche.sols.casias = dict | Dossier imprime `{'nom':…,'sur_place':False,…}` | **FAUX-CLIENT** | `src/labuse/exports/robinet_fiche.py:572-576` (`_c_sols` renvoie le dict brut, rendu via `str`) |
| **E-03** | AN0347, DY0106, EV0324, DS0186 (4/10) | propriétaire / destinataire | Dossier « COMMUNE DE … (PM, SIREN) » | Courrier « À l'occupant » | incohérence | `src/labuse/courrier_adressage.py:88-90` (PM sans siège enrichi → « À l'occupant », dénomination jetée) |
| **E-04** | EV0324 (41 009 m²) ; CZ0678 (objectif ≠ défaut) | Étude de faisabilité | `POST /modules/etude` | `HTTP 000` timeout > 60-200 s | **FAUX-CLIENT** | moteur `src/labuse/implantation/` — pas de borne de temps ni d'échec propre sur grande assiette |
| **E-05** | DY0106 (à cheval N/Ud) | constructibilité | Dossier « non constructible / saturée > 300 % » | Comparer/Étude « Ud R+4 350 m² » | incohérence | résiduel (zone dominante N) vs moteur d'implantation (portion Ud) non réconciliés (`app.py` §potentiel vs `implantation/`) |
| **E-06** | BO0852 | potentiel §10 | « saturée, SDP consommée » + « Marge SDP non calculée » | « surélévation 0,6 m » | incohérence | bloc §10 Dossier (trois phrases d'état non exclusives) `src/labuse/exports/blocs/` |
| **E-07** | AV0110 | gabarit vs capacité | « terrain exigu · Zone d'implantation 0 m² » | « Plafond d'emprise 114,7 m² · Hauteur 7,0 m » | incohérence | `src/labuse/gabarit/builder.py` (plafond/hauteur rendus même quand zone d'implantation nulle) |
| **E-08** | EV0324 (AU2c) | AU « ouverture sous conditions » | fiche.au_ouverture + Dossier §4 portent le caveat | Comparer `cause=None` / faisabilité `avertissements=[]` (18 454 m²) | incohérence | `src/labuse/faisabilite/` + `/compare` ne propagent pas `au_ouverture` |
| **E-09** | DY0106, EV0324 | libellé zone (à cheval) | fiche/Comparer = dominante (N / AU2c) | faisabilité.capacite.zone = constructible (Ud / U2c) | incohérence | `src/labuse/implantation/service.py` (zone retenue = constructible, non étiquetée « portion ») |
| **E-10** | 9/10 | Étude de zone — emplois | données `emplois.postes_min 11 730 … 24 210` | PDF « Emplois salariés [sans nombre] » | erreur | `src/labuse/exports/blocs/etude_zone.py:51-54` (`if libelle` court-circuite `elif postes_min` ; `zone.py:263` pose TOUJOURS `libelle`) |
| **E-11** | EV0324, BW0102 | distance équipement | géocodage manquant | « (0 m) » imprimé | erreur | rendeur équipements Dossier/§proximités (0 = absence, pas une distance) |
| **E-12** | AD0554 (+ gabarit calculables) | gabarit — emprise | règle « 40 % » | « Emprise maximale : 40.0 » (sans unité, point décimal) | cosmétique | `src/labuse/exports/blocs/gabarit.py` (valeur brute non formatée FR) |
| **E-13** | EV0324, CZ0678 | permis Sitadel | année de dépôt | « déposé 2024-01-01 » (ISO + jour fabriqué) | erreur | rendeur permis Dossier (date ISO + placeholder `-01-01`) |
| **E-14** | 9/10 | Étude de zone | — | « chiffre d'affaires.. » (double point) | cosmétique | `src/labuse/exports/blocs/etude_zone.py` (concaténation d'une phrase déjà ponctuée) |
| **E-15** | AV0110 | apporteur — référence | « …référence 97411000AV0110 » | « …97411000AV0110et le numéro » (collé) | cosmétique | `src/labuse/exports/blocs/apporteur.py` (espace manquant avant « et ») |
| **E-16** | AN0347 | apporteur — voisines | « 6 parcelles voisines » | « (AN 0350, AN 0346, AN 0267, AN 0463 …) » (4/6) | erreur | `src/labuse/exports/blocs/apporteur.py` (liste bornée + « … » dans un champ de données) |
| **E-17** | AD0554, AV0110 | gabarit — sources | — | « BD TOPO BD TOPO® » + bloc-source répété sous 2 règles | doublon | `src/labuse/exports/blocs/gabarit.py` (attribution dupliquée par règle) |

---

## Banc rejouable — `scripts/coherence/chasse_docs.py`

17 gardes, une par écart, contre l'API live (`CHASSE_DOCS_BASE`, défaut `http://127.0.0.1:8830`). **Avant correction : 17 ECART ; 0 ECART attendu après CHASSE-DOCS-FIX-1.** Les gardes qui rendent un PDF exigent `pdftotext` (sinon SKIP, jamais un faux OK). Chaque garde SKIP honnêtement si son témoin perd la condition (zone sans mixité, parcelle non PM…), pour rester robuste à un re-run de données.

```
LABUSE_DATABASE_URL=… uvicorn labuse.api.app:app --port 8830 --app-dir src   # API servie
python scripts/coherence/chasse_docs.py
```

---

## Proposition de mandat — CHASSE-DOCS-FIX-1

Fermer les 17 écarts par la cause (lecture seule → correction), 1 lot par famille, banc `chasse_docs.py` à 0 ECART en sortie :

- **Lot 1 — le client voit des chaînes propres (FAUX-CLIENT).**
  - E-02 : `_c_sols` (robinet_fiche.py) doit rendre une **phrase** (« Ancien site industriel CASIAS *Sucrerie Casernes*, en arrêt, à 44 m »), jamais un dict. Garde E-02.
  - E-04 : borner le moteur d'implantation (timeout dur côté service + message « étude trop lourde, non générée » au lieu d'un `HTTP 000 timeout`), ou pré-calculer en tâche de fond. Garde E-04.

- **Lot 2 — la mixité et la constructibilité ne se contredisent plus (incohérence).**
  - E-01 : la phrase d'absence de `mixite_clause` ne doit pas affirmer « seuils non renseignés » quand `mixite_seuil_m2`/`quota_pct` sont servis — la reformuler en « déclenchement non évalué (pas de programme saisi) » ou la masquer dès que la clause de zone est valide. `declarations/fiche/reste_a_declarer.yaml:120`. Garde E-01.
  - E-05 / E-09 : réconcilier le §potentiel (zone dominante) et le moteur d'implantation (portion constructible) sur une parcelle à cheval — un seul discours de constructibilité, le libellé « zone » nommant la **portion** (« Ud sur 46 % »). Gardes E-05, E-09.
  - E-06 : le §10 doit trancher UNE cause (« saturée » **xor** « marge non calculée ») et ne pas afficher une surélévation positive sous un verdict de saturation. Garde E-06.
  - E-07 : masquer le plafond d'emprise / la hauteur quand la zone d'implantation vaut 0 m² (terrain exigu). Garde E-07.
  - E-08 : propager `au_ouverture` (caveat « ouverture sous conditions ») dans Comparer et l'Étude, comme le fait le Dossier §4. Garde E-08.

- **Lot 3 — champs vides, zéros, dates (erreur).**
  - E-10 : `etude_zone.py` doit imprimer la fourchette « 11 730 à 24 210 » (inverser l'ordre des branches, ou faire de `libelle` un suffixe comme le fait le Flash). Garde E-10.
  - E-11 : « (0 m) » → « distance non géocodée » (ou masquer). Garde E-11.
  - E-13 : afficher l'**année** de dépôt Sitadel (« déposé en 2024 »), jamais une date ISO ni un jour fabriqué. Garde E-13.
  - E-16 : lister toutes les voisines annoncées (ou dire « 6 parcelles — voir Assemblage »), sans « … » coupant la donnée. Garde E-16.

- **Lot 4 — typographie FR (cosmétique).**
  - E-12 (« 40.0 » → « 40 % »), E-14 (double point), E-15 (espace avant « et »), + la famille (point décimal, `%` collé, milliers non espacés) via le helper FR unique `implantation/format.py` ↔ `lib/format.ts`. Gardes E-12, E-14, E-15.
  - E-17 : dédupliquer l'attribution source du Gabarit (« BD TOPO » une fois). Garde E-17.

- **Hors lots (produit, à trancher par Vic)** : badge « Sources modifiées depuis » insensible aux hypothèses (angle D) ; étiquetage Taxe `sdp_gabarit_m2` = SDP résiduelle ≠ SDP max de l'Étude ; charge foncière négative imprimée au Comparatif ; `surfaceParcelleM2` du Gabarit = portion de zone sur parcelle à cheval.

---

*Artefacts : `docs/audit-2026-10/chasse-docs/<idu>/` (fiche + 9 documents + outils + `pdftotext`). Scripts : `scripts/coherence/_chasse_docs_collecte.py` (collecte), `_chasse_docs_analyse.py` (notion × lecteur), `chasse_docs.py` (banc). Lecture seule — aucune donnée servie modifiée, aucun merge.*
