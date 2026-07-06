# NOTES INPI RNE — Vague A3

## État : TEMPS 1 (reconnaissance) — BLOQUÉ à l'étape 1 (connexion SFTP)

### Fait
- Branche `ingestion/inpi-rne` créée (jamais sur `main`).
- Identifiants présents dans `.env` (gitignoré) : `INPI_SFTP_USER`, `INPI_SFTP_PASSWORD`. Jamais lus en clair, jamais commités.
- Tooling prêt : `paramiko` 5.0.0 installé, `sftp`/`ssh` CLI dispo, `expect` dispo.

### Blocage réseau — `www.inpi.net` injoignable depuis cette machine
Diagnostic (05/07/2026) :

| Cible | Résultat |
|---|---|
| `www.inpi.net` DNS | résout → `82.210.44.40` |
| `www.inpi.net:22` (SFTP) | **timeout** (paquet silencieusement drop) |
| `www.inpi.net:2222` | **timeout** |
| `www.inpi.net:443` | **timeout** |
| `ping www.inpi.net` | **100 % packet loss** |
| `github.com:22` (témoin SSH) | ✅ OK |
| `https://api.ipify.org` (témoin egress HTTPS) | ✅ OK |

**Conclusion** : l'egress SSH/HTTPS de la machine fonctionne (témoins OK). C'est
l'hôte `82.210.44.40` qui *drop tous les ports + ICMP* pour notre source →
signature classique d'un **firewall à liste blanche d'IP source**. INPI provisionne
l'accès SFTP par compte et il est documenté que des IP sont bloquées (volume / non
déclarées). Notre IP publique de sortie n'est vraisemblablement pas déclarée.

**IP publique de sortie à déclarer chez INPI : `83.204.133.163`** (résidentielle
Orange, potentiellement dynamique — à re-vérifier avant chaque campagne, ou prévoir
une IP de sortie stable).

### Action requise de Vic (avant de pouvoir reprendre la reco)
Une des options :
1. Déclarer / whitelister l'IP `83.204.133.163` dans l'espace INPI
   (« Mes accès API / SFTP »), puis me redonner le feu vert.
2. OU confirmer le bon hôte/port si `www.inpi.net:22` n'est pas la bonne cible.
3. OU fournir une IP de sortie stable (VPN/bastion) qui sera whitelistée.

Tant que la connexion ne passe pas, **impossible** de faire les étapes 2-4 de la
reco (arborescence, volume, échantillon JSON, stratégie) — elles en dépendent toutes.

---

---

## MàJ 05/07/2026 — bascule SFTP → API REST RNE (auth OK)

SFTP abandonné (firewall IP). On passe par l'**API REST publique RNE** :
`https://registre-national-entreprises.inpi.fr/api`.

- Auth : `POST /api/sso/login` `{"username","password"}` avec le **compte portail**
  (`INPI_API_USERNAME`/`INPI_API_PASSWORD` dans `.env`), après activation « accès API »
  côté INPI. → `200` `{token, user}` (token JWT ~1100 car.).
  Couches d'erreur traversées : creds SFTP → `401 identifiants invalides` ;
  compte non activé → `403 connection_type_not_allowed` ; activé → `200`.
- Lecture : `GET /api/companies/{siren}` header `Authorization: Bearer {token}`.

### Chemins de champs VÉRIFIÉS sur SCI ALOE (siren 913037362), pas devinés
Racine : `formality.content.personneMorale` (= `pm`).
- **SIREN** : `pm.identite.entreprise.siren` (aussi racine `siren`).
- **Forme juridique** : `pm.identite.entreprise.formeJuridique` = `"6540"` (code Insee ; 6540=SCI).
  Aussi `formality.formeJuridique` et `formality.content.natureCreation.formeJuridique`.
- **Dirigeants** : `pm.composition.pouvoirs[]` (n = `nombreRepresentantsActifs`).
  Chaque pouvoir a `typeDePersonne` = `INDIVIDU` | `ENTREPRISE` :
  - INDIVIDU → `pouvoirs[].individu.descriptionPersonne` :
    - **date de naissance** : `.dateDeNaissance` = `"1977-06"` → format **AAAA-MM**
      (mois, jamais le jour — granularité diffusible RGPD). ← **signal A3 (âge dirigeant)**.
    - `.nom`, `.prenoms[]`, `.role` (code rôle), flag `.dateDeNaissancePresent`.
    - **prise de fonction** : `.dateEffetRoleDeclarant` (champ existe mais **absent** sur
      SCI ALOE : `dateEffetRoleDeclarantPresent=false`). → peuplé de façon INCONSTANTE.
  - ENTREPRISE → `pouvoirs[].entreprise` (`siren`,`denomination`,`formeJuridique`) : le
    dirigeant est une personne morale (pas d'âge direct — cf. dirigeants gigognes).
  - `roleEntreprise` : "30" observé sur le gérant individu, "99" (autre) sur les PM.
- **Diffusion RGPD** : `formality.diffusionCommerciale`, `formality.diffusionINSEE`.
  Sur SCI ALOE : `True`/`O` → dirigeant physique diffusible, `dateDeNaissance` présente.

### ⚠️ Procédures collectives : ABSENTES de `/api/companies/{siren}`
Recherche exhaustive sur le JSON : 0 occurrence de procedure/liquidation/redressement/
sauvegarde/jugement/radiation/dissolution/observation/cessation. **Cet endpoint ne porte
PAS le signal procédure.** → Le recoupement BODACC (bonus du brief) n'est PAS faisable via
`/companies`. Les procédures restent sourcées **BODACC (A1)** — déjà en base. Si on veut
vraiment les procédures via RNE, il faudra explorer un autre endpoint (actes/évènements) —
mais non nécessaire, doublon avec BODACC.

### Points d'attention pour la stratégie d'ingestion
- **1 requête = 1 SIREN** (pas de batch observé). ~9 697 SIREN → throttle + pagination à
  prévoir ; le token expire (à gérer : re-login). Vérifier quotas/rate-limit avant la passe.
- **Dirigeants gigognes** : quand tous les dirigeants sont des PM (ex. SCI gérée par SCI/SAS),
  pas d'âge direct → soit on remonte au SIREN gérant, soit pas de signal âge pour ce SIREN.
- `dateDeNaissance` au mois → l'âge est calculable à ±1 an, suffisant pour le signal.

---

## MàJ 05/07/2026 — TEMPS 2 (ingestion) construit

Branche `ingestion/inpi-rne`. Commit séparé fix vue BODACC (SIREN normalisé) déjà posé.

- **Connecteur** `src/labuse/connectors/inpi_rne.py` : login+refresh JWT (décodage `exp`,
  re-login proactif -60 s + sur 401), `GET /companies/{siren}`, retry/backoff 429/5xx,
  parsing pur (`parse_company`, `compute_age`, `propension_band`). Identifiants en env
  `INPI_API_*` (chargés de `.env`, jamais en dur).
- **Table** `pm_dirigeants` (ORM, models.py) + **vues** `v_pm_propension_vendre` (grain SIREN,
  âge de l'aîné recalculé à la requête, `age_source` direct/aucun_individu/sans_dirigeant,
  `propension_band`) et `v_foncier_propension_vendre` (grain parcelle). `ensure_pm_propension_view`
  ajouté à `create_all` ET `ensure_schema`. Tag `# TODO étage 2` — NON branché au score.
- **Ingestion** `src/labuse/ingestion/inpi_rne.py` : `eligible_sirens` (9 chiffres, exclut
  groupes publics 1/2/3/4/9 — « dans le doute garder »), `ingest_inpi_rne` (upsert idempotent),
  `sample_report`. Île = **9 579 SIREN**, Saint-Paul = **1 569**.
- **`data_sources`** : ligne « INPI RNE (dirigeants) » (seed_sources.py).
- **Tests** `tests/test_inpi_rne.py` : 12 passent (âge, bande, parsing, RGPD non-diffusible,
  refresh jeton, éligibilité, signal aîné, taux gigogne, pas de faux signal, idempotence).

### RGPD — garde effective
`_parse_pouvoir` n'attache nom/prénoms/naissance d'une personne physique QUE si l'entreprise
est diffusible (`diffusionCommerciale`). Les dirigeants personnes morales (open data) gardent
leur SIREN (`gerant_siren`) pour la mesure gigogne.

### Reste (après validation échantillon par Vic)
- Feu vert pour l'île entière (9 579 SIREN), chunké/résumable (runner /tmp/run_inpi_sample.py
  → à intégrer proprement en `ingestion/run_all` ou commande CLI si Vic valide).
- Décision récursion gigogne selon le taux mesuré sur Saint-Paul.

---

## MàJ 05/07/2026 — passe île + récursion gigogne depth-1

### Passe île entière (depth-0) — LANCÉE
Commande `labuse ingest-inpi-rne` (résumable/chunkée). Île = 9 579 SIREN ; échantillon
Saint-Paul (1 515) déjà en base → `--resume` traite les 8 064 restants (~90 min).
Échantillon Saint-Paul validé par Vic : **taux gigogne 20,5 %**, âges min 22 / médiane 64 /
max 104, 1 971 parcelles à gérant âgé. Âges extrêmes = fiches non mises à jour (→ A2 décès affinera).

### ⏸️ Gigogne depth-1 — EN PAUSE (rate-limit INPI), reprise = `labuse ingest-inpi-gigogne`
Lancée sur l'île (918 cibles suivables), **crashée puis rate-limitée** :
- 1ʳᵉ tentative : crash sur HTTP 429 persistant → corrigé (commit résilience : backoff
  exponentiel 6 essais + une cible en échec est SAUTÉE, plus de crash).
- Reprise (throttle 1 s) : INPI **429 sur chaque `GET /companies`** (login SSO OK, lecture
  bridée) suite aux ~9 000 requêtes depth-0 + tentatives gigogne → mise en PAUSE pour ne pas
  taper une API bridée.
- **État persisté : 187 / 918 cibles résolues** (870 lignes `pm_dirigeant_gigogne`). Ces 187
  sont passées `age_source='gerant_societe'` dans la vue ; reste **731 cibles**.
- **REPRISE (quota probablement QUOTIDIEN — réessayer le lendemain)** : relancer simplement
  `labuse ingest-inpi-gigogne` (résumable : les résolues sortent d'elles-mêmes du périmètre
  `aucun_individu`, repart sur les 731 restantes). Pas de sonde auto (choix Vic).
- Table `pm_dirigeant_gigogne` + vue enrichie DÉJÀ en prod (créées au 1er lancement).

### Récursion gigogne depth-1 — détail technique
Itération séparée (commits dédiés). `resolve_gigogne()` / commande `ingest-inpi-gigogne`.
- Table `pm_dirigeant_gigogne` (depth-0 `pm_dirigeants` NON modifiée).
- Vue `v_pm_propension_vendre` : fallback → `age_source='gerant_societe'` (COALESCE direct, gigogne).
- Bornée à 1 niveau (jamais les gérants des gérants), auto-référence écartée (`gerant<>cible`),
  cache de run (un gérant requêté une fois) → pas de boucle.
- ⚠ Pas encore de commande CLI dédiée ni d'application au schéma de la BASE RÉELLE (la vue réelle
  référencera `pm_dirigeant_gigogne` : créer la table AVANT de rejouer `ensure_pm_propension_view`
  en prod — fait automatiquement par `create_all`/`ensure_schema`, mais à vérifier avant lancement).
- 5 tests : résolution, cycle, borne 1 niveau, priorité au direct, idempotence. Total A3 = 17 tests.

## MàJ 06/07/2026 — rendement gigogne plafonné par `diffusionCommerciale` (VOULU, pas un bug)

Diagnostic (série de `+0 physiques` malgré une API qui répond) : les gérants-sociétés suivis en
depth-1 sont souvent **`diffusionCommerciale=False`** (cabinets d'audit, holdings — ils optent
fréquemment pour la non-diffusion commerciale). Or la garde RGPD de `_parse_pouvoir`
(`connectors/inpi_rne.py:180`, `if diffusible:`) n'attache nom/prénoms/`date_naissance` QUE si
l'entreprise est diffusible.

⚠ L'API RENVOIE pourtant la date pour ces sociétés (vérifié 06/07 : gérant 338113954 « SFG LA
VOUGERAIE », dirigeant BINDSCHEDLER `dateDeNaissance=1938-02`, `dateDeNaissancePresent=True`) — on
la NULLE nous-mêmes, à dessein, car on est un outil de prospection COMMERCIALE et on respecte
l'opt-out `diffusionCommerciale` (**décision Vic 06/07 : option A, on garde ce comportement**).

Conséquences (assumées, PAS un bug) :
- Le **rendement gigogne est structurellement plafonné** : seules les cibles dont le gérant est
  DIFFUSIBLE se résolvent (les 187 d'hier étaient diffusibles). Les séries de `+0` = séries de
  gérants non diffusibles → normal.
- La **population `age_source='aucun_individu'` est GONFLÉE** : une société non diffusible qui a
  pourtant un gérant PHYSIQUE voit sa date nullée → elle apparaît `aucun_individu` (et devient une
  cible gigogne qui ne pourra pas résoudre non plus). Donc « aucun_individu » ≠ « réellement sans
  personne physique ».
- La passe en cours capte les diffusibles ; on la laisse finir. (Option B « âge seul sans nom pour
  non-diffusibles » = écartée pour l'instant.)

## Hors périmètre repéré (à ne PAS faire sans validation)
- Procédures collectives via RNE : nécessiterait un autre endpoint (actes/évènements) — non fait,
  doublon avec BODACC A1. À ne PAS ajouter sans demande explicite.
- Erreur ruff **pré-existante** I001 dans `cli.py` (bloc d'imports de `warm-vue-mer`, ligne ~410) :
  antérieure à cette session, PAS corrigée (hors périmètre). `ruff --fix` la réglerait.
