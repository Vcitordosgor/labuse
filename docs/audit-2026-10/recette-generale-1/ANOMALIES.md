# ANOMALIES — Recette générale 1 (16/10/2026)

Format par anomalie : **[GRAVITÉ]** titre — Où / Reproduire / Capture / Cause probable (fichier:ligne).
Gravité : **bloquant** (empêche usage/plante) · **gênant** (dégrade sans bloquer) · **cosmétique** (visuel mineur).


---

## Famille 1 — Carte

Bilan : **aucune anomalie bloquante ni gênante.** 3 points cosmétiques/informatifs ci-dessous.
0 erreur console JS, 0 réponse HTTP 4xx/5xx sur l'ensemble de la famille.

### A-01-1 — Recherche : pas de message « aucun résultat » dans le dropdown live
- **Gravité** : cosmétique
- **Où** : barre de recherche globale (header) · `http://localhost:5998/socle/`
- **Reproduire** :
  1. Charger la carte.
  2. Taper « zzzqwerty » dans la barre « Rechercher : IDU, SIREN, propriétaire, adresse… » SANS
     presser Entrée.
- **Observé** : le dropdown n'affiche que les communes-raccourcis fixes (Saint-Denis, Saint-Paul,
  La Possession, Sainte-Marie, Trois-Bassins) et aucun message « aucun résultat ». Le message
  honnête « Aucun résultat (IDU, SIREN, propriétaire ou adresse) pour « zzzqwerty » » n'apparaît
  qu'à la **validation (Entrée)**, sous forme de toast. Un utilisateur qui ne presse pas Entrée
  peut croire que la recherche est muette, ou confondre les communes-raccourcis avec des résultats.
- **Capture** : captures/01-carte/003_search-absurde.png · 004_search-absurde-enter.png
- **Cause probable** : `frontend/src/components/header/Header.tsx:185` — le `setToast('Aucun
  résultat …')` est déclenché au submit (ligne ~156/185), pas sur le dropdown d'autocomplétion
  live, qui n'a pas d'état vide explicite.

### A-01-2 — Compteur « total foncier » : 433 229 vs 432 350 (écart 879)
- **Gravité** : cosmétique
- **Où** : panneau FILTRES, bouton « Voir les N parcelles » · carte
- **Reproduire** :
  1. Charger la carte, ouvrir FILTRES (aucun filtre).
  2. Observer le nombre dans « Voir les N parcelles » au chargement puis après stabilisation.
- **Observé** : la valeur affichée oscille entre **433 229** (cible d'animation / fallback, issue de
  `/accueil/chiffres`.parcelles = parc vivant) et **432 350** (compte SQL live `/filtre?limit=0` =
  base scorée du run q_v18). Écart de 879 parcelles. Les deux chiffres sont légitimes (parc total
  vs périmètre du run servi), mais le chiffre « d'accroche » vu en premier est ~879 plus haut que
  le nombre réellement filtrable. Aucun chiffre faux n'est servi.
- **Capture** : captures/01-carte/001_filtres-panneau-ouvert.png
- **Cause probable** : `frontend/src/components/panel/FiltreLabuse.tsx:632-645` — `totalIle`
  (getAccueilChiffres = 433 229) sert de cible/fallback tandis que `getFiltreCount` (432 350) est
  le live ; vérifié côté API (`/accueil/chiffres`=433229, `/filtre?limit=0`=432350, tous deux
  déterministes).

### A-01-3 — Mobile : app entièrement bloquée (écran-barrage « disponible sur ordinateur »)
- **Gravité** : cosmétique (comportement VOLONTAIRE, pas un défaut — consigné pour traçabilité)
- **Où** : tout viewport mobile (390px) · `http://localhost:5998/socle/`
- **Reproduire** :
  1. Ouvrir en mobile (`ouvrir({mobile:true})`) ou réduire la fenêtre sous le seuil mobile.
  2. Naviguer vers `` ou même un deep-link `#idu=97401000AC0428`.
- **Observé** : un écran unique « LABUSE est disponible sur ordinateur. Ouvrez app.labuse.immo
  depuis votre ordinateur. [Contact] » s'affiche à la place de la carte ; AUCUN panneau
  (COUCHES/FILTRES), recherche, zoom ou bouton n'est monté, même via deep-link. L'écran est
  propre : 0 débordement horizontal (`debordements` = 0), 0 erreur, centré correctement.
- **Capture** : captures/01-carte/001_mobile-chargement-initial.png · 002_mobile-deeplink-idu.png
- **Cause probable** : décision produit assumée — `frontend/src/main.tsx:75-79` : si
  `estAppareilMobile()` alors seul `EcranOrdinateur` (`components/EcranOrdinateur.tsx`) est monté
  (« CHARGEMENT-1 point 6 : téléphone/tablette, l'app NE s'ouvre PAS »). → Les contrôles mobiles
  demandés (panneaux utilisables, texte coupé) sont donc sans objet sur cette famille.
