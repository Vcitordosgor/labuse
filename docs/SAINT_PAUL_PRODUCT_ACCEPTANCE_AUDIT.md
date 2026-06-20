# SAINT-PAUL — Audit d'acceptation PRODUIT (recette finale avant réplication)

> Recette produit complète de Saint-Paul + LABUSE : pas seulement « ça marche techniquement »,
> mais « est-ce un produit fort, propre, premium, vendable cher, fidèle à la promesse *tout au
> même endroit, interprété, exploitable* ? ». Audit du 2026-06-20 (12 blocs).
>
> **Méthode** : recette base (lecture seule), test Playwright de toute l'UI, audit code/config
> (barème, prix, données→UI), captures d'écran. Aucune donnée modifiée, aucune autre commune touchée.

## Verdict général

**Saint-Paul est techniquement IMPECCABLE et le produit est genuinement PREMIUM** — fiche claire,
données complètes et interprétées, traçabilité totale, vocabulaire promoteur. Les faiblesses ne sont
**pas structurelles** : ce sont des **finitions de crédibilité** (bilan à calibrer/badger, barème à
documenter, IA à activer) qui séparent « très bon outil » de « licence chère incontestable ».

**Aucun bug bloquant. Aucun bouton cassé. Aucune incohérence de données.**

---

## 1. Recette technique Saint-Paul ✅

| Contrôle | Résultat |
|---|---|
| Parcelles · sections | **51 129 · 98** ✅ |
| Doublons IDU · géométries invalides | **0 · 0** ✅ |
| Parcelles évaluées | **51 129 / 51 129 (100 %)** ✅ |
| Couches critiques | bâti 83 981 · zonage 100 % · pente · voirie · PPR · ravines ✅ |
| `/readyz` · `/demo-status` | **200 · ready_for_demo=True, 14/14** ✅ |
| Tests Saint-Paul | **12/12** ✅ · fiche < 1 s · suite 383/383 ✅ |

**Angles morts trouvés malgré les tests verts (mineurs, non bloquants) :**
- **1 parcelle ~0 m²** (sliver cadastral, arrondi). Artefact donnée, pas un bug.
- **156 « opportunités » de 251–500 m²** : au-dessus du seuil de déclassement (250 m²) mais **trop
  petites pour un programme de promotion** → sur-classement au bas de l'échelle (cf. bloc 7).
- SAR = proxy informatif (ne pénalise plus) → la famille « sar » crédite 10 pts de complétude pour
  une donnée qui n'influence plus le verdict.

## 2. Test de l'interface — TOUS les boutons ✅

| Élément | Fonctionne | Utile | Clair | Reco |
|---|:--:|:--:|:--:|---|
| Recherche / audit parcelle (réf, adresse, polygone) | ✅ | ✅ | ✅ | — |
| Ouvrir / fermer fiche (Escape, inert OK) | ✅ | ✅ | ✅ | — |
| Quick-filters (opportunité/à creuser/écartée/faux positif) | ✅ | ✅ | ✅ | — |
| Shortlist (183 items) | ✅ | ✅ | ⚠ | Score de priorité opaque (bloc 7) |
| Pipeline (Kanban) | ✅ | ✅ | ✅ | — |
| Notes / Contact / Relance (form inline) | ✅ | ✅ | ✅ | — |
| Export HTML/MD · Fiche PDF (print) | ✅ | ✅ | ✅ | — |
| Bouton IA « Expliquer cette parcelle » | ✅ | ✅ | ⚠→✅ | **Élevé en haut de fiche (corrigé, bloc 3)** |
| Mode Verdict / Mutabilité | ✅ | ✅ | ⚠ | tooltips ajoutés ; découvrabilité à améliorer |
| Mesurer (distance + surface) | ✅ | ✅ | ✅ | ajouter unité hectare |
| Dessiner une zone | ✅ | ✅ | ⚠ | pas de résumé zone (surface, n parcelles, potentiel) |
| Assemblage (sélection + étude cumulée) | ✅ | ✅ | ✅ | — |
| Couches carte / zoom / sélection | ✅ | ✅ | ✅ | tuiles externes : `ERR_CERT` en sandbox (à vérifier hors-sandbox) |

**Aucun bouton cassé. Aucune erreur JS produit** (seules erreurs console = certificats des tuiles
carto externes, spécifique à l'environnement sandbox).

## 3. Assistant IA « Expliquer cette parcelle » — ✅ CORRIGÉ (élevé)

- **Avant** : enterré dans le **8ᵉ accordéon** (replié) → invisible, secondaire.
- **Comportement** : sans clé → bouton **désactivé propre** (« clé API requise » + tooltip) ; avec
  clé (provider Anthropic prêt) → synthèse **anti-hallucination** (whitelist des faits réels, jamais d'invention).
- **CORRECTION APPLIQUÉE** : bloc **« Analyse IA de la parcelle »** remonté **juste sous L'essentiel**
  (y 901→399), encadré premium (accent doré, micro-copy « synthèse experte, à partir des seules
  données réelles, jamais d'invention »), état désactivé propre conservé. → perception « outil expert ».
- **Constat honnête (post-LOT 2)** : la re-cascade après l'index voirie a régénéré les évaluations
  **sans `ai_payload`** (cascade sans `?ai=true`). `_latest_eval` renvoie donc l'éval récente → le
  **sous-bloc « Analyse LA BUSE · IA » (règles) est actuellement vide sur toutes les parcelles**.
  Le bloc reste correct (rendu conditionnel : vide = rien d'affiché, jamais d'erreur). Réactiver l'IA
  règles = relancer la cascade avec `?ai=true` ou brancher la clé LLM (hors périmètre recette : pas de re-cascade).
- **Reste** : activer `ANTHROPIC_API_KEY` pour transformer le teaser en wow factor.

## 4. Dessiner une zone — fonctionne, à enrichir

Fonctionne (Leaflet natif : clic = sommet, double-clic = terminer). Deux usages : **auditer un
polygone** (récupère les parcelles incluses) et **créer une zone de veille** (alertes DVF/permis).
**Manques pour un usage promoteur fort** : pas de **résumé de zone** (surface dessinée, nombre de
parcelles concernées, potentiel SDP/logements cumulé), pas de bouton « effacer la zone » explicite,
pas d'export/ajout pipeline de la zone. → **Proposé**, non appliqué (touche la logique d'audit).

## 5. Mesurer — VENDABLE (pas bricolé)

Distance **géodésique** (`map.distance`) + surface **géodésique** (`geodesicAreaM2`), polygone or
pointillé + tooltip permanent. Unités m/km (distance), m² (surface), reset par re-clic. **C'est un
vrai outil**, pas un gadget. Seule amélioration simple : **unité hectare** au-delà de ~10 000 m²
(un promoteur raisonne en ha pour les grands tènements).

## 6. Mutabilité / Verdict — fonctionnent, vocabulaire à clarifier

Deux **modes de coloration carte** : **Verdict** (couleur = statut LA BUSE) et **Mutabilité**
(couleur = bâti/non-bâti, pour repérer le foncier **libre**). Distincts et utiles. **Confusion
possible** : un promoteur ne distingue pas spontanément « verdict », « mutabilité », « potentiel
brut » (score), « opportunité » (statut). **Corrigé** : tooltips ajoutés sur les deux modes.
**Proposé** : libellés plus parlants (« Bâti / libre » pour mutabilité), légende permanente, et
distinction explicite dans la fiche entre **score brut** (jauge), **verdict** (statut) et
**mutabilité** (occupation).

## 7. Notes, scores & barèmes — architecture solide, documentation insuffisante

| Score | Formule | Critères | Justification | Limite |
|---|---|---|---|---|
| **opportunity_score** [0-100] | 50 base − pénalités SOFT_FLAG (×1/2/3) + bonus (zonage, DVF, surface saturante, propriétaire, permis, accès) | cascade | Traçable (chaque point = motif) | **Seuil opportunité = 65 non justifié** ; poids accès (3) < importance |
| **completeness_score** [0-100] | Σ poids familles couvertes (= 100) | 12 familles de couches | Confiance données | SAR 10 pts pour un proxy informatif |
| **verdict** | HARD_EXCLUDE→exclue/faux-positif ; compl<50→à creuser ; opp≥65 & compl≥50→opportunité ; déclassement métier | score + cascade + déclassement | Flux cohérent, prudent | **Disjonction cognitive** : score 72 + verdict « à creuser » (compl<50) déroute |
| **priority_score (shortlist)** | verdict_base + opp + 0,4×compl + densif + résiduel + éco + proprio − risque + bonus assemblage/marché | composite | Classement promoteur | **Pondérations arbitraires** (120/50/25/18/−30/30/15) non sourcées |
| **marge bilan** | 9 % du CA | calibration | Fourchette réelle 8-10 % | **Doc incohérente** (RAPPORT dit 16 %) |

**Constat** : architecture **bien pensée** (cascade → scoring → déclassement métier, traçabilité
totale), mais **~17 « magic numbers » + 5 seuils PLACEHOLDER** (90 %/5 % A-N, 50 % ER, 30 % pente,
10 m ravine, 65 opportunité, 40/60 % pente déclassement) **non documentés**. Défendable « si on
assume le rôle d'outil à calibrer ensemble » ; **non défendable** si un promoteur demande « pourquoi
65 ? » et la réponse est « c'est comme ça ». → **Action : 1 page de barème justifié.**

## 8. Prix, bilan & cohérence économique — méthode solide, valeurs à fiabiliser

- ✅ **DVF rigoureux** : Q1/médiane/Q3 par secteur, exclusion aberrants (Tukey IQR), dédup, badge
  **fiable/fragile/insuffisant** + raisons. **Excellent.**
- ✅ Prix neuf **ventilé par bassin PLU** (sourcé), loyers DHUP / Obsimmo / occupation INSEE sourcés.
- ⚠ **Coûts = estimées optimistes** : construction 2 100 €/m² SDP, VRD 90 €/m², marge 9 % →
  un promoteur avec ses vrais devis (≈ 2 400 €/m², VRD réel) obtient une **charge foncière nettement
  inférieure** → **contestable si utilisé pour décision/financement** (OK pour prospection/shortlist).
- ⚠ **Placeholders non badgés** : « Coût construction 2 100 €/m² » affiché **sans badge « estimé »**
  → un expert suppose un chiffre fiable. Le bandeau global « indicatif » existe, mais pas par ligne.
- ⚠ Incohérence doc marge (9 % code vs 16 % RAPPORT) ; bonus vue mer + prix secteur balnéaire =
  risque de double-compte.
- ✅ Bilan d'une « opportunité » = **crédible en ordre de grandeur** (signe correct), avertissement
  charge foncière négative affiché. → **À calibrer (case C) avant positionnement financier.**

## 9. Promesse « tout au même endroit » — ✅ TENUE

**27 couches rendues ET compréhensibles** dans la fiche (cadastre, PLU/zonage/prescriptions, PPR,
SAR, bâti, voirie/accès, pente, vue mer, DVF, Obsimmo, loyers, occupation INSEE, propriétaires,
PLH, SITADEL, assemblage, bilan, scores, prospection). Synchrone (verdict/marché/faisabilité) +
lazy-load (altimétrie/expo/réseaux/PLU détaillé). **Aucune donnée « en base mais invisible »**.
Angles morts mineurs : divergence SAR seulement en vigilance ; lazy-load perçu comme « fiche
incomplète » ; réseaux affichés en « à vérifier » générique.

## 10. Construit / non construit — ✅ CLAIR

- Fiche : « Occupation — 0 % bâti » / « X bâtiments couvrant Y % (BD TOPO) », badge SOURCÉ, label
  prudent (libre / déjà bâti / partiellement mutable).
- Carte : mode **Mutabilité** colore bâti vs libre (à rendre plus découvrable).
- **R1 efficace** : aucune « opportunité » bâtie > 50 % (vérifié sur les 524). Un promoteur
  distingue immédiatement « libre » / « déjà construit » / « partiellement mutable ».

## 11. Qualité produit / vendable — notes

| Dimension | Note | Commentaire |
|---|:--:|---|
| **Produit** | **7,5/10** | Fiche premium, données complètes interprétées ; freins : bilan à fiabiliser, barème à documenter |
| **UX** | **8/10** | Clair, rapide, tout fonctionne, IA élevée ; mineurs : mutabilité cachée, lazy-load, résumé zone |
| **Data** | **8,5/10** | 27 couches, badges sourcé/estimé, DVF rigoureux, cadastre complet ; PPR partiel (PEIGEO), coûts estimés |
| **Métier promoteur** | **7,5/10** | Parle le langage, assemblage, bilan ; freins : chiffres bilan contestables, petites « opportunités » |
| **Démo commerciale** | **8/10** | 8 parcelles scénarisées conformes, vitrine BK0023 forte ; IA à activer pour le wow |
| **Éléments « premium »** | — | L'essentiel décisionnel, badges provenance, traçabilité source par source, jauge, exports |
| **Éléments « prototype »** | — | placeholders bilan non badgés, magic numbers non documentés, IA désactivée par défaut |

**Prêt à vendre en licence chère : OUI SOUS RÉSERVE** — vendable **maintenant comme outil de
prospection/shortlist premium** ; pour appui décision/financement, exécuter les 5 actions ci-dessous.

## 12. Corrections & décision

### Corrections APPLIQUÉES (non risquées, front)
1. **IA élevée** en bloc « Analyse IA de la parcelle » en haut de fiche (perception outil expert).
2. **Tooltips** sur les modes Verdict / Mutabilité (clarté).

### Corrections PROPOSÉES (validation requise — touchent logique/data/jugement)
1. **Badger « estimé »** chaque coût du bilan (construction, VRD, marge) — affichage de provenance.
2. **Calibrer le bilan** (case C : coûts réels Réunion) — valeurs métier.
3. **Documenter le barème** (les ~17 seuils/poids) — 1 page.
4. **Resserrer les petites « opportunités »** (251–500 m² → « à creuser ») — seuil de déclassement.
5. **Badge divergence SAR** dans L'essentiel ; **découvrabilité Mutabilité** ; **résumé zone**
   dessinée ; **unité hectare** mesure ; corriger l'incohérence doc marge (16 %→9 %).

### Décision
- **Démo promoteur : GO SOUS RÉSERVE** — montrable maintenant (fiche premium, vitrine BK0023) ;
  **activer la clé IA** + assumer le bilan comme **indicatif** avant la démo.
- **Réplication autres communes : GO** — Saint-Paul est le gold standard technique (verrouillé,
  testé, index voirie persisté, méthode `lot2_import_saint_paul.py` paramétrable). Les finitions
  produit (bilan, barème, IA) sont **transverses** (pas spécifiques Saint-Paul) → la réplication
  peut avancer en parallèle.

---

*Audit lecture seule + 2 corrections front non risquées. Aucune donnée modifiée, aucune autre commune touchée.*
