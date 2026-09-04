# COMPTE-RENDU RETOURS-12 — `fix/retours-12`

Recette navigateur sur la base réelle (backend :8000 mode local, front `/socle/` buildé),
un commit par lot. Une ligne par travail : **fait** / **fait autrement** (pourquoi) / **pas fait** (motif).
Inventaires T1/T2/T5/T7/A1 joints dans ce dossier (`INVENTAIRE-*.md`).

Prérequis vérifiés : RETOURS-11 (11a `0eeee93f` + 11b/c/d `cf4d6052`) et DESTINATIONS-1
(`2ac9e39e`) sont mergés sur `main`. Run servi lu par pointeur (`runs.current()`), q_v12 non basculé.

---

## LOT T — transversal (commit 1)

- **T1 — recherche par référence courte `BW0917` — FAIT.** Grammaire UNIQUE dans `lib/format.ts`
  (`estSectionNumero` + `normSectionNumero` — casse, espaces, tirets, zéros de tête, LOI-3). Le champ
  partagé `ParcelInput` (≈ 12 outils : Étudier, Faisabilité, Risques, Solaire, Remonter le temps,
  Courrier, Diligence, Étude de zone, Densifier, Mon secteur…) reconnaît désormais la référence courte
  et **désambiguïse** : plusieurs communes → liste (commune + surface), l'utilisateur tranche ; la commune
  du contexte passe en tête. L'Omnibox du header alignée sur la même grammaire (plus de `remote[0]` au
  hasard : multi-communes → toast qui nomme les communes). Backend `/parcels/search` renvoie la surface
  pour la désambiguïsation. **Recette navigateur** : `BW0917` dans « Étudier un bien » → 2 candidates
  (Saint-Benoît 1 434 m² · Saint-Paul 8,17 ha) ; forme `BW 917` normalisée → même résultat. Tests
  `refCadastrale.test.ts` (3 formes × reconnaissance/normalisation). Inventaire complet : `INVENTAIRE-T1`.
  - *Réserve honnête* : `ScanPatrimoine` garde sa résolution propre (`resoudre()`, orientée propriétaire :
    nom/SIREN/IDU/adresse) — hors périmètre « référence parcelle », non rebranché. Les barres full-text
    (PLU annuaire, CRM, Sources, intra-fiche, admin Flux) restent du filtrage local, hors sujet T1.
- **T2 — SIREN/SIRET cliquable Pappers — FAIT.** Composant unique `shared/Siren.tsx` (SIREN 9 → lien
  `pappers.fr/entreprise/{siren}`, SIRET 14 affiché entier mais lié sur les 9 premiers, pas de lien si
  la valeur n'a pas 9/14 chiffres, `target=_blank rel=noopener`). Posé sur : fiche parcelle propriétaire
  PM (Fiche.tsx), historique propriétaire (×2), Scan patrimoine, Assemblage/Promoteurs (moteurs ×2),
  Veille promoteurs, drawer Permis (ModulePanel). Tests `Siren.test.tsx` (9/14/non-conforme/vide).
  Inventaire : `INVENTAIRE-T2`.
  - *Fait autrement* : le SIREN du **popup patrimoine** (ModulePanel `fiche` tuple `[string,string]`) et
    le badge **admin Programmes** (champ éditable) restent en texte — types/contexte non-JSX ; notés.
- **T3 — rail latéral fixe — FAIT (correctif, retest post-mandat).** Le shell fixe le rail par flexbox,
  mais le symptôme vu par Vic est réel sur **fenêtre de faible hauteur** : le rail restait fixe alors que
  son **contenu défilait en interne** et faisait sortir Admin/Sources de la vue (mesuré : `sourcesVisible:false`
  et `navScrolls:true` dès h ≤ 560 px). **Correctif** : la zone basse (Admin/Sources) sort du conteneur
  `overflow-y-auto` et s'épingle en bas du rail (`shrink-0`) ; l'oiseau reste en haut ; seul le bloc des
  catégories défile si nécessaire. Re-mesuré : Sources visible à h = 900 / 560 / 420. Capture
  `T3-rail-fenetre-basse`. (Livré en correctif Lot T, commit dédié — Lot T était déjà commité.)
- **T4 — en-têtes de tableau collants + opaques — FAIT.** Classe partagée `.thead-sticky` (fond opaque
  `--bg-3`, `z-20` — sous les overlays z-40, au-dessus des lignes). Appliquée à Densifier
  (`Renouvellement.tsx` — était sticky **sans z-index**, cause du chevauchement), Prospection solaire,
  et la table « 24 communes » (`blocB.tsx`, remontée z-10 → z-20). Admin (Courrier/Produit/Destinations)
  laissés non-sticky (tables courtes).
- **T5 — infobulles redondantes retirées — FAIT.** Pastilles de communes (MapView) : l'infobulle ne
  garde QUE le fait non affiché (nb de parcelles chaudes), plus de répétition du nom ni de
  « ouvrir la fiche » ; sans fait à ajouter → aucune infobulle. Lignes d'acquisitions (Communes) :
  « Ouvrir la parcelle {idu} » retirée (le lien est déjà sous la ligne — voir O11). Veille promoteurs :
  « Ouvrir la fiche parcelle » retirée. Inventaire : `INVENTAIRE-T5`.
- **T6 — contraste garanti au survol — FAIT.** Correctif AU COMPOSANT : `.chip` + variantes de teinte ;
  sur `.hover-fill:hover` la chip bascule en fond sombre plein (`--ink`) et reprend sa teinte via
  `--chip-fg` (contraste ≥ 4,5:1) — fin du bug racine `.hover-fill:hover * { color:--ink }` qui rendait
  le millésime `2024→2025` vert-sur-vert dans Acquisitions. Appliqué au badge millésime (Communes).
- **T7 — sortie du prisme « opération » — FAIT (règle transversale + libellés de 1er niveau).**
  Les verdicts d'opération de premier niveau ne se présentent plus comme des faits sur la parcelle :
  « L'opération ne finance pas ce foncier » → « à ces hypothèses, une opération de ce type ne dégage rien
  pour le terrain — c'est le résultat d'un scénario, pas la valeur de la parcelle » (EtudierBien) ;
  idem Assemblage M16 (moteurs) et restitution Copilote (strings). Français d'abord : « CA visé » →
  « Chiffre d'affaires visé (CA) ». Bannière « Étudier un bien » rendue descriptive/neutre. Tests
  existants mis à jour (Assemblage, etat1 Copilote) vers le nouveau libellé. Inventaire : `INVENTAIRE-T7`.
  - *Report assumé* : la **refonte structurelle deux niveaux** de l'accueil (descriptif d'abord, bilan
    d'opération derrière un geste explicite) relève d'**O2** (Faisabilité) et sera livrée dans le Lot O bloc 2.

**Vérifs Lot T** : tsc 0 · build OK · suite frontend 160/160 (dont 8 nouveaux tests) · backend
`/parcels/search` validé sur base réelle · 0 erreur page à la recette · golden intact (0 fichier scoring touché).

---

## LOT C — carte & couches (commit 2) — À FAIRE
## LOT O bloc 2 — outils O1-O7 (commit 3) — À FAIRE
## LOT O bloc 3 — outils O8-O13 (commit 4) — À FAIRE
## LOT J — Projets (commit 5) — À FAIRE
## LOT A — IA + compte-rendu final (commit 6) — À FAIRE
