# MANDAT AUDIT-NU-3 — Lot P : tous les exports d'une même parcelle

**Registre.** Audit LECTURE SEULE joué le 2026-11-01. Branche `audit/nu-3-p`, worktree
`~/Desktop/labuse-nu3-p`, API **9440** (venv PDF-capable `~/Desktop/labuse-main/.venv` + `PYTHONPATH`
du worktree, donc le code servi est **bien celui de `audit/nu-3-p`**), front 6640 non requis (les
documents se génèrent par leurs routes HTTP + la fonction Flash directe). Run servi `q_v20`, base Mac
`labuse` (434 582 parcelles). **Aucune écriture base, aucun merge, aucun accès prod.** Les 150+ PDF/ZIP
produits, les scripts et les matrices sont dans `docs/audit-2026-11/nu-3/P/out/`.

> Note d'intendance. Le mot « financier » / « banquier » / « argumentaire » du mandat correspond à
> UN seul générateur (`/financier/{idu}.pdf`, vers lequel `/dossier-banquier` et `/argumentaire`
> redirigent en 308). Ce document est **verrouillé par un questionnaire interactif** (programme + régime
> TVA) : sans saisie, il répond 422 « Programme constructible / Régime de TVA manquants » — il n'est
> donc **pas générable depuis la seule référence cadastrale** et sort du jeu comparé. De même la « lettre
> de zonage » du mandat n'est pas un produit autonome : le seul courrier est `/courrier/pdf` (lettre AU
> PROPRIÉTAIRE, POST interactif). Le jeu réellement comparable depuis un IDU est détaillé plus bas.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Documents générés & lus** | **~130 PDF + 10 ZIP pré-dossier** : 10 parcelles × (Dossier, Export-fiche, Apporteur, Pré-dossier PC [ZIP multi-pièces], Gabarit, Étude de zone, Estimer, Comparatif, Étude de faisabilité, Flash) + extraction `pdftotext` de chaque pièce. |
| **Couples fait×document comparés** | **340** (docs décrivant LA parcelle, faits stricts) + confrontations à l'écran (fiche JSON) sur aléas, emprise, propriétaire. |
| **Familles d'écart inter-documents** | **5** (96 couples divergents, tous ramenés à 5 causes racines). |
| **Bloquant** | **0** |
| **Majeur** | **4** inter-documents (label SDP Flash ; compteur de risques à 3 valeurs ; emprise bâtie à 2 moteurs ; prix médian maison à 2 moteurs) **+ 1 régression de rejeu** hors périmètre documentaire (filtre « Risques/PPR » carte → 0 parcelle). |

**Verdict de synthèse.** *Les 15 « documents » nommés au mandat ne sont pas 15 générateurs : ils se
replient sur **10 générateurs réellement atteignables** (le Banquier = l'Argumentaire = le Financier,
tous trois verrouillés derrière un questionnaire ; l'« Export fiche » = le Dossier au texte près ; la
« lettre de zonage » n'existe pas). Sur ces 10, **les faits élémentaires d'une même parcelle concordent
remarquablement** — contenance, zone PLU, dernière vente (€ + date), hauteurs (une fois séparés faîtage /
égout / bâti mesuré), propriétaire, millésime des sources, référence cadastrale, adresse : **zéro écart**.
Le danger, comme dans NU-1, n'est pas l'arithmétique mais **l'assemblage et le libellé** : (1) le Flash
dit « SDP **résiduelle** » là où tous les autres disent « SDP **restante** » (régression du correctif
M-T01, 10/10 parcelles) ; (2) la tuile « RISQUES » montre **trois nombres différents** pour la même
parcelle selon le document (Dossier = `n_vigilances`, Estimer = `n_al`, fiche = `aleas.n`) ; (3) l'**emprise
bâtie** sort de deux moteurs (fiche BD TOPO vs Estimer moteur gabarit) ; (4) le **prix médian maison**
sort de deux moteurs (Dossier/Flash = `marche_dvf` vs Estimer = comparables de précision).*

---

## Les 10 parcelles témoins

Tirées variées, **hors des 12 témoins de NU-1 et des 24 de J** (exclusion vérifiée par script,
`out/exclude_all.txt`).

| rôle | IDU | commune | repère |
|---|---|---|---|
| nue zone U | 97416000HS0478 | Saint-Pierre | 885 m², Ug, sans bâti significatif |
| maison bâtie | 97409000AC0102 | Saint-André | 1 563 m², UC, vente DVF 12/2025 250 k€ |
| copropriété | 97401000AM0380 | Les Avirons | 4 940 m², Uc, RNIC 105 lots |
| PPR (part rouge) | 97421000AC0444 | Salazie | 1 470 m², PPR rouge 21 % + bleue 36 % |
| à cheval (risques) | 97415000CY0419 | Saint-Paul | 1 717 m², U2c, PPR rouge 28 %, 6 aléas |
| RNU | 97417000BD0225 | Saint-Philippe | 2 160 m², sans PLU opposable |
| grande > 1 ha | 97416000CS1048 | Saint-Pierre | 18 897 m², Acu |
| petite < 150 m² | 97401000AD0095 | Les Avirons | 110 m², Ud3 |
| vendue récemment | 97415000AZ1645 | Saint-Paul | 986 m², U4c, maison DVF 2025 455 k€ |
| propriétaire PM | 97411000CM0169 | Saint-Denis | 1 500 m², SARL AICHA PROMOTIONS (SIREN 477863963) |

---

## Ce que « 15 documents » veut dire en vrai — carte des générateurs

| Nommé au mandat | Route / voie réelle | Disponible depuis un IDU seul ? |
|---|---|---|
| Dossier expert (fiche) | `/parcels/{idu}/export.pdf` | **oui** — et son **texte est identique** au Dossier Docs |
| Dossier (Docs) | `/dossier/{idu}.pdf` | oui (10/10) |
| Bilan (Docs) / Banquier / Argumentaire | `/financier/{idu}.pdf` (← `/dossier-banquier`, `/argumentaire` en 308) | **non** — 422, questionnaire programme + TVA (0/10) |
| Apporteur | `/apporteur/{idu}.pdf` | oui (10/10) |
| Pré-dossier PC | `/pre-dossier/{idu}.zip` (CERFA + PCMI1/2/4/7-8 + règles-zonage + LISEZMOI) | oui (10/10) |
| Gabarit | `/gabarit/{idu}.pdf` | **4/10** (6 × 422 honnête « calcul incomplet ») |
| Comparatif | `/comparatif.pdf?idus=…` | oui (apparié ; 10/10) |
| Étude de zone | `/etude-zone.pdf?idu=&rayon_km=2` | oui (10/10) — **document de RAYON, pas de la parcelle** |
| Étude de faisabilité | `POST /modules/etude/pdf` | **7/10** (3 × 400 honnête « simulation impossible ») |
| Estimer un bien | `/analyse-annonce/{idu}.pdf` | oui (10/10) |
| Flash | `generate_flash_report(idu)` | oui (10/10) |
| Lettre de zonage | — (n'existe pas ; `/courrier/pdf` = lettre au propriétaire, POST) | n/a |

**Observation de périmètre (dette) :** les 422/400 ci-dessus sont tous **honnêtes** (message clair, jamais
un 500 ni un PDF vide). Le Gabarit refuse quand le règlement ne borne pas l'emprise ou que la capacité
n'est pas résolue ; l'Étude de faisabilité refuse quand aucune implantation collective ne passe les
contrôles durs (« zone d'implantation après reculs : 0 m² » sur la parcelle PM, 8 m² sur la petite). Ces
refus **concordent** avec ce que la fiche annonce, donc ne sont pas des écarts.

---

## Méthode

Pour chaque parcelle : génération de tous les documents atteignables par leurs **routes réelles** (mêmes
URL que les boutons de l'app), extraction par script (`out/extract2.py`, `pdftotext -layout` + regex à
**concepts séparés** — un extracteur par fait, valeur étiquetée unique, jamais « tout nombre en m² »).
Chaque fait est confronté entre les documents **décrivant la parcelle** (Dossier, Export-fiche, Apporteur,
Pré-dossier, Gabarit, Estimer, Flash). L'Étude de zone, le Comparatif et l'Étude de faisabilité sont lus
mais **sortis de la comparaison stricte** : la première décrit un rayon, le deuxième met 2 parcelles en
regard, la troisième sort un scénario collectif — leurs « médiane », « propriétaires » (entreprises de la
zone), « logements » ne sont pas le fait de la parcelle. Puis confrontation à l'**écran** (fiche JSON
`GET /parcels/{idu}?source=q_v20`) sur les faits sensibles. Matrices : `out/docs/<idu>.csv` (fait × doc),
écarts : `out/ecarts.csv`, faits bruts : `out/facts_long.csv`.

---

## Résultat — les faits qui CONCORDENT (socle sain)

Sur les 340 couples comparés, **concordance stricte (0 écart)** pour :

| fait | parcelles où ≥ 2 docs le portent | tous d'accord |
|---|---|---|
| contenance / surface terrain | 9 | **9** |
| zone PLU (code complet Ug/UC/Ud3…) | 9 | **9** |
| SDP restante — **valeur** (m²) | là où captée | **égales** (ex. maison 1 020 = 1 020) |
| hauteur faîtage (réglementaire) | 4 | **4** (12 m partout) |
| hauteur égout (réglementaire) | — | cohérente (9 m) |
| hauteur bâti mesurée | — | cohérente (4,6 m) |
| dernière vente — € + date | 3 (seules à en avoir) | **3** (ex. 250 000 € · 12/2025) |
| propriétaire | 9 | **9** (PM : Dossier = Apporteur = « AICHA PROMOTIONS ») |
| millésime des sources (« Données LABUSE au ») | 4 | **4** (21/10/2026) |
| référence cadastrale / filiation | 10 | **10** |
| adresse / code postal | 10 | **10** |

La zone est servie en **code complet** (Ug, UC, U2c, Acu…) dans tous les documents ; le Flash l'affiche
aussi en **famille** (« Zone PLU « U » (urbaine) ») — redondance, pas contradiction. La « date de
génération » est **02/11/2026** partout (jour **Réunion**, UTC+4, cohérent inter-documents, cf. `tz.today_reunion`).

---

## Résultat — les ÉCARTS inter-documents (5 familles, cause à l'appui)

### P-01 — MAJEUR — Le Flash dit « SDP **résiduelle** », tout le reste dit « SDP **restante** » (régression M-T01)

- **Constat** : 10/10 parcelles. Dossier, Export-fiche et Estimer impriment « SDP **restante** » ; le Flash
  imprime « Au sol (**SDP résiduelle** du run servi) » et « ~N m² de **sdp résiduelle** ».
- **La valeur, elle, concorde** (ex. maison 1 020 m² = 1 020 m²) : c'est **uniquement le mot** qui diverge.
- **Cause** : `src/labuse/flash/templates/rapport.html.j2:172-174` (libellé codé en dur « SDP résiduelle du
  run servi », champ `potentiel.au_sol.sdp_residuelle_m2`). Le correctif **M-T01** (FIX-NU3-1 : « SDP restante
  partout ») **n'a pas été appliqué au gabarit Flash**. → **OUVERT.**
- **Finesse** : le Flash ajoute un 3ᵉ nombre « plancher (SDP) ~1 120 m² = vendable ÷ rendement 80 % » : un
  autre « SDP » encore, dans le même document — à surveiller (confusion possible pour le client).
- **Portée** : M-T01 est **tenu** sur Dossier, Comparatif, fiche écran et Copilote (vérifié) ; le mot
  « résiduelle » survit au **Flash** (ci-dessus) et à des libellés **client** partageant le même champ
  `sdp_residuelle_m2` : `ModulePanel.tsx:359,1179`, `moteurs.tsx:817`, `Successions.tsx:45`.

### P-02 — MAJEUR — La tuile « RISQUES » montre TROIS nombres pour une même parcelle

- **Constat** (10/10) : pour une seule parcelle, le compteur de risques affiché dépend du document.

  | parcelle | Dossier / Export-fiche (= tuile écran) | Estimer | fiche JSON |
  |---|---|---|---|
  | maison 97409000AC0102 | **5 vigilances** (`n_vigilances`) | **2 aléas** (`n_hazards`) | `n_hazards`=2, `aleas.n`=3 |
  | à cheval 97415000CY0419 | **7 vigilances** | **2 aléas** | `n_hazards`=2, `aleas.n`=6 |
  | PPR 97421000AC0444 | **6 vigilances** | **2 aléas** | `n_hazards`=2, `aleas.n`=4 |
  | nue 97416000HS0478 | **3 vigilances** | **1 aléa** | — |

- **Cause** : trois compteurs servis sous trois intitulés —
  - Dossier/tuile écran : `n_vigilances` (toutes les lignes §5 « Risques et environnement », SOFT+HARD,
    bassin versant exclu) — `src/labuse/exports/miroir.py:1121` + `robinet_fiche.py:570` ;
  - Estimer : `n_hazards` = aléas distincts dédoublonnés DEAL/PPR — `src/labuse/exports/blocs/annonce.py:178` ;
  - fiche JSON : expose *en plus* `aleas.n` (lignes `aleas.liste`, PPR compté comme ligne).
- **Lecture** : **J#4 (FIX-NU3-1) EST fermé pour la paire fiche↔Estimer** — l'Estimer (`n_hazards`) ==
  l'aléa de la fiche (`n_hazards`), prouvé 4/4 (cf. annexe). MAIS le résumé « fiche == Estimer == PDF »
  **survend** : la tuile « RISQUES » du Dossier (et de l'écran) affiche `n_vigilances`, un AUTRE compteur
  sous un AUTRE mot. Le client lit **« 5 vigilances » au Dossier et « 2 aléas » à l'Estimer** sur la même
  parcelle. Chaque métrique est défendable, mais elles s'affichent au même emplacement sans se recouvrir.
  → **OUVERT (présentation inter-documents).**

### P-03 — MAJEUR — L'emprise bâtie sort de deux moteurs selon le document

- **Constat** (5/10 divergent) : Dossier/Export-fiche/Apporteur impriment l'emprise **BD TOPO** (fiche
  `le_bien.emprise_batie_m2`) ; l'Estimer imprime une **autre** emprise (bloc « SUR CETTE PARCELLE / Bâti
  existant, emprise »).

  | parcelle | Dossier/Apporteur (BD TOPO) | Estimer |
  |---|---|---|
  | maison 97409000AC0102 | 105 m² | **136 m²** |
  | copro 97401000AM0380 | 1 682 m² | **1 824 m²** |
  | vendue 97415000AZ1645 | 143 m² | **270 m²** |
  | à cheval 97415000CY0419 | 425 m² | **482 m²** |

- **Cause** : l'Estimer lit le **moteur Gabarit** (`_bati_existant`, `src/labuse/api/gabarit.py`) pour son
  bloc « bâti existant, emprise », tandis que Dossier/Apporteur lisent `le_bien.emprise_batie_m2` (fiche).
  Deux mesures d'emprise coexistent → deux chiffres. (Même famille que l'alerte « deux sources » de NU-1.)

### P-04 — MAJEUR — Le « prix médian maison » sort de deux moteurs selon le document

- **Constat** (5/5 des parcelles avec marché maison) : Dossier et Flash s'accordent ; l'Estimer diffère.

  | parcelle | Dossier / Flash (`marche_dvf`) | Estimer (comparables précision) |
  |---|---|---|
  | maison 97409000AC0102 | 2 144 €/m² | 2 148 €/m² |
  | vendue 97415000AZ1645 | 3 361 €/m² | **3 664 €/m²** (+9 %) |
  | PPR 97421000AC0444 | 1 848 €/m² | **1 736 €/m²** (−6 %) |
  | RNU 97417000BD0225 | 2 232 €/m² | 2 241 €/m² |

- **Cause** : le Dossier et le Flash servent le prix ancien médian de `marche_service.marche_dvf` (profil
  banquier, fenêtre/rayon propres) ; l'Estimer sert la médiane **maison** de son moteur de précision
  (ESTIMER-PRECISION-1 : 16 ventes rayon 500 m 2021-2025 vs 14 ventes 2022-2025). Même intitulé « prix médian
  maison », deux valeurs. Écart ténu sur certaines (2 144 vs 2 148) mais **jusqu'à +9 %** (vendue). Prolonge
  G-009 de NU-3-G (« 3 €/m² marché/bien selon l'écran »).

### P-05 — MINEUR — Libellé taxe : moteur « ≤ 5 m² », notice « < 5 m² »

- Le moteur d'exonération applique bien **≤ 5 m²** (borne inclusive, `taxe_amenagement.py:258-262`,
  correctif FIX-NU3-1 **FERMÉ**), mais deux chaînes de description disent encore « surfaces **< 5 m²** »
  (`regles/taxe_amenagement_eur.py:13`, `taxe_amenagement.py:181`). Logique juste, texte à aligner.

---

## Stabilité structurelle entre les 10 parcelles

- **Dossier** : 8 à 11 pages selon la richesse de la parcelle ; **les 12 sections sont présentes sur les
  10 parcelles** (Identité → Limites et sources). Pied de page, millésime et mention légale identiques.
- **Aucun champ vide imprimé**, aucun gabarit non substitué (`{{ }}`), aucune trace technique. Les seuls
  « None/null/nan » détectés par le scan sont des **sous-chaînes de mots français** (« capacité **null**e »,
  « non calculable ») : messages honnêtes, pas des fuites.
- **Aucune section ne disparaît sans raison** : quand un fait manque, le document l'écrit (« aucune mutation
  DVF », « non déterminé », « VÉRIFIÉ : RIEN »). Pré-dossier : mêmes pièces CERFA/PCMI à chaque fois ; la
  pièce et sa ligne LISEZMOI s'omettent **ensemble** quand une donnée bloque (cohérent).
- **Dates/millésimes cohérents** d'un document à l'autre (sources au 21/10/2026, génération au 02/11/2026).

---

## Rejeu des majeurs de NU-3 (FIX-NU3-1 à 4) sur leurs témoins

Rejeu lecture seule contre l'API live `:9440` (run q_v20), PDF `pdftotext`, code au `fichier:ligne`.

| majeur (fix) | témoin(s) | verdict | preuve |
|---|---|---|---|
| **J#1** titre Faisa ≠ « nu » sur sliver constructible | AM0380, CM0169 | **FERMÉ** | AM0380 « Uc sur 96 % » (parts Uc 96/N 4) ; CM0169 « AUh sur 0 %, à cheval » ; `modules.py:1897-1902` |
| **J#4** compteur aléas fiche==Estimer==PDF | AC0102, AC0444, CY0419, HS0478 | **FERMÉ pour la paire fiche↔Estimer** ; **OUVERT au Dossier** | Estimer « 2/2/2/1 aléas » == `aleas.n_hazards` fiche ; MAIS Dossier « 5/6/7/3 **vigilances** » = `n_vigilances` (`robinet_fiche.py:570`). Cf. P-02 |
| **J#5** « surface libre » − part PPR rouge | AO0010 (100 % rouge), AC0444, CY0419 | **FERMÉ** | AO0010 : « 696 563 m² (100 %) » → **1 125 m² (0 %)** ; `bati.py:302-306` (contenance − emprise − `interdit_m2`) |
| **M-T01** « SDP restante » partout | AC0102 + fiche/Comparatif/Copilote | **FERMÉ sur Dossier/Comparatif/fiche/Copilote** ; **OUVERT ailleurs** | « restante » dans `comparatif.py:140`, `annonce.py:176`, `miroir.py:1122`, `ComparePanel.tsx:96`. **Résidu « résiduelle » : Flash `rapport.html.j2:172` (P-01, 10/10) + client `ModulePanel.tsx:359,1179`, `moteurs.tsx:817`, `Successions.tsx:45`** |
| **M-T02** sous-titre Flash | template Flash | **FERMÉ** | `flash/templates/rapport.html.j2:26` = « Pré-analyse d'une parcelle » (plus « Étude de faisabilité ») |
| **G-007** Assemblage SDP bornée + % hors zone | AM0380+AM1395, CS1048+HS0478 | **FERMÉ** | AM0380+AM1395 : pct_hors_zone **35 %**, SDP 2 527 bornée ; CS1048+HS0478 : **97 % hors zone**, SDP 273 ; `assemblage.py:233-254` |
| **OUT-COMPARER-009** Comparer == Calculette | DX0049 | **FERMÉ** | Calculette (hypothèses calibrées servies) → par_m2 **75**, central **68 265** == `reference_comparer` ; `modules.py:2501` |
| **taxe** exo abri ≤ 5 m² | API barème | **FERMÉ** (commentaire périmé l.181) | 5,0 m² → « 5 m² ≤ 5 m² — exonérée » ; 5,01 → taxée ; `taxe_amenagement.py:256` ; notice `regles/taxe_amenagement_eur.py:13` dit encore « < 5 » |
| **ESTIMER-009** exposition une seule fois | AC0102, CY0419, HS0478 | **FERMÉ** | « exposition » 1× (en-tête) ; source unique `exposition_parcelle` `robinet_fiche.py:121-139` |
| **SECTEUR-005** « commune entière » = vraie médiane | Saint-Paul, Saint-André | **FERMÉ** | St-Paul appart 4 694 €/m² == `mediane_commune` (n=1 476) ; St-André 1 645 (n=191) ; `mon_secteur.py:95` |
| **FIX-NU3-2** `surface_hab` hors bornes → 422 | AC0102 | **FERMÉ** | `inf/1e9/-5/0` → **422** (plus de 500) ; `Query(None,gt=0,le=100000)` `pige/api.py:1807`, `documents.py:250` |
| **FIX-NU3-2** `exception_handler(Exception)` générique | code | **FERMÉ** | `@app.exception_handler(Exception)` `app.py:842` |
| **FIX-NU3-2 / G-001** filtre Risques·PPR carte | Saint-Paul + île (q_v20) | **OUVERT / RÉGRESSÉ** | `flags=risques` → **0 parcelle** (attendu ~405 764). L'expansion `CRITICAL_LAYERS['risques']=['ppr','georisque_alea']` (`app.py:58`) ne matche aucune couche de `parcel_flags`/du geojson (token réel = `risques`) → filtre serveur ET client (`filters.ts:72,111`) sélectionnent **rien** |

**Hors périmètre documentaire du lot P (non rejoués)** : tout FIX-NU3-3 (surveillance jobs, sauvegardes,
vigies fraîcheur/escalade, 2FA pilote, charge `perf_limits`), FIX-NU3-4 (extension Chrome Radar), et côté
FIX-NU3-2 les comptes/paiement (402/grâce) et l'a11y/contrastes/aria-live.

**La régression à retenir** : le **filtre « Risques/PPR » de la carte** (G-001) montre désormais **zéro
parcelle** là où il devrait en montrer ~405 k — silencieusement, serveur comme client. Le correctif a mappé
`risques → ['ppr','georisque_alea']`, deux `kind` absents des données servies (le token réel est `risques`).
Plus grave que l'état d'avant-fix (où `risques` passait littéralement). À remapper `risques → ['risques']`
avec un test de non-vacuité.

---

## Verdict

**Les 15 documents d'une parcelle disent-ils la même chose ?** — *Sur les faits élémentaires (contenance,
zone, dernière vente, hauteurs, propriétaire, millésime, référence, adresse) : oui, au mot et au m² près ;
mais quatre familles d'assemblage dissonent — le Flash parle de « SDP résiduelle » quand les autres disent
« restante », la tuile « RISQUES » affiche trois nombres différents pour la même parcelle, et l'emprise
bâtie comme le prix médian maison sortent de deux moteurs selon qu'on lit le Dossier ou l'Estimer.*

---

## Annexes

- `out/parcelles.csv` — les 10 témoins et leur rôle.
- `out/docs/<idu>.csv` — **10 matrices fait × document** (une par parcelle).
- `out/ecarts.csv` — les 96 couples divergents (fait, doc_a/val_a, doc_b/val_b).
- `out/facts_long.csv` — tous les faits extraits (doc × fait × valeur).
- `out/generation_log.csv` — disponibilité/HTTP de chaque document.
- `out/pdf/` — tous les PDF générés (non versionnés : politique MENAGE-1 binaires hors git).
- Scripts : `/tmp/nu3p/generate.py`, `gen_flash.py`, `gen_etude.py`, `extract2.py` (copiés en annexe si besoin).
