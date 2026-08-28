# RECETTE-2 — captures (vérif des 7 correctifs)

Prises sur le stack dev réel (uvicorn nouveau backend + vite, base dev). Les captures « clip » et
« 390 » sont les plus lisibles ; les « 1440 » donnent le contexte plein écran.

| Capture | Lot | Ce qui est vérifié |
|---|---|---|
| `01b-filtres-survol-bulle-clip` | **A** | Section « 1 · Communes » = codes postaux SEULS ; survol de 97413 → bulle **« Cilaos »** (nom de commune seul, pas de CP répété). |
| `01-filtres-communes-cp-1440` | A | La liste des communes en CP (plein écran). |
| `22-veille-criteres-sans-actions-390` | **A + B** | Volet Critères de la Veille : les Communes y sont AUSSI en CP seuls (sélecteur partagé) ; et **aucun** bouton « Voir les parcelles » / « Demander à LABUSE » (bloc révélation retiré en Veille). |
| `21-parcelles-suivies-inversees-390` | **E** | « Parcelles suivies · 6/50 » : l'**IDU** (AB 0004, BV 0120…) est le TITRE, la **commune** (Saint-Paul, Saint-Benoît…) en secondaire discret. |
| `23-zone-notaire-resout-390` | **C4** | Champ activité : « notaire » propose **« Activités juridiques »** (6910Z) — la nomenclature complète, pas les seuls commerces. |
| `07-zone-familles-parcourir-1440` | C4 | Le déroulé **parcourable par famille** d'activité (21 sections). |
| `24-zone-sans-pdf-libelles-390` | **C1 + C2 + C3** | Panneau Étude de zone : **pas de bouton « Exporter le PDF »** (seul « Nouvelle étude ») ; « **non couvert · le registre des établissements n'est pas encore servi sur LABUSE** » et « actifs · pas encore servi sur LABUSE » (plus de jargon SIRENE/MOBPRO/ingéré) ; note de pied **sans** SIRENE ni MOBPRO (non servies). |
| `25-ia-sans-brief-390` | **D1** | Section IA / Copilote **sans** la carte « Votre brief du matin ». |
| `26-notifications-sans-point-du-jour-390` | **D2** | En-tête Notifications = « préférences » seul, **sans** « Le point du jour ». |

Note (LOT E) : l'IDU est rendu via `iduCourt` (forme courte lisible « AB 0004 ») ; le style de chaque
position est conservé (titre / secondaire), seuls les contenus sont échangés.
