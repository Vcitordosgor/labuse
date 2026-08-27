"""PREMIER EURO · E3/E4 — pages serveur : onboarding founding + légales + webhook Stripe.

Parcours (décisions Vic) : invitation (lien signé, email pré-rempli) → mot de passe sur la
façade Coffre → acceptation CGV (checkbox HORODATÉE + version, loggée) → Stripe Checkout
(founding appliqué, montant visible côté Stripe) → retour → compte actif au webhook.
Pages rendues serveur dans la nuit Coffre — la façade React n'est pas touchée.
"""
from __future__ import annotations

import html
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from . import coffre_ui
from ..config import get_settings

log = logging.getLogger("labuse.onboarding")
router = APIRouter(tags=["onboarding"])


def get_db():
    from .app import get_db as _g
    yield from _g()


# ── le gabarit Coffre serveur — délègue au design system validé (coffre_ui, partie E) ──

def _page(titre: str, corps: str, large: bool = False, head: str = "", pied: bool = True) -> str:
    footer = ('<p class="note">Radar foncier · La Réunion — <a href="/cgv">CGV</a> · '
              '<a href="/mentions-legales">mentions légales</a> · '
              '<a href="/confidentialite">confidentialité</a></p>') if pied else ""
    return coffre_ui.page(titre, coffre_ui.OISEAU + corps + footer,
                          w=760 if large else None, legal=large, head=head)


# ── E4 · invitation → mot de passe + CGV → Checkout ──

@router.get("/invitation", include_in_schema=False)
def invitation_page(token: str = "", db: Session = Depends(get_db)):
    from ..comptes import PLANS, valider_invitation
    inv = valider_invitation(db, token) if token else None
    if not inv:
        return HTMLResponse(_page("invitation", """
<h1>Invitation introuvable</h1><p class="sous">lien expiré ou déjà utilisé</p>
<p style="text-align:center;font-size:12.5px">Demandez un nouveau lien à votre contact LABUSE —
les invitations expirent après 7 jours.</p>"""), status_code=404)
    p = PLANS.get(inv["plan"], PLANS["integral"])
    return HTMLResponse(_page("créer votre accès", f"""
<h1>Créer votre accès</h1>
<p class="sub">licence {p['label']} · {p['eur_mois']} €/mois · engagement 12 mois</p>
<p style="text-align:center;font-size:12.5px;color:var(--mut);margin:-2px 0 20px">Votre e-mail est déjà validé par l'invitation. Choisissez un mot de passe et vous entrez dans le radar foncier de La Réunion.</p>
<form method="post" action="/invitation" novalidate>
<input type="hidden" name="token" value="{html.escape(token)}">
<label for="email">E-mail</label>
<div class="field"><input id="email" type="email" autocomplete="email" value="{html.escape(inv['email'])}" disabled
  aria-label="Votre e-mail (fixé par l'invitation)"></div>
<label for="password">Choisissez un mot de passe</label>
<div class="field"><input id="password" name="password" type="password" minlength="10" required
  autocomplete="new-password" autofocus aria-describedby="rules" oninput="labStrength(this.value)"></div>
<div class="meter" id="meter" aria-hidden="true"><i></i><i></i><i></i></div>
<div class="meterlbl" id="rules" role="status" aria-live="polite">10 caractères minimum — mélangez lettres, chiffres et symboles.</div>
<div class="consent"><input type="checkbox" id="cgv" name="cgv" value="oui" required aria-required="true" onchange="labCgv()">
<label for="cgv">J'ai lu et j'accepte les <a href="/cgv" target="_blank">conditions générales</a>.</label></div>
<button type="submit" id="cta" disabled aria-disabled="true">Continuer vers le paiement →</button>
<p class="meterlbl" id="cgverr" role="status" aria-live="polite" style="text-align:center;margin-top:8px">Vous devez d'abord accepter les conditions générales pour continuer.</p>
</form>
<p class="note">Paiement sécurisé par Stripe — aucune donnée de carte ne transite par LABUSE.</p>
<script>
// M18-A2 : le bouton reste INACTIF tant que les CGV ne sont pas cochées (plus de cul-de-sac).
function labCgv(){{var c=document.getElementById('cgv'),b=document.getElementById('cta'),e=document.getElementById('cgverr');var on=c.checked;b.disabled=!on;b.setAttribute('aria-disabled',String(!on));e.style.display=on?'none':'block';}}
labCgv();
</script>""",
                        head=coffre_ui.STRENGTH_JS))


@router.post("/invitation", include_in_schema=False)
async def invitation_submit(request: Request, db: Session = Depends(get_db)):
    from urllib.parse import parse_qs

    from ..comptes import activer_par_invitation, audit
    q = parse_qs((await request.body()).decode("utf-8", "replace"))
    token = (q.get("token") or [""])[0]
    password = (q.get("password") or [""])[0]
    cgv = (q.get("cgv") or [""])[0] == "oui"
    if not cgv:
        # M18-A2 : plus de cul-de-sac — un retour vers le formulaire existe toujours.
        return HTMLResponse(_page("conditions", f"<h1>Conditions requises</h1>"
                                  f"<p class='sous'>vous devez d'abord accepter les conditions générales pour continuer</p>"
                                  f"<p style='text-align:center;margin-top:18px'><a class='pill' href='/invitation?token={html.escape(token)}'>← Revenir</a></p>"),
                            status_code=400)
    s = get_settings()
    try:
        inv = activer_par_invitation(db, token, password, s.cgv_version)
    except ValueError as e:
        return HTMLResponse(_page("mot de passe", f"<h1>Mot de passe refusé</h1><p class='sous'>{html.escape(str(e))}</p>"
                                  f"<p style='text-align:center'><a href='/invitation?token={html.escape(token)}'>revenir</a></p>"),
                            status_code=400)
    if not inv:
        return RedirectResponse("/invitation", status_code=303)
    audit(db, "cgv_acceptees", inv["compte_id"], inv["id"], f"version={s.cgv_version}")
    db.commit()
    # DASHBOARD-V1 · D9 — compte d'ESSAI (déjà ACTIF, échéance posée par l'admin) : pas de
    # Checkout — l'accès est ouvert tout de suite, la porte est /login. À l'échéance, la
    # bascule automatique (suspension) proposera l'abonnement.
    from sqlalchemy import text as _text
    row = db.execute(_text("SELECT statut, essai_expire_at FROM comptes WHERE id = :c"),
                     {"c": inv["compte_id"]}).mappings().first()
    # VPS · AC-020 — compte INTERNE déjà actif SANS échéance d'essai (admin nominatif créé
    # par `labuse creer-admin`) : rien à payer, la porte est /login (avec 2FA pour un admin).
    if row and row["statut"] == "actif" and row["essai_expire_at"] is None:
        return HTMLResponse(_page("accès ouvert", """
<h1>Votre accès est ouvert</h1>
<p>Mot de passe enregistré — votre compte est actif, rien à régler.</p>
<p style="margin-top:26px;text-align:center"><a href="/login" style="display:inline-flex;align-items:center;gap:8px;background:var(--mint);color:var(--mint-ink);font:600 15px inherit;padding:15px 32px;border-radius:var(--r);text-decoration:none">Entrer dans LABUSE →</a></p>"""))
    if row and row["statut"] == "actif" and row["essai_expire_at"] is not None:
        return HTMLResponse(_page("essai", """
<h1>Votre accès d'essai est ouvert</h1>
<p>Compte activé — vous disposez de l'accès complet à LABUSE pendant la durée de l'essai.
À l'échéance, l'accès se met en pause (vos données restent intactes) et un abonnement
vous sera proposé.</p>
<p style="margin-top:26px;text-align:center"><a href="/login" style="display:inline-flex;align-items:center;gap:8px;background:var(--mint);color:var(--mint-ink);font:600 15px inherit;padding:15px 32px;border-radius:var(--r);text-decoration:none">Entrer dans LABUSE →</a></p>"""))
    # → ÉCRAN DE BASCULE Checkout (partie E) : le moment d'anxiété est adressé par une page
    # de confiance AVANT Stripe. La mécanique de paiement (creer_checkout/webhook) est
    # inchangée — seul un écran présentational + un jeton signé s'ajoutent.
    return RedirectResponse(f"/onboarding/paiement?t={coffre_ui.pay_token(inv['compte_id'])}",
                            status_code=303)


# ── PARTIE E · surface 4 — LA BASCULE VERS CHECKOUT (le point d'anxiété : rassurer) ──

@router.get("/onboarding/paiement", include_in_schema=False)
def paiement_bascule(t: str = "", db: Session = Depends(get_db)):
    from ..comptes import PLANS
    cid = coffre_ui.pay_cid(t)
    if cid is None:
        return HTMLResponse(_page("paiement", "<h1>Lien expiré</h1><p class='sub'>reprenez "
                                  "depuis la porte</p><p style='text-align:center'>"
                                  "<a href='/login'>se connecter</a></p>"), status_code=400)
    p = PLANS["integral"]
    return HTMLResponse(_page("votre abonnement", f"""
<h1>Votre abonnement</h1><p class="sub">dernière étape avant votre espace</p>
<div class="recap"><div class="prix">{p['eur_mois']} € <span style="font-size:14px;color:var(--mut);font-weight:400">/ mois</span></div>
<div class="quoi">Licence {p['label']} — accès complet. <b style="color:var(--txt)">Engagement 12 mois</b>, facturé mensuellement.</div></div>
<div class="trust" role="list">
  <div role="listitem">{coffre_ui.LOCK_SVG} Paiement <b style="color:var(--txt)">sécurisé par Stripe</b> — page hébergée, chiffrée.</div>
  <div role="listitem"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" stroke-width="1.5" aria-hidden="true"><path d="M10 2l6 3v5c0 4-3 6.5-6 8-3-1.5-6-4-6-8V5z"/><path d="M7.5 10l1.8 1.8L13 8"/></svg> <b style="color:var(--txt)">Aucune donnée bancaire</b> ne transite par LABUSE.</div>
  <div role="listitem"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" stroke-width="1.5" aria-hidden="true"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 1.5"/></svg> {p['eur_mois']} €/mois pendant 12 mois, puis reconduction par périodes de 12 mois — dénonçable avant chaque échéance (vous êtes prévenu à l'avance). Facture émise automatiquement.</div>
</div>
<form method="post" action="/onboarding/paiement"><input type="hidden" name="t" value="{html.escape(t)}">
<button type="submit">{coffre_ui.LOCK_SVG.replace('var(--mint)','currentColor')} Payer {p['eur_mois']} €</button></form>
<p class="note">Vous serez redirigé vers Stripe. Rien n'est débité tant que vous n'avez pas confirmé.</p>""",
                        pied=False))


@router.post("/onboarding/paiement", include_in_schema=False)
async def paiement_lancer(request: Request, db: Session = Depends(get_db)):
    from urllib.parse import parse_qs

    from sqlalchemy import text as _t
    t = (parse_qs((await request.body()).decode("utf-8", "replace")).get("t") or [""])[0]
    cid = coffre_ui.pay_cid(t)
    if cid is None:
        return RedirectResponse("/login", status_code=303)
    email = db.execute(_t("SELECT email FROM utilisateurs WHERE compte_id = :c LIMIT 1"),
                       {"c": cid}).scalar()
    # mécanique de paiement INCHANGÉE (auditée) : creer_checkout → Stripe ; repli honnête sans clé
    try:
        from ..facturation import creer_checkout
        return RedirectResponse(creer_checkout(db, cid, email or ""), status_code=303)
    except Exception as e:  # noqa: BLE001 — ConfigError (pas de clé) ou indispo Stripe
        log.warning("checkout indisponible compte %s : %s", cid, e)
        return HTMLResponse(_page("paiement", """
<h1>Compte créé — paiement à venir</h1><p class="sub">le paiement en ligne n'est pas encore ouvert</p>
<p style="text-align:center;font-size:12.5px">Votre mot de passe est enregistré et vos conditions
acceptées. Votre contact LABUSE vous enverra le lien de paiement sécurisé — l'accès s'ouvrira
au règlement.</p><p style="text-align:center"><a href="/login">retour à la porte</a></p>"""))


@router.get("/onboarding/retour", include_in_schema=False)
def onboarding_retour(ok: int = 1):
    if ok:
        return HTMLResponse(_page("bienvenue", """
<div class="big"><div class="mark ok" aria-hidden="true">✓</div>
<h1>Bienvenue chez LABUSE</h1><p class="sub">votre abonnement Intégral est actif</p>
<p style="font-size:13.5px;line-height:1.6;color:var(--txt)">Vous avez désormais accès à tout le radar
foncier de La Réunion — le scoring des parcelles, les fiches sourcées, les outils d'analyse et le dossier
banquier. Un guide de prise en main en 5 gestes vous attend dès votre première connexion.</p>
<p style="margin-top:26px"><a href="/login" style="display:inline-flex;align-items:center;gap:8px;background:var(--mint);color:var(--mint-ink);font:600 15px inherit;padding:15px 32px;border-radius:var(--r);text-decoration:none;box-shadow:0 8px 24px rgba(92,230,161,.30)">Entrer dans LABUSE →</a></p>
<p class="note" style="margin-top:16px">Connectez-vous avec votre e-mail et le mot de passe que vous venez de choisir.</p></div>""", pied=False))
    return HTMLResponse(_page("paiement interrompu", """
<div class="big"><div class="mark soft" aria-hidden="true">↺</div>
<h1>Paiement interrompu</h1><p class="sub">rien n'a été débité</p>
<p style="font-size:13px">Aucun souci. Reprenez quand vous voulez : connectez-vous sur
<a href="/login">la porte</a> avec votre email et votre mot de passe, le paiement se relancera.</p></div>""",
                        pied=False))


# ── E1 · reset mot de passe ──

@router.get("/reset", include_in_schema=False)
def reset_page(token: str = ""):
    if not token:
        # M18-A6 : vrai self-service — un formulaire, plus « écrivez à votre contact ».
        return HTMLResponse(_page("mot de passe oublié", """
<h1>Mot de passe oublié ?</h1><p class="sub">on vous envoie un lien de réinitialisation</p>
<form method="post" action="/reset-demande" novalidate>
<label for="email">Votre e-mail</label>
<div class="field"><input id="email" name="email" type="email" required autofocus
  autocomplete="email" inputmode="email" autocapitalize="none" spellcheck="false"
  placeholder="prenom.nom@cabinet.re" aria-required="true"></div>
<button type="submit">Recevoir le lien →</button></form>
<p class="linkrow"><a href="/login">← Retour à la connexion</a></p>"""))
    return HTMLResponse(_page("nouveau mot de passe", f"""
<h1>Nouveau mot de passe</h1><p class="sub">choisissez-le soigneusement</p>
<form method="post" action="/reset" novalidate>
<input type="hidden" name="token" value="{html.escape(token)}">
<label for="password">Nouveau mot de passe</label>
<div class="field"><input id="password" name="password" type="password" minlength="10" required
  autocomplete="new-password" autofocus aria-describedby="rules" oninput="labStrength(this.value)"></div>
<div class="meter" id="meter" aria-hidden="true"><i></i><i></i><i></i></div>
<div class="meterlbl" id="rules" role="status" aria-live="polite">10 caractères minimum.</div>
<button type="submit">Enregistrer</button></form>
<p class="note">Par sécurité, toutes vos sessions ouvertes seront fermées.</p>""",
                        head=coffre_ui.STRENGTH_JS))


def _envoyer_reset_email(email: str, lien: str) -> None:
    """M18-A6 → M21-B1 — POINT D'ENVOI du lien de réinitialisation, désormais BRANCHÉ sur le
    transport SMTP unique (`labuse.mail`). Envoi en tâche de fond (ne bloque pas la requête, pas de
    fuite de timing sur l'existence du compte). Sans SMTP configuré, `send_email` journalise le mail
    (lien inclus, = file d'attente dev) et ne prétend rien. Le token n'est jamais logué en clair
    hors de ce cas dev."""
    from ..emails import reset_password
    from ..mail import send_email_async

    sujet, corps = reset_password(lien)
    send_email_async(email, sujet, corps)
    log.info("[RESET-EMAIL] envoi déclenché → %s", email)


@router.post("/reset-demande", include_in_schema=False)
async def reset_demande(request: Request, db: Session = Depends(get_db)):
    # M18-A6 : mécanique COMPLÈTE (token 1 h + page reset). Anti-énumération : réponse identique
    # que le compte existe ou non. L'ENVOI réel s'active dès que l'e-mail sera branché (_envoyer_reset_email).
    from urllib.parse import parse_qs

    from ..comptes import demander_reset
    q = parse_qs((await request.body()).decode("utf-8", "replace"))
    email = (q.get("email") or [""])[0].strip()
    if email:
        try:
            res = demander_reset(db, email)
            if res:
                db.commit()
                _envoyer_reset_email(res["email"], res["lien"])
        except Exception:  # noqa: BLE001 — jamais bloquer, jamais révéler l'existence du compte
            pass
    # État HONNÊTE (boussole) : le message dépend de l'état du TRANSPORT (pas de l'existence du
    # compte — anti-énumération). SMTP branché → on annonce l'envoi (conditionnel « si un compte
    # existe ») ; SMTP absent (dev) → on ne prétend PAS qu'un e-mail est parti.
    from ..mail import mail_configured
    if mail_configured():
        corps = """<div class="big"><div class="mark ok" aria-hidden="true">✓</div>
<h1>Vérifiez votre boîte mail</h1><p class="sub">un lien valable 1 heure vient d'être envoyé</p>
<p style="font-size:13px;line-height:1.6">Si un compte est associé à cette adresse, un e-mail de
réinitialisation vient de lui être envoyé. Pensez à vérifier vos indésirables. Le lien expire dans 1 heure.</p>
<p style="margin-top:18px"><a class="pill" href="/login">← Retour à la connexion</a></p></div>"""
    else:
        corps = """<div class="big"><div class="mark ok" aria-hidden="true">✓</div>
<h1>Demande enregistrée</h1><p class="sub">un lien valable 1 heure a été généré</p>
<p style="font-size:13px;line-height:1.6">Si un compte est associé à cette adresse, un lien de
réinitialisation lui est destiné. <b style="color:var(--warn)">L'envoi automatique par e-mail n'est pas
actif sur cet environnement</b> — votre contact LABUSE peut vous le transmettre.</p>
<p style="margin-top:18px"><a class="pill" href="/login">← Retour à la connexion</a></p></div>"""
    return HTMLResponse(_page("demande enregistrée", corps, pied=False))


@router.post("/reset", include_in_schema=False)
async def reset_submit(request: Request, db: Session = Depends(get_db)):
    from urllib.parse import parse_qs

    from ..comptes import appliquer_reset
    q = parse_qs((await request.body()).decode("utf-8", "replace"))
    try:
        ok = appliquer_reset(db, (q.get("token") or [""])[0], (q.get("password") or [""])[0])
    except ValueError as e:
        return HTMLResponse(_page("mot de passe", f"<h1>Refusé</h1><p class='sous'>{html.escape(str(e))}</p>"),
                            status_code=400)
    if not ok:
        return HTMLResponse(_page("lien expiré", "<h1>Lien expiré</h1><p class='sous'>"
                                  "demandez un nouveau lien</p><p style='text-align:center'>"
                                  "<a href='/reset'>mot de passe oublié</a></p>"), status_code=400)
    return HTMLResponse(_page("mot de passe changé", """
<h1>Mot de passe changé</h1><p class="sous">toutes les sessions ont été fermées</p>
<p style="text-align:center;margin-top:18px"><a href="/login" class="pill">Se connecter →</a></p>"""))


# ── E2 · webhook Stripe (signé — la sécurité EST la signature) ──

@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    import stripe as _stripe
    from ..facturation import ConfigError, traiter_webhook
    payload = await request.body()
    try:
        r = traiter_webhook(db, payload, request.headers.get("stripe-signature"))
    except ConfigError as e:
        log.error("webhook stripe : %s", e)
        return JSONResponse({"detail": "webhook non configuré"}, status_code=503)
    except (_stripe.SignatureVerificationError, ValueError) as e:
        # REVUE · R6 — signature INVALIDE (ou payload illisible) = rejet sec 400. Distinct d'une
        # erreur de TRAITEMENT (ci-dessous) : le message trompeur « signature invalide » posé sur
        # toute exception masquait les vrais bugs de handler et empêchait le rejeu Stripe utile.
        log.warning("webhook stripe REJETÉ (signature) : %s", type(e).__name__)
        return JSONResponse({"detail": "signature invalide"}, status_code=400)
    except Exception as e:  # noqa: BLE001 — erreur de TRAITEMENT : 500 → Stripe REJOUE (idempotent)
        log.error("webhook stripe : échec de traitement %s: %s", type(e).__name__, e)
        return JSONResponse({"detail": "traitement du webhook en échec"}, status_code=500)
    return {"ok": True, **{k: v for k, v in r.items() if k != "compte_id"}}


# ── E3 · pages légales (drafts SOLIDES — relecture Vic obligatoire, avocat recommandé
#     avant premières signatures : noté au rapport ; non bloquant pour construire) ──

# M-P (point 5) : identité EI renseignée — SIRET connu 987 641 917 00016 (→ SIREN 987 641 917) ;
# établissement à SAINT-PAUL (Réunion), pas Saint-Denis. ⚠ RELIQUAT Vic : rue + code postal précis
# à compléter (l'adresse de rue exacte n'était pas fournie) ; e-mail de contact à brander ou assumer.
_EDITEUR = ("Victor L. — entrepreneur individuel (EI) · Saint-Paul, Île de La Réunion, France.<br>"
            "SIREN : <b>987&nbsp;641&nbsp;917</b> · SIRET : <b>987&nbsp;641&nbsp;917&nbsp;00016</b> · "
            "contact : kampusreunion@gmail.com")


@router.get("/cgv", include_in_schema=False)
def cgv_page():
    s = get_settings()
    return HTMLResponse(_page("conditions générales", f"""
<div class="legal">
<h1>Conditions générales de vente et d'utilisation</h1>
<p class="sous">version {s.cgv_version} — service LABUSE</p>
<p class="maj">Contrat B2B entre professionnels. L'acceptation est recueillie à la création du
compte (case à cocher horodatée, version consignée).</p>

<h2>1. Objet</h2>
<p>LABUSE est un service en ligne d'aide à la prospection foncière à La Réunion :
agrégation, croisement et lecture de <b>données publiques</b> (cadastre, urbanisme, risques,
marchés, publications légales), assortis d'indicateurs et d'analyses produits par des
traitements automatisés.</p>

<h2>2. Nature des analyses — la clause boussole</h2>
<p>Les scores, verdicts, badges, estimations et synthèses fournis par LABUSE constituent une
<b>pré-analyse indicative fondée exclusivement sur des données publiques</b>, dont la
fraîcheur et la complétude sont affichées dans le service (mentions « Sourcé » / « Estimé »).
Ils ne constituent <b>ni un conseil</b> juridique, notarial, fiscal, financier ou en
investissement, <b>ni une garantie</b> de constructibilité, de rentabilité ou de faisabilité.
Ils ne remplacent <b>ni un certificat d'urbanisme, ni l'instruction d'une autorisation, ni
l'intervention d'un notaire</b> ou de tout professionnel réglementé. Le Client demeure seul
responsable de ses décisions et de leurs vérifications préalables.</p>

<h2>3. Comptes et accès</h2>
<p>La création de compte se fait sur invitation. Une licence Intégral ouvre <b>un accès
nominatif unique</b> (1 licence = 1 utilisateur) ; les identifiants sont personnels et
incessibles. LABUSE peut suspendre un compte en cas d'impayé (après les relances du
prestataire de paiement) ou d'usage abusif (extraction massive, revente de données,
partage d'accès, contournement technique).</p>

<h2>4. Prix et paiement</h2>
<p><b>Intégral</b> : abonnement mensuel de 349 € par licence, accès complet au service.
<b>Flash</b> : 79 € par rapport — paiement unique donnant droit à UN rapport PDF portant
sur UNE parcelle, téléchargeable pendant 30 jours (article 4 bis). Prix hors taxes le cas
échéant — le régime de TVA applicable figure sur les factures. Paiement par carte via
<b>Stripe</b> (paiement hébergé : aucune donnée de carte ne transite par LABUSE), factures
et reçus émis par Stripe.</p>

<h2>4 bis. Le rapport Flash</h2>
<p>Le rapport Flash est un document numérique généré et livré immédiatement après paiement.
<b>L'exécution commence dès le paiement, à la demande expresse de l'acheteur, qui renonce
le cas échéant à son droit de rétractation</b> (contenu numérique fourni immédiatement).
Le rapport porte exclusivement sur la parcelle confirmée par l'acheteur avant paiement ;
l'article 2 (nature des analyses) s'y applique intégralement. En cas d'échec technique de
génération, LABUSE fournit le rapport par tout moyen ou rembourse le paiement.</p>

<h2>5. Durée, reconduction et résiliation</h2>
<p>L'abonnement est souscrit pour une <b>durée ferme de 12 mois</b> à compter de son activation, facturé
mensuellement. À l'échéance, il est <b>reconduit tacitement pour des périodes successives de 12 mois</b>,
sauf dénonciation par le client au plus tard <b>un mois avant la date anniversaire</b> (depuis son espace
ou par e-mail à son contact LABUSE).</p>
<!-- M-P (point 5) — À SIGNALER À L'AVOCAT : L. 215-1 est un article du code de la CONSOMMATION,
     invoqué ici dans un contrat annoncé « B2B entre professionnels ». L'offrir contractuellement
     n'est pas faux (protection Chatel accordée au client), mais à valider en relecture juridique. -->
<p>Conformément à l'article L. 215-1 du code de la consommation (loi Chatel), LABUSE <b>informe le client,
au plus tôt trois mois et au plus tard un mois avant le terme de chaque période, de sa faculté de ne pas
reconduire</b> l'abonnement. À défaut d'information dans ce délai, le client peut mettre fin gratuitement à
la reconduction à tout moment à compter de la date de reconduction, les sommes correspondant à la période
postérieure lui étant remboursées.</p>
<p>Pendant la période d'engagement de 12 mois, l'abonnement n'est pas résiliable par anticipation, sauf
motif légitime (cessation d'activité dûment justifiée, manquement de LABUSE à ses obligations). LABUSE peut
résilier avec un préavis de 30 jours ; en cas d'arrêt du service, les sommes de la période non servie sont
remboursées.</p>

<h2>6. Disponibilité</h2>
<p>LABUSE est fourni « en l'état », avec un engagement de <b>meilleurs efforts</b> sur la
disponibilité et la correction des incidents — sans niveau de service (SLA) chiffré ni
pénalités. Les interruptions de maintenance sont, autant que possible, programmées hors
heures ouvrées de La Réunion.</p>

<h2>7. Données du Client et données publiques</h2>
<p>Les projets, tris, annotations et paramètres créés par le Client lui appartiennent ; il
peut en demander l'export puis l'effacement. Les données publiques agrégées restent régies
par leurs licences d'origine (Licence Ouverte, etc.). Le Client s'interdit la revente ou la
rediffusion systématique des contenus du service.</p>

<h2>8. Données personnelles (RGPD)</h2>
<p>Données traitées : email, nom du compte, journal technique de connexion, données de
facturation (chez Stripe). Aucune donnée de carte chez LABUSE. Finalités : fourniture du
service, facturation, sécurité. Durée : la vie du compte, puis effacement sous 30 jours de
la demande (droit d'accès, de rectification et d'effacement : kampusreunion@gmail.com).
Sous-traitants : Stripe (paiement), hébergeur du serveur (UE), service d'acheminement des
e-mails (SMTP).</p>
<p><b>E-mails envoyés.</b> LABUSE adresse des e-mails <b>transactionnels</b>, nécessaires au service
et sans consentement requis : réinitialisation de mot de passe (à votre demande) et avis d'échéance
avant reconduction (art. L. 215-1). LABUSE peut aussi adresser une <b>lettre récapitulative
périodique</b> (« le point de la semaine ») liée à votre usage : chaque envoi porte un lien de
<b>désinscription en un clic</b> (en-tête <i>List-Unsubscribe</i>) et vous pouvez vous y opposer à
tout moment. <b>Aucune prospection commerciale, aucune revente de données.</b></p>

<h2>9. Responsabilité</h2>
<p>Dans les limites permises par la loi entre professionnels, la responsabilité totale de
LABUSE, toutes causes confondues, est plafonnée aux <b>sommes effectivement payées par le
Client au cours des douze (12) derniers mois</b>. Les dommages indirects (perte de chance,
d'exploitation, décision d'investissement) sont exclus — dans le prolongement de l'article 2.</p>

<h2>10. Droit applicable</h2>
<p>Droit français. Compétence : les tribunaux dans le ressort de Saint-Denis de La Réunion,
après tentative de résolution amiable (30 jours).</p>
</div>"""), status_code=200)


@router.get("/mentions-legales", include_in_schema=False)
def mentions_page():
    return HTMLResponse(_page("mentions légales", f"""
<div class="legal"><h1>Mentions légales</h1>
<h2>Éditeur</h2><p>{_EDITEUR}</p>
<h2>Hébergement</h2><p>Serveur dédié dans l'Union européenne (OVHcloud). Paiements :
Stripe Payments Europe Ltd.</p>
<h2>E-mails</h2><p>LABUSE envoie des e-mails <b>transactionnels</b> (réinitialisation de mot de
passe à votre demande, avis d'échéance avant reconduction) et, le cas échéant, une <b>lettre
récapitulative périodique opt-out</b> (désinscription en un clic, en-tête <i>List-Unsubscribe</i>).
Détail à l'<a href="/cgv">article 8 des CGV</a>. Aucune prospection commerciale, aucune revente.</p>
<h2>Propriété</h2><p>Marque, interface et traitements LABUSE — tous droits réservés. Les
données publiques agrégées restent soumises à leurs licences d'origine.</p></div>"""))


@router.get("/confidentialite", include_in_schema=False)
def confidentialite_page():
    return HTMLResponse(_page("confidentialité", """
<div class="legal"><h1>Confidentialité & cookies</h1>
<h2>Cookies</h2><p>LABUSE utilise un <b>unique cookie strictement fonctionnel</b>
(session de connexion, httpOnly, Secure). Aucun cookie publicitaire, aucune mesure
d'audience tierce — c'est pourquoi <b>aucun bandeau de consentement n'est requis</b>
(exemption CNIL des traceurs strictement nécessaires, documentée ici).</p>
<h2>Données</h2><p>Voir l'article 8 des <a href="/cgv">CGV</a> (RGPD) : données minimales,
finalités limitées, droit d'accès et d'effacement sur simple email.</p>
<h2>Journalisation</h2><p>Les journaux techniques (connexions, erreurs) ne contiennent ni
mot de passe, ni token, ni donnée de carte ; ils servent la sécurité du service.</p></div>"""))


# ── /moi — l'app lit qui je suis + l'état d'abonnement (bandeau « paiement requis ») ──

@router.get("/moi", include_in_schema=False)
def moi(request: Request, db: Session = Depends(get_db)):
    from .auth import COOKIE
    from ..plans import plan_courant
    # M16-C : le plan RÉEL courant (stub env-driven aujourd'hui — plan_par_compte=False tant que le
    # mandat Auth & Plans n'a pas branché le palier par compte en base ; on ne fabrique aucun « Pro »).
    plan = plan_courant()
    plan_bloc = {"plan": plan,
                 "plan_label": {"essentiel": "Essentiel", "integral": "Intégral"}.get(plan, plan.capitalize()),
                 "plan_par_compte": False}
    tok = request.cookies.get(COOKIE) or ""
    if not tok.startswith("u."):
        return {"mode": "pilote", **plan_bloc}   # session pilote (pré-bascule) — pas de compte
    from ..comptes import session_utilisateur
    u = session_utilisateur(db, tok[2:])
    if not u:
        return JSONResponse({"detail": "session expirée"}, status_code=401)
    return {"mode": "compte", "role": u["role"], "statut_compte": u["statut_compte"], **plan_bloc}


# ── M16-C : « Proposer une amélioration » (menu compte) → table `suggestions` consultable ──
# Destination = base (pas d'e-mail : aucune infra e-mail dans l'app, cf. audit M16-A3). Vic lit via
# `labuse suggestions`. On ne promet rien qu'on ne tient pas : le retour est bien stocké, durable.
@router.post("/suggestions", include_in_schema=False)
def suggestion_create(body: dict, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text
    from .auth import COOKIE
    texte = (body.get("texte") or "").strip()
    if len(texte) < 3:
        return JSONResponse({"detail": "Message trop court."}, status_code=400)
    cat = body.get("categorie") or "idee"
    if cat not in ("bug", "idee", "autre"):
        cat = "autre"
    contexte = (body.get("contexte") or "")[:160]
    mode = "compte" if (request.cookies.get(COOKIE) or "").startswith("u.") else "pilote"
    db.execute(text("INSERT INTO suggestions (categorie, texte, contexte, compte_mode)"
                    " VALUES (:c, :t, :x, :m)"),
               {"c": cat, "t": texte[:4000], "x": contexte, "m": mode})
    db.commit()
    return {"ok": True}


@router.get("/guide", include_in_schema=False)
def guide_page():
    corps = """
<div class="legal"><h1>Prise en main — 5 gestes</h1>
<p class="maj">Le guide vit ici, sobre — la démo accompagnée reste le vrai onboarding.</p>
<h2>1. Allumer l'analyse</h2><p>« Afficher l'analyse LABUSE » colore l'île par verdict —
chaque couleur est calculée, jamais une opinion.</p>
<h2>2. Ouvrir une fiche</h2><p>Cliquez une parcelle (ou cherchez un IDU) : verdict, règles
traduites, risques, marché — chaque ligne porte sa source (Sourcé / Estimé).</p>
<h2>3. Décrire un projet</h2><p>Le copilote transforme votre phrase en critères ; le tri
alimente vos retenues, qui deviennent des pistes CRM automatiquement.</p>
<h2>4. Les outils</h2><p>Comparateur de communes, rareté ZAN, carnet de secteur, bascules
datées — le registre Outils, groupé par intention.</p>
<h2>5. Le dossier banquier</h2><p>Depuis toute fiche : un PDF sourcé que votre financeur
lit en trois minutes.</p>
<p style="margin-top:20px"><a href="/" class="pill">Revenir à l'app</a></p></div>"""
    return HTMLResponse(_page("prise en main", corps, large=True))


# ═══════════ FLASH — 79 € one-shot : UNE parcelle, UN rapport PDF (refonte 22/07) ═══════════
# Parcours : /flash (adresse ou IDU → validation honnête de la parcelle) → confirmation
# (commune, surface, ce que contient le rapport, le prix) → Stripe Checkout (paiement
# unique, email collecté par Stripe) → /flash/retour (poll de génération, spinner sobre)
# → lien de téléchargement signé (30 jours). Sans compte, sans abonnement, sans email maison.

@router.get("/flash", include_in_schema=False)
def flash_page(idu: str = "", annule: int = 0, db: Session = Depends(get_db)):
    note_annule = ('<p class="err">Paiement interrompu — rien n\'a été débité.</p>' if annule else "")
    parcelle = None
    if idu and len(idu) == 14:
        from sqlalchemy import text
        parcelle = db.execute(text(
            "SELECT idu, commune, round(surface_m2) AS m2 FROM parcels WHERE idu = :i"),
            {"i": idu.upper()}).mappings().first()
    if parcelle:
        return HTMLResponse(_page("rapport Flash", f"""
<h1>Votre rapport Flash</h1><p class="sub">tout sur cette parcelle, en un PDF sourcé</p>
<div class="recap"><div style="font:600 13px ui-monospace,monospace;color:var(--hi)">{html.escape(parcelle['idu'][8:10])} {html.escape(parcelle['idu'][10:])} · {html.escape(parcelle['commune'])} · {('%d' % (parcelle['m2'] or 0))} m²</div>
<div class="quoi" style="margin-top:10px"><b style="color:var(--txt)">Dans votre PDF :</b> identité et plan,
zonage et <b style="color:var(--txt)">règles d'urbanisme calibrées</b> (hauteur, emprise, ce qu'on peut y
construire), risques (Géorisques, PPR, littoral), marché DVF du secteur, permis voisins et
<b style="color:var(--txt)">potentiel de transformation</b> — chaque donnée avec sa source (Sourcé /
Estimé) et son millésime.</div></div>
<div class="trust" role="list">
  <div role="listitem"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" stroke-width="1.5" aria-hidden="true"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 1.5"/></svg> Livré en <b style="color:var(--txt)">quelques secondes</b>, lien valable 30 jours.</div>
  <div role="listitem"><svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="var(--mint)" stroke-width="1.5" aria-hidden="true"><path d="M4 10l4 4 8-9"/></svg> Ce qu'une simple fiche cadastrale ne dit pas : <b style="color:var(--txt)">les règles PLU traduites</b> et le potentiel constructible chiffré.</div>
  <div role="listitem">{coffre_ui.LOCK_SVG} Paiement unique — <b style="color:var(--txt)">aucune donnée de carte</b> ne transite par LABUSE.</div>
</div>
<div class="recap" style="margin-top:6px"><div class="prix">79 € <span style="font-size:13px;color:var(--mut);font-weight:400">paiement unique, sans abonnement</span></div></div>
<form method="post" action="/flash"><input type="hidden" name="idu" value="{html.escape(parcelle['idu'])}">
<button type="submit">Payer 79 € et recevoir mon rapport →</button></form>
<p class="linkrow"><a href="/flash">← changer de parcelle</a></p>
<p class="note">Pré-analyse sur données publiques officielles — ne remplace ni certificat d'urbanisme ni
conseil notarial. Le lien de téléchargement (30 jours) s'affiche dès la génération.</p>""", pied=False))
    introuvable = ('<p class="err">Parcelle introuvable — vérifiez l\'IDU (14 caractères).</p>'
                   if idu and not parcelle else "")
    return HTMLResponse(_page("rapport Flash", f"""
<h1>Rapport Flash</h1><p class="sub">le dossier complet d'une parcelle, en PDF · 79 €</p>
{note_annule}{introuvable}
<div class="recap" style="margin-bottom:16px">
<div style="font-size:12.5px;color:var(--txt);line-height:1.65"><b style="color:var(--hi)">Ce que vous
obtenez :</b> zonage et règles d'urbanisme calibrées (hauteur, emprise, ce qu'on peut y construire),
risques (Géorisques, PPR, littoral), marché DVF du secteur, permis voisins et potentiel de transformation.
Chaque donnée <b style="color:var(--txt)">avec sa source et sa fraîcheur</b>.</div>
<div style="font-size:12px;color:var(--mint);margin-top:11px;line-height:1.55">→ Ce que vous n'auriez pas
trouvé seul : les règles du PLU traduites en clair, le potentiel constructible chiffré, et les signaux
croisés que LABUSE agrège — pas une simple fiche cadastrale.</div></div>
<form method="get" action="/flash">
<label for="idu">Identifiant de parcelle (IDU)</label>
<div class="field"><input id="idu" name="idu" type="text" minlength="14" maxlength="14" required
  autofocus inputmode="text" placeholder="97415000CW0658" aria-describedby="iduhint"
  style="font-family:ui-monospace,monospace"></div>
<button type="submit">Voir ma parcelle →</button></form>
<p class="meterlbl" id="iduhint">14 caractères — figure sur cadastre.gouv.fr, ou demandez-le à votre contact LABUSE. Le rapport est généré sur la parcelle EXACTE.</p>"""))


@router.post("/flash", include_in_schema=False)
async def flash_submit(request: Request, db: Session = Depends(get_db)):
    from urllib.parse import parse_qs

    from sqlalchemy import text as _text
    q = parse_qs((await request.body()).decode("utf-8", "replace"))
    idu = (q.get("idu") or [""])[0].strip().upper()
    ok = db.execute(_text("SELECT 1 FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
    if not ok:
        return RedirectResponse("/flash", status_code=303)
    try:
        from ..facturation import creer_checkout_flash
        url = creer_checkout_flash(db, idu)
        return RedirectResponse(url, status_code=303)
    except Exception as e:  # noqa: BLE001 — pas de clé/prix : page honnête, jamais un bouton mort
        log.warning("flash checkout indisponible (%s)", e)
        return HTMLResponse(_page("paiement indisponible", """
<h1>Paiement indisponible</h1><p class="sous">réessayez dans quelques minutes</p>
<p style="text-align:center;font-size:12.5px">Le paiement en ligne ne répond pas. Rien n'a été
débité — réessayez, ou écrivez à votre contact LABUSE.</p>"""), status_code=503)


@router.get("/flash/retour", include_in_schema=False)
def flash_retour(session_id: str = ""):
    return HTMLResponse(_page("votre rapport", f"""
<div class="big"><div class="mark ok" id="mark" aria-hidden="true"><span class="spin" style="border-color:rgba(92,230,161,.3);border-top-color:var(--mint)"></span></div>
<h1 id="hero" style="font-size:17px">Votre rapport arrive…</h1>
<p class="sub" id="sub">paiement reçu · nous assemblons votre PDF</p></div>
<div id="etat" role="status" aria-live="polite" style="text-align:center;margin-top:12px;font-size:13px;color:var(--mut)">
Quelques secondes — le téléchargement s'affiche ici.</div>
<script>
const sid = {session_id!r};
// M18-B3 : « votre rapport est prêt » = la vedette ; le bouton PDF, gros et rempli, saute aux yeux.
const DL = '<a href="#L" style="display:inline-flex;align-items:center;gap:9px;background:var(--mint);color:var(--mint-ink);font:600 15px inherit;padding:16px 34px;border-radius:var(--r);text-decoration:none;box-shadow:0 10px 30px rgba(92,230,161,.32)">&#8595; Télécharger mon rapport PDF</a>';
// M145 C.2 — aucun spinner infini sur un paiement encaissé : après ~2 min (60 × 2 s), on DIT
// l'incident honnêtement (paiement confirmé, lien par e-mail / reçu Stripe) et on cesse de sonder.
let tries = 0; const MAX_TRIES = 60;
async function poll() {{
  try {{
    const r = await fetch('/flash/statut?session_id=' + encodeURIComponent(sid));
    const d = await r.json();
    const el = document.getElementById('etat');
    if (d.statut === 'generee' && d.lien) {{
      document.getElementById('mark').innerHTML = '✓';   // spinner → coche (état PRÊT)
      document.getElementById('hero').textContent = 'Votre rapport est prêt';
      document.getElementById('sub').textContent = 'paiement reçu · votre PDF est généré';
      el.innerHTML = DL.replace('#L', d.lien) +
        '<p style="font-size:11.5px;color:var(--dim);margin-top:16px;line-height:1.6">Lien valable 30 jours — ' +
        'conservez le PDF. Reçu et facture dans votre e-mail Stripe.</p>';
      return;
    }}
    if (d.statut === 'erreur') {{
      el.innerHTML = '<p style="color:var(--err)">La génération a rencontré un problème — ' +
        'elle va être retentée automatiquement. Si rien ne vient, écrivez à votre contact ' +
        'LABUSE avec votre reçu Stripe : le rapport vous sera fourni.</p>';
    }}
  }} catch (e) {{}}
  tries++;
  if (tries >= MAX_TRIES) {{
    document.getElementById('mark').innerHTML = '!';   // spinner → alerte (on ARRÊTE de tourner)
    document.getElementById('hero').textContent = 'Votre paiement est bien confirmé';
    document.getElementById('sub').textContent = 'la génération prend plus de temps que prévu';
    document.getElementById('etat').innerHTML = '<p style="font-size:12.5px;line-height:1.6">' +
      'Votre paiement est confirmé chez Stripe — rien n\\'est perdu. La génération prend plus de temps ' +
      'que prévu : le lien vous parviendra par e-mail, ou rouvrez cette page un peu plus tard. En cas ' +
      'de doute, écrivez à votre contact LABUSE avec votre reçu Stripe, le rapport vous sera fourni.</p>';
    return;   // on ne sonde plus — jamais de spinner infini
  }}
  setTimeout(poll, 2000);
}}
poll();
</script>"""))


@router.get("/flash/statut", include_in_schema=False)
def flash_statut_api(session_id: str = "", db: Session = Depends(get_db)):
    from ..facturation import flash_statut
    return flash_statut(db, session_id)


@router.get("/flash/telecharger", include_in_schema=False)
def flash_telecharger(token: str = "", db: Session = Depends(get_db)):
    from pathlib import Path

    from fastapi.responses import FileResponse

    from ..facturation import flash_pdf_par_token
    p = flash_pdf_par_token(db, token)
    if not p or not Path(p).exists():
        return HTMLResponse(_page("lien expiré", """
<h1>Lien expiré</h1><p class="sous">le téléchargement n'est plus disponible</p>
<p style="text-align:center;font-size:12.5px">Les liens Flash sont valables 30 jours.
Écrivez à votre contact LABUSE avec votre reçu Stripe — le rapport vous sera renvoyé.</p>"""),
                            status_code=404)
    return FileResponse(p, media_type="application/pdf",
                        filename=f"labuse_flash_{Path(p).stem}.pdf")

# ═══ M23-A — MARQUE DU CLIENT (logo + coordonnées) sur les documents ABONNÉ ═══
# Upload png/jpg/svg ≤ 512 Ko, SIGNATURE de fichier vérifiée (jamais le mime déclaré),
# SVG à <script> refusé. Champs vides = rien ne s'imprime (M22-C4). Le Flash 79 €
# n'affiche JAMAIS cette marque (produit LABUSE).

def _compte_session(request: Request, db) -> int:
    # M-K (P2-65) : délègue au résolveur UNIQUE tenant.compte_ou_401 (current_compte + 401 si
    # None). Plus de lecture cookie à la main — même règle partout.
    from .tenant import compte_ou_401
    return compte_ou_401(request)


@router.post("/moi/logo", include_in_schema=False)
async def moi_logo(request: Request, db: Session = Depends(get_db)) -> dict:
    """Upload en BODY BRUT (fetch/curl --data-binary) — pas de multipart : zéro dépendance
    nouvelle (python-multipart absent des deps, pyproject = source de vérité). Le format
    RÉEL est vérifié par signature (marque.valider_logo), le Content-Type est indicatif."""
    from ..marque import ensure_colonnes, valider_logo
    cid = _compte_session(request, db)
    contenu = await request.body()
    try:
        mime = valider_logo(contenu, request.headers.get("content-type") or "")
    except ValueError as e:
        raise HTTPException(422, str(e))
    ensure_colonnes(db)
    from sqlalchemy import text as _t
    db.execute(_t("UPDATE comptes SET logo = :b, logo_mime = :m WHERE id = :c"),
               {"b": contenu, "m": mime, "c": cid})
    db.commit()
    return {"ok": True, "mime": mime, "octets": len(contenu)}


@router.delete("/moi/logo", include_in_schema=False)
def moi_logo_suppr(request: Request, db: Session = Depends(get_db)) -> dict:
    from ..marque import ensure_colonnes
    cid = _compte_session(request, db)
    ensure_colonnes(db)
    from sqlalchemy import text as _t
    db.execute(_t("UPDATE comptes SET logo = NULL, logo_mime = NULL WHERE id = :c"), {"c": cid})
    db.commit()
    return {"ok": True}


@router.post("/moi/marque", include_in_schema=False)
def moi_marque(payload: dict, request: Request, db: Session = Depends(get_db)) -> dict:
    """Raison sociale / coordonnées / mention libre COURTE (couverture personnalisable A4).
    Champs vides acceptés (= rien ne s'imprime, M22-C4)."""
    from ..marque import ensure_colonnes
    cid = _compte_session(request, db)
    m = {k: str(payload.get(k) or "").strip()[:240]
         for k in ("raison_sociale", "coordonnees", "mention")}
    ensure_colonnes(db)
    import json as _json
    from sqlalchemy import text as _t
    db.execute(_t("UPDATE comptes SET marque = :m WHERE id = :c"),
               {"m": _json.dumps(m), "c": cid})
    db.commit()
    return {"ok": True, "marque": m}


@router.get("/moi/marque", include_in_schema=False)
def moi_marque_get(request: Request, db: Session = Depends(get_db)) -> dict:
    """M54-EXPO-2 — relit la marque + logo COURANTS du compte (préremplissage/prévisualisation du
    widget). Même chemin de compte que l'upload (`_compte_session`) → round-trip fidèle. `has_logo`
    + `logo_data_uri` alimentent l'aperçu ; les 3 champs préremplissent le formulaire."""
    import base64 as _b64
    from sqlalchemy import text as _t

    from ..marque import ensure_colonnes
    cid = _compte_session(request, db)
    ensure_colonnes(db)
    row = db.execute(_t("SELECT logo, logo_mime, marque FROM comptes WHERE id = :c"),
                     {"c": cid}).mappings().first()
    m = (row and row["marque"]) or {}
    out: dict = {k: (m.get(k) or "") for k in ("raison_sociale", "coordonnees", "mention")}
    out["has_logo"] = bool(row and row["logo"])
    if row and row["logo"]:
        out["logo_data_uri"] = f"data:{row['logo_mime']};base64," + _b64.b64encode(row["logo"]).decode()
    return out
