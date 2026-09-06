# Lot F — Inventaire des points d'entrée IA & cantonnement

Objectif (F2) : l'IA ne subsiste que dans **la fiche parcelle** et **le Copilote**. Partout ailleurs,
le point d'entrée IA disparaît (les endpoints back restent). Dashboard admin hors périmètre.

## F1 — Inventaire (côté client)

### À CONSERVER — les deux surfaces autorisées

| `fichier:ligne` | Surface | Point d'entrée IA | Endpoint / action |
|------------------|---------|-------------------|-------------------|
| `frontend/src/components/fiche/Fiche.tsx:1164` | Fiche parcelle | bouton « Poser une question » (AskBar) | `askParcel()` → `/parcels/{idu}/ask` |
| `frontend/src/components/fiche/Fiche.tsx:1169` | Fiche parcelle | bouton « Synthèse IA » | `getExplain()` → `/parcels/{idu}/explain` |
| `frontend/src/components/fiche/AskBar.tsx` | Fiche parcelle | panneau question/réponse | `/parcels/{idu}/ask` |
| `frontend/src/components/fiche/constructibilite.tsx:419` | Fiche parcelle (onglet Faisabilité) | bouton « Expliquer ce calcul en clair » + AvisIA | `faisabiliteExplain()` |
| `frontend/src/components/copilote/*` (CopiloteEmbarque, CopiloteView, AccueilCopilote) | Copilote | conversation NL | `copiloteV2Ask()` → `/api/copilote-v2/ask` |

### À RETIRER — IA hors des deux surfaces

| `fichier:ligne` | Écran | Point d'entrée IA | Action |
|------------------|-------|-------------------|--------|
| `frontend/src/components/fiche/constructibilite.tsx:419-441` **via l'outil M22** | **Outil Faisabilité** (mode « par parcelle ») | `FaisabiliteTab` est PARTAGÉ fiche↔outil : dans l'outil il embarquait le bouton IA « Expliquer ce calcul » + AvisIA | **RETIRÉ** : prop `embedded` → le bloc IA ne s'affiche que dans la fiche (`!embedded`). Description M22 « explication IA » supprimée. |

**C'était le seul point d'entrée IA hors fiche/Copilote.** Tous les appels aux endpoints IA
(`askParcel`, `getExplain`, `faisabiliteExplain`, `copiloteV2Ask`) sont — vérifié par grep — dans
`fiche/` et `copilote/` uniquement ; aucun outil, aucune carte, aucun panneau n'appelle un endpoint IA.

### Cas limite conservé (décision signalée)

| `fichier:ligne` | Écran | Élément | Décision |
|------------------|-------|---------|----------|
| `frontend/src/components/panel/LeftPanel.tsx:459` | Accueil | tuile « Demander au Copilote » | **Conservée** : c'est un LANCEUR vers le Copilote (`setView('copilote')`), pas une surface IA en soi. La retirer rendrait le Copilote (surface autorisée) inatteignable depuis l'accueil. |

## F2 — Retrait (fait)

`FaisabiliteTab({ idu, embedded })` : le bloc IA (`data-faisa-explain`) est gardé par `!embedded`.
L'outil M22 (mode parcelle) passe `embedded` → plus de point d'entrée IA hors fiche. Endpoints back
(`/parcels/*/explain`, `/api/copilote-v2/*`, etc.) intacts. Tests : `Faisabilite.test.tsx` (fiche →
bouton présent ; embedded → aucun `data-faisa-explain`).

## F3 — Aucun écran vidé de son seul contenu utile

L'outil Faisabilité par parcelle garde la capacité constructible, le calcul tracé étape par étape et
la charge foncière — il ne perd que l'explication IA. Aucun écran ne tombe à vide ; rien à arbitrer.
