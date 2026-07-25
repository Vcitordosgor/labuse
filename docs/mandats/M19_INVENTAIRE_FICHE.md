# M19 — PHASE 1 : Inventaire exhaustif de la fiche parcelle

**Branche** `audit/m19-inventaire`. Document seul, zéro code. Autonome (pas d'arrêt) : **rien n'est
supprimé** — cet inventaire liste tout, marque les ⚠ (potentiellement faux) et 💤 (candidat rétrogradation)
pour arbitrage Vic au retour, et propose la hiérarchie 3 niveaux appliquée en PHASE 3.

**Contrat de données** : `GET /parcels/{idu}` → type `Fiche` (idu, commune, adresse, `proprietaire_moral`
{denomination/siren/groupe — **personne morale, public**}, surface_m2, statut, q_score, a_score,
a_completude, completeness_score, coords, evenement, evenement_detail, **lines[]** (`FicheLine` auto-sourcé),
flags[], score_v, score_v2, etage0, icd, reglement_plu, potentiel_transformation, viabilisation,
gestionnaires). Blocs complémentaires chargés à l'ouverture : `/ortho/equipements`, `/traducteur-plu`,
`/v2/score`, `/modules/faisabilite` (+ `/charge`, `/explain`), `/modules/parcelle-permis`, `/sources`,
`/anti-fiche`, `/signalements`.

**Boussole — vérifié** : ✅ **aucune identité de personne physique** n'est jamais affichée. Le type `Fiche`
ne porte que `proprietaire_moral` (personne morale = DGFiP public). Un particulier est rendu par le texte
générique « Propriétaire : personne physique ou non recensé » (Fiche.tsx:1269) — jamais de nom.

Tags fiabilité : **sourcé-vérifié** (source officielle) · **calculé** (formule déterministe) · **estimé**
(modèle/statistique) · **saisi-hyp** (hypothèse utilisateur) · **absence** (rien = neutre).

---

## P1.1 — LISTE EXHAUSTIVE (par zone actuelle)

### A. EN-TÊTE (Fiche.tsx:1020-1090)
- **IDU** · `Fiche.idu` · sourcé-vérifié
- **Adresse postale** · `Fiche.adresse` (BAN) · sourcé-vérifié · ⚠ **C3 : tronquée par ellipse** (à afficher entière, 2 lignes si besoin)
- **Lien « Rechercher à cette adresse ↗ »** (Pages Jaunes) · statique · → **C2** (renommer « Voir sur Pages Jaunes », styler jaune)
- **Commune** · `Fiche.commune` · sourcé-vérifié
- **Surface m²** (`fmtM2`) · `Fiche.surface_m2` · sourcé-vérifié
- **Badge verdict** (Brûlante/Chaude/À creuser/Écartée) · `score_v2.tier` sinon `statut` · calculé (`verdictMeta`)
- **rang N** (si brûlante/chaude) · `score_v2.rang` · sourcé-vérifié · ⚠ rang masqué pour les autres tiers (incohérence de transparence)
- **×N** (mutation) · `score_v2.mult_base` · sourcé-vérifié · ⚠ **score sans explication inline** (voir P1.2)
- **Badge « signaux vendeur N/100 »** · `score_v.v_score` · sourcé-vérifié · ⚠ **score sans explication** (P1.2)
- **Badge « Confiance données N/100 »** (si <85) · `icd.score`/`icd.bande` · sourcé-vérifié · ⚠ **≥85 = badge masqué** (silence = faux « parfait ») (P1.2)
- **Bouton suivi 👁** · `toggleWatch(idu)` · → **C4** (devenir cloche 🔔, cohérent M16)
- **Bouton partage ↗** · `createShare(idu)` (M20) · sourcé-vérifié
- **Bouton cloche/fermer** (header) · UI
- **⚠ Absent (à AJOUTER, pas supprimé)** : référence cadastrale (section/numéro) — l'en-tête n'affiche que IDU+commune+surface.

### B. BANDEAU « ÉCARTÉE » (Fiche.tsx:980-992) → **C1**
- **Bandeau rouge « LABUSE l'a écartée — voici pourquoi »** · condition `verdictEcartee` · → **C1** (supprimer le bandeau ; motif à côté du badge « Écartée » avec « voir pourquoi »)
- **Motifs d'exclusion dure (≤4)** · `lines[].result==='HARD_EXCLUDE'` · sourcé-vérifié · ⚠ tronqué à 4, pas de « voir plus »
- **Repli « qualité insuffisante (Q<50) »** · calculé

### C. BANDEAU « ÉVÉNEMENT » (Fiche.tsx:994-999)
- **Bandeau rouge « ● ÉVÉNEMENT — force priorité dossier »** · `evenement==='rouge' && statut==='chaude'` · calculé · 💤 (héritage v1.3, redondant avec le scoring v2 — à **rétrograder** dans le tiroir Signaux, pas supprimer)
- **Détail événement** · `evenement_detail` (BODACC) · sourcé-vérifié

### D. BLOC IA « DEMANDER À L'IA » (AskBar.tsx) → **C8**
- **Libellé « ✦ Demander à l'IA » + badge PREMIUM** · statique · → **C8** (une seule ligne ; accroche « Une question sur cette parcelle ? » ; UI premium violet)
- **Sous-titre** (« une question sur cette parcelle → » / « dernière réponse gardée ») · calculé
- **Champ question + 6 chips d'exemples** · statique (whitelist backend)
- **Réponse IA + sources (SOURCÉ/ESTIMÉ/ABSENT) + deeplinks** · `askParcel(idu, q)` · sourcé-vérifié (IA ancrée)
- **États : quota atteint / dégradé / absent / caché** · calculé

### E. SYNTHÈSE — SCORES & BLOCS (Fiche.tsx:1172-1254)
- **Équipements (ortho)** · `getOrthoEquipements` : Piscine ~m² (estimé), PV détecté ~m² (estimé), CES probable (estimé), Pente N° (sourcé RGE ALTI), **flag « terrassement lourd probable »** (estimé, confiance inconnue) · ⚠ heuristique · 💤 (cosmétique → tiroir Terrain)
- **Avertissement « Accès à vérifier »** · `lines[] layer==='acces' PASS` · ⚠ (293k faux positifs, non pondéré ; note d'honnêteté enterrée)
- **Score Q « Qualité » N/100 + barre** · `q_score` · calculé · ⚠ **explication en hover seulement** (P1.2)
- **Statut matrice (historique)** (si pilote v2) · `statut` · 💤 (legacy → niveau 3)
- **Score A « Accessibilité » N/100 + barre** · `a_score` · calculé · ⚠ explication hover (P1.2)
- **Bloc « Signaux vendeur » (V)** · `score_v` : score/band/badge, **liste de signaux** (points, label, famille, EN COURS/CLÔTURÉE, confiance de match, âge, source BODACC/RNE/DGFiP/DVF/Cartofriches/ADEME) · sourcé-vérifié · badge « Signaux partiels » si couverture partielle
- **Bloc « Probabilité de mutation (P) »** (ScoreV2Block) · `/v2/score` : tier, ×mult, percentile, rang, badges (copro/veille_succession/événement), **contributions (5, log_hazard signé)** · calculé · ⚠ « non scorée » (404) ne dit pas la raison ; bin technique masqué
- **Bloc « Confiance données » (ICD)** · `icd` : score, bande, **liste « ce qui manque »**, cloisonnement · sourcé-vérifié
- **Bloc « Potentiel de transformation »** · `potentiel_transformation` : niveau, libellé, % SDP consommée, SDP résiduelle estimée, surélévation, source · estimé · ⚠ SDP résiduelle ~0 peut masquer « non calculable »
- **Bloc « Règlement PLU »** · `reglement_plu` : zone, « voir l'article/règlement », articles (≤6), note, disclaimer · sourcé-vérifié
- **Bloc « Viabilisation »** (ViabilisationBlock) · `viabilisation` : score/band, contributions, raccordement qualitatif, assainissement, PV (S3REnR), disclaimer · calculé
- **Bloc « Permis à proximité »** (PermitsProximityBlock) · `modParcellePermis` : counts 100/200 m, liste (≤12 : nature, date, nb_lgt, distance), fiche permis cliquable · sourcé-vérifié
- **Bloc « Gestionnaires »** (GestionnairesBlock) · `gestionnaires` : à jour au, EPCI, eau/assainissement/SPANC/électricité (opérateur+confiance), note, disclaimer · sourcé-vérifié
- **« Signaler une erreur »** (formulaire) · `POST /signalements` · fonction QA
- **Jauge « Complétude · N% »** · `completeness_score` · calculé · ⚠ **sens implicite** (P1.2)
- **Section Flags** · `flags[]` (SOFT_FLAG) · sourcé-vérifié · 💤 (bruit d'audit → niveau 3)

### F. ONGLETS RÈGLES / RISQUES / MARCHÉ / PROPRIO (Fiche.tsx:1256-1282)
Chaque onglet = `lines.filter(onglet===X)`, rendu par `Line()`. Chaque ligne porte : **poids** (±N), **layer**
(couche technique au survol), **libellé français** (`detail`), **sévérité** (fort/moyen/faible/info), **source
cliquable** (`source_table#id`) + **date** → **SourceDrawer** (fournisseur, catégorie, accès, fiabilité,
synchronisée le, doc). Tout sourcé-vérifié.
- **Règles** : couches zonage_plu_gpu, prescription_plu, foncier_public, emprise_lineaire/routiere, residuel_socle, safer, sar, surface, parc_national, foret_publique, cinquante_pas, sup + **Traducteur PLU** (« Traduire ma zone en français courant », zone, règles appliquées Sourcé/Estimé, lien règlement).
- **Risques** : PPR, sol_pollue, cavite, icpe, mvt, pente, ravine, trait_de_cote, abf, ens, eau, bruit_route · ⚠ **le NÉGATIF (« hors PPR », « aucun risque ») est une ABSENCE** (rien affiché) — à transformer en **affirmation visible** (exigence maquette : tiroir Risques fermé = « ✓ aucun risque bloquant · 9/N couches vérifiées »).
- **Marché** : dvf, sitadel, amenites, potentiel_foncier_region, ocs_ge, friche, acces.
- **Proprio** : `proprietaire_moral` (dénomination/SIREN/groupe + lien Patrimoine M02) OU texte « personne physique ou non recensé » ; couches proprietaire, age_dirigeant, bodacc, dpe_passoire, assemblage.

### G. ONGLET FAISABILITÉ (Fiche.tsx:723-812)
- **Capacité constructible** : verdict, gabarit (niveaux+hauteur), SDP, logements, SHAB vendable · calculé/estimé · « estimation générique » si zone non calibrée · bandeau
- **Calcul étape par étape** : `steps[]` (label, valeur, source, provenance Sourcé/Estimé/Dérivé) · traçabilité
- **« Expliquer ce calcul en clair »** (IA) · `faisabiliteExplain` · IA ancrée sur les steps
- **Calculette de charge foncière** (`Calculette`, **composant partagé avec l'outil M15-C2 — ne pas dupliquer**) : sourcé (SDP vendable, prix sortie DVF, terrain) + hypothèses (coût, marge) + résultat (charge foncière centrale, fourchette, €/m²) + aide achat (prix demandé → supportable/trop cher) + avertissements · calculé/saisi-hyp

### H. ONGLET BILAN (Fiche.tsx:815-869)
- Capacité (idem) + **Marché prix de sortie bâti** (médiane €/m², type, N ventes/rayon, fiabilité, tendance, **couverture DVF datée**) · sourcé-vérifié + **Fiscal & leviers** (QPV, TVA, note) + **RTAA DOM** (exigences par volet cadre/thermique/acoustique/aération/ECS + condition altitude + lien Légifrance + vérifié le)

### I. ONGLET POURQUOI PAS (PourquoiPas.tsx) — si écartée/flags
- Anti-fiche `/anti-fiche/{idu}` : motifs RÉDHIBITOIRE / VIGILANCE + sources · sourcé-vérifié

### J. BARRE D'ACTIONS (Fiche.tsx:1288-1356)
- **+ Pipeline** (`addToPipeline`, → « ✓ Dans le pipeline ») · fonction
- **+ Projet** (`ProjetButton`, menu dédoublonné M15-C3 : ajoutables + « Déjà dans ») · fonction
- **👁 Suivi** → **C4** (cloche)
- **↗ Partage** (`createShare`) · fonction
- **Exports** : **PDF** (`pdfUrl` avec hypothèses calculette), **Dossier** (`/dossier/{idu}.pdf`), **Banquier** (async prepare→statut→pdf) → **C6** (renommer), **1950** (M08 comparateur), **Cadastre** (fond IGN Plan interne) → **C7** (ouvrir cadastre.gouv.fr), **Maps** (Google Maps) · ⚠ **C5 : un bouton déborde à droite, inaccessible** (probablement « Maps » ou le dernier — la rangée doit se réorganiser)
- **Disclaimer légal** · statique

---

## P1.2 — SCORES SANS EXPLICATION (proposition de libellé/explication client)

Les explications existent parfois en **hover uniquement** (`SCORE_TIP` dans status.ts, `CLIENT.scoreQ/completude`
dans strings.ts). La refonte les rend **visibles** (une micro-preuve/légende sous chaque score). Tous les
libellés vont dans `strings.ts` (R3).

| Score | Champ | Ce qu'il mesure | Libellé/explication client proposé (à écrire dans strings.ts) |
|---|---|---|---|
| **Q — Qualité** | `q_score` | qualité intrinsèque (règles PLU, risques, terrain) | « **Potentiel constructible** N/100 — qualité du terrain au regard des règles, risques et accès. » |
| **A — Accessibilité** | `a_score` | accès/desserte/aménités | « **Accès & desserte** N/100 — voirie, réseaux, aménités à proximité. » |
| **V — Signaux vendeur** | `score_v.v_score` | probabilité que le propriétaire vende (BODACC/RNE/succession…) | « **Signaux de mise en vente** N/100 — indices publics que le propriétaire pourrait céder (procédures, âge de détention, succession). » |
| **P — Probabilité de mutation** | `score_v2.mult_base` (×N) | combien de fois plus susceptible de muter que la moyenne | « ×N **plus susceptible de muter** que la parcelle moyenne de l'île (12 mois). » (réutiliser `CLIENT.mult.unite`) |
| **ICD — Confiance données** | `icd.score` | complétude des sources disponibles (≠ qualité terrain) | « **Confiance des données** N/100 — part des sources renseignées pour CETTE parcelle. Ce n'est pas une note du terrain. » + **toujours afficher** (ne plus masquer ≥85 : « ✓ dossier complet ») |
| **Complétude** | `completeness_score` | part des couches disponibles | fusionner/aligner avec ICD (redondance à signaler — voir ⚠). Libellé « **Dossier renseigné à N %** ». |
| **Viabilisation** | `viabilisation.score` | faisceau de preuves de raccordement | « **Raccordabilité** N/100 — faisceau d'indices eau/élec/assainissement. » |
| **Potentiel de transformation** | `potentiel_transformation.niveau` | marge de densification restante | « **Marge de densification** — ce qu'il reste à construire vs le déjà-bâti. » |

**⚠ Redondance à signaler (non tranchée — pas supprimée)** : `completeness_score` (jauge Complétude) et
`icd.score` (Confiance données) mesurent des choses proches (part des sources). Les deux restent affichés ;
proposition = les **rapprocher visuellement** dans un même tiroir « Confiance & sources » et laisser Vic
trancher une éventuelle fusion.

---

## P1.3 — HIÉRARCHIE PROPOSÉE (3 niveaux) — appliquée en PHASE 3

Principe maquette : **fermé, ça informe**. Chaque tiroir affiche sa **valeur clé** (niveau 1) choisie comme
une phrase d'argumentaire. Niveau 2 = le cœur à l'ouverture. Niveau 3 = « voir le détail » (replié, jamais
supprimé). Le verdict n'est pas un tiroir : c'est l'en-tête de rapport.

| Tiroir | Niveau 1 (fermé — valeur clé) | Niveau 2 (ouvert — cœur) | Niveau 3 (replié — détail expert) |
|---|---|---|---|
| **Verdict** (en-tête) | Verdict + rang + ×N + « X plus probable » | 3 pastilles d'arguments | — |
| **Constructibilité / Règles** | zone + SDP restante (ex. « U1a · 800 m² ») + jauge SDP | zonage, hauteur/emprise calibrées, potentiel transformation | prescriptions, articles PLU, traducteur, règlement, confiance calibrage |
| **Risques** | « ✓ aucun risque bloquant · N/N couches » (9 segments verts) | risques présents (sévérité) + négatifs affirmés (hors PPR…) | chaque couche, source, date, extrait |
| **Marché** | « demande forte · N ventes/12 mois » + sparkline | médiane €/m², tendance, couverture DVF | comparables (anonymisés), lignes DVF, fiscal & leviers |
| **Propriétaire** | « 1 propriétaire · succession » (ou pastilles indivision/détenu N ans) | dénomination PM/SIREN (ou « personne physique — non nommée »), signaux vendeur | liste signaux V (BODACC…), lien Patrimoine M02 |
| **Faisabilité / Financier** | « R+2 · charge foncière 410 k€ · calcul tracé » | capacité, gabarit, calculette | steps tracés, explication IA, bilan, RTAA DOM |
| **Viabilisation & réseaux** | raccordabilité (ex. « confirmée ») + terrain (pente) | eau/élec/assainissement, équipements (piscine/PV/pente) | contributions, gestionnaires, coûts qualitatifs |
| **Permis à proximité** | « N permis (300 m · 24 mois) » | liste des permis récents | fiche permis, distances |
| **Confiance & sources** | « ✓ dossier renseigné à N % » (ICD/complétude) | ce qui manque | cloisonnement, drawer sources, signaler une erreur |
| **Pourquoi pas** (si écartée) | motif principal à côté du badge « Écartée » | motifs rédhibitoires/vigilance | sources anti-fiche |

Chaque **rétrogradation en niveau 3 est réversible** : rien n'est retiré, tout reste accessible via « voir le
détail ». Vic peut contester une ligne du tableau d'un coup d'œil.

---

## ⚠ LISTE DES INFOS SUSPECTES / POTENTIELLEMENT FAUSSES (pour arbitrage Vic — AUCUNE supprimée)

1. **rang masqué hors brûlante/chaude** — laisser affiché pour tous les tiers (cohérence). Corrigeable en PHASE 3 (afficher le rang partout).
2. **ICD ≥85 → badge masqué** — silence lu comme « parfait ». Corriger : afficher « ✓ dossier complet ».
3. **« terrassement lourd probable »** (pente) — heuristique à confiance inconnue → afficher « estimé » explicitement.
4. **« Accès à vérifier »** — 293k faux positifs, non pondéré → afficher clairement « signal informatif, non pondéré ».
5. **« non scorée » (v2 404)** — ne dit pas la raison (copro vs hors périmètre vs run absent) → préciser.
6. **SDP résiduelle ~0** — peut masquer « non calculable » → distinguer 0 exact de indéterminé.
7. **Événement badge (legacy v1.3)** — redondant post-v2 → rétrograder (niveau 3), pas supprimer.
8. **Complétude vs ICD** — redondance (voir P1.2).
9. **Tendance DVF sur 2-3 ventes** — volatilité → afficher la fiabilité à côté.

## 💤 CANDIDATS RÉTROGRADATION NIVEAU 3 (vrais mais rarement décisifs — repliés, pas supprimés)
Statut matrice historique · Flags SOFT_FLAG · Groupe label propriétaire · SPANC (souvent NULL) · Couche
assemblage · Équipements cosmétiques (piscine/PV/CES) · Badge score V « N.A. » (public/bailleur).

---

## SUITE (autonome, sans arrêt)
CC enchaîne sur **PHASE 2** (3 maquettes, variante A par défaut) puis **PHASE 3 + LOT C**. Vic lira cet
inventaire au retour et pourra **contester toute rétrogradation** (tableau P1.3) ou **marquer une info « à
retirer »** — seul cas où une suppression sera faite.
