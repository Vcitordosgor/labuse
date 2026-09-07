# Relecture des cinq documents — 07/09/2026

Passe document par document sur les maquettes du 05/09. Ce qui manque, ce qui est à corriger, ce qui peut être ajouté. Le Financier est traité en dernier et en détail (§5), avec son questionnaire.

---

## 1. Ce que j'ai vérifié d'abord

L'arithmétique du Financier de la maquette est juste : 3 003 550 € de chiffre d'affaires, 720 852 € de marge et frais, 66 780 € de VRD, charge foncière de 287 k€ / 92 k€ / −140 k€ selon le coût de construction, marge résiduelle de 163 k€ (5,4 % du CA) au prix demandé, terrain nu de marché à 569 856 €. Les trois bornes de sensibilité tombent juste.

**Mais le résultat est faux quand même**, pour une raison qui n'est pas arithmétique : voir §5.1.

---

## 2. Dossier — 5 ajouts

| # | À ajouter | Pourquoi | Disponible ? |
|---|---|---|---|
| D-a | **Historique de mutation de la parcelle** : quand elle a été vendue, à quel prix, sous quel régime | C'est public (DVF), c'est dans la base, et c'est l'information la plus utile qui n'apparaît nulle part. Savoir que le propriétaire a acheté 180 k€ en 2019 change tout le regard sur un prix demandé à 650 k€. Aujourd'hui aucun des six documents ne le dit. | ✅ DVF, `mutations_12m_n` existe mais ne couvre que 12 mois — il faut l'historique complet de l'IDU |
| D-b | **Permis déposés sur la parcelle elle-même** (accordés, refusés, retirés) | Un refus antérieur sur cette parcelle est le signal le plus fort qui soit, et il est dans Sitadel. Aujourd'hui on ne montre que les permis *voisins*. | 🔎 à vérifier : le rattachement Sitadel → parcelle est-il fiable ? Sinon, à l'échelle de l'adresse |
| D-c | **Divisibilité** | Le moteur `division_or` existe, l'id `divisible_classe` est au registre, et le Dossier n'en parle pas. Une parcelle divisible vaut plus qu'une parcelle qui ne l'est pas. | ✅ moteur existant |
| D-d | **Gabarits voisins** : hauteur des bâtiments qui entourent | Ce qui passe en mairie ressemble à ce qui existe déjà autour. Un R+3 au milieu de R+1 ne passe pas, même si le PLU l'autorise. | ✅ LiDAR HD MNH (au catalogue, jamais servi) ou BD TOPO |
| D-e | **Copropriété** | Si le bâti est en copropriété, la vente n'est pas une vente de parcelle mais de lots : le montage change entièrement. | 🔎 à vérifier en base |

**Une correction** : la section 7 « Autour de la parcelle » annonce un périmètre à 10 minutes à pied et donne 4 120 habitants, mais le chiffre servi aujourd'hui vient d'un isochrone 10 minutes en voiture (19 617 habitants). Tant que le mode piéton n'est pas branché, il faut servir le périmètre réellement calculé, avec son mode dans le libellé — sinon on imprime un chiffre juste sous un titre faux.

---

## 3. PDF résumé — 2 ajouts

- **Le prix d'achat de la parcelle** (D-a), en une ligne. C'est le résumé : cette ligne y vaut trois autres.
- **Un renvoi explicite** : « Version complète : Dossier parcelle · Bilan chiffré : Financier ». Aujourd'hui le lecteur ne sait pas qu'il a un extrait entre les mains.

---

## 4. Apporteur — 3 ajouts, dont un juridique

| # | À ajouter | Pourquoi |
|---|---|---|
| A-a | **Mention de non-mandat** : « Ce document ne vaut pas mandat. Vous n'êtes pas habilité à négocier, à faire une offre ni à engager l'émetteur. » | Un apporteur qui annonce un prix au propriétaire crée une attente, parfois une obligation. C'est la protection de Stéphanie, elle manque. |
| A-b | **Date d'émission et durée de validité** | Un brief qui circule six mois plus tard avec des chiffres périmés est un risque. |
| A-c | **Le prix d'achat historique** (D-a) | Le propriétaire le connaît déjà — aucun risque de fuite — et l'apporteur arrive en sachant à quoi s'attendre. |

Une question ouverte : faut-il une case **« le propriétaire est-il joignable, et par quel canal »** ? C'est souvent le vrai blocage.

---

## 5. Financier — le point important

### 5.1 🔴 Le bilan est faux sur la TVA, et l'erreur dépasse le résultat

Le prix de sortie retenu, 4 730 €/m², vient de DVF : c'est un **prix d'acte, donc TTC**. Le coût de construction, 2 550 €/m², est un prix d'entreprise, donc **HT**. Le bilan additionne les deux tels quels.

À La Réunion, la TVA sur le logement neuf est de 8,5 %. En chiffres :

| | Aujourd'hui | Si le CA est ramené HT |
|---|---|---|
| Chiffre d'affaires | 3 003 550 € | 2 768 249 € |
| Charge foncière (coût 2 550) | 92 218 € | **−143 083 €** |

**L'écart, 235 k€, est deux fois et demie le résultat annoncé.** Autrement dit : l'opération présentée comme « limite mais possible » est en réalité déficitaire, ou pas — selon un point d'hypothèse que le document ne mentionne jamais.

Je ne suis pas comptable et le régime réel dépend du montage (TVA sur marge à l'acquisition, récupération de la TVA sur les coûts, taux réduit pour l'accession sociale) : ce n'est pas à LABUSE de trancher. Mais **c'est à LABUSE de poser la question et d'afficher l'hypothèse retenue.** Un bilan qui ne dit pas s'il travaille HT ou TTC ne peut pas être vrai par accident.

**Ce qu'il faut** : un champ « régime de TVA » au questionnaire, la mention HT ou TTC sur chaque ligne du bilan, et un renvoi à l'expert-comptable pour le régime.

### 5.2 Sept postes absents du bilan

Chacun se compte en dizaines de milliers d'euros sur cette opération.

| Poste | Ordre de grandeur ici | Pourquoi il manque aujourd'hui |
|---|---|---|
| **Frais d'acquisition du foncier** (notaire, droits ou TVA sur marge) | 5 à 8 % du prix du terrain | Jamais évoqué |
| **Honoraires techniques** : architecte, bureaux d'études, contrôle technique, coordination sécurité, assurance dommages-ouvrage | 10 à 15 % du coût travaux | Peut-être inclus dans les « 12 % d'honoraires », mais personne ne le sait |
| **Étude de sol G2** obligatoire, et fondations en zone PPR | devis | Absent |
| **Stationnement** si sous-sol ou silo | 15 à 25 k€ la place, soit 120 à 200 k€ ici | Le scénario « au sol » l'évite, mais le document propose l'autre scénario sans le chiffrer |
| **Aléas et imprévus** | 3 à 5 % du coût travaux | Absent |
| **Portage financier** : durée réelle (9 mois d'instruction + recours + 20 mois de chantier ≈ 3 ans) | les « 3 % de frais financiers » sont forfaitaires et muets sur la durée | La durée n'apparaît nulle part |
| **Redevance d'archéologie préventive** | 0,68 €/m² de surface créée | Absent |

### 5.3 La mixité sociale peut renverser le bilan

Le Dossier dit « secteur de mixité sociale : quota imposé ». Le bilan dit « non déclenché » sous réserve du seuil. Si le quota s'applique, une part du programme se vend à un bailleur autour de 2 200 à 2 800 €/m² au lieu de 4 730 : à 25 % de logements sociaux, le chiffre d'affaires perd de l'ordre de 300 k€. Le mécanisme doit exister dans le bilan, même s'il n'est pas déclenché ici — sinon le premier programme concerné donnera un résultat faux sans que personne ne le voie.

### 5.4 Ce qui manque au document lui-même

- **Un compte à rebours de trésorerie** — même sommaire : acquisition, études, chantier, livraison. Un banquier lit un calendrier autant qu'un résultat.
- **Le seuil de rentabilité** : à quel prix d'achat l'opération atteint la marge visée ? C'est la question que le porteur se pose vraiment, et elle se déduit du bilan.
- **Le prix de revient au m²**, pour comparer à d'autres opérations.
- **La double sensibilité** : aujourd'hui je ne fais varier que le coût de construction. Le prix de sortie compte autant.

### 5.5 Le questionnaire — proposition complète

Aujourd'hui : 6 champs. C'est trop peu pour un bilan juste, et c'est le bon moment pour demander, puisque le client vient chercher un chiffre.

**Principe** : quatre écrans courts, tout pré-rempli avec une valeur sourcée ou un usage de place, chaque champ modifiable, et **rien d'inventé** — un champ laissé vide sort en « non chiffré » dans le document, jamais remplacé par une valeur par défaut silencieuse.

**Écran 1 — Votre projet**
Scénario (reconstruction / réhabilitation / surélévation) · nombre de logements visé (pré-rempli 8, fourchette 7-9) · typologie moyenne · part de logement social ou intermédiaire (pré-remplie par la règle de mixité de la zone) · stationnement (au sol / sous-sol / silo).

**Écran 2 — Le foncier**
Prix demandé par le vendeur · prix déjà refusé, si connu · frais d'acquisition (notaire, droits — pré-rempli 7 %) · commission d'apporteur · coût de démolition (« non chiffré » par défaut) · dépollution ou étude de sol si connue.

**Écran 3 — Vos coûts**
Coût de construction €/m² (pré-rempli par la fourchette sourcée EPTB/CDC) · honoraires techniques (%) · VRD et raccordements · coût par place de stationnement · aléas (%) · taxe d'aménagement (calculée, modifiable).

**Écran 4 — Vos conditions**
Prix de sortie €/m² (pré-rempli par le neuf observé, l'ancien affiché en repère) · prix de vente au bailleur pour la part sociale · marge visée (%) · **régime de TVA** (assujetti avec récupération / TVA sur marge / autre — avec un mot d'explication) · durée de portage (mois) · apport et taux, si le client veut sa LTV.

Soit une vingtaine de champs, dont une douzaine déjà pré-remplis correctement. Cinq minutes pour un promoteur, et le document devient défendable.

### 5.6 Trois règles pour que le Financier reste vrai

1. **Aucun poste inventé.** Un champ vide s'imprime « non chiffré », et le résultat porte alors la mention « maximum : les postes non chiffrés le réduiront ». Jamais un défaut silencieux.
2. **HT ou TTC sur chaque ligne**, et le régime en tête du bilan.
3. **Le résultat est une fourchette, pas un nombre.** Le chiffre unique est ce qui a rendu l'ancien Banquier indéfendable ; la sensibilité doit rester en face du résultat, sur les deux axes (coût et prix de sortie).

---

## 6. Pré-dossier PC — un ajout

Aux corrections déjà listées, ajouter la **redevance d'archéologie préventive** et la **taxe d'aménagement** dans la fiche de zonage : ce sont les deux montants que le pétitionnaire découvre après le dépôt, et ils sont calculables.

---

## 7. Ce que je propose comme ordre

1. Trancher la TVA (§5.1) — c'est le seul point qui rend un document faux aujourd'hui.
2. Valider le questionnaire à quatre écrans (§5.5) : il conditionne la maquette du Financier et le mandat de l'écran de saisie.
3. Les ajouts du Dossier : D-a (prix d'achat historique) et D-c (divisibilité) sont disponibles tout de suite ; D-b, D-d, D-e demandent une vérification en base.
4. Les trois lignes de l'Apporteur, dont la mention de non-mandat.

Rien de tout cela ne change la forme des maquettes : ce sont des blocs à ajouter et des hypothèses à rendre visibles.
