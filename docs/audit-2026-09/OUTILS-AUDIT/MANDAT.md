# MANDAT OUTILS-AUDIT-1 — Audit des 15 outils en lecture seule

**Statut :** PRÊT — joué sur `fix/retours-12` non mergé (état réel des outils).
**Rédigé par :** Fable, 05/09/2026.
**Branche :** `audit/outils-1`, créée depuis `fix/retours-12`.
**Emplacement du mandat :** `docs/audit-2026-09/OUTILS-AUDIT/MANDAT.md`
**Livrable unique :** `docs/audit-2026-09/OUTILS-AUDIT/RAPPORT.md`

---

## Étape 0 — avant toute écriture

CC vérifie et affiche : `pwd`, `git branch --show-current`, `git status -sb`.
Conditions : arbre `~/Desktop/labuse-outils`, branche `audit/outils-1`, arbre propre, la branche contient les commits de RETOURS-13/14/15.
Si une condition échoue : CC s'arrête, signale, n'écrit rien.

## Nature du mandat

**Lecture seule.** Aucune modification de code, aucune migration, aucune écriture en base, aucun fix « en passant ». Le seul fichier produit est le rapport. Ce qui est trouvé de cassé est consigné, pas corrigé.

CC ne juge pas l'ergonomie visuelle (c'est l'objet d'une recette séparée sur captures). CC constate des faits : ce que l'outil lit, calcule, rend, et ce qu'il ne rend pas.

## Périmètre — les 15 outils du menu Outils

1. Étudier un bien
2. Faisabilité
3. Taxe d'aménagement
4. Pièges & risques
5. PLU
6. Comparer des parcelles
7. Assemblage
8. Scan patrimoine (deux onglets : possèdent / construisent)
9. Courrier propriétaire
10. Densifier l'existant
11. Permis
12. Communes (trois entrées : Comparaison / Évolution du marché / Acquisitions récentes)
13. Prospection solaire (deux modes : Piscines / Ensoleillement)
14. Mon secteur
15. Étude de zone

Si le menu réel diffère de cette liste, CC audite le menu réel et note l'écart en tête de rapport.

**Hors périmètre :** Radar, Veille, Projets, CRM, Copilote, exports PDF, dashboard admin. Ils n'apparaissent que dans la section « Connexions » de chaque fiche.

---

## Partie A — une fiche par outil (15 fiches, structure fixe)

### A1. Identité
- Nom affiché, entrée du menu, route front, fichier(s) front, endpoints back, module(s) moteur.

### A2. Entrées
- Modes d'entrée réellement câblés : IDU · adresse · référence cadastrale courte (ex. `BW0917`) · clic carte · SIREN/SIRET · nom d'entreprise · dessin.
- Pré-remplissage depuis une fiche parcelle ouverte, depuis une fiche Radar, depuis un autre outil : OK / ABSENT, avec preuve.
- Comportement à l'ouverture sans contexte (état vide) : ce qui est demandé à l'utilisateur.

### A3. Sources lues
- Tables et vues lues, avec le run : doit être `q_v11_m137` via la constante unique (tout accès direct à une table LIVE ou à un run périmé = KO).
- Pour chaque champ servi à l'écran : statut Sourcé / Estimé / Absent et si ce statut est affiché.

### A4. Calculs
- Moteurs appelés (`sector_price`, `plu/destinations`, résiduel, cascade, scoring, etc.).
- Tout calcul fait au front sur une donnée métier = KO.
- Tout chiffre affiché dont CC ne retrouve pas la chaîne table → moteur → écran = DOUTE.
- Hypothèses implicites (taux, coefficients, seuils, fenêtres temporelles) : valeur, fichier:ligne, et si l'utilisateur les voit.

### A5. Sorties
- Ce que l'outil rend : écran, tableau, carte, export, geste (vers Projets, CRM, Courrier, autre outil).
- Ce qu'il ne rend pas alors que son moteur le calcule (valeur calculée puis jetée).

### A6. Données en base non servies — la colonne clé
Pour cet outil, lister toute donnée **déjà en base** qui serait pertinente à sa question et qu'il ne lit pas. Format : `table.champ — ce que ça apporterait — Sourcé/Estimé`.
CC ne s'autocensure pas et n'arbitre pas : il liste. L'arbitrage est fait ensuite par Vic.

### A7. Connexions
- Vers quels outils / écrans cet outil renvoie, et lesquels renvoient vers lui.
- Renvois attendus mais absents (un outil qui parle de la même parcelle sans lien).
- Le fait vit-il dans une seule section ou est-il dupliqué ailleurs (règle « un fait, une section »).

### A8. Mesures
Sur trois parcelles fixes choisies par CC et gravées en tête de rapport (une en zone U dense, une en zone A ou N, une à Saint-Philippe RNU) : temps de réponse serveur de chaque endpoint de l'outil, nombre de requêtes, et résultat observé (rendu / vide / erreur).

### A9. Usage
- Existe-t-il un capteur d'usage pour cet outil (dashboard Produit) ? Si oui, valeur sur 30 jours. Si non : ABSENT.

### A10. Dettes et anomalies
- Bugs, faux positifs, valeurs douteuses, vestiges (tests verrouillant un ancien nom, flags morts, tables mortes lues).
- Chaque ligne : OK / KO / ABSENT / DOUTE + preuve `fichier:ligne` + impact en une phrase.

### A11. Verdict factuel (3 lignes max)
Ce que l'outil fait bien. Ce qu'il ne fait pas. Ce qui est cassé. Pas de recommandation produit.

---

## Partie B — matrice données × outils

Inventaire du feature store et des couches en base, par thème (cadastre, PLU/destinations, DVF, Sitadel, propriétaires PM/MAJIC, risques, réseaux, équipements BPE/SIRENE, solaire/LiDAR, Filosofi, transport, etc.).
Pour chaque table ou vue : quels outils la lisent (parmi les 15).
Une table lue par aucun outil = ligne surlignée. C'est la réserve de puissance.

## Partie C — regroupements non servis

À partir de la matrice, CC liste des regroupements de données existantes qu'aucun outil ne sert aujourd'hui, sous la forme : « données X + Y + Z permettent de répondre à la question métier Q ; faisabilité technique : moteur existant / à écrire ; volume ».
Faits et faisabilité seulement. Aucune maquette, aucun nom d'outil, aucun avis sur la pertinence commerciale.

---

## Règles du rapport

- Une fiche par outil, dans l'ordre du menu. Chaque fiche tient en une page écran ; les preuves longues vont en annexe.
- Tout constat porte une preuve `fichier:ligne` ou une requête SQL rejouable.
- Les KO sont récapitulés en tête de rapport, classés 🔴 (faux chiffre servi ou donnée périmée) · 🟠 (fonction annoncée absente ou cassée) · 🟡 (dette, vestige, perf).
- Un compte-rendu de 20 lignes max en fin de rapport : nombre de KO/ABSENT/DOUTE, les trois constats les plus lourds, les limites de l'audit (ce que CC n'a pas pu vérifier).
- Commit unique sur `audit/outils-1`, push, **pas de merge** — Vic merge.

## Après ce mandat

Vic envoie ses captures (2-3 par outil) en parallèle. Fable croise le rapport et les captures, rend une fiche de synthèse par outil avec verdict franc — y compris « ne pas y toucher » — plus la liste des outils candidats. Ce que Vic valide devient des mandats CC de correctifs, priorisés.
