# RECETTE-9 T10 — le verrou des libellés : de la liste noire au rattachement aux vocabulaires

## Le constat
Le verrou des libellés (W5/W8) était une **liste noire figée à la main** (`_CODES_TECHNIQUES`,
19 codes). Il attrapait `surelevation` mais aurait **laissé passer tout nouveau code** de
vocabulaire ajouté sans qu'on pense à l'y inscrire. Le verrou des **nombres**, lui, **ancre**
chaque nombre imprimé à une valeur *réellement servie* par le registre — c'est un rattachement,
pas une interdiction de motifs.

## Ce qui est fait (implémenté, faisable dans le mandat)
La liste noire est désormais **DÉRIVÉE des vocabulaires contrôlés eux-mêmes** (leur source de
vérité) : `scenarios.SCENARIOS`, `tiers_client.{PALIERS_CLIENT, DOMAINE_PALIERS,
CORRESPONDANCE_LEGACY, TIERS_CLIENT}`, `enums.{CascadeVerdict, Severity, SourceResultStatus}`.
On ne retient que les formes **non ambigües** :
- code contenant `_` (snake_case) ;
- code EN MAJUSCULES ;
- variante **sans accent** d'un libellé mono-mot accenté (« Surélévation » → `surelevation`,
  « Priorité » → `priorite`, « Écartée » → `ecartee`), dérivée des libellés des vocabulaires.

Conséquence : **tout nouveau code** snake_case / MAJUSCULES / variante sans-accent est couvert
**automatiquement**, sans toucher au verrou (ex. `en_cours`, un futur `declasse_xxx`, un futur
`SOFT_EXCLUDE`). Vérifié : dérivé = **31 codes** (⊇ les 19 de la main, +12 auto), **0 faux
positif** (les mots français `reconstruction`, `revente`, `division`, `chaude`, `faible`… ne
sont pas pris). Tests : `tests/test_recette9_verrou_libelles.py` (4) + provenance Z5 (5) verts.
Un petit `_SUPPLEMENT` documenté reste pour les variantes sans-accent dont le libellé accenté
n'est plus exposé par son vocabulaire (`brulante`, `opportunite`) — à retirer quand ils le seront.

## Ce qui reste (parité pleine avec les nombres — non implémenté, chemin + coût)
Ce crible **ne voit toujours pas un libellé FRANÇAIS INVENTÉ** qui n'est ni un code de vocabulaire
ni un identifiant technique (une zone « Fantaisie », un motif rédigé faux). Le verrou des nombres
y arrive parce qu'un nombre est **ancré par sa valeur** à une donnée servie ; un libellé, noyé dans
la prose, n'a pas d'ancre.

**Chemin pour la parité** : un **tag de provenance au rendu**. Chaque libellé imprimé porterait
son origine (`chiffre_id` / vocabulaire) dans un span `data-provenance="<id>"`, posé par les aides
de rendu. La sonde confronterait alors **chaque libellé tagué** à la valeur *réellement servie* par
le registre pour ce `chiffre_id` — exactement comme les nombres. Un libellé imprimé **sans** tag, ou
dont le tag ne correspond pas à la valeur servie, échouerait la CI.

**Coût** : toucher les aides de rendu partagées (`rendu.ligne_kv`, `nature.chip`, `rendu.section`,
`chip_span`) pour émettre ces spans dans **tous** les blocs (~toutes les lignes clé/valeur), plus
une passe de sonde qui parse le HTML tagué et compare au registre. C'est un refactor de la **couche
de rendu** (transverse, ~30-40 points d'appel), à faire sous go — hors périmètre de ce mandat.
