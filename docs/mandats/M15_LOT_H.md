# M15 — LOT H : Sources — statut de fraîcheur « dernière version »

**Branche** : `fix/m15-h-sources-fraicheur` · Build 0 erreur · Golden 116/116 (`LABUSE_DEV_MODE=1`). Preuve `qa/m15/H/h1_trois_etats.png`. Suite de M14-E + audit M14-A1.

## Principe (Vic)
Ce qui compte : que **la version consultée soit la dernière qui existe**, pas « vérifié tel jour ». Un INSEE 2021 est à jour si l'INSEE n'a rien publié depuis. → statut centré sur la **version**, plus sur une date de contrôle.

## H1 — Trois états (selon `source_radar.statut`, cf. LOT A)
- **Sondable + à jour** (`a_jour`) → **« ✓ Dernière version disponible »** (menthe). Le ✓ est **vérifié par le radar** (aucune version plus récente côté producteur), jamais déclaratif. Title = date du dernier passage.
- **Sondable + en retard** (`nouvelle_publication`) → **« ▲ Nouvelle version publiée »** (ambre) — ré-ingestion à faire. **Implémenté** ; aucun source n'est actuellement dans cet état (les 9 sondables sont à jour) — l'état s'affichera dès qu'une publication amont sera détectée.
- **Non sondable** (`non_sondable`) → **« le producteur publie [cadence] »** (factuel, gris). Aucune promesse de vérification. **Jamais de « — » nu.**

## H2 — Marqueur sondable / non sondable (discret, non anxiogène)
Sur la ligne du nom : **« ✓ vérifiée auto »** (menthe, 9 sondables) vs **« cadence producteur »** (gris, 43 non sondables). Titles explicites : une source « cadence producteur » **n'est PAS douteuse** — son producteur n'expose simplement pas de date interrogeable.

**Couverture réelle** : **9 sources vérifiées automatiquement** (BODACC, BAN, Cadastre Etalab, DEAL côte, DPE ADEME, DVF, SRU, QPV, SITADEL) / **43 déclaratives**. Conforme à l'audit M14-A1.

## H3 — Version en service complétée
Filosofi = « millésime 2021 ». BPE INSEE / SAFER = « millésime non tracé en base » (repli honnête, non inventé — à renseigner en prod).

## H4 — Aucun 48 h fictif
Le ✓ « Dernière version disponible » repose sur la **cadence réelle du radar** (hebdomadaire), pas sur une promesse de 48 h. Si Vic passe le radar à 48 h (1 ligne de cron), l'affichage ne change pas. Rien de fictif.

## Preuve (Playwright)
« ✓ Dernière version disponible » ✓, « le producteur publie » ✓, marqueurs « ✓ vérifiée auto » (9) et « cadence producteur » (43) ✓, **aucun « — » nu** ✓.
