# MANDAT RETOURS-4 — recette visuelle du 31/08 (soir)

**Branche : `fix/retours-4`** (neuve, depuis `main` **après** merge de `fix/retours-3`). Bloc commun habituel à coller avec ce mandat.

**Étape 0** : `pwd`, branche, arbre propre — sinon s'arrêter sans écrire.
**Fin de session obligatoire** : `tsc`, build, tests, puis **CC commite son travail sur la branche** avant de rendre son compte-rendu. Le merge reste à Vic.

**Référence** : `docs/audit-2026-08/maquette-accueil-v4.html` — **fenêtre desktop complète** (bandeau, rail, panneau 360, carte). Les v2/v3 étaient dessinées hors contexte, d'où des icônes hors d'échelle : les proportions ne se jugent que dans la fenêtre entière.

---

## S1 — Accueil : proportions et chiffres

1. **Icônes trop grosses.** Tuile **34 px**, glyphe **17 px**, stroke 1.9, coin 9 px. La tuile ne dépasse jamais la hauteur du bloc titre + description.
2. **Les 3 chiffres disparaissent à 100 % de zoom** (visibles seulement vers 80 %) — c'est un débordement, pas un état de chargement. Bande compacte : nombre 15 px, libellé 10 px, `white-space:nowrap` sur le nombre, ellipse sur le libellé, jamais de règle qui masque le bloc selon la largeur. **Recette : lisibles à 100 %, 110 % et 125 %, et à 320 px de large.**
3. **« Suivre le marché — Radar » sur une seule ligne** : `nowrap` + ellipse sur tous les titres de carte. Descriptions raccourcies pour tenir sur une ligne à 360 px :
   - Explorer la carte → « couches, filtres, parcelles »
   - Suivre le marché — Radar → « les biens en vente »
   - Demander au Copilote → « “terrain 1 000 m² à Saint-Paul” »
   - Ouvrir un outil → « 16 outils fonciers »
4. **Survol** : exactement le même contraste que les catégories du rail — aplat plein `--mint` (mauve sur le Copilote), texte et glyphe en encre sombre, **tuile en fond transparent avec contour sombre** (pas de pastille foncée qui fait tache). Voir la maquette.

## S2 — Rail : ordre et zone basse

1. **Sources tout en bas**, collé au pied du rail, **Admin juste au-dessus** (Admin visible pour Vic seul ; pour un client, Sources se retrouve donc seul en bas). Ordre haut : Carte · Outils · Copilote · Radar · Veille · Projets · CRM. Séparateur avant la zone basse.
2. Survol plein inchangé (déjà livré), y compris sur les deux entrées du bas.

## S3 — Survol plein : les surfaces oubliées

La règle est globale (R2.2 de RETOURS-3) mais trois écrans ne l'ont pas. À appliquer **à l'identique** (aplat plein, contenu inversé, mauve sur IA) :

1. **Projets** — lignes de la liste « Vos projets » et onglets Actifs/Archivés/Mes courriers.
2. **Outils** — cartes du tiroir Outils.
3. **Fiche parcelle** — cartes de section (« Le terrain » : Urbanisme, Constructibilité, Risques…) **et** les 8 tuiles d'export (PDF, Dossier, Finance, Cadastre, Argumentaire, Maps, Courrier, Pré-dossier PC).

Balayage : toute case cliquable de l'app doit avoir ce survol. Lister au compte-rendu celles trouvées hors de ces trois écrans.

## S4 — Radar, dépôt agence : l'URL échoue (HTTP 403) — refonte du parcours

Constat Vic : la lecture serveur est bloquée par le portail, **et un client ne fera jamais « vider le cache → Cmd+S → coller le HTML »**. Le parcours doit donc changer, pas seulement son message.

Ordre des chemins dans l'étape 1 :

1. **Formulaire court — chemin principal.** C'est SON annonce : l'agence connaît les faits. Champs : adresse exacte, type, prix, surface bâtie, surface terrain, nb de pièces (facultatif), URL de l'annonce. Rattachement parcelle immédiat depuis l'adresse. Aucun contenu d'annonce n'est stocké — seulement les faits et le lien, doctrine inchangée. Sept champs remplis en une minute, sans quitter l'app.
2. **Coller l'URL — raccourci optionnel.** Tentative de lecture serveur one-shot (déjà livrée) ; si elle passe, le formulaire arrive **pré-rempli** et l'agence n'a qu'à valider. Si elle échoue : bascule silencieuse sur le formulaire vide avec une ligne grise « Ce portail ne laisse pas lire ses pages automatiquement — complétez les champs ci-dessous ». Plus aucune erreur rouge.
3. **Coller le HTML (Cmd+S) — chemin d'expert, replié.** Sous un « Autre méthode ▾ ». C'est le chemin de Vic pour sa collecte, pas celui des agences.

Le flag admin reste fermé jusqu'à la réponse de l'avocat. Rien ne change côté doctrine ni côté parseur.

## S5 — Veille promoteurs : lisibilité des cartes

Constat Vic : mots coupés, dates et chiffres entassés, SIREN qui déborde, actions serrées.

1. **Carte d'opération remise à plat** : nom du propriétaire sur une ligne (ellipse, `title` complet au survol) · une ligne de faits `Type · N permis · N logements` · une ligne `Commune · période` · IDU sur sa propre ligne en monospace, ellipse. Jamais deux valeurs qui se chevauchent.
2. **Actions en bas de carte**, alignées : « voir son patrimoine » et « sa frise ». Pas de retour à la ligne au milieu d'un libellé.
3. **Popup carte** : même hiérarchie, largeur minimale suffisante pour que « voir la parcelle / voir son patrimoine » tiennent côte à côte sur une ligne.
4. Le plafond « 200 affichées » reste, avec sa notice.

## S6 — Logo

Aujourd'hui l'oiseau et le mot « LABUSE » sont collés ensemble dans le bandeau. Il faut les séparer.

1. **L'oiseau vert existant** — l'asset actuel, **à l'identique, aucun redessin** — est déplacé **au sommet du rail, juste au-dessus de « Carte »**, centré sur la largeur du rail, dans une zone signature (hauteur du bandeau, séparateur dessous). Il n'est ni cliquable, ni survolable, ni focusable, et ne prend jamais d'état actif.
2. **Le mot-symbole reste exactement à sa place dans le bandeau**, sans l'oiseau. Il est **agrandi (~29 px, gras)** pour occuper l'espace que l'oiseau libère, et devient **bicolore : « LA » en blanc, « BUSE » en vert** `--mint`. Un seul bloc de texte, pas d'espace entre les deux moitiés.

## S7 — Fusion Veille promoteurs → Scan patrimoine

Décision Vic : le nom **« Scan patrimoine » est conservé** — on veut parfois simplement regarder ce qu'une entreprise possède, et « promoteurs » referme le sujet à tort. La veille des opérations devient un **second onglet du même outil**, pas un bouton ni un outil séparé.

1. **Une barre de recherche unique** en tête : nom d'entreprise, SIREN/SIRET, IDU ou adresse. Un seul champ, la nature de la saisie est détectée.
2. **Deux onglets** : « Ce qu'ils possèdent » (le scan actuel, par défaut) · « Ce qu'ils construisent » (les opérations, écran actuel de Veille promoteurs, carte comprise).
3. Le propriétaire sélectionné est **partagé entre les deux onglets** : on bascule sans re-saisir. Les ponts croisés livrés en RETOURS-3 deviennent une bascule d'onglet.
4. « Veille promoteurs » disparaît du menu Outils (redirection interne conservée). Compteur d'outils mis à jour partout : 16 → 15.
5. La description de l'outil devient : « Ce qu'un propriétaire possède, et ce qu'il construit. »

---

## Compte-rendu attendu

Par lot : fait / constat / reste. Attendus nommés : S1.2 cause du masquage des chiffres · S3 liste des surfaces cliquables restées sans survol plein · S7 nouveau compte d'outils. Commit fait par CC. Merge isolé en dernier :

```bash
cd ~/Desktop/labuse-merge && git merge --no-ff fix/retours-4
```
