# M19 — FICHE PARCELLE : refonte — RAPPORT FINAL

Mandat autonome (Vic absent). CC a enchaîné les 4 phases sans arrêt de validation. **Rien n'a été
supprimé (R1)**, variante **A retenue (R2)**, texte client **centralisé dans `strings.ts` (R3)**, **la
non-régression a primé (R4)** : `golden 116/116` et `tsc + vite build` verts à chaque étape.

Une branche par phase, **poussée, non mergée** (CC ne merge jamais — Vic merge `--no-ff`).

| Phase | Branche | État |
|---|---|---|
| 1 · Inventaire | `audit/m19-inventaire` | poussée · `docs/mandats/M19_INVENTAIRE_FICHE.md` |
| 2 · Maquettes | `design/m19-maquettes` | poussée · `qa/m19/maquettes/` (A/B/C + MAQUETTES.md) |
| 3 · Implémentation + LOT C | `feat/m19-fiche` | poussée · 2 commits (LOT C, tiroirs) |
| 4 · Vérif post-merge | — | à faire **après** merge Vic |

---

## PHASE 1 — inventaire (doc seul)
`M19_INVENTAIRE_FICHE.md` : **P1.1** liste exhaustive de tout l'affiché (en-tête, verdict, 8 onglets, blocs
scores, actions, IA) avec source / fraîcheur / fiabilité + flags ⚠ (potentiellement faux) et 💤 (candidat
rétrogradation) ; **P1.2** les scores Q/A/V/P/ICD/Complétude/Via/Potentiel + libellé client proposé ; **P1.3**
la hiérarchie 3 niveaux (fermé informe / ouvert / replié). **Boussole vérifiée** (3 agents) : aucune identité
de personne physique n'est jamais affichée (type `Fiche` = `proprietaire_moral` seul, DGFiP public).

## PHASE 2 — maquettes (variante A retenue)
3 maquettes HTML cliquables sur **une parcelle réelle** (`97418000AT2317`, Sainte-Marie, brûlante rang 11
×22, propriétaire CBO TERRITORIA, 2 signaux vendeur, sous-densité 126 m²), palette = tokens réels du design
system. **A** (fidèle, défaut), **B** (densité 2 col), **C** (regroupement 3 sections). **A retenue** : elle
traduit la direction validée (« fermé ça informe », verdict-en-tête, carte accent unique) sans rompre la
respiration. États dégradés mockés (sans adresse / écartée / partielle). Rendus PNG (gitignorés, backup local).

## PHASE 3 — implémentation sur `feat/m19-fiche`

### LOT C (commit `65ee2e6`) — 9 correctifs + texte centralisé (R3)
Tout le texte client neuf vit dans `CLIENT.fiche` (`strings.ts`).
- **C1** · le bandeau rouge « écartée » séparé est **retiré** ; le motif principal s'affiche **à côté du badge**
  + « voir pourquoi → » (ouvre l'onglet Pourquoi pas). Les motifs sourcés y restent intégralement (R1).
- **C2** · « Rechercher à cette adresse ↗ » → **« Voir sur Pages Jaunes »**, stylé jaune (nod marque).
- **C3** · l'adresse n'est **jamais tronquée** — elle passe à deux lignes au besoin (`break-words`, plus de `truncate`).
- **C4** · l'œil 👁 devient **cloche 🔔** (cohérent avec les notifications M16 que le suivi alimente).
- **C5** · les 6 exports **débordaient** (rangée `flex` non-wrap : le 6e bouton « Maps » sortait du panneau
  400 px) → **grille 3 colonnes**, 2 rangées régulières, aucun débordement. ✔ *le bouton fautif identifié = « Maps » (dernier).*
- **C6** · **« Banquier » → « Note de financement »** (3 pistes étudiées, cf. `strings.ts` : *Note de financement* /
  *Dossier financeur* / *Présentation banque* — la 1re retenue). Renommé dans les 4 états du bouton.
- **C7** · **« Cadastre ↗ »** ouvre le cadastre officiel **externe**, paramétré sur la parcelle. ⚠ *Nuance
  technique (reliquat de jugement)* : `cadastre.gouv.fr` (Struts/POST) n'expose **pas** de lien GET par parcelle ;
  le parcellaire officiel adressable par URL est le **Géoportail (IGN — Parcellaire Express)**, centré sur les
  coordonnées avec la couche cadastrale active. C'est la même donnée cadastrale officielle. À arbitrer si Vic
  veut absolument le domaine `cadastre.gouv.fr` (impliquerait un formulaire POST, non-linkable proprement).
- **C8** · le bloc IA replié en **une ligne** : accroche client **« Une question sur cette parcelle ? »** en tête,
  **PREMIUM** violet assumé.
- **C9** · en-têtes dégradés soignés (sans adresse → « Adresse non disponible » ; écartée → motif + « voir pourquoi »).
- **P1.2** · les explications de scores (Q/A/V/ICD/Complétude) sont **centralisées** dans `CLIENT.fiche.scores`
  (prêtes à être rendues visibles, plus seulement en survol).

### Tiroirs P1.3 (commit `b5cc012`) — Synthèse « fermé, ça informe »
Composant **`FicheDrawer`** réutilisable : fermé = **valeur clé lisible** (niveau 1), détail au clic (niveau 2/3,
**monté paresseusement**). Les blocs secondaires de la Synthèse passent en tiroirs, chacun avec sa valeur clé :
Probabilité de mutation (« Brûlante · ×N · rang »), Confiance des données (« libellé · N/100 »), Potentiel de
transformation, Règlement PLU (« zone »), Viabilisation (« libellé »), Permis à proximité, Gestionnaires, Flags.
**Les blocs existants sont réutilisés tels quels** (`ScoreV2Block`, `IcdBlockView`, `ViabilisationBlock`,
`GestionnairesBlock`, `PermitsProximityBlock`…) → **zéro touche aux données**. Q / A / Signaux vendeur restent
visibles en tête (contenu verdict-adjacent). **Rien supprimé (R1)** — seulement réorganisé en niveaux.

### Non-régression (R4) — vérifiée
- `tsc -b && vite build` : **0 erreur** à chaque commit.
- `golden 116/116` (`:8060`, `LABUSE_DEV_MODE=1`) : vert (changements 100 % frontend, données intactes).
- Fiche **réelle capturée** via le store (nominal + tier brûlante + Synthèse fermée/ouverte) : rendu conforme,
  pas de casse. Captures d'implémentation : `qa/m19/maquettes/impl_*.png` (backup local).
- Intacts et non touchés : **+ Pipeline**, **+ Projet** (menu dédoublonné M15-C3), **exports** PDF / Dossier /
  1950, **module IA**, **calculette** (composant `Calculette` partagé avec l'outil M15-C2 — non dupliqué),
  **suivi**, onglets Règles / Risques / Marché / Proprio / Bilan / Faisabilité / Pourquoi pas.

## Onglets → tiroirs (strangler, 8 commits) — **TERMINÉ** (option 2, Vic)
Les 8 onglets ont été **fondus en tiroirs, un par commit**, sans big-bang : chaque onglet est **reparenté**
(son rendu existant, inchangé) dans un `FicheDrawer` de la pile Synthèse. Ordre de risque croissant tenu.
Après CHAQUE onglet : `tsc + build + golden 116/116` + capture (fermé/ouvert). Aucun onglet récalcitrant.

| # | Commit | Onglet | Valeur clé fermée (P1.3) |
|---|---|---|---|
| 1 | 3046c71 | **Risques** | **« ✓ rien à signaler · N couches vérifiées »** — le négatif AFFIRMÉ (sinon « N vigilance · M couches sans risque ») |
| 2 | 473ead7 | Marché | « 498 €/m² · 91 ventes secteur » (médiane structurée `dvf_parcelle`, typée) |
| 3 | 95575e6 | Proprio | « CBO TERRITORIA · Gérant âgé (81 ans)… » (signal dominant sinon type ; personne physique jamais nommée) |
| 4 | ff9c352 | Règles | « Zone UB · 126 m² SDP » |
| 5 | 47b5e10 | Bilan | « ~126 m² SDP · marché & fiscal » |
| 6 | b57301a | Pourquoi pas | « motifs d'écartement & points de vigilance » (conditionnel écartée/flaggée ; le C1 « voir pourquoi » l'ouvre) |
| 7 | bc1c83d | Faisabilité | « ~126 m² SDP · charge foncière » (calculette PARTAGÉE M15-C2, réutilisée, jamais dupliquée) |
| — | 9488c2a | *finalisation* | barre d'onglets → **nav pure** (« Synthèse » remonte, chaque libellé ouvre+scrolle son tiroir) |

Infra strangler : `FicheDrawer` gagne `id`/`aria-expanded` ; pendant la migration, un clic d'onglet migré
ouvrait+scrollait le tiroir tandis que les non-migrés gardaient l'ancienne bascule (les deux navigations
coexistaient — étape intermédiaire testable). **Fix R4** (fonction préservée) : le PDF reflète la charge
foncière dès que la calculette est active (`calculette` store non-null = tiroir Faisa/Bilan ouvert), au lieu de
dépendre d'un onglet actif devenu tiroir. **Captures finales** : `qa/m19/maquettes/impl_FINAL_ferme.png` (fiche
entière en pile de tiroirs, chacun informe fermé) + `impl_FINAL_ouvert.png` (7 tiroirs ouverts, tout le contenu
présent). La fiche EST désormais la pile « fermé ça informe » de la maquette A : verdict + scores en tête, puis
chaque section en tiroir informatif. Plus d'onglets qui masquent — tout est là, replié (R1).

## Arbitrages laissés à Vic (aucun blocage, rien supprimé)
1. **C7 cadastre** : Géoportail (Parcellaire Express IGN) au lieu de `cadastre.gouv.fr` (non-linkable en GET). Cf. supra.
2. **Rétrogradations niveau 3** (P1.3) appliquées : badge événement legacy, statut matrice historique, flags,
   équipements cosmétiques → repliés, jamais retirés. Vic peut contester chaque ligne du tableau P1.3.
3. **⚠ suspects** de P1.1 (rang masqué hors brûlante/chaude, ICD ≥85 masqué, redondance Complétude/ICD, « accès
   à vérifier » non pondéré…) : **signalés, laissés en place** — leur correction dépend d'une décision produit.
4. **Onglets → tiroirs** : ✅ FAIT (strangler 8 commits). La barre subsiste en **nav** ; Vic peut décider de la
   retirer complètement si la navigation par scroll suffit.

## PHASE 4 (après merge Vic)
Rejouer `golden 116/116` sur la prod, vérifier la fiche en ligne (LOT C + tiroirs), confirmer exports/IA/calculette.
