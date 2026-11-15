# COMPTE-RENDU — CHIRURGICAL-FIX-1

> Correction des écarts de l'audit AUDIT-CHIRURGICAL-3 (`docs/audit-2026-11/chirurgical-3/ECARTS-3.md`).
> Branche `fix/chirurgical-1` (depuis `origin/main` + audit mergé). **Pas de merge dans main.** Un commit par lot.
> Preuves : captures avant/après dans `~/Desktop/chasse-1/_fix/` et `~/Desktop/chasse-1/_ecrans/` (audit) ; phrases citées depuis les fichiers régénérés ; tests dédiés.
> Tests ajoutés : `tests/coherence_ecrans/test_chirurgical_fix_1.py` (réel, AM0838/AO0050), `tests/test_chirurgical_fix_1_unit.py` (unitaire).

## LOT A — Un seul verdict de non-constructibilité, partout (`564307560`)
Lu au point unique `potentiel_batir`. Une parcelle en zone urbaine mais non constructible pour une autre raison (habitat interdit en UE, PPR rouge) porte le même verdict/motif partout.

| Écart | Correction | Preuve |
|---|---|---|
| **E101** fiche affichait « aucune SDP résiduelle exploitable » (trompeur) au lieu de la cause | `AnalyseLabuseCard.tsx` : rend `cause_libelle` dès qu'une cause écarte (comme la liste), masque la contribution | Écran : fiche AM0838 affiche « **Non retenue — habitat interdit en zone UE.** » (`~/Desktop/chasse-1/_fix/FIX_E101_AM0838_apres_1440.png`). Test vitest `AnalyseLabuseCard.test.tsx` |
| **E104** Bilan modèle présentait AM0838 100 % constructible | `bilan/reperes.py` `sources_parcelle` consulte `potentiel_batir` → `non_constructible_pct=100` + `non_constructible_motif` ; front `BilanEcran.tsx` nomme le motif | API : `/bilan/97404000AM0838/modele` → `non_constructible_pct=100.0, motif="Habitat interdit dans cette zone", constructible_m2=0` |
| **E105** Estimer écrivait « zone non constructible (Pas) » sur une commune RNU | `pige/estimer3.py` `_zone_code` rejette les mots non-codes (« Pas de PLU local » → None) | API : `/radar/annonce/estimation3/97417000AO0050` → « Pas d'estimation : pas de potentiel constructible résiduel » (plus de « (Pas) »). Unit `_zone_code` |
| **E112a** Comparatif rendait la cause brute « habitat interdit:UE » | `ComparePanel.tsx` + `exports/blocs/comparatif.py` : cause « code:ZONE » écrite en clair « habitat interdit (zone UE) » | Unit `_cause_court('habitat_interdit:UE') == 'habitat interdit (zone UE)'` |
| **E117** Taxe prefill `deja_batie=false` sur une parcelle bâtie non constructible | `api/app.py` prefill lit aussi `p_model_bati.emprise_bati_m2` (peuplée hors `parcel_residuel`) | API : prefill AM0838 `deja_batie=true`, AO0050 (nu) `deja_batie=false` |

**Garde** : `test_chirurgical_fix_1.py` échoue si une surface (fiche/Bilan/Estimer/Comparatif) dit autre chose que la fiche sur AM0838 et AO0050 (3 passed, réel).

### Complément LOT A / LOT H point 10 (`a84d0d0fa`)
- **Fiche** : la tuile Zone affichait « PLU · constructible » (lu de la seule famille U) au-dessus de « habitat interdit » de l'Analyse. Désormais si `potentiel_a_batir.constructible===false`, la tuile d'une parcelle U/AU reste neutre (« PLU »). **Preuve écran** : AM0838 « UE · PLU » (plus « constructible ») vs AD0887 (constructible) « Ud · PLU · constructible » (`~/Desktop/chasse-1/_fix/FIX_zone_AM0838_apres_1440.png`).

## LOT B — Chiffres et messages faux (`8cb1a906d`)
| Écart | Correction | Preuve |
|---|---|---|
| **E103** TVA du Bilan non bornée → CA HT faux ×17 | `api/bilan.py` : `field_validator` borne la TVA à [0,1] (fraction). Le front envoie déjà `v/100`, donc aucun impact utilisateur | API : `tva:20` → **422**, `tva:0.20` → **200**. Unit `test_tva_bilan_bornee_et_validee` |
| **E106** Scan patrimoine : faux signal « succession/sommeil » sur une ASL | `api/modules.py` : le signal exige un SIREN d'entreprise (9 chiffres) | API : ASL `siren=U23889204` → `inpi_sans_dirigeant=false` |
| **E107** Gabarit disait « ne porte pas d'enveloppe constructible » sur AD0887 constructible | `gabarit/engine.py` (INCOMPLETE_MESSAGE), `Gabarit.tsx`, `exports/builder.py`, `api/documents.py` : « Gabarit non calculable » + raison + « ne préjuge pas de la constructibilité — capacité estimée dans la fiche » ; le vrai cas inconstructible garde son libellé | PDF AD0887 : « Gabarit non calculable sur cette parcelle (une limite n'est pas qualifiée)… Cela ne préjuge pas de la constructibilité… ». Écran (`~/Desktop/chasse-1/_fix/FIX_E107_gabarit_AD0887_apres_1440.png`) |
| **E1** surface : recherche/sélecteurs affichaient le dessin (1 699) vs fiche cadastre (1 703) | `api/recherche.py` : suggest sert `COALESCE(contenance, dessin)` | API : suggest `97422000AD0887` → sub « **1 703 m²** » |
| **E2** Apporteur : refus livré en 200 (PDF « Document non genere ») | `api/documents.py` : refus propre **422** + message accentué ; front affiche déjà le message | API : `/apporteur/97422000AD0887.pdf` → **422** |
| **Solaire** : « Toiture (emprise) » 425 vs emprise fiche 345 | `ProspectionSolaire.tsx` : grandeur nommée « Surface de toiture » (pans de toit, proxy BD TOPO/CoSIA), distincte de l'emprise au sol | Libellé + note « la surface de toiture… dépasse l'emprise au sol (débords, pente) » |
| **E108** bloc 198 vs 118 parcelles | **INFIRMÉ** — faux positif de lecture d'écran ; les deux surfaces servent **118** (parcel_blocs.n_parcelles, 278 ha). Aucun changement | DB : `parcel_blocs` id 33679 n_parcelles=118 ; patrimoine ET blocs endpoints = 118 |

## LOT C — Code mort retiré (`b41935e33`)
| Écart | Correction | Preuve |
|---|---|---|
| **E109** mail `email_change` : aucun déclencheur | Retiré : builder `_email_change`, template Brevo 18, échantillon, `ORDRE_CATALOGUE` | `test_compte2_brevo` registre mis à jour |
| **E119** mail `radar_digest` : legacy sans trigger | Retiré : builder, template 12, alias legacy « radar », échantillon | `test_alias_radar_legacy_retire` (alias→None) |
| **E110** vérif/aperçu des gabarits Brevo lisaient du HTML mort | `brevo.apercu_template`/`verifier_templates` branchés sur le **rendu local** (`mails_contenu`) ; tests non-local | `test_apercu_branche_sur_le_rendu_local`, `test_verification_branchee_sur_le_rendu_local` |
| **E114** export CSV projet : helper `projetCsvUrl` sans appelant | Front : `projetCsvUrl` supprimé ; back : `/projets/{id}/export.csv` répond **410** (comme l'export PDF) | — |
Tests : `test_mails_1_gabarit` + `test_compte2_brevo` = **193 passed**.

## LOT D — Cosmétique (`3f3609bfb`)
| Écart | Correction | Preuve |
|---|---|---|
| **E100** période RNIC code brut `DE_2001_A_2010` | `CoproprietesBlock.tsx` + `api/pdf_premium.py` (`_periode_lisible`) : « 2001–2010 », « avant 1949 », « à compter de 2011 » | Écran ES0054 : « · **2001–2010** · » (`~/Desktop/chasse-1/_fix/FIX_E100_ES0054_periode_apres_1440.png`) |
| **E112b** Comparatif : chips de contraintes en double | `ComparePanel.tsx` (`dedupContraintes` par libellé affiché) + `comparatif.py` (dédup exact) | — |
| **E113** CRM : note longue non tronquée | `crm/Kanban.tsx` : `line-clamp-4` + `title` (note entière au clic) | — |
| **E115** Radar : porte « Leboncoin » (site unique) alors que la pige = plusieurs portails | `RadarHub.tsx` « portails d'annonces » ; `RadarMarcheColonne.tsx` « (Leboncoin, Bien'ici) » | DB : portails leboncoin 428 + bienici 100 |
| **E116** signature : commentaires « fondateur » ≠ valeur « Gestionnaire relation entreprise » | `gabarit_mail.py`/`mails_contenu.py`/test : commentaires alignés (valeur inchangée) | — |
| **comptes de risques** | **Vérifié** : chacun nomme déjà son unité (fiche « N aléas distincts » + infobulle, Pièges « N contraintes relevées sur la parcelle », Comparatif « Contraintes relevées » dédoublonné). Métriques différentes, pas le même nombre. Aucun changement au-delà d'E112b | — |

## Pour la fusion (fichiers partagés avec `fix/chirurgical-docs`)
La session « docs » touche Apporteur, Estimer, Dossier. Mes changements les plus petits possibles sur ces zones, à fusionner :
- **`pige/estimer3.py`** (E105) : ajout du blocklist `_NON_CODES` + garde dans `_zone_code` (10 lignes, isolé). N'affecte pas les prix/comparables.
- **`api/documents.py`** (E2 Apporteur `_exiger_nom_du_compte` → 422 ; E107 `_gabarit_refus_pdf` sépare « inconstructible » de « incalculable »). Isolé du contenu Apporteur (date PLU).
- **`api/pdf_premium.py`** (E100 `_periode_lisible`) : helper ajouté + 1 ligne d'usage.

## LOT H — contre-audit documents (état : investigué, à exécuter en passe dédiée)
Le **point 10** (fiche « PLU constructible » vs « habitat interdit ») est **fait** (ci-dessus, `a84d0d0fa`).
Les **points 1–9** touchent la génération des documents (Bilan Excel/PDF, Apporteur, Pré-dossier, Comparatif, Dossier, Estimer). J'ai produit la **carte du code** complète (fichier:ligne + correctif par point) : `LOT-H-carte-code.md`.

**Pourquoi une passe dédiée** : la régénération des documents est sensible (pièges confirmés cette session) et le mandat exige une **preuve citée depuis le fichier régénéré** par point. Deux obstacles rencontrés :
1. **Processus API fantômes** : plusieurs uvicorn sur `:7460` survivaient aux relances (nohup détaché) et resservaient du code périmé → régénération trompeuse. (Remède : `kill -9` par `lsof -ti tcp:7460` AVANT relance, lancer via background harnais, et vérifier `etime`/PID.)
2. **Point 6 (marge de hauteur)** : la seule définition du libellé « Marge de surélévation (au faîtage) » est `registre/donnees.py` (vérifié par grep exhaustif). Je l'ai corrigé en « (sous la règle de hauteur) » et **vérifié en process** (`DONNEES['marge_surelevation_m'].libelle` = nouveau libellé), MAIS le Dossier régénéré affichait toujours l'ancien libellé — une **seconde source de rendu** du libellé reste à localiser (archive/miroir) avant de pouvoir prouver la correction. Changement **reverté** pour ne pas laisser un correctif non prouvé sur une donnée lue partout.

**À exécuter (par ordre de gravité, voir la carte)** : 1 Bilan Excel 100 % marge coûts vides (+ taxe sans assiette dans le PDF) ; 2 Apporteur mêmes alertes que la fiche + ICPE ; 3 Pré-dossier PCMI4 IS0448 PPR ; 4 Comparatif bâti 27 vs 13 % + proprio ; 5 copropriété voisine « à proximité » ; 6 marges hauteur nommées (source libellé à localiser) ; 7 Estimer « assiette constructible » AM0838 ; 8 perméable ≠ pleine terre ; 9 stationnement non réglementé. À LISTER seulement : Étude de zone (revenu/niveau de vie), ventes double Estimer BW2635. Fichiers partagés `fix/chirurgical-docs` (Apporteur/Estimer/Dossier) : changement minimal + listé.
