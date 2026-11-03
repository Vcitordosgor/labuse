-- ============================================================================
-- DEPLOY-JOHN-COPILOTE4 — migration de schéma tracée (prod labuse-vps)
-- Posée AVANT le redémarrage, hors charge (aucune session client, aucun VACUUM,
-- aucune passe calcul-nuit/Radar en cours). Cible : fcd545595 -> main (4f7504e70).
--
-- JOHN-TAYLOR-1 pose SEPT tables NEUVES. Dans le code, chaque module les crée
-- « paresseusement » au premier usage (CREATE TABLE IF NOT EXISTS via .ensure()),
-- hors du heal pré-service. Le mandat demande de les POSER AVANT le redémarrage,
-- en migration tracée : c'est ce fichier. Le DDL est COPIÉ À L'IDENTIQUE des
-- modules (john/journal.py, carnet.py, resume.py, veille.py, chat.py, actions.py)
-- => après cette migration, les .ensure() paresseux sont des no-op (IF NOT EXISTS).
--
-- Tout est NEUF et idempotent : aucune table existante n'est touchée, aucun
-- lecteur de l'ANCIEN code (fcd545595) ne lit ces tables. Sans risque, une seule
-- transaction. Ordre : conversations AVANT messages (FK ON DELETE CASCADE).
--
-- COPILOTE-4 ne requiert AUCUNE migration ici : ses tables
-- (copilote_conversations / copilote_messages) sont déjà posées par le heal
-- pré-service (étape « copilote_v2 »), la contrainte FK ON DELETE CASCADE et les
-- colonnes (sujet, payload) existent déjà, et la rétention 30 j est une valeur de
-- config (copilote_v2_retention_jours), pas du schéma.
-- ============================================================================

\timing on

BEGIN;

-- john_journal : journal des actions de John (y compris refus / échecs).
CREATE TABLE IF NOT EXISTS john_journal (
  id          bigserial PRIMARY KEY,
  ts          timestamptz NOT NULL DEFAULT now(),
  compte_id   integer,                 -- le compte admin à l'origine de l'ordre (None = système/test)
  compte      varchar(120),            -- libellé lisible (email/nom) pour le journal
  action      varchar(48) NOT NULL,    -- la clé d'action (liste fermée)
  args        jsonb NOT NULL DEFAULT '{}'::jsonb,
  confirme    boolean NOT NULL DEFAULT false,  -- vrai si l'action exigeait « tu confirmes ? »
  ok          boolean NOT NULL,
  resume      text                     -- une phrase sur le résultat (pour le journal lisible)
);

-- john_carnet : carnet de bord (décisions de Vic, incidents passés, doctrines).
CREATE TABLE IF NOT EXISTS john_carnet (
  id       bigserial PRIMARY KEY,
  cle      varchar(80) UNIQUE,              -- clé stable (idempotence du seed + anti-doublon)
  type     varchar(16) NOT NULL,            -- decision | incident | doctrine
  titre    text NOT NULL,
  corps    text NOT NULL,
  statut   varchar(12) NOT NULL DEFAULT 'actif',  -- actif | propose | rejete
  par      varchar(120),                    -- qui a posé / proposé la ligne
  cree_at  timestamptz NOT NULL DEFAULT now(),
  valide_at timestamptz
);

-- john_resume : résumé du matin (07:30) écrit par John.
CREATE TABLE IF NOT EXISTS john_resume (
  id      bigserial PRIMARY KEY,
  jour    date NOT NULL DEFAULT (now() AT TIME ZONE 'Indian/Reunion')::date,
  ts      timestamptz NOT NULL DEFAULT now(),
  urgent  boolean NOT NULL DEFAULT false,
  sujet   text NOT NULL,
  corps   text NOT NULL,
  par     varchar(12) NOT NULL DEFAULT 'john'   -- john | repli
);

-- john_veille : items de la veille de nuit (réglementaire / sources / concurrence).
CREATE TABLE IF NOT EXISTS john_veille (
  id       bigserial PRIMARY KEY,
  ts       timestamptz NOT NULL DEFAULT now(),
  axe      varchar(16) NOT NULL,        -- reglementaire | sources | concurrence
  titre    text NOT NULL,
  source   text NOT NULL,
  date_vue varchar(40),
  libelle  varchar(24) NOT NULL,        -- à intégrer | source B à valider | info | concurrence
  url      text,
  extrait  text
);

-- john_ecarts_acceptes : registre des écarts acceptés AVEC raison.
CREATE TABLE IF NOT EXISTS john_ecarts_acceptes (
  id     bigserial PRIMARY KEY,
  ts     timestamptz NOT NULL DEFAULT now(),
  ref    varchar(120) NOT NULL,
  raison text NOT NULL,
  par    varchar(120)
);

-- john_conversations : sessions de conversation (admin seul, rétention 90 j).
CREATE TABLE IF NOT EXISTS john_conversations (
  id         bigserial PRIMARY KEY,
  cree_at    timestamptz NOT NULL DEFAULT now(),
  maj_at     timestamptz NOT NULL DEFAULT now(),
  compte_id  integer,
  pending    jsonb                     -- action en attente de confirmation {action, args} | null
);

-- john_messages : messages d'une conversation (tombent par CASCADE avec la conv).
CREATE TABLE IF NOT EXISTS john_messages (
  id       bigserial PRIMARY KEY,
  conv_id  bigint NOT NULL REFERENCES john_conversations(id) ON DELETE CASCADE,
  ts       timestamptz NOT NULL DEFAULT now(),
  role     varchar(12) NOT NULL,        -- user | assistant
  contenu  text NOT NULL,
  sources  jsonb NOT NULL DEFAULT '[]'::jsonb
);

COMMIT;

\timing off
