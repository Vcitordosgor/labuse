# Signalement de qualité de donnée — RNE / INPI (dates de naissance de dirigeants)

> Texte prêt à envoyer au producteur. **Aucune modification n'a été faite en base LABUSE** :
> ces 481 valeurs restent servies « âge inconnu » (exclues de l'outil Successions et du filtre 70+),
> et sont corrigées à la source par le producteur.
> Pièce jointe (hors dépôt) : `~/Documents/LABUSE-INPI/inpi-481-dates-aberrantes.csv`.

---

**Objet :** Anomalies de dates de naissance de dirigeants (personnes physiques) dans le Registre National des Entreprises — 481 cas

**Destinataire :** INPI — Registre National des Entreprises (RNE) / support données ouvertes
**Expéditeur :** LABUSE — réutilisateur des données RNE en open data (réutilisation encadrée, art. L. 323-2 CRPA)
**Date :** 2026-10-20
**Contact :** kampusreunion@gmail.com

Madame, Monsieur,

Dans le cadre de notre réutilisation des données ouvertes du Registre National des
Entreprises, nous avons relevé **481 enregistrements de dirigeants personnes physiques
(`type_personne = INDIVIDU`) dont la date de naissance est manifestement erronée**. L'âge
qui en découle est hors de toute plausibilité pour une fonction de direction :

- **479 cas** donnent un âge **inférieur à 18 ans**, dont **un cas daté dans le futur
  (naissance « 2026-11 »)** et de nombreuses naissances récentes (2008 à 2025) ;
- **2 cas** donnent un âge **supérieur à 110 ans** (naissances « 1911-11 » → 114 ans et
  « 1909-03 » → 117 ans).

Ventilation par âge calculé (au 2026-10-20) :

| Âge | Nombre | | Âge | Nombre |
|----:|-------:|-|----:|-------:|
| 0 (futur/2026) | 1 | | 10 | 34 |
| 1 | 1 | | 11 | 36 |
| 2 | 1 | | 12 | 32 |
| 3 | 2 | | 13 | 43 |
| 4 | 5 | | 14 | 67 |
| 5 | 8 | | 15 | 57 |
| 6 | 8 | | 16 | 50 |
| 7 | 22 | | 17 | 68 |
| 8 | 20 | | 114 | 1 |
| 9 | 24 | | 117 | 1 |

**Total : 481.**

Ces anomalies proviennent vraisemblablement de saisies erronées à la source (inversion/typo
d'année, année de dépôt saisie à la place de l'année de naissance). Nous ne les corrigeons
pas de notre côté — les valeurs restent affichées « âge inconnu » et sont écartées de nos
traitements — afin de ne pas diverger du registre officiel.

**Nous vous demandons de bien vouloir vérifier et corriger ces enregistrements à la source.**
La liste complète est jointe au format CSV (`inpi-481-dates-aberrantes.csv`, conservée hors dépôt
dans `~/Documents/LABUSE-INPI/`), identifiée par
`siren`, `representant_id` (identifiant RNE du représentant), `role_entreprise`,
`date_naissance` (telle que diffusée), âge calculé et motif. Aucun nom n'est inclus : les
identifiants `siren` + `representant_id` suffisent à retrouver chaque fiche dans le RNE.

Exemples (3 premiers de la liste) :

| siren | representant_id | role | date_naissance | âge | motif |
|---|---|---|---|---|---|
| 443982939 | 80c171b7-…-96e48e683992 | 30 | 2026-11 | 0 | date future |
| 443917810 | e07f8dbf-…-78520a956011 | 75 | 2025-03 | 1 | mineur |
| 851847939 | 07d4c861-…-4d851439235c | 75 | 2024-10 | 2 | mineur |

Nous restons à votre disposition pour tout complément.

Cordialement,
L'équipe LABUSE

---

### Méthode (pour mémoire interne)

Requête de détection (prod `labuse`, lecture seule), reproduisant la garde I5 de
`CHASSE-INVARIANTS-FIX-1` (cf. `chasse-invariants-1/domaine-6.md`) élargie à tout le stock :

```sql
SELECT siren, representant_id, role_entreprise, date_naissance, age_calcule
FROM (
  SELECT siren, representant_id, role_entreprise, date_naissance,
         date_part('year', age(to_date(date_naissance,'YYYY-MM')))::int AS age_calcule
  FROM pm_dirigeants
  WHERE type_personne='INDIVIDU' AND date_naissance IS NOT NULL
) t
WHERE age_calcule < 18 OR age_calcule > 110
ORDER BY age_calcule, siren;   -- 481 lignes
```

L'âge est calculé par rapport à la date du jour ; le décompte 481 vaut au 2026-10-20 et peut
glisser de ±quelques unités aux bornes avec le temps (anniversaires des cas proches de 18 ans).
