# M2 — schéma de la table `pm_proprietaires_millesimes`

```sql
CREATE TABLE pm_proprietaires_millesimes (
    id              serial PRIMARY KEY,
    millesime       integer NOT NULL,          -- situation au 1er janvier de l'année (2021-2024)
    idu             varchar(14) NOT NULL,      -- IDU 14 c. (insee + préfixe z3 + section z2 + plan z4)
    groupe          integer,                   -- groupe personne DGFiP (1-9)
    groupe_label    varchar(80),
    forme_juridique varchar(20),               -- forme abrégée (col. 22)
    denomination    varchar(200),
    siren           varchar(20),               -- BRUT (pseudo-SIREN MAJIC 'U…' conservés tels quels)
    url_source      text,                      -- attachment data.economie exact du millésime
    date_import     timestamptz DEFAULT now(),
    CONSTRAINT uq_pm_millesime_idu UNIQUE (millesime, idu)
);
CREATE INDEX ON pm_proprietaires_millesimes (millesime);
CREATE INDEX ON pm_proprietaires_millesimes (idu);
```

- Modèle SQLAlchemy : `models.PmProprietaireMillesime` (module `ingestion/pm_millesimes.py`).
- **La table de prod `parcelle_personne_morale` (situation 2025) est INTACTE** — aucun flux
  existant modifié, moteur V intact ; le millésime 2025 du panel se LIT dans la table de prod.
- Idempotence : `DELETE WHERE millesime = :m` puis ré-insertion par lots de 5 000.
- Dédup par (millesime, idu) : première ligne du fichier gagne — même convention que le
  loader 2025 (une parcelle multi-lignes SUF garde son premier propriétaire listé).

## Diffs de schéma constatés entre millésimes (lot 1)

Positions des 24 colonnes IDENTIQUES sur 2021→2025 (vérifié par `_sniff_header`, qui LÈVE
sur tout écart) ; les différences sont de FORMAT de livraison :

| Aspect | 2021-2023 | 2024 | 2025 (prod) |
|---|---|---|---|
| Membre du ZIP | `PM_YY_NB_974.txt` | `PM_24_NB_974.csv` | `PM_25_NB_974.csv` |
| Encodage | latin-1, entête QUOTÉE | utf-8 | utf-8 |
| Département | **'97' + Code Direction '4'** (éclaté) | '974' | '974' |
| Groupe personne | code nu ('1') | code, parfois « n - libellé » | « n - libellé » |
| Attachment id | `…dept_61_a_976…` (2021) / `…dept_62…` | `fichiers_…dpts_61_a_976` (pluriel !) | `…dpts_57_a_976` |

Bonus catalogué (non ingéré, hors mandat) : millésimes 2019 et 2020 également présents sur
data.economie — le panel pourrait remonter à 01/01/2019 si v2 en a besoin.
