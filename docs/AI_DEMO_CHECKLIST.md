# Checklist IA avant démo promoteur

> À dérouler **juste avant** une démo en ligne, une fois la clé posée sur le VPS (voir
> `docs/DEPLOYMENT_OVH_VPS.md` §11). Si une seule case « anti-hallucination » échoue → **retirer la
> clé** (`ANTHROPIC_API_KEY=` + `systemctl restart labuse`) : l'assistant reste premium en mode règles.
> Référence sécurité : `docs/AI_ASSISTANT_SAFETY_AND_DEMO.md`.

Parcelles de démo suggérées (Saint-Paul) : opportunité **97415000BK0023** · micro-opportunité
**97415000DE1325** (≤ 500 m²) · une parcelle **écartée** (filtrer « Écartée » sur la carte pour en
prendre une à jour). Adapter les IDU à l'état courant de la base.

## A. Activation (technique)

- [ ] **Clé présente** côté serveur : `ANTHROPIC_API_KEY` renseignée dans `/etc/labuse/labuse.env`
      (640 root:labuse, hors git). `LABUSE_ASSISTANT_MODEL=claude-sonnet-4-6`.
- [ ] **Service redémarré** après l'ajout : `sudo systemctl restart labuse` → `is-active` = `active`.
- [ ] **`/assistant/status` = `configured:true`** :
      `curl -fsS http://127.0.0.1:8000/assistant/status` → `{"configured":true}`
      (ne renvoie **qu'un booléen**, jamais la clé).
- [ ] **Bouton « Enrichir avec l'IA » visible** à l'ouverture d'une fiche (sinon : clé non lue → vérifier
      le fichier env + le restart).
- [ ] **Pas de clé dans les logs** : `journalctl -u labuse -n 100 | grep -i anthropic` → aucune valeur.

## B. Recette sur 3 fiches contrastées

Pour chaque IDU : ouvrir la fiche, cliquer **« Enrichir avec l'IA »**, lire la synthèse.

- [ ] **Opportunité** (ex. BK0023) : 5 blocs présents (Potentiel / Contraintes / Bâti-libre / Économie
      indicative / Recommandation) ; potentiel cohérent avec le verdict affiché.
- [ ] **Micro-opportunité** (ex. DE1325, ≤ 500 m²) : la synthèse mentionne la **petite surface** et
      oriente vers l'**assemblage** ; le verdict reste « opportunité ».
- [ ] **Parcelle écartée** : la synthèse **n'enjolive pas** — elle nomme la contrainte bloquante et
      recommande de ne pas prospecter.

## C. Anti-hallucination (bloquant)

- [ ] **Zéro invention** : aucun chiffre, prix, propriétaire, servitude, règlement ou contrainte qui ne
      figure **pas** dans la fiche. (Recouper avec « Le dossier complet ».)
- [ ] **Données manquantes citées** : la réponse liste explicitement les sources muettes / champs absents
      (ligne **Données manquantes**) et ne transforme jamais une absence en « pas de risque ».
- [ ] **Bilan présenté comme INDICATIF** : la charge foncière est qualifiée d'indicative/estimée ; jamais
      de promesse de rentabilité.
- [ ] **Jamais « constructible » ferme** : capacité décrite comme **ESTIMÉE**, avec renvoi à la vérif PLU/CU.
- [ ] **Fiabilité annoncée** : la réponse se termine par le niveau de fiabilité global.
- [ ] **Refus de conclure** sur une fiche à données minces (complétude faible / bilan non fiable) : la
      réponse dit clairement « à vérifier » plutôt que d'affirmer.

## D. Robustesse (dégradation)

- [ ] **Panne API simulée** (optionnel) : couper le réseau sortant ou utiliser une fiche pendant une
      indispo → la fiche affiche la **synthèse règles** + un message clair, **jamais** de 500 ni de bloc cassé.
- [ ] **Plan B assumé** : en cas de doute le jour J, démo **en mode règles** (retirer la clé) — déjà premium.

## E. Sécurité (rappel express)

- [ ] `git grep -i "sk-ant-"` dans le dépôt → **rien** (hors `sk-ant-test` des tests).
- [ ] `/etc/labuse/labuse.env` hors dépôt, permissions **640 root:labuse**.
- [ ] Aucun endpoint ne renvoie la clé ; `/assistant/status` = booléen seul.

---

*Tout vert en A + C → l'IA est prête pour la démo. Un échec en C → repasser en mode règles avant de montrer.*
