# Maquettes des exports v2 — 05/09/2026

Quatre PDF rendus avec WeasyPrint 69 (le moteur de LABUSE), sur la parcelle 97415000BO0852 avec les valeurs corrigées par EXPORTS-1. Les fichiers `.html` + `maquette.css` sont les gabarits ; les `.pdf` sont ce que ça donne.

| Document | Pages | Fichier |
|---|---|---|
| Dossier (= Flash sans la section 9) | 10 | `maquette-dossier.pdf` |
| PDF — résumé sans financier | 3 | `maquette-pdf-resume.pdf` |
| Financier (page 1 = le formulaire dans l'app, puis le document) | 1 + 4 | `maquette-financier.pdf` |
| Apporteur | 3 | `maquette-apporteur.pdf` |

Les lignes marquées ◌ viennent de blocs pas encore branchés à l'export (propriétaire nominatif, destinations, DPU, PEB, loyers, zone piétonne, taxe d'aménagement, historique de propriété) : valeurs d'exemple, structure réelle.

## Les choix de forme

- **Une seule chose mémorable par document : le verdict.** Une phrase en tête de section, qui conclut. Vert quand la nouvelle est bonne, rouge quand elle ne l'est pas, gris quand c'est neutre. C'est ce qui manquait à tous les anciens exports : ils posaient des chiffres et laissaient le lecteur arbitrer.
- **La nature de chaque donnée, à chaque ligne** : sourcé (mint), estimé (gris), dérivé (gris, ƒ), projet (ambre). L'ambre n'apparaît que là où le client a saisi quelque chose — c'est la règle DA v3, enfin appliquée.
- **Aucun mauve** : plus aucune prose IA dans les exports.
- **Trois tuiles au plus**, jamais un chiffre seul en hero.
- **Pagination fluide** : les sections s'enchaînent, aucun titre orphelin, aucune page vide. Le Dossier passe de 9 pages aérées à 10 pages pleines avec trois fois plus d'information.
- **Rien en capitales, pas de code interne, pas de renvoi vers l'app.** Le Flash est autonome.
- Police : Inter (déjà celle de LABUSE), chiffres tabulaires ; identifiants en mono.

## Ce qui change, document par document

**Dossier** — 10 sections au lieu de 11 dispersées. Le bloc Potentiel unique (au sol / en hauteur / reconstruction) remplace les quatre verdicts contradictoires. Le zonage complet arrive (destinations, servitudes traduites, ER/EBC, DPU). La section 7 passe en piéton. La section 9 est un encart tant que le formulaire n'est pas rempli ; absente du Flash.

**PDF** — n'est plus l'écran imprimé. Trois pages tirées du Dossier, mêmes blocs, sans le financier.

**Financier** — le formulaire d'abord (six champs, tous pré-remplis avec la valeur du secteur, coût de construction désormais sourcé). Puis : verdict, hypothèses en ambre, programme repris du Dossier, bilan à rebours, **sensibilité au coût de construction**, **écart au prix demandé**, marché en regard, vigilance. Un seul prix de sortie.

**Apporteur** — 3 pages : la parcelle en un coup d'œil (pauvre en analyse, volontairement), puis les questions adaptées à ce terrain avec cases et lignes à remplir. Confidentiel en tête.

**Pré-dossier PC** — pas de maquette : ce sont des corrections sur un pack existant. Le CERFA suit le scénario (13406 maison individuelle / 13409 collectif) ; la notice PCMI4 gagne le PPR, le bruit, la servitude PM1 et l'ABF ; la fiche zonage gagne les destinations, la taxe d'aménagement, le délai d'instruction et les articles ; PCMI1 repère la parcelle par un cercle ; PCMI2 dessine les deux bâtiments avec les cotes ; la ligne PCMI8 ne se coupe plus sur deux pages.

## À valider par Vic

1. Le verdict en tête de section — trop direct, ou exactement ça ?
2. Le Dossier à 10 pages pleines — ou préfères-tu plus d'air et 14 pages ?
3. Les exemples du Financier (650 k€ demandés, 60 k€ de démolition) — ce sont des chiffres inventés pour montrer le mécanisme.
4. L'Apporteur : le ton des questions, et l'absence volontaire de tout chiffre d'analyse.
