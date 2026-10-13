# LOT B — chaque passage testé (navigateur piloté)

Témoins : parcelle normale/bizone `97411000BZ1065` (Saint-Denis, Uh), parcelle `97415000AB0001` (Saint-Paul), **disparue** `97411000AE0013` (projets 237/241), commune Saint-Denis, run servi q_v18. Mode auth-off local.

## Résultats par catégorie (CASSÉ / FAUX / PERTE / RETOUR / LIEN)

| Passage testé | Catégorie | Résultat |
|---|---|---|
| Rail → 9 vues (Carte, Outils, Docs, Copilote, Radar, Projets, CRM, Admin, Sources) | CASSÉ | **OK** — toutes rendent (Docs « Mes documents », Copilote « BRIEF DU MATIN », Radar « Deux chemins », CRM « 184 parcelles suivies », Admin « TOUR DE CONTRÔLE · run q_v18 », Sources OK). 0 ErrorBoundary. |
| Deep-link `/socle/#idu={idu}` + rechargement réel | LIEN | **OK** — ouvre la fiche, URL réécrite `#f=1&idu=…` ; survit au reload. |
| Deep-link `/socle/#parcelle={idu}` (format des mails/notifs) | LIEN | **ÉCART N-1 🟠** — n'ouvre PAS la fiche (accueil nu). |
| Fiche parcelle DISPARUE (depuis projet / deep-link / recherche) | CASSÉ | **ÉCART N-2 🔴** — plante toute l'app (ErrorBoundary). |
| Liens externes fiche (Cadastre, Maps, Errial, KMZ) | LIEN | **OK** — coords/adresse/idu injectés, `_blank`, aucun `127.0.0.1`. KMZ sert 200. |
| Lien Pages Jaunes | LIEN | **ÉCART N-3 ⚪** — commune dupliquée dans la requête (fonctionne quand même). |
| Fiche → outil Faisabilité (raccourci) | PERTE/RETOUR | **OK** — hash `#f=1&m=programme&idu=…` : module + parcelle préchargée (pas de PERTE) ; bouton « ← Outils » ; fiche conservée (idu en store). |
| Omnibox : saisie `97415000AB0001` + Entrée | FAUX | **OK** — ouvre la bonne fiche (idu présent, BZ1065 remplacé). |
| Admin → « Ouvrir l'app cliente → » | RETOUR | **OK** — revient à l'app cliente, `#admin=1` effacé, rail restauré. |
| Radar / Admin deep-links (`#radar=1`, `#admin=1`) | LIEN | **OK** — survivent au clic/URL. |

## Limites du mode auth-off (documentées, pas des écarts)
- `GET /moi/prefs-carte` → 401 au chargement (2 erreurs console) : route exigeant un compte identifié ; front best-effort, carte OK (cf. ÉTAPE0 · ⚪ artefact).
- Liste **Projets** vide en auth-off (projets scoped au `compte_id`, nul ici). Le chemin « projet → parcelle disparue » atteint le MÊME crash N-2 (composant Fiche, indépendant du chemin d'entrée) — prouvé par deep-link.

## Écarts du Lot B
- **N-1 🟠** lien digest mail `#parcelle=` n'ouvre pas la fiche.
- **N-2 🔴** fiche d'une parcelle disparue plante l'app.
- **N-3 ⚪** Pages Jaunes : commune dupliquée.
(Détails et causes dans ECARTS.md.)
