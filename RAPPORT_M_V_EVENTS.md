# M-V · Volet 2 — Badge non-lu : suivi « vu » par compte des events de marché

**Problème** : depuis M-T V2, les events de marché (compte_id NULL : bascule/bodacc/match)
comptent au badge de chaque compte, mais `lu` est **une seule colonne sur la ligne partagée**.
`mark-read` était borné à `compte_id IS NOT DISTINCT FROM :cid` → un compte réel ne pouvait pas
marquer un event de marché (compte_id NULL ≠ son cid), donc **le badge ne descendait jamais**.
(Effet secondaire : seul le bucket pilote NULL pouvait écrire ce `lu` partagé — pour tous.)

**Fix** — table `event_seen (compte_id, event_id, seen_at)`, PK composite :
- **Lecture** : un event de marché est « lu » pour un compte réel s'il a une ligne dans
  `event_seen`. Un event du compte (perso, ou pilote sur ses lignes NULL) garde la colonne `lu`.
  Fragment SQL unique `_seen(alias)` réutilisé par la liste, le compteur global et par parcelle.
- **`mark-read`** : event du compte → `UPDATE lu` (inchangé) ; event de marché vu par un compte
  réel → `INSERT event_seen` (jamais d'UPDATE sur la ligne partagée). Le `INSERT … SELECT … WHERE
  e.compte_id IS NULL AND e.kind = ANY(market)` **borne au marché** : impossible de « voir »
  l'event perso d'autrui ni une ligne NULL hors marché (SEC-IDOR préservé).
- **`read-all`** : `UPDATE lu` des perso **+** `INSERT event_seen` de tous les events de marché
  pas encore vus. Couvre les deux familles.
- **Rétention** : FK `event_id → event_log(id) ON DELETE CASCADE` (les vus d'un event supprimé
  partent avec) ; FK `compte_id → comptes(id) ON DELETE CASCADE` posée par `tenant.ensure_scoping`
  (RGPD : supprimer un compte emporte ses vus). `comptes` n'existant pas au DDL de `events`, la
  table naît avec la seule FK event, la FK compte est ajoutée idempotemment après.

**Front** : aucun changement nécessaire. Le bouton « ✓ Marquer lu » s'affiche déjà pour tout item
`!e.lu`, et `e.lu` est désormais la valeur PAR COMPTE calculée par l'API → le badge descend et
l'item se grise, sans toucher au front.

**Compte neuf** : pas de ligne `event_seen` → tous les events de marché existants comptent non-lus
(comportement assumé — ils sont nouveaux pour lui).

**Validation** (`tests/test_audit_secu.py::test_seen_marche_par_compte`) : A marque lu un event de
marché → son badge descend, celui de B est **inchangé** ; la ligne partagée `lu` reste `false`,
une ligne `event_seen` est posée ; `read-all` couvre le marché ; les events perso gardent le
comportement d'avant. Cloison M-T/M-K non régressée (tests existants verts). **65/65 verts**
(audit_secu + copilote_events + dpe).
