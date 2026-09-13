# APPORTEUR — SPEC (liste FERMÉE des lignes autorisées)

RECETTE-12 E1. Ce document est la **spec fermée** du Brief apporteur : la liste exhaustive des lignes
que le document a le droit d'imprimer, tirée des décisions de Vic du 05/09 et de la v3 du 08/09
(`maquette-apporteur-v3.html`). Le test `tests/test_recette12_apporteur_spec.py` lit le bloc
`AUTORISÉ` ci-dessous et **échoue si une ligne du `pdftotext` ne correspond à AUCUN motif** — et si un
motif de la liste `INTERDIT` apparaît. **Toute modification future de l'Apporteur passe d'abord par
cette spec.**

## Page 1 — autorisé

- Titre, adresse, IDU, date d'émission + validité (90 jours), bandeau confidentiel + sans mandat.
- **L'émetteur, nom et téléphone** (c'est à lui que l'apporteur renvoie ses réponses ; Vic a refusé
  l'anonymat de l'émetteur le 05/09).
- Surface, zone, « sur place » (**nombre de bâtiments + emprise**, PAS la hauteur), « ce qui gêne », accès.
- Dernière vente de la parcelle, datée + chiffrée, **si connue**.
- Parcelles voisines du même propriétaire (« À côté »), **si connues**.
- Propriétaire (type), plan de situation.

## Page 1 — retiré (INTERDIT)

- « Ce qu'on peut y bâtir » / capacité constructible (l'apporteur la répéterait au propriétaire).
- « Prix du secteur » / tout prix (deviendrait l'ancre du vendeur).
- La hauteur LiDAR / faîtage (inutile à sa mission — ajoutée à tort en RECETTE-11).

## Questionnaire

- **Trois « L'ESSENTIEL »**, pas quatre : prix attendu/refusé, bail, parcelles voisines. Le contact
  (nom + coordonnées) est le **premier champ obligatoire**, **sans** l'étiquette.
- « Si loué : sous quel bail ? » (jamais « Sous quel bail ? » sec).
- Photos : envoyées **à l'émetteur nommé** en page 1 (jamais « n'imprimez rien »). « Votre retour »
  renvoie au même émetteur.

## EL0157 — dernière vente et voisines

Absentes sur EL0157 par **donnée inconnue**, pas par branchement manquant : 0 mutation DVF pour cette
parcelle (`dvf_mutations_parcelle`), et le propriétaire est une **personne physique** (aucun cluster
de parcelles voisines du même SIREN). Les deux branchements tournent et renvoient « rien » à juste titre.

---

## AUTORISÉ

Un motif (regex Python, `re.fullmatch` sur la ligne `pdftotext` détourée) par ligne. Les valeurs
dynamiques (adresse, IDU, dates, émetteur, aléas, montants) sont couvertes par des motifs génériques.

```
LABUSE
Brief apporteur
Un (bien bâti|terrain) à sonder
.*\d{5}.*
\d{9}[A-Z0-9]{5}
Émis le \d{2}/\d{2}/\d{4} — valable 90 jours \(jusqu'au \d{2}/\d{2}/\d{4}\)
Confidentiel, et sans mandat\..*
habilité à négocier.*
Émetteur : .+
C'est à cet émetteur que vous renvoyez vos réponses et vos photos\.
La parcelle
Surface
[\d  ]+m²
Zone
.*famille [A-Z].*
Um .*|.*—.*constructible.*
Sur place
\d+ bâtiments.*
\d+ m² au sol
terrain a priori nu
Ce qui gêne
.*(PPR|inondation|mouvement de terrain|préemption|réservé|boisé|bruit|DPU|PEB).*
Accès
arrêt de bus à \d+ m
Dernière vente
[a-zéûapp]+ \d{4} — .*€.*|.*€.*
À côté
\d+ parcelles? voisines?.*
Propriétaire
(Personne (physique|morale).*|Indivision.*|État.*|Copropriété.*|SC[ICP].*|SA[RS].*|.+\(SIREN.*)
Plan de situation — la parcelle \(contour\) et ses voisines.*
fond cartographique momentanément indisponible.*
Voilà ce qui est public\..*
les pages suivantes vous demandent\.
\d/4
Qui décide
Une parcelle en indivision, ce sont autant de signatures.*
première chose qui fait échouer une.*
vente\.
Nom et coordonnées de la personne à qui vous avez parlé \(obligatoire\)
(Qui détient réellement la parcelle.*|La parcelle est détenue par une société.*)
signataires \?
Gérant, associés, nombre de signataires \?
Tous les décideurs sont-ils d'accord pour vendre \?
Oui
Non
Pas tous
Ne sait pas
Un notaire est-il déjà saisi \? Lequel \?
La vente
Le prix déjà refusé vaut plus qu'un prix annoncé.*
L'ESSENTIEL
Quel prix attend-il \? Quel prix a-t-il déjà refusé \?
Est-il vendeur \? Depuis quand, et pourquoi \?.*
liquidités, lassitude…
Qui est déjà passé \?.*
offres reçues et montants si connus
Un mandat de vente est-il en cours \?
Simple
Exclusif
Par quel canal le joindre à nouveau \?.*
via un tiers \?
Le bâti et son occupation
Un bail commercial en cours peut geler l'opération.*
premier si c'est le cas\.
Les bâtiments sont-ils occupés \? Par qui \?
Vides
Le propriétaire
Des locataires
Une activité
Si loué : sous quel bail \?.*
Fin de bail, loyers perçus\.
État général du bâti ; diagnostics disponibles \(amiante, plomb\) \?
Le sol
Un ancien garage, dépôt ou station-service.*
Un établissement classé \(ICPE\).*
dépollution\.|.*changerait le coût\.|.*au Dossier\).*
Quel était l'usage du site avant \?.*
Cuves enterrées, remblais, pollution connue \?
Ce que les papiers diraient
Ce qui ne se voit ni sur le terrain ni au cadastre.*
Servitudes de passage, litiges de voisinage.*
empiètements connus \?
Hypothèques, procédures en cours \?
Titre de propriété disponible \?.*
donation, succession — et l'année\.
Le voisinage et la mairie
Un achat groupé de parcelles voisines.*
\d+ parcelle\(s\) voisine\(s\) appartiennent au même propriétaire.*
change complètement l'opération\.
Savoir
Vendrait-il aussi .*|Les parcelles voisines sont-elles à vendre \? Du même propriétaire \?
D'autres.*à vendre \?
Que dit la mairie de ce secteur \? Que disent les voisins \?.*
Projets connus, oppositions, associations\.
Les photos
Cinq vues : depuis la voie, puis aux quatre coins.*
citant la référence \d{9}[A-Z0-9]{5}\.
Votre retour
À renvoyer à .+
Date de la visite · vos coordonnées
Ce qu'il faut savoir et qu'aucune question ne couvre
```

## INTERDIT

```
Ce qu'on peut y bâtir
plancher restant
Prix du secteur
€/m²
au faîtage
LiDAR
n'imprimez rien
Sous quel bail \?$
```
