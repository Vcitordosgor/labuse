# CHARTE DA — LABUSE (v1, validée par Vic le 23/09/2026)

Référentiel unique pour l'audit DA-AUDIT-1 et les correctifs DA-FIX-n.
**[A]** = déjà tranché par Vic (RETOURS-11→19, RECETTE-1/2/6) — rappel, pas de débat.
**[?]** = règle nouvelle, validée le 23/09/2026 — même valeur que [A] désormais.

Règle générale : chaque règle vit dans UN composant partagé (`primitives.tsx` + grammaire CSS), jamais réécrite écran par écran.

---

## 1. Couleurs d'état

- [A] **Actif = vert opaque**, contenu inversé sombre (fond de carte, « Toute l'île », « ← Outils » menu ouvert, chevrons, onglet courant, filtre coché).
- [A] **Survol = opaque de sa propre couleur**, contenu inversé sombre (contour vert → vert opaque, contour ambre → ambre opaque, surfaces IA restent mauves ; icône : fond vert, glyphe sombre).
- [A] Sur une barre survolée, le chevron n'a pas de fond propre ; hors survol son contour reste visible.
- [A] Deux actions sur une ligne = deux zones dissociées au survol, jamais un aplat continu.
- [A] Pas de bleu, sauf SIREN/SIRET souligné. Liens secondaires « voir la fiche → » = jaune permanent.
- [?] **Désactivé = 40 % d'opacité**, pas de survol, curseur not-allowed. Une seule valeur d'opacité dans toute l'app.
- [?] **Focus clavier** = même rendu que le survol (pas d'anneau bleu navigateur).

## 2. Boutons — trois niveaux, pas plus

- [?] **Primaire** (fond vert opaque, texte sombre) : UNE action principale par écran, max.
- [?] **Secondaire** (contour vert, fond transparent, survol → vert opaque) : toutes les autres actions.
- [?] **Lien texte** (souligné, sans contour) : navigation ou action mineure (« annuler », « voir plus »). Jamais pour une action qui modifie des données.
- [?] Un mot cliquable sans soulignement ni contour est INTERDIT — c'est un bouton secondaire ou un lien.
- [?] Même hauteur (32 px), même rayon, même padding, même police pour les trois niveaux. Icône seule = carré de 32.
- [?] **Trois rayons dans toute l'app, pas un de plus** : 4 px pour ce qui fait moins de 20 px (cases, chevrons, pastilles de compte) · 6 px pour tout le reste (boutons, champs, lignes, cartes, tuiles, panneaux, tiroirs) · pilule (999 px) pour les chips de filtre, les badges et les barres de défilement. Tout contrôle interactif fait 32 px de haut (bouton, chip, champ court) ; l'omnibox seule fait 40.
- [A] Aucun bouton CSV, aucun point d'entrée IA hors fiche/Copilote.
- [?] Ton `danger` (rouge) réservé aux actions destructrices (Supprimer, Écarter, `st-ecartee`). *(DA-FIX-2 Lot 0, Vic 24/09/2026)*

## 3. Retour

- [A] Un seul composant `<Retour/>`, en haut à gauche du panneau, toujours au même endroit. Rendu **bouton secondaire** (contour vert, 32 px, rayon 6, survol vert plein) — jamais un lien souligné, jamais un texte gris.
- [?] Libellé : « ← Outils » depuis l'écran 1 d'un outil, « ← [étape précédente] » depuis une étape, « ← [outil de départ] » après un pont — jamais « Retour » seul, jamais une croix pour revenir en arrière (la croix ferme, elle ne recule pas).
- [A] Retour après un pont = état d'origine restitué (sélection, filtres).
- [?] `Échap` = retour d'une étape ; jamais fermeture du panneau entier.

## 4. Entrée d'un outil

- [?] Tout outil qui part d'une parcelle s'ouvre sur **l'omnibox (adresse / IDU / réf courte type BW0917) + « ou cliquez la carte »**. Les deux gestes, toujours, même rendu. Liste : Faisabilité, Taxe, Risques, PLU par parcelle, Comparer, Assemblage, Scan, Courrier, Densifier, Solaire, Remonter le temps, Gabarit (+ fiche parcelle depuis la carte).
- [?] Outil qui part d'une commune/zone : sélecteur de commune + « ou dessinez sur la carte » (Communes, Étude de zone, Permis, Successions, Blocs fonciers).
- [A] La réf cadastrale courte marche dans TOUTES les barres.
- [A] Omnibox permanente en tête quand l'outil a un résultat (on peut changer de parcelle sans revenir).

## 5. Filtres, tris, cases

- [?] Un seul composant chip (coche = vert opaque), un seul composant case, un seul composant tri (flèche ▲▼ dans l'en-tête).
- [A] « Tout / Tous » toujours dernier à droite.
- [A] Pagination : < 200 tout d'un coup, sinon 200 + « voir 200 de plus — N / M ».
- [A] Tri par défaut jamais la surface.
- [?] Un filtre actif se voit depuis le bouton du panneau (pastille avec le compte), même panneau fermé.

## 6. Scroll, accordéons, apparition

- [A] Aucune barre horizontale, nulle part. Barre verticale verte opaque au survol, style défini une fois.
- [A] Accordéon : fermé = ◀ (pointe à gauche), ouvert = ▼ ; chevron actif vert opaque.
- [?] **Une seule animation d'apparition** (fondu + 4 px de montée, 150 ms) pour panneaux, tiroirs, cartes. Rien d'autre : pas de slide, pas de zoom, pas de rebond.
- [?] Aucune animation au scroll (pas d'éléments qui apparaissent en défilant) — tout est là à l'ouverture.
- [?] Transitions de survol : 100 ms, une seule courbe.

## 7. Infobulles, badges, listes

- [A] Aucune infobulle au survol, sauf contrôles de la carte (couches, légende).
- [A] Badge de score seulement là où l'analyse LABUSE a été demandée.
- [?] Un seul composant badge (pilule, 3 couleurs : vert / ambre / neutre), un seul composant ligne de liste, un seul composant carte cliquable (icône inversée au survol — [A]).
- [A] Table dans un panneau outil (320 px) = cartes empilées + barre de tri, jamais 6 colonnes.

## 8. Vide, erreur, chargement

- [?] Trois états, un composant chacun, même rendu partout : « rien ici » (texte + action), « erreur » (texte + réessayer), « chargement » (squelette, pas de spinner).
- [A] Un échec technique ne se déguise jamais en absence de donnée (« non déterminée » ≠ « non calculée »).

---

## Ce que ça donne pour l'audit

L'audit DA-AUDIT-1 vérifie chaque écran contre les 8 blocs ci-dessus et dresse une grille écran × règle. Périmètre : 17 outils, fiche parcelle, fiche commune, carte + panneaux (Couches, Filtre, Analyse), Veille + cloche, Projets, CRM, Copilote, Compte.
