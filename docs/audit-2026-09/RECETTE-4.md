# RECETTE-4 — rapport

**Branche** : `feat/recette-4` (depuis `feat/recette-3`). **Worktree** : `~/Desktop/labuse-recette4`.
**Run servi** : `q_v11_m137` — **inchangé**. Aucun rescoring, aucun rebuild de cascade, aucune bascule, aucun merge.
**Règle de preuve** : chaque « fait » a été constaté dans un vrai navigateur (Playwright) contre le backend
réel (uvicorn `:8022` + front vite `:5177`). Preuves : `RECETTE-4-preuves/`.

## Étape 0
`pwd` = worktree · branche `feat/recette-4` · arbre propre · `.env` présent (DB `labuse` locale,
`postgresql+psycopg://openclaw@localhost:5432/labuse`). Mandat archivé : `MANDAT-RECETTE-4.md`.

---

## Tableau des 9 points

| # | État | Constaté au navigateur | Preuve `fichier:ligne` / capture |
|---|------|------------------------|----------------------------------|
| **U1** | ✅ Fait | Fiche commune **Saint-Paul** : ligne « Taxe foncière (taux) » = **41,8 %** (REI 2025), détail TFPB commune/EPCI 0 %/TEOM 16 %, source DGFiP. Servie **live** (le cache nocturne la donnait `null`). Financier : nouvelle section « Fiscalité locale et régime applicable » (taux sourcés + taxe de portage **dite**, valeur locative exigée, jamais devinée). | `fiche_commune.py:229` (`fiscalite`+`perime`), `app.py:2088` (rafraîchi live), `exports/blocs/financier.py` (`_fiscalite_locale`), `builder.py:162` · `recette4-u1-fiche-commune-tfpb.png`, `recette4-u4-financier-pdf.png` |
| **U2** | ✅ Fait | Fiche **parcelle** `97415000DK1044` (Saint-Paul) : « Zonage d'investissement locatif : **A** » (était « B1 » en dur pour toute l'île — **faux** pour les 4 communes zone A). Saint-Denis reste **B1**. Fiche commune : « Zonage logement (ABC) — zone A ». Financier : zone + régime portés. | `app.py:4240` (`_territoire_fiscal_block`), `app.py:2093` (live) · `recette4-u2-fiche-parcelle-zoneA.png` |
| **U3** | ✅ Fait | TFPB et zonage A/B/C restent **hors scoring** : informations servies, aucune variable de modèle touchée. Aucun run/rescoring/rebuild/bascule. | — |
| **U4** | ✅ Fait | Le Financier sort **de bout en bout** : questionnaire 4 écrans → « Ouvrir le document Financier » → **PDF 200, 3 pages** (verdict, hypothèses, bilan à rebours, sensibilité, fiscalité). **Les 20 questions apparaissent toutes** au bilan (test différentiel : basculer chaque champ change le document). **Aucune question morte** à retirer. | `financier_questionnaire.py` (20 champs), `builder.py:144` (mapping), `blocs/financier.py` · `recette4-u4-financier-pdf.png` |
| **U5** | ✅ Fait | Courrier propriétaire sur **3 parcelles** : `97415000DK1044` (**PM** LOTISSEMENT DU GOLF, **adresse nulle**), `97422000AD1237` (PP, Le Tampon), `97411000KA0296` (Saint-Denis). **Aucun champ vide** ne s'imprime ; le corps n'imprime **ni nom ni adresse** de propriétaire (adressage générique). PDF DK1044 rendu et relu. | `ModulePanel.tsx` (`remplirGabaritCourrier`), `api/courrier.py:302` · `recette4-u5-courrier-dk1044-1.png` · `CourrierRecette4.test.tsx` (3) |
| **U6** | ✅ Fait (liste ci-dessous) | Les points « à recetter à l'œil » de RECETTE-2/3 = **S11** (carte) et **S7/T1** (apporteur). État réel constaté. | § U6 · `recette4-u6-apporteur-p1-1.png`, `recette4-u6-s11-carte-paliers.png` |
| **U7** | ✅ Fait | Maquette apporteur validée (v3) archivée à côté du rapport. | `RECETTE-4-preuves/maquette-apporteur-v3.html` |
| **U8** | ⏳ Lot 3 | Note cascade DPU/PEB/DPF/zones humides — écrite au Lot 3 (rien exécuté). | § U8 |
| **U9** | ⏳ Lot 3 | Ne rien exécuter — respecté. | — |

---

## U1 — la taxe foncière (TFPB) enfin servie

La source REI (`commune_rei`, 24/24, taux 29,55→68,40 %) était **ingérée mais invisible du client**. Le
code de service (`fiche_commune.fiscalite`) existait pourtant depuis SOURCES-1 lot 5 — mais la fiche commune
est servie depuis un **cache nocturne** (`commune_contexte_cache`, job `fiche-commune-cache`) qui **précède**
SOURCES-1 : il portait `fiscalite: null`. C'est la vraie raison du « nulle part » de RECETTE-3.

**Correctif (sans rebuild)** : la TFPB et le zonage A/B/C sont des **passe-plats bon marché** (une ligne). On
les resservit **live** dans `_rafraichir_partages` (`app.py:2088`), exactement comme comparable/SRU (doctrine
O8 : « un seul moteur, deux écrans d'accord, jamais figé »). Résultat : toujours servis, jamais périmés,
aucun job à relancer.

**Fraîcheur** : `fiscalite()` porte désormais `perime` (ingestion > 1 an) + `maj_at`. La ligne fiche commune
affiche « … · à rafraîchir » quand la donnée vieillit — comme la taxe d'aménagement. Aujourd'hui `perime =
false` (REI ingéré il y a 2 j), donc **pas d'alerte** (comportement correct) ; la logique est gardée par test.

**Financier** : section « Fiscalité locale et régime applicable » — taux TFPB commune/EPCI/TEOM sourcés +
datés (REI). La **taxe foncière de portage** est **dite** : « elle se calcule sur la valeur locative cadastrale
× le taux communal × la durée ; reportez la valeur locative de l'avis — LABUSE n'en invente aucune ». C'est
« dite et sourcée, jamais devinée en silence » sans corrompre le bilan numérique par une valeur locative
inventée.

## U2 — le zonage A/B/C descend en fiche parcelle (et corrige un faux)

Le bloc parcelle `dispositifs_dom` affirmait « La Réunion est classée en **zone B1** … s'applique à toute
l'île ». **Faux** : l'arrêté DHUP classe **4 communes en zone A** (Saint-Paul, Saint-Leu, Les Avirons,
L'Étang-Salé) et 20 en B1 (mesuré en base : `commune_zonage_abc`). La fiche parcelle sert désormais la zone
**réelle** de sa commune (sourcée + datée), `null` si non ingérée (jamais devinée). Vérifié : Saint-Paul → A,
Saint-Denis → B1. Zone + régime (PTZ, plafonds, prix bailleur, TVA accession) aussi portés au Financier.

## U4 — Financier de bout en bout + les 20 questions

**Bout en bout** : questionnaire 4 écrans (pré-remplis sourcés) → « Enregistrer » → « Ouvrir le document
Financier » → PDF 200 (3 pages). Constaté au navigateur.

**Les 20 questions apparaissent-elles toutes au bilan ?** Vérifié par **test différentiel** : pour chacun des
20 champs, deux jeux de réponses complets ne différant que par ce champ produisent **deux documents
différents** → la réponse de chaque champ change le bilan. **Aucune question morte.** (RECETTE-2 S3 avait déjà
retiré les 4 champs muets : type de stationnement, prix déjà refusé, commission d'apporteur, apport.) Nuance
honnête : `typologie_moyenne_saisi` n'agit que via le **repli surface** (quand le potentiel ne chiffre pas de
surface vendable — cas d'un terrain nu) ; elle reste donc une entrée légitime.

**Finding latent (hors périmètre, signalé)** : `financier_questionnaire.enregistrer` avec `compte_id = NULL`
n'active jamais `ON CONFLICT (compte_id, idu)` (en SQL, `NULL ≠ NULL`) → il **empile des doublons** et
`charger` lit le plus ancien. **Sans effet en production** (les documents sont générés avec un `compte_id`
réel — `current_compte(request)`), mais un correctif propre serait une clé d'unicité tolérante au NULL. Laissé
tel quel (périmètre fermé).

## U5 — courrier propriétaire sans champ vide

Le PDF (`/courrier/pdf`) imprime le corps **verbatim** ; les variables `{parcelle} {commune} {surface}` sont
substituées par `remplirGabaritCourrier` (RECETTE-2 S8), qui **supprime le segment entier** quand une variable
manque (jamais « () », « à , », ni marqueur résiduel). Le corps n'imprime **ni nom ni adresse** de
propriétaire — adressage générique (SPF/CERFA), l'adresse ne sert qu'à l'**envoi**, pas au texte. Vérifié sur
3 parcelles (dont PM sans adresse) + cas-limite commune ET surface absentes ; PDF DK1044 relu (propre).

## U6 — les points « à recetter à l'œil » : liste et état réel

| Point (origine) | Sujet | État réel constaté |
|---|---|---|
| **S11** (RECETTE-2) | Carte, mode analyse : voile gris retiré, opacité **uniforme 0,72**, palier porté par la **couleur** | **Code correct** : `MapView.tsx:73` `OPINION_OPACITY = 0.72`, appliqué en analyse (`:1744`, `:1886`), voile supprimé. **Le canvas WebGL ne se capture pas** en screenshot dans cet environnement (limite connue depuis COUCHES-1 : « capture WebGL impossible → Vic shoote les pixels »). État : code correct, **pixels à confirmer par Vic**. |
| **S7 / T1** (RECETTE-2 → validé RECETTE-3) | Brief apporteur, maquette validée (v3) | **Rendu conforme** : apporteur PDF 200 (5 pages) — **bandeau unique** confidentiel, plan « La parcelle » (Surface, Zone, Sur place, Ce qu'on peut y bâtir, Ce qui gêne, Prix, Propriétaire = « Personne morale — LOTISSEMENT DU GOLF », « À côté » voisines même propriétaire, Accès). Cf. `recette4-u6-apporteur-p1-1.png`. |

Les autres points visuels de RECETTE-2 (S4, S24 « non reproduit » ; S15/S16/S17/S25/S26 « corrigé » avec
captures) étaient déjà soldés à leur tour, captures à l'appui — rien de pendant.

## U7 — maquette apporteur archivée

`RECETTE-4-preuves/maquette-apporteur-v3.html` (copie de la v3 validée), référence des prochains tours.

---

## U8 / U9 — Lot 3 (note cascade)
Voir le commit du Lot 3 : la note écrite (DPU / PEB / DPF / zones humides), **rien exécuté**.

## Tests
- Front : `tsc -b` **0**. Vitest zones touchées **13/13** (CourrierService, CourrierRecette4, Financier
  questionnaire, ficheCommune).
- Back : gardes `tests/test_recette4.py` **5/5** ; tests des zones touchées (fiche_commune, financier,
  sources1_lot5, exports2_lot5, dispositifs) **30/30**.
- Documents contre backend réel : financier / apporteur / dossier / courrier → **PDF 200**.
