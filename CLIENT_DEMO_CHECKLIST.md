# LA BUSE — Checklist avant rendez-vous client

> À dérouler **la veille**, puis **le matin même** (10 minutes). Tout doit être vert
> AVANT de partir — rien ne s'improvise devant un promoteur.

## Infrastructure (la veille)

- [ ] **Serveur joignable** : `ssh` OK ; `docker compose -f docker-compose.pilot.yml ps`
      → db healthy, app running, caddy running.
- [ ] **HTTPS actif** : `curl -s https://<domaine>/healthz` → `{"status":"ok"}`,
      certificat valide, `http://` redirige vers `https://`.
- [ ] **/readyz** : `curl -s https://<domaine>/readyz` → HTTP 200, `"ready":true`.
- [ ] **prepare-pilot** : `docker compose … exec app labuse prepare-pilot`
      → `✅ PILOTE PRÊT` (≈ 6 s si déjà prêt — sinon il répare et le dit).
- [ ] **Backup fait** : `ls -lh backups/` → dump du jour (~240 Mo) **et** une copie
      HORS du serveur (`backups/backup.log` sans ÉCHEC).

## Application (le matin)

- [ ] **Login OK** depuis un navigateur externe : `/` → page de connexion ; mauvais mot
      de passe refusé ; bon mot de passe → carte. `/stats` en navigation privée → 401.
- [ ] **demo-status** : panneau « 🎬 Démo guidée » → **✅ Démo prête** (ou
      `exec app labuse doctor --json` → `ready_for_demo: true`).
- [ ] **warm-demo OK** : `exec app labuse warm-demo` → `✅ 8/8 … conformes et exportables`.
- [ ] **8 parcelles de démo** ouvertes une fois chacune (instantanées si cache chaud) :
      BK0023 (opportunité VACANTE+bilan) · BV0912 (bâti léger signalé) · BN1351 (PPR→à creuser) ·
      BH0283 (SAR compatible) · BO0845 (parking déclassé) · BV1431 (pente) ·
      BO0619 (micro-parcelle) · BP0571 (résidence détectée — correctif déjà bâti).
- [ ] **Exports OK** : export HTML de BK0023 ouvert, propre (résumé, bilan, disclaimers) —
      en garder un sous la main (pièce jointe de secours).
- [ ] **Pipeline non vide** : Kanban avec les entrées de démo (aucun nom réel).

## Humain

- [ ] **Mot de passe pilote prêt** à transmettre (canal séparé — jamais par l'écran partagé).
- [ ] **Réseau du lieu testé** : la carte charge (tuiles CARTO/IGN + unpkg) depuis le
      réseau où aura lieu la démo ; sinon prévoir partage 4G.
- [ ] **Discours limites prêt** (DEMO_PACK.md §I) : pré-analyse sur données publiques ;
      « opportunité vérifiée » = contrôlée sur les couches disponibles, **pas** une
      garantie de constructibilité ; bilan = simulation indicative ; propriétaire à
      identifier (manuel) ; SAR partiel ; PPR = prescriptions à vérifier.
- [ ] Plan B : export HTML/PDF des fiches clés si le réseau tombe.

**Un seul ✗ ci-dessus = on répare avant le rendez-vous, pas pendant.**
