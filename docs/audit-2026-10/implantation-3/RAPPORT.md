# IMPLANTATION-3 — Rapport

Le document **« Étude de faisabilité »** (PDF, 8 pages) devient **l'export figé de l'outil**
d'[IMPLANTATION-2](../implantation-2/RAPPORT.md) : il lit la **même réponse que l'écran**
(`POST /modules/etude`), jamais un second calcul. En parallèle, le **Dossier** (et donc le Flash)
**cesse de dupliquer la capacité** : le nombre de logements vit désormais dans l'Étude.

> Nature du document : pré-faisabilité automatisée. Ni étude d'architecte, ni preuve de conformité,
> ni dossier de permis. Le mot « conforme » **n'apparaît jamais** (vérifié). Toutes les hypothèses
> sont « Estimé ».

Branche `feat/implantation-3` depuis `main` `ea71e5db` (après merge d'IMPLANTATION-2).
Worktree `~/Desktop/labuse-implant3`, ports 8851 / 6051. **2 commits, pas de merge, pas de run, rien en prod.**

- **Étape 0** — `pwd` = worktree, branche `feat/implantation-3`, arbre propre, IMPLANTATION-2 présent
  dans `main` (`9e508d7b`…`ea71e5db`). ✅
- Commits : `fe7a78a0` (LOT A) · `d4466ddf` (LOT B).

---

## LOT A — le PDF « Étude de faisabilité »

### Un document, pas un second calcul
`src/labuse/exports/etude_faisabilite.py` (nouveau). **Fonction pure du payload** : `rendu_etude(payload,
genere_le, scenario_ref)` → `{html, numero, retenu_ref}`. Il n'interroge rien, ne recalcule rien — il
met en page la réponse de `implantation.service.etudier_payload` (celle que l'écran affiche). **Même
builder, même thème** que les 7 autres documents : `exports.rendu.page_html` + `theme.css` + WeasyPrint
(`render_pdf`), avec un `<style>` scopé pour les seules formes propres à l'Étude (deux statuts, pastilles
de contrôle 4 états, citations) — aucun jeton couleur nouveau (réutilise les variables de `theme.css`).

**8 pages** (maquette v3, partie 2) + annexe :
1. **Synthèse** — fourchette (scénarios *Exploitable* seulement), tableau des scénarios (retenu
   surligné), **deux statuts** (contrôles automatisés · statut de l'étude), 6 tuiles, avertissement.
2. **Terrain** — plan de situation **rendu depuis la géométrie servie** (SVG projeté du GeoJSON),
   parcelles + contenance, pente LiDAR, limites, accès.
3. **Règles et contraintes** — chaque règle **citée** (article · page PDF) ; contraintes cartographiées
   (ligne absente si la contrainte ne touche pas le terrain). Jamais « conforme ».
4. **Enveloppe** — zone d'implantation (SVG) + surfaces (plafond d'emprise lu du contrôle, jamais
   recalculé).
5. **Plan masse du scénario retenu** — SVG depuis la géométrie (bâti, places, allées, accès, espaces
   libres, voie) ; « chaque nombre = nombre d'objets dans la géométrie ».
6. **Distribution et coupe** — répartition par niveau (T2/T3/T4, SDP) + coupe schématique (TN LiDAR,
   règle de hauteur).
7. **Capacité et contrôles 4 états** — programme + tableau des contrôles (Réussi · Échoué · Non effectué ·
   Non applicable), citation au Réussi.
8. **Hypothèses, limites, sources** — hypothèses « Estimé », points à confirmer, sources + **version du
   moteur et des règles** ; mention d'archivage.
   **Annexe** — les autres scénarios (un plan masse par scénario).

### Le verrou « toute ligne du PDF est une ligne de l'outil » (extension V5d/V5f)
`nombres_hors_payload(payload, html)` : **chaque nombre imprimé** (hors SVG — un dessin — et hors jetons
de structure : pagination, n° de document, date, code EPSG, réf. cadastrale) **doit être servi par le
payload**. Les ancres sont construites en parcourant le payload (chaque nombre sous sa forme **exacte et
arrondie** — le document arrondit les m² comme l'écran — et les nombres **nichés dans les chaînes** de
contrôle/règle : les contrôles portent « ≤ 1 222 m² (70 % …) », « R+2 ≈ 9 m »…). **0 fuite** exigée.

> Conséquence concrète : le PDF ne peut imprimer QUE des nombres que le moteur a produits (resume,
> contrôles, terrain, règles, hypothèses). Un plafond d'emprise, une marge, une distance sont **lus
> dans le payload**, jamais recalculés côté PDF.

### Deux portes, un document
`POST /modules/etude/pdf` (`src/labuse/api/modules.py`, `EtudePdfIn = EtudeIn + scenario_ref`) :
**un seul calcul** (`etudier_payload`) puis rendu — jamais un second calcul.
- **Tuile de l'outil** « Étude de faisabilité (PDF) » (`M22Programme.tsx`) : exporte le **scénario
  affiché** (`scenario_ref` = onglet actif) **avec sa configuration** (objectif, programme, hypothèses
  surchargées).
- **9e carte Docs** « Étude de faisabilité » (`catalogue.ts` + `DocumentsView.tsx`) : **parcelle →
  Générer** produit la **configuration par défaut** (collectif, équilibre).
- Front : `useOuvrirDocument` accepte un `init` (POST + blob, erreurs FR) — mêmes gestes que les 7 autres
  documents ; biblio « Mes documents » liste et régénère l'Étude (POST de la recette archivée).

### Archive — le PDF se rejoue à l'identique
La route archive la **recette** dans `documents_generes` (jamais le PDF), **côté serveur** (elle a le
payload calculé → versions exactes) : `config` (entrées + hypothèses + `scenario_ref`), **version du
moteur et des règles**, et l'**instantané des millésimes**. Le n° de document (`EF-AAAAMMJJ-XXXX`) est
**déterministe** par assiette+date. Les deux portes archivent à l'identique.

### Preuves LOT A
`tests/test_implantation3_pdf.py` — **13 tests `reel` verts** sur les 3 témoins
(L'Étang-Salé, Saint-André, Saint-Denis) : **verrou 0 fuite**, 8 sections présentes, **jamais
« conforme »**, n° déterministe, le PDF **imprime les chiffres du scénario retenu** (réciproque), la
route sert un `application/pdf`. Voir `PROOFS-pdf.md` (0 écart HTML *et* pdftotext, 3 communes) et les
PDF `pdf/etude-*.pdf` + captures `captures/*-p1/p5`.

---

## LOT B — le Dossier (et donc le Flash)

### §Potentiel : plus de doublon de capacité
`src/labuse/exports/miroir.py` (rendu LIVE du Dossier/Flash). La ligne **« Capacité (logements) : N »**
(qui, au départ, imprimait le drapeau booléen « 1 » ; corrigée en fourchette par A-05-1, mais **tirée de
l'ancien moteur de faisabilité**) devient un **renvoi** :

> **Nombre de logements** · voir l'Étude de faisabilité

**Aucun nombre** de logements n'est plus imprimé depuis l'ancien moteur. La **partie réglementaire**
(SDP résiduelle, marge de surélévation) **reste inchangée** (extracteurs `sdp_residuelle_m2` /
`marge_surelevation_m` non touchés). Changement **chirurgical** : seul le rendu de `capacite_logements`
est intercepté ; collecte, nature et sources du §12 inchangées.

**Avant / après** sur 5 parcelles (`dossier-avant-apres.md`) :
`Capacité (logements) 4–6 logements` → `Nombre de logements · voir l'Étude de faisabilité`.

### Le Flash suit (même document)
Le Flash **EST** le Dossier (alias `builder` : `flash` → `dossier`). Vérifié sur les 5 parcelles : le
Flash porte le **même renvoi**, automatiquement.

### ⚠ STOP — deux AUTRES exports impriment encore un nombre de logements de l'ancien moteur
Conformément au mandat (« s'il y en a, le lister et STOP sur ce point »), **aucune correction** n'y est
apportée — chacun est un document propre dont la décision revient à Vic :

| Export | Où | Source | Note |
|---|---|---|---|
| **Bilan** (Financier) | « Le programme → Logements » (`exports/builder.py:239-244`, `blocs/financier.py:177`) | `_fourchette_logements` (ancien moteur), **en repli** | la saisie du porteur `logements_vises_saisi` est **prioritaire** ; c'est le programme de l'opération, pas le § capacité |
| **Comparatif** | colonne « Logements possibles » (`app.py:8081-8082` → `blocs/comparatif.py:27`) | `fourchette.logements_au_sol` (ancien moteur) | fourchette côte à côte des parcelles comparées |

### Le scoring n'est pas touché (ce qu'il lit de l'ancien moteur)
- **Scoreur** (`api/scoreur.py`) : lit `parcel_faisabilite` **uniquement** pour la **SDP / SHAB
  vendable / surface / prix de sortie** (`shab_vendable_m2`, `sdp_plancher_m2`, `terrain_m2`,
  `prix_sortie_median`). Il **ne sert JAMAIS un nombre de logements**. Rien changé.
- **Copilote** : **ne lit pas** la capacité (seulement `faisabilite.zonage` et `marche_commune`) —
  confirmé (déjà vérifié en IMPLANTATION-2).

### Preuves LOT B
`tests/test_a05_1_capacite_pdf_fiche.py` réécrit — **2 témoins `reel` verts** : le Dossier imprime le
renvoi, **aucun nombre** de logements à cette ligne, **plus de libellé « Capacité (logements) »**. Les
tests unitaires touchant `capacite_logements` (Apporteur, nature, déclarations) restent verts
(le §Potentiel du Dossier était le seul rendu concerné).

---

## Preuves (synthèse)

- **Backend** : `test_implantation3_pdf.py` **13 `reel`** + `test_a05_1` **2 `reel`** verts
  (base applicative réelle, run servi). Le moteur historique n'est pas touché (`etudier`/`etudier_multi`
  inchangés) → les 99 tests `reel` d'IMPLANTATION-1/2 restent valides.
- **Front** : `tsc` **0**, **vitest 259/259**.
- **PDF** : 3 PDF générés (`pdf/etude-{etang-sale,saint-andre,saint-denis}.pdf`) ; `PROOFS-pdf.md`
  = **0 écart** (HTML et pdftotext), chiffres du retenu imprimés, « conforme » absent.
- **Dossier** : `dossier-avant-apres.md` (5 parcelles) + Flash vérifié.
- **Captures** : `captures/*-p1.png` (synthèse) et `*-p5.png` (plan masse rendu depuis la géométrie).

### Résultats servis (témoins, objectif « équilibre »)
| Commune | Zone | Scénario retenu | Logts | Places | SDP |
|---|---|---|--:|--:|--:|
| L'Étang-Salé | UA | A (deux barres, R+3) | 28 | 34 | 1 800 m² |
| Saint-André | UC | A (R+2) | 27 | 40 | 1 695 m² |
| Saint-Denis | Ui | A (R+2) | 12 | 12 | 795 m² |

---

## Reproduire

```bash
# base réelle (lecture seule), venv du dépôt principal, /src du worktree
export PGHOST=/tmp PYTHONPATH=src PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj
export LABUSE_APP_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse

# tests dédiés (marqués reel ; test_a05_1 aussi local)
<python> -m pytest tests/test_implantation3_pdf.py tests/test_a05_1_capacite_pdf_fiche.py -q

# front
cd frontend && npx tsc -b && npx vitest run
```

API en dev : `uvicorn labuse.api.app:app --port 8851` ; front : `LABUSE_API_DEV=http://127.0.0.1:8851
npm run dev -- --port 6051`. L'outil « Étude de faisabilité » (groupe Instruire) porte la tuile
« Étude de faisabilité (PDF) » ; la 9e carte de la page Documents génère la configuration par défaut.
