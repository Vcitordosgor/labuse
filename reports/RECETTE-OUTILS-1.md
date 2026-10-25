# RECETTE-OUTILS-1 — rapport

Branche `fix/recette-outils-1` depuis `origin/main` (`4e7504f6`). Worktree `~/Desktop/labuse-recette-outils`, API `:8820`, Vite `:6020` (servi sous `/socle/`, auth désactivée en local, proxy dev → API). Base de données `labuse` locale (lecture seule sur la donnée servie). Captures Chrome système, `reports/RECETTE-OUTILS-1/captures/<n>-avant.png` / `<n>-apres.png`.

**Légende statut** : FAIT · NON FAIT (raison) · ARBITRAGE (décision prise seul, notée).

## État initial de `main`

- Stack montée : API `:8820` saine (`/healthz` 200), Vite `:6020` OK, proxy dev → API OK.
- Données : `parcels` 431 236 lignes. Endpoints testés OK (`/parcels/search`, `/moteurs/assemblage`). L'assemblage AD0213/0214/0215 renvoie exactement les chiffres du mandat.
- Tests ciblés `main` : _(à renseigner)_

---

## T — règles transversales

| Règle | Outils touchés | Statut | Captures |
|---|---|---|---|
| T1 — changer d'outil vide tout | | | |
| T2 — chaque outil lit les données servies | | | |
| T3 — un seul « Retour » | | | |
| T4 — clic carte = adresse dans la barre | | | |
| T5 — fin du « Réinitialiser » en haut | | | |
| T6 — export PDF = document Docs | | | |
| T7 — un seul format « Voir plus » | | | |

### Tableau T2 — outil → source lue → correctif

_(à renseigner)_

---

## Points 1 → 52

### PLU
- **1** — single Retour :
- **2** — placeholder :
- **3** — retirer phrase :
- **4** — retirer onglet « Par parcelle » :
- **5** — audit « Simuler l'ouverture » + verdict chemin Procédure :

### Permis
- **6** — fiche unique en bulle carte :
- **7** — clic liste = même bulle + surlignage :

### Communes
- **8** — Fiche en overlay :
- **9** — T2 sources :
- **10** — retirer encart Méthode :
- **11** — Radar colonnes/zéros/agrégat/noms :

### Scan patrimoine
- **12** — défilement liste + accordéon 4 chiffres :
- **13** — « Retour » fonctionne :
- **14** — opérations en accordéons + 2 Boutons charte :

### Assemblage
- **15** — vérif calculs + accordéon Bilan :
- **16** — Bouton charte Étude faisabilité :

### Comparer
- **17** — bloc EntreeParcelle + puces :
- **18** — retirer phrase :
- **19** — retirer « Retour à la carte » / « Tout vider » :
- **20** — tableau plus beau :
- **21** — Exporter en PDF = Docs :
- **22** — retirer mention bas de tableau :
- **23** — retirer persistance 15 min :

### Remonter le temps
- **24** — retirer encart Zones noires :
- **25** — parcelle ouvre sa fiche :

### Étude de zone
- **26** — retirer section 3 Activité :
- **27** — marges chevrons accordéons :
- **28** — vérif rayons 0,5/1/2/5 km :
- **29** — Exporter en PDF :
- **30** — accordéons fermés par défaut :

### Gabarit réglementaire
- **31** — vérif calculs + contradiction risques :
- **32** — 3D centrée sur la parcelle :
- **33** — 3D orientable + « Vue par défaut » :
- **34** — Docs Gabarit = outil + Exporter en PDF :

### Taxe d'aménagement
- **35** — libellé titre :
- **36** — vérif barèmes 2026 + abattements/exonérations :

### Prospection solaire
- **37** — single Retour + pied T7 Piscines :
- **38** — Ensoleillement ouvre la fiche + Retour :

### Blocs fonciers
- **39** — filtres directs puis repliés :
- **40** — retirer texte :
- **41** — listing variante B « Cartes » :
- **42** — petit bouton Scan patrimoine :

### Successions à venir
- **43** — troncature/superposition :
- **44** — retirer fin de phrase :

### Courrier
- **45** — retirer ligne envoi postal :
- **46** — corrections texte courrier :
- **47** — retirer encart « Vos demandes » :
- **48** — Bouton charte + Retour :

### Docs
- **49** — retirer phrase d'intro :
- **50** — retirer carte Comparables DVF + « huit » :
- **51** — docs = données servies + parité outil :

### Copilote
- **52** — grille d'exemples homogène :

---

## Vu, non fait

_(à renseigner)_
