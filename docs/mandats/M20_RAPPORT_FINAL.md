# M20 — RAPPORT DE VAGUE

Petit mandat de finition (courrier sur fiche · barre à 7 tuiles · parité Dossier/Flash). Autonome, filet
`avant-m20` (main `171a87f`). **CC ne merge pas** — 3 branches poussées, non mergées. Golden 116/116 par lot,
`LABUSE_DEV_MODE=1`, jamais réparé. Modèle P gelé. Zéro identité de personne physique.

## 1. Preuves par point

### LOT A — Courrier propriétaire depuis la fiche (`feat/m20-a-courrier-fiche`)
- **7e tuile « Courrier »** dans la barre d'actions → `setModule('courriers')` : ouvre le module **M09 EXISTANT**
  (un seul moteur, cf. Outils — aucune réimplémentation, comme la calculette M15-C2).
- **Pré-remplissage** : M09 initialise déjà l'IDU depuis `selectedIdu`. Ajout d'une **synchro** (étape « Parcelle »
  suit `selectedIdu`) pour le cas « module déjà ouvert, on change de parcelle » — vaut pour **les deux points
  d'entrée** (fiche + Outils), **aucune divergence**.
- **Boussole (A3, critique)** : héritée de M09, **aucune logique propriétaire nouvelle**. Bannière M09 : « adressé
  génériquement (aucune identité de propriétaire particulier utilisée ; identification via SPF/CERFA) ».
  - **Cas personne MORALE** (`97418000AT2317`, CBO TERRITORIA) → `qa/m20/a/A_courrier_PM.png` : IDU pré-rempli,
    raison sociale/SIREN publics visibles côté fiche.
  - **Cas personne PHYSIQUE** (`97418000AT2374`) → `qa/m20/a/A_courrier_PP.png` : IDU pré-rempli
    (`97418000AT2374`), propriétaire affiché **« privé »**, **aucun nom / aucune adresse** — module utilisable,
    identité non fournie. Test automatisé : « aucun nom exposé ».
- Preuve barre : `qa/m20/a/A_barre_7tuiles.png` (7 tuiles, libellés entiers).

### LOT B — Barre d'actions à 7 tuiles (`fix/m20-b-barre-7-tuiles`)
- Grille **6 → 7 colonnes** dans le **bloc segmenté UNIQUE** (réf. M19 conservée : fond `#0e1311`, bordure
  `#1e2823`, séparateurs `#16201c`). **Un seul rang**, pas de menu, pas de scroll horizontal.
- Ordre : **PDF · Dossier · Finance · 1950 · Cadastre · Maps · Courrier**.
- **B3 accessibilité prouvée** (`qa/m20/b/B_barre_7tuiles.png` + mesures) : panneau **359 px**, **7 tuiles × 51 px**,
  `horizScroll = false`, **aucune troncature**, **toutes dans le panneau**, toutes cliquables.
- La barre est **identique à celle du LOT A** (même JSX/strings) → merge A+B sans conflit ; seul A ajoute la synchro M09.

### LOT C — Parité Dossier / Flash (`fix/m20-c-parite-dossier`)
- Voir le détail : **`docs/mandats/M20_C_PARITE_DOSSIER.md`** (tableau de parité complet).
- Preuve : `qa/m20/c/dossier_section07.png` (+ `dossier_AT2317.pdf`) — Dossier réel sur `97418000AT2317` montrant
  la **section 07 « Contexte commune & leviers »** (vélocité PC ~9 mois + caveat, SRU 28,7 %, QPV/TVA, conso ENAF)
  et le **Gisement solaire PVGIS** (1500 kWh/kWc + caveat gradient côtier).

## 2. Tableau de parité Flash / Dossier (LOT C) — résumé

Moteur **commun** (`collect_report_data` + `rapport.html.j2` + `render_report_html`) → parité **structurelle**.
L'enrichissement M18-D (section 07 + solaire) n'était **pas sur main** (branche `feat/m18-d` non mergée) : **ni
Flash ni Dossier** ne l'avaient. **Aligné** en reprenant le code M18-D (cherry-pick `flash/data.py` + template) →
les deux l'ont désormais. Marqueurs présents **Flash ET Dossier** : Contexte commune, permis accordés (caveat),
SRU, QPV, ENAF, Gisement solaire, gradient côtier (caveat), millésimes. Différences **intentionnelles** : mention
« Généré via LABUSE pour [raison sociale] » (Dossier seul), pas de page tarifaire (aucun des deux). Tableau complet
dans `M20_C_PARITE_DOSSIER.md`.

## 3. Libellés retenus — barre à 7 tuiles
- **« Financier » → « Finance »** (RETENU). Options écartées consignées dans `strings.ts` : « Banque » (évoque un
  contact, pas un document), « Note fin. » (abréviation moins lisible). « Finance » garde le sens « document de
  financement » et tient sans troncature à 51 px. Les 6 autres libellés (PDF, Dossier, 1950, Cadastre, Maps,
  Courrier) tiennent tels quels. Tous centralisés dans `strings.ts` (R3).

## 4. Quota Dossier (C3 — rapport seul, aucune décision)
**Câblé et actif** : `dossier_quota_mois = 20` (config) ; si plan ≠ Intégral et `utilisés_mois ≥ 20` → **HTTP 429** ;
compteur incrémenté dans `usage_compteurs` ; `/dossier/statut` expose les restants. **Nuance** : la porte d'accès
par plan `plans.acces("dossier_parcelle")` est un **stub « toujours vrai aujourd'hui »** (personne n'est bloqué).
Activer/ajuster quota + porte = **décision Vic** (politique commerciale), hors périmètre.

## 5. Non fait / bloqué / réserves
- **Réserve LOT B** : la 6e tuile reste **« Maps »** (fonction Google Maps préservée) là où une référence antérieure
  évoquait « Courrier » — désormais « Courrier » est la **7e** tuile (LOT A). Cohérent.
- **LOT C — dépendance** : l'alignement reprend le code M18-D validé mais **non poussé**. Si Vic mergeait aussi
  `feat/m18-d-pdf-flash-enrichi` par ailleurs, il y aurait recouvrement (mêmes fichiers `flash/data.py` + template) —
  à merger l'un OU l'autre, pas les deux. Recommandation : merger **C** (qui porte le code + la preuve de parité) et
  archiver `feat/m18-d` comme doublon.
- Aucun autre point bloqué.

## 6. Branches & ordre de merge (Vic, `--no-ff`)
```
feat/m20-a-courrier-fiche   (courrier + synchro M09 + 7e tuile + boussole PM/PP)
fix/m20-b-barre-7-tuiles    (barre 7 col + « Finance » + accessibilité) — bar identique à A, merge propre
fix/m20-c-parite-dossier    (enrichissement M18-D repris → parité Flash/Dossier) — indépendant
```
Ordre suggéré : **A → B → C** (A et B partagent la barre à l'identique ; C est backend, indépendant).
Puis **LOT D** (vérif sur main mergée) — à exécuter après le merge.
