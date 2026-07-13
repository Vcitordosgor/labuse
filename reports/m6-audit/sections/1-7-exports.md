# M6 · Phase 1 · §1.7 — Audit de TOUS les exports

Audit LECTURE SEULE du 13/07/2026, instance auditée `http://127.0.0.1:8010` (branche `audit/grand-check`, run servi `q_v3_datagap`, run v2 `m36-l2f-2026-2026-07-12`). Fichiers testés conservés sous `reports/m6-audit/exports-samples/`.

## Inventaire des exports trouvés (code + front)

| # | Export | Endpoint | Branché dans l'UI ? |
|---|--------|----------|---------------------|
| 1 | CSV liste résultats | `GET /parcels/export.csv` | oui — bouton « ⬇ CSV » (ResultsSection.tsx:415, `limit=5000`) |
| 2 | PDF fiche parcelle (premium) | `GET /parcels/{idu}/export.pdf` | oui — `pdfUrl()` (fiche) |
| 3 | PDF Dossier parcelle (« Flash ») | `GET /dossier/{idu}.pdf` (générateur `labuse.flash`) | oui — Fiche.tsx:976 |
| 4 | PDF projet (shortlist) | `GET /projets/{pid}/export.pdf` | oui — `projetPdfUrl()` |
| 5 | PDF baromètre | `GET /moteurs/barometre.pdf` | oui — moteurs.tsx:194 |
| 6 | CSV Vues/segments « à l'occupant » | `POST /segments/export` | oui — SegmentsPage |
| 7 | ZIP publipostage (CSV + étiquettes PDF + gabarit) | `POST /segments/publipostage` | oui — SegmentsPage:345 |
| 8 | ZIP pré-dossier PC (CERFA + plan + règles) | `GET /pre-dossier/{idu}.zip` | non repéré dans le front |
| 9 | Fiche md / html / one-pager | `GET /parcels/{idu}/export?format=md\|html\|onepager` | non (API seulement, lots antérieurs) |
| 10 | Courrier SPF (texte) | `GET /parcels/{idu}/spf-letter` | non repéré dans le front |

Parcelles témoins (vérité SQL + écran) : `97423000AB1908` (brûlante v2 rang 1, Les Trois-Bassins), `97421000AV0615` (tier v2 brûlante MAIS étage 0 → écartée effective, Salazie), `97408000AP1647` (chaude rang 2), `97413000CH0577` (réserve foncière), `97409000AO0625` (copro, à creuser).

---

## ⚠ Constat transverse P0 — tous les PDF sont en 500 sur l'instance auditée

Tout endpoint PDF/ZIP répond **HTTP 500** sur `:8010` : `/parcels/{idu}/export.pdf`, `/moteurs/barometre.pdf`, `/projets/13/export.pdf`, `/dossier/{idu}.pdf`, `/pre-dossier/{idu}.zip`, `/segments/publipostage`.

- **Cause** (reproduite hors serveur) : l'instance 8010 tourne dans l'env conda `labusedb` où **`fpdf2` est absent** et **WeasyPrint ne charge pas `libgobject-2.0`** — alors que `pyproject.toml` déclare bien `fpdf2>=2.8`, `weasyprint>=61`, `pypdf>=5`. L'env `.venv` (instance :8000, non touchée) a toutes les dépendances.
- **Qualification** : anomalie d'**environnement/packaging de l'instance d'audit** (env conda incomplet), pas un bug du code produit. Mais côté client c'est un bouton qui rend une page blanche « Internal Server Error » → P0 opérationnel tant que l'env de service n'est pas complet.
- Tous les contenus PDF ci-dessous ont donc été générés **hors serveur, avec le même code et la même base (lecture seule, `.venv` + rollback)** pour auditer le contenu.

---

## Tableau exports × critères

| Export | Génération | Encodage (accents) | BOM Excel | Volumétrie | Cohérence app ↔ export (v2) | Adresse postale | IDU |
|---|---|---|---|---|---|---|---|
| 1. CSV liste | ✅ 200 | ✅ UTF-8 (é/è/É OK) | ❌ **absent** | ⚠ **plafond 5 000 silencieux** | ✅ tier/rang/×N/scores identiques (5/5 témoins) | ❌ **absente** | ✅ |
| 2. PDF fiche premium | ⚠ 500 sur :8010 (env) / ✅ hors serveur | ✅ | n/a | complète (2 p.) | ✅ « Brûlante v2 · rang 1 · ×64.0 » = écran ; étage 0 → « Écartée » = écran | ❌ coordonnées GPS seulement | ✅ |
| 3. PDF Dossier parcelle (Flash) | ⚠ 500 sur :8010 (env) / ✅ hors serveur (5 p.) | ✅ | n/a | complète | ❌ **Q/A matrice seuls, aucun verdict v2** (voir audit dédié) | ❌ (param `adresse` jamais passé) | ✅ |
| 4. PDF projet | ⚠ 500 sur :8010 (env) / ✅ hors serveur | ✅ | n/a | top 5 + compteur (« 87 correspondent ») | ❌ **« À creuser · qualité 75/100 » = matrice, pas de tier v2** | ❌ | ⚠ réf. courte « AB 0849 » (IDU complet absent) |
| 5. PDF baromètre | ⚠ 500 sur :8010 (env) / ✅ hors serveur | ✅ (Médiane, L'Étang-Salé) | n/a | agrégats OK | ✅ (agrégats DVF/Sitadel, hors scoring) | n/a | n/a |
| 6. CSV Vues « occupants » | ✅ 200 | ✅ | ✅ `utf-8-sig` + `;` (Excel FR) | ✅ **2 381/2 381** (= compteur écran, `X-Rows`) | ✅ (données preset, hors scoring) | ✅ BAN complète (n°, voie, CP, ville) | ✅ |
| 7. ZIP publipostage | ❌ 500 sur :8010 (env) / ✅ hors serveur | ✅ | ✅ (CSV interne) | 2 227 lignes (adresse BAN exigée — voulu, documenté) | ✅ | ✅ | ✅ |
| 8. ZIP pré-dossier PC | ⚠ 500 sur :8010 (env) / ✅ hors serveur | ✅ (Impasse des Pétrels) | n/a | 4 fichiers, CERFA 11 champs remplis | n/a (réglementaire) | ✅ BAN dans le CERFA (cadre 3.1) | ✅ |
| 9. md / html / one-pager | ✅ 200 | ✅ | n/a | complète | ❌ **verdict LEGACY** (« a_creuser · Opportunité 61/100 » pour la brûlante rang 1) | ❌ | ✅ |
| 10. Courrier SPF | ✅ 200 | ✅ | n/a | n/a | n/a | ⚠ champ [Adresse] à remplir (voulu) | ✅ + section/n° |

### Preuves volumétrie CSV liste (vs compte SQL)

| Requête | Écran/SQL | CSV | Verdict |
|---|---|---|---|
| brûlantes île | 117 (écran « 117 brûlantes v2 » = SQL) | 117 | ✅ complet |
| Les Trois-Bassins | 730 (SQL) | 730 | ✅ complet |
| La Possession | 3 194 (SQL) | 3 194 | ✅ complet |
| Saint-Leu | 6 080 (SQL) | **5 000** | ❌ tronqué sans avertissement |
| « Tout » île | 79 043 (affiché à l'écran) | **5 000** | ❌ tronqué sans avertissement |

Le plafond est `limit ≤ 5000` (app.py:589) ; le front appelle en dur `limit: 5000` (api.ts:105) ; ni le fichier, ni le bouton, ni un en-tête ne signalent la troncature (l'export segments, lui, renvoie `X-Rows`).

### Cohérence champ par champ (5 témoins, app = écran vérifié Playwright + JSON fiche)

| Parcelle | App (écran) | CSV liste | PDF fiche premium |
|---|---|---|---|
| 97423000AB1908 | Brûlante v2 · rang 1 · ×64.0 · Q44/A64 · compl. 92 | `brulante,1,64.0,…,44,64,92` | « Brûlante v2 · rang 1 · ×64.0 », Q44/A64/92 |
| 97421000AV0615 (étage 0) | « LABUSE l'a écartée » + P v2 brûlante ×7.1 | `ecartee,389,7.1,…,50,50,74` | « Écartée », Q50/A50/74 |
| 97408000AP1647 | chaude rang 2 ×64.0 | `chaude,2,64.0,…,60,66,92` | — |
| 97413000CH0577 | réserve rang 229505 ×0.91 | `reserve_fonciere,229505,0.9` | — |
| 97409000AO0625 | copro, à creuser ×0.92 | `a_creuser,,0.9,oui` (copro ✓, propriétaire SHLMR ✓) | — |

CSV liste, fiche JSON, PDF fiche premium et écran racontent **la même vérité v2** — y compris la brûlante « écartée matrice » (statut matrice affiché en historique barré dans le PDF). Seule nuance : ×63.97 arrondi « ×64.0 » partout (cohérent).

---

## Audit dédié — PDF « Flash » / Dossier parcelle (`/dossier/{idu}.pdf`)

Générateur `labuse.flash.report.render_report_html` (module Flash Lot 1, présent sur la branche), template `rapport.html.j2` v1.0. Échantillon : `dossier_flash_97423000AB1908.pdf` (5 pages) + capture `dossier_flash_97423000AB1908_p1.png`.

- **Écriture en base** : l'endpoint incrémente `usage_compteurs (kind='dossier')` après génération → conformément au mandat, le PDF a été généré **hors endpoint** (fonction pure, lecture seule). Mon appel HTTP témoin a rendu 500 **avant** l'INSERT (aucun compteur consommé, vérifié en SQL). `/dossier/statut` : `disponible: true, plan integral, illimité`.
- **Données exactes** : ✅ vérifiées vs SQL — contenance 313 m², réf. 97423 AB 1908, zone 1AUb/AUc (97423_PLU_20220602), SDP résiduelle 183 m² (= fiche app), Q 44 / A 64, « complétude du signal A 67 % » (= `a_completude` SQL 67 — attention : la fiche app affiche AUSSI « complétude 92 » qui est `completeness_score` ; deux métriques différentes correctement libellées, mais un client qui compare les deux documents voit 67 % vs 92 sans explication), risques PPR B3 + aléa mouvement de terrain faible/modéré (= cascade app), DVF 16 ventes/6 301 €/m², Sitadel 18 autorisations, pente 3,6°.
- **Score v2 (pas matrice) ?** ❌ **ANOMALIE MAJEURE** : le rapport ne montre QUE Q/A matrice en valeur absolue avec une grille « Q < 50 = qualité foncière faible ». Pour la **brûlante v2 n° 1 de l'île** (Q=44), le client lit donc « qualité foncière faible » alors que l'app affiche « Brûlante v2 · rang 1 ». Aucune mention du tier v2/×N. Le générateur (feat/module-flash, antérieur à M5.1) n'a pas suivi l'unification v2 → **deux vérités**.
- **Mentions légales** : ✅ présentes et correctes — bloc « Mentions » p. 4 (« Document d'information… ne constitue ni un document d'urbanisme opposable, ni une étude de faisabilité réglementaire, ni un conseil juridique ») + pied de page répété sur **chaque** page + n° de rapport, date, version modèle, attribution OSM. L'endpoint ajoute en plus « Généré via LABUSE pour {raison sociale} » sur chaque page (vérifié dans le code, dossier.py:100-104 — non testable en HTTP à cause du 500 env).
- **Disclaimer « ne remplace pas un certificat d'urbanisme »** : ❌ **absent au mot près** — la formule n'existe nulle part dans le code (`grep certificat` : 0 hit produit). La couverture sémantique (« ne vaut ni document d'urbanisme opposable, ni étude de faisabilité ») est proche mais le CU n'est pas nommé. À trancher en Phase 2a (ajout d'une ligne au template).
- **Rendu visuel** : ✅ propre (capture p.1 : marque, carte OSM avec contour parcelle, cartouche) ; accents parfaits ; 154 Ko.
- **Adresse postale** : ❌ absente — `collect_report_data(adresse=None)` : l'endpoint dossier ne passe jamais l'adresse BAN alors qu'elle existe en base (le pré-dossier CERFA la remplit : « 27 Impasse des Pétrels, 97426 »). La source « Base Adresse Nationale » est même listée p. 4 sans qu'aucune adresse ne figure au rapport.

---

## Anomalies consignées

**P0**
1. **Tous les exports PDF/ZIP → HTTP 500 sur l'instance auditée** (env conda `labusedb` sans `fpdf2` ni libs WeasyPrint, deps pourtant déclarées au pyproject). Côté produit : prévoir un message d'erreur honnête plutôt qu'un « Internal Server Error » nu. (Vérifier l'env de l'instance servie au client avant toute démo.)
2. **Dossier parcelle / Flash PDF : vérité différente de l'app** — Q/A matrice + grille « Q<50 faible » sans le verdict v2 ; la brûlante rang 1 y paraît médiocre. Le client reçoit deux vérités (mandat : « le client ne reçoit jamais deux vérités »).

**P1**
3. **CSV liste : troncature silencieuse à 5 000 lignes** (écran annonce 79 043 / Saint-Leu 6 080 → fichier 5 000, aucun signal). Correctif simple : ligne d'avertissement dans le fichier, `X-Rows`/total, ou pagination.
4. **CSV liste : aucune adresse postale** (les adresses BAN existent en base et sortent dans l'export segments). IDU seul.
5. **PDF projet : verdict matrice (« À creuser · qualité 75/100 »), pas de tier v2** ; réf. parcelle en « section n° » sans IDU complet ni adresse.
6. **Exports fiche `md/html/onepager` (API) : verdict LEGACY** (`_build_fiche` : « a_creuser · Opportunité 61/100 » pour la brûlante v2 rang 1) — non branchés dans l'UI mais accessibles ; à aligner ou à retirer.
7. **CSV liste sans BOM UTF-8** → accents cassés à l'ouverture double-clic dans Excel (l'export segments fait `utf-8-sig` + `;` — la recette existe, à copier).
8. **Adresse postale absente des PDF fiche premium et Dossier/Flash** (coordonnées GPS ou rien) — correction Phase 2a annoncée par le mandat.

**P2**
9. Paramètre legacy `statuts=` du CSV accepte des valeurs qui ne matchent jamais (`exclue` ∉ `matrice_statut`) → fichier vide silencieux.
10. `/segments/export` n'appelle pas `_garde_export_suspendu` (seul `/publipostage` le fait) — sans effet aujourd'hui (`exports_suspendus: []`) mais garde asymétrique si une suspension revient.
11. Preset `pv-residentiel` : pas de mention de fiabilité en pied d'export (la facture « ESTIMÉE » voyage sans sa mention, contrairement aux presets piscine/ANC/élagage).
12. Disclaimer « ne remplace pas un certificat d'urbanisme » absent au mot près de tous les documents (couverture sémantique partielle présente partout).
13. `filigrane_export` écrit la trace `export_fingerprints` **avant** la génération des étiquettes : un publipostage qui plante (cf. P0 env) enregistre quand même une empreinte sans fichier livré.

## Écritures en base pendant l'audit (transparence)

Conformément à l'exception « logs d'accès inoffensifs » : mes 2 appels `/segments/export` + 1 `/segments/publipostage` (échoué) ont ajouté 2-3 lignes de traçabilité par design produit (`export_fingerprints` 30 → 32, compteur `usage_compteurs kind='export'`) + les lignes `consultation_log` du middleware sur chaque GET. Aucun crédit/quota Dossier consommé (vérifié), aucune donnée produit modifiée. Les PDF ont été générés hors serveur en session lecture seule (rollback).

## Fichiers testés (exports-samples/)

CSV : `csv_brulantes.csv` (117), `csv_defaut.csv` (5 000/79 043), `csv_saintleu.csv` (tronqué), `csv_troisbassins.csv`, `csv_possession.csv`, `csv_saintandre.csv`, `csv_ecartees_salazie.csv`, `csv_copro_probe.csv`, `csv_exclues.csv` (vide), `segment_pv-residentiel_occupants.csv` (+ `seg_export.headers`).
PDF (+ texte extrait + rendu p.1) : `fiche_premium_97423000AB1908.pdf/.txt/_p1.png`, `fiche_premium_97421000AV0615.pdf/.txt`, `dossier_flash_97423000AB1908.pdf/.html/.txt/_p1.png`, `barometre.pdf/.txt/_p1.png`, `projet_13.pdf/.txt/_p1.png`.
ZIP : `pre_dossier_97423000AB1908.zip` (+ `pre_dossier_extract/`), `publipostage_pv-residentiel.zip`.
Autres : `fiche_97423000AB1908.md/.html`, `onepager_97423000AB1908.html`, `spf_letter_97423000AB1908.txt`.
UI : `ui_liste_brulantes.png`, `ui_fiche_brulante_AB1908.png`, `ui_fiche_ecartee_AV0615.png` (script `frontend/qa/audit_m6_exports.mjs`).
