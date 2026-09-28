# Le format de déclaration — RACCORDEMENT-1, lot 0 (FIGÉ)

> **Ce dossier n'est pas du code.** C'est la liste, surface par surface, de ce que chaque
> écran de l'app a le droit d'afficher. Une case à l'écran = une ligne ici. On le lit sans
> ouvrir un seul fichier Python.

## L'image

Le **registre** (`src/labuse/registre/donnees.py`) est **le compteur** : chaque donnée y est
définie une fois, avec sa source, son unité, sa définition. **On ne le touche pas.**

Une **déclaration** est **un câble** : elle relie une case d'un écran à une ligne du registre.
Chaque surface spécifique a **un fichier** dans ce dossier. Une case qui n'est nommée par
aucune déclaration ne s'affiche pas (verrou G8, lot 6).

## Deux régimes

- **Surfaces génériques** — le Copilote, la page Sources, le manifeste de la fiche, la fiche
  commune. Elles consomment **tout** ce que le registre offre, d'office. **Aucun fichier par
  surface** : elles sont listées, une ligne chacune, dans `generiques.yaml`. Un seul câble, gros.

- **Surfaces spécifiques** — les tuiles et sections de la fiche parcelle, les outils, les
  couches, le Radar, les 5 documents, le score, la cascade. **Un fichier chacune**, ici, sous
  le dossier de sa catégorie (`fiche/`, `outils/`, `couches/`, `radar/`, `documents/`,
  `score/`, `cascade/`).

## Un fichier de surface

```yaml
# ── En-tête : ce qu'est la surface ──
surface:   fiche_entete_tuiles      # identifiant unique (= l'id du robinet quand il existe)
nom:       "En-tête de la fiche — les six tuiles"
categorie: fiche                    # fiche · outil · couche · radar · document · score · cascade
parent:    fiche_parcelle           # la surface qui la contient, ou null
route:     "/parcels/{idu}"         # d'où la donnée arrive (endpoint API, builder PDF, tuiles MVT)
rendu:     tuiles                   # tuiles · sections · carte · pdf · texte

# ── Les données servies, DANS L'ORDRE D'AFFICHAGE ──
donnees:
  - quoi:  surface_parcelle_m2      # ← l'identifiant du REGISTRE (clé de DONNEES). Rouge s'il n'existe pas.
    ou:
      rang:    10                   # ordre dans la surface — NUMÉROTÉ DE 10 EN 10 (insérer sans renuméroter)
      etat:    en_tete              # en_tete · replie · sur_demande
      section: "En-tête"           # le sous-groupe visible (facultatif)
    comment:                        # L'AFFICHAGE. Chaque champ est FACULTATIF : omis → hérité du registre.
      libelle: "Surface"            # le libellé montré (≠ libellé du registre si la surface renomme)
      unite:   "m²"
      format:  entier_m2            # entier · entier_m2 · pourcent · euro · euro_m2 · degre · classe · texte · liste · date · verdict
      i:       "Contenance cadastrale de la parcelle (DGFiP)."   # le contenu de la bulle « i »
    absence: "Surface : contenance cadastrale non disponible pour cette parcelle."
    absence_type: absente_ici       # absente_ici · non_publiee · non_ingeree (voir plus bas)
    pourquoi: "Première mesure du bien ; toujours en tête, jamais repliée."
```

### Les six choses que dit chaque ligne (mandat lot 0 + ajustement Vic)

| champ          | ce qu'il dit                                                             | obligatoire |
|----------------|--------------------------------------------------------------------------|-------------|
| `quoi`         | l'identifiant du registre (`DONNEES[...]`)                               | **oui**     |
| `ou`           | section, rang (de 10 en 10), et l'état : `en_tete` / `replie` / `sur_demande` | **oui** |
| `comment`      | libellé affiché, le `i`, l'unité, le format — omis = hérité du registre  | non¹        |
| `absence`      | ce que la surface dit quand la donnée n'existe pas pour cette parcelle   | **oui**     |
| `absence_type` | la **cause** de l'absence — elle change la phrase pour le client         | **oui**     |
| `pourquoi`     | une ligne : pourquoi elle est là, à ce rang, dans cet état              | **oui**     |

¹ `comment` peut être omis entièrement : la surface affiche alors le libellé et l'unité du
registre. On ne le remplit que pour **renommer**, poser un `i` propre à l'écran, ou forcer un
format. **Aucune duplication imposée** — c'est ce qui garde les fichiers courts et le registre
seule source de vérité.

### `absence` — le VOCABULAIRE est fermé (COHERENCE-FIX-1 lot D)

Toute phrase d'absence appartient à l'une des **cinq formes** du registre
(`src/labuse/registre/absences.py`) : `non_disponible` · `aucun` · `hors_perimetre` ·
`sans_objet` · `non_calculable`. Une phrase libre qui n'entre dans aucune forme **casse le
verrou V6b** — on la reformule dans le vocabulaire, on n'invente pas une sixième forme.
(À l'écran, un chiffre absent se rend « — » — format.ts ; « n.c. » est réservé à la
sentinelle SIRENE 1900.)

### `absence_type` — la cause de l'absence (ajustement Vic)

Le client n'entend pas la même phrase selon **pourquoi** la donnée manque. Trois causes :

| valeur         | ce que ça veut dire                                                        | ton client |
|----------------|----------------------------------------------------------------------------|------------|
| `absente_ici`  | la source publie, mais la parcelle/le bien n'a pas la donnée (pas de bâti…) | factuel : « rien ici » |
| `non_publiee`  | le producteur ne publie pas (commune/périmètre/échelle non couverts)       | « non publié par X » |
| `non_ingeree`  | la source publie, LABUSE ne l'a pas encore ingérée ici (dette **interne**) | **neutre** — ne dit JAMAIS « non ingéré » au client |

> Vic en demandait deux (`absente_ici` / `non_publiee`). J'ajoute `non_ingeree` : des cas réels
> l'imposent (la tuile « Taxe foncière » dit aujourd'hui « taux non ingéré » — le REI *publie*,
> c'est notre dette, pas un trou du producteur). La phrase client d'un `non_ingeree` reste neutre
> et n'expose jamais notre retard ; la valeur sert aussi à l'onglet Câblage à compter notre dette.

### Les états de `ou.etat`

- `en_tete` — visible d'emblée, en haut de la surface.
- `replie` — dans un accordéon fermé ; un clic l'ouvre (la donnée est déjà chargée).
- `sur_demande` — chargée seulement au clic (appel séparé) ; pour le lourd/rare.

> Une surface complète n'est pas une surface où tout est visible en même temps — c'est une
> surface où tout est **atteignable** et **rien n'est perdu**.

## Ce que le format garantit (et que le verrou G8 vérifie, lot 6)

1. **Une surface n'affiche que ce que sa déclaration nomme.** Rien hors registre.
2. **Toute donnée qui a une valeur sur la parcelle est consommée par ≥ 1 surface visible.**
   Sinon elle apparaît **rouge** dans l'onglet Câblage (lot 6) : une donnée sans câble.
3. **Une surface générique consomme tout** — elle n'a pas à énumérer.

## Une source nouvelle se branche en une ligne

Quand une source arrive au registre, elle apparaît d'office sur les génériques (Copilote,
Sources). Pour qu'un client la voie sur un écran précis, on ajoute **une ligne** au fichier de
cette surface : `quoi`, `ou`, `absence`, `pourquoi`. Rien d'autre. C'est le but du mandat.

## Le loader

`src/labuse/registre/declarations.py` lit ces fichiers, vérifie que chaque `quoi` existe au
registre et que les champs obligatoires sont là, et **dérive** l'onglet Câblage (par donnée :
qui la consomme ; par surface : ce qu'elle prend, et en gris ce qu'elle pourrait prendre).
Jamais saisi deux fois : le graphe vient des fichiers.

## Production vs échantillons

`declarations/_exemples/` contient les deux **échantillons** de validation du format (lot 0) —
ils prouvent le format mais **ne sont pas des câbles** : l'assembleur `?raccorde=1` et l'onglet
Câblage lisent la **production** seule (`declarations/{fiche,outils,couches,…}/`). Au lot 1 la
production est vide → la fiche `?raccorde=1` est vide (la preuve de la coupe). Au lot 2 les
déclarations de production sont écrites, et chaque fichier fait réapparaître sa surface.

---
**FIGÉ le 2026-09-14 (lot 0). Validé sur deux surfaces : `_exemples/fiche/entete_tuiles.yaml` (une
tuile de fiche) et `_exemples/outils/taxe_amenagement.yaml` (un outil).**
