# ÉTUDE V6-2 — Lot 3 : stationnement en sous-sol + bornes 60/75 s + vitesse < 20 s

## 1. Bornes & timeouts (mandat §1)
Borne du moteur portée de **30 → 60 s** ; tout ce qui attend derrière aligné sur **~75 s** (15 s de marge).
- App : `api/modules.py` `_ETUDE_TIMEOUT_S = 60`. Le message « Étude trop lourde » reste à la borne (503).
- Front : `lib/api.ts` `ETUDE_FETCH_TIMEOUT_MS = 75_000` (sur `postEtude` + le PDF) — garde-fou réseau.
- nginx : `deploy/nginx/labuse.conf` `proxy_read/send_timeout 75s`. Caddy : `deploy/Caddyfile.prod`
  `transport http { read_timeout 75s }`. uvicorn : `deploy/systemd/labuse.service` `--timeout-keep-alive 75`.
- **Aucune modification directe sur le VPS** : fichiers + geste de prod pour Vic dans
  `docs/deploiement/etude-v6-2-timeouts.md`.
- Pendant le calcul, l'écran affiche **« Calcul en cours, jusqu'à une minute… »** (étape 3 + bouton).

## 2. Stationnement en sous-sol (mandat Lot 3 d'origine)
- **Toggle** dans « Hypothèses modifiables » : **Aérien (défaut) / Sous-sol**.
- **Places au niveau −1** : en sous-sol, aucune place aérienne ; le sol reste libre pour le bâti → **plus
  de logements** (le parking ne mange plus l'assiette). `poser_sous_sol` enregistre places + emprise + rampe.
- **Rampe au sol** : un objet « rampe » (≈ 4 × 6 m) adossé à la voie, dans l'espace libre.
- **Emprise sous-sol ≤ emprise réglementaire** : contrôle dédié **« Emprise du sous-sol » ≤ CES × contenance**
  (`places × 25 m²/place` enterrés, rampes + circulation comprises, convention `m2_par_place_sous_sol`).
  C'est CE contrôle (pas le comptage) qui plafonne la capacité en sous-sol.
- **« Testez en sous-sol »** : CTA affiché dans « Ce qui limite » **quand le stationnement AÉRIEN plafonne**
  (facteur limitant prouvé, Lot 2). Un clic bascule le mode ET relance en un appel.
- **Même study_id → même PDF** : `stationnement` entre dans l'empreinte `_study_id` → l'aérien et le
  sous-sol ont des study_id DISTINCTS ; pour une config donnée, l'écran et le PDF partagent le même id
  et les mêmes chiffres (verrou inchangé).
- **Recette Étang-Salé 23 T2 + 6 T3** : aérien → maximum **32 R+3** (parking plafonne, −16 logts prouvé) ;
  sous-sol → maximum **48 R+3**, **48 places au −1**, emprise enterrée **1 200 m² ≤ emprise réglementaire**,
  rampe ~20 m² au sol. (Repère architecte : 29 logts R+3, 31 places.)

## 3. Vitesse < 20 s en local (mandat §2)
- La **capacité maximale** ne fait plus de 2ᵉ recherche : c'est le meilleur candidat FAISABLE de la
  recherche PRINCIPALE (même répartition que la demande) → ≥ toute variante dessinée (cohérent) et **stable**
  (deux demandes de même répartition → même maximum). Suppression de la recherche « équilibre » séparée.
- Le **contrefactuel « sans places »** (facteur stationnement) est LU dans la trace de cette même recherche
  (on lève les deux contrôles que le parking consomme : Stationnement + Perméabilité pleine terre, et
  l'Emprise du sous-sol en mode enterré) — aucun 2ᵉ passage.
- Le **sous-sol est calculé seulement au clic** « Testez en sous-sol » (requête séparée) → l'étude aérienne
  par défaut reste rapide.
- **Mesures locales** : Étang-Salé aérien ≈ **13 s**, sous-sol ≈ **3 s** ; Saint-Denis aérien ≈ **19 s**
  (< 20), sous-sol plus rapide. (Avant la refonte : Saint-Denis ≈ 25 s.)

## Tests
- `tests/test_etude_v6_capacite.py` (reel) : sous-sol libère le sol (sous-sol > aérien en logements),
  places au −1, aucune place aérienne, contrôle « Emprise du sous-sol », study_id distinct, < 30 s.
  + capacité stable entre deux demandes (Lot 2, inchangé).
- `EtudeV6.test.tsx` (Lot 3) : le CTA « Testez en sous-sol » apparaît quand l'aérien plafonne et relance
  en `stationnement: sous_sol` ; le résultat sous-sol affiche places au −1 + emprise + rampe.

## Vérifié
- **tsc 0 · vitest 293/293** (EtudeV6 15/15). **pytest** capacité/sous-sol (reel). **chasse_docs 20·0·0 ·
  chasse_donnees 23·0·2 SKIP.**
- Captures `captures/lot3-aerien-cta-sous-sol.png` (CTA) + `lot3-apres-sous-sol.png` (résultat sous-sol).
