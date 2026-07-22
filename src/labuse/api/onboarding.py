"""PREMIER EURO · E3/E4 — pages serveur : onboarding founding + légales + webhook Stripe.

Parcours (décisions Vic) : invitation (lien signé, email pré-rempli) → mot de passe sur la
façade Coffre → acceptation CGV (checkbox HORODATÉE + version, loggée) → Stripe Checkout
(founding appliqué, montant visible côté Stripe) → retour → compte actif au webhook.
Pages rendues serveur dans la nuit Coffre — la façade React n'est pas touchée.
"""
from __future__ import annotations

import html
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..config import get_settings

log = logging.getLogger("labuse.onboarding")
router = APIRouter(tags=["onboarding"])


def get_db():
    from .app import get_db as _g
    yield from _g()


# ── le gabarit Coffre serveur (même nuit que auth.login_page, contenu plus long) ──

def _page(titre: str, corps: str, large: bool = False) -> str:
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>LABUSE — {html.escape(titre)}</title><style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#060A08;color:#C9DCD1;font:14px/1.65 -apple-system,'Inter',sans-serif;padding:24px}}
.bloc{{width:100%;max-width:{'760px' if large else '420px'}}}
.oiseau{{display:block;margin:0 auto 10px;height:26px;width:auto}}
h1{{font:600 15px inherit;letter-spacing:.18em;text-transform:uppercase;color:#ECF5EF;
text-align:center;margin:0 0 4px}}
.sous{{text-align:center;font-size:11px;color:#5C7268;letter-spacing:.08em;margin:0 0 26px}}
label{{display:block;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:#8FA69A;margin:16px 0 6px}}
input[type=email],input[type=password]{{width:100%;background:none;border:0;border-bottom:1px solid #1E2A23;
color:#ECF5EF;font:14px inherit;padding:8px 2px;outline:none;transition:border-color .15s}}
input:focus{{border-bottom-color:#5CE6A1}}
.cgvbox{{display:flex;gap:10px;align-items:flex-start;margin:20px 0 0;font-size:12px;color:#8FA69A}}
.cgvbox input{{accent-color:#5CE6A1;margin-top:3px}}
button{{margin-top:24px;width:100%;background:none;border:1px solid #5CE6A1;border-radius:8px;
color:#5CE6A1;font:600 13px inherit;padding:10px;cursor:pointer;transition:background .15s}}
button:hover{{background:rgba(92,230,161,.08)}}
.err{{min-height:18px;font-size:12px;color:#E8695A;text-align:center;margin-top:14px}}
.note{{font-size:10.5px;color:#5C7268;text-align:center;margin-top:22px;line-height:1.6}}
.legal h2{{font-size:13px;color:#ECF5EF;margin:26px 0 6px}}
.legal p,.legal li{{font-size:12.5px;color:#C9DCD1}}
.legal .maj{{color:#5C7268;font-size:11px}}
a{{color:#5CE6A1;text-decoration:none}}a:hover{{text-decoration:underline}}
.pill{{display:inline-block;border:1px solid rgba(92,230,161,.4);border-radius:999px;
padding:2px 10px;font-size:11px;color:#5CE6A1}}
</style></head><body><div class="bloc">
<svg class="oiseau" viewBox="0 0 240 82" fill="#C9A961" aria-hidden="true">
<path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z"/></svg>
{corps}
<p class="note">Radar foncier · La Réunion — <a href="/cgv">CGV</a> · <a href="/mentions-legales">mentions légales</a> · <a href="/confidentialite">confidentialité</a></p>
</div></body></html>"""


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
<p class="sous">licence {p['label']} · {p['eur_mois']} €/mois · 1 licence = 1 accès</p>
<form method="post" action="/invitation">
<input type="hidden" name="token" value="{html.escape(token)}">
<label for="email">Identifiant</label>
<input id="email" type="email" value="{html.escape(inv['email'])}" disabled>
<label for="password">Mot de passe (10 caractères minimum)</label>
<input id="password" name="password" type="password" minlength="10" required autocomplete="new-password" autofocus>
<div class="cgvbox"><input type="checkbox" id="cgv" name="cgv" value="oui" required>
<label for="cgv" style="all:unset;font-size:12px;color:#8FA69A;cursor:pointer">
J'ai lu et j'accepte les <a href="/cgv" target="_blank">conditions générales</a> —
les analyses LABUSE sont une pré-analyse sur données publiques, jamais un conseil.</label></div>
<button type="submit">Continuer vers le paiement →</button>
<div class="err"></div></form>
<p class="note">Paiement sécurisé par Stripe — aucune donnée de carte ne transite par LABUSE.</p>"""))


@router.post("/invitation", include_in_schema=False)
async def invitation_submit(request: Request, db: Session = Depends(get_db)):
    from urllib.parse import parse_qs

    from ..comptes import activer_par_invitation, audit
    q = parse_qs((await request.body()).decode("utf-8", "replace"))
    token = (q.get("token") or [""])[0]
    password = (q.get("password") or [""])[0]
    cgv = (q.get("cgv") or [""])[0] == "oui"
    if not cgv:
        return HTMLResponse(_page("conditions", "<h1>Conditions requises</h1><p class='sous'>"
                                  "l'acceptation des CGV est nécessaire</p>"), status_code=400)
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
    # → Stripe Checkout (founding appliqué) ; sans clé Stripe : page d'attente HONNÊTE
    try:
        from ..facturation import creer_checkout
        url = creer_checkout(db, inv["compte_id"], inv["email"])
        return RedirectResponse(url, status_code=303)
    except Exception as e:  # noqa: BLE001 — ConfigError (pas de clé) ou indispo Stripe
        log.warning("checkout indisponible compte %s : %s", inv["compte_id"], e)
        return HTMLResponse(_page("paiement", """
<h1>Compte créé — paiement à venir</h1><p class="sous">le paiement en ligne n'est pas encore ouvert</p>
<p style="text-align:center;font-size:12.5px">Votre mot de passe est enregistré et vos conditions
acceptées. Votre contact LABUSE vous enverra le lien de paiement sécurisé — l'accès s'ouvrira
au règlement.</p><p style="text-align:center"><a href="/login">retour à la porte</a></p>"""))


@router.get("/onboarding/retour", include_in_schema=False)
def onboarding_retour(ok: int = 1):
    if ok:
        return HTMLResponse(_page("bienvenue", """
<h1>Paiement reçu</h1><p class="sous">votre espace est prêt</p>
<p style="text-align:center;font-size:12.5px">Merci. Votre abonnement est actif — connectez-vous
avec votre email et votre mot de passe. Un guide de prise en main vous attend dans l'app
(lien discret, en bas du premier écran).</p>
<p style="text-align:center;margin-top:18px"><a href="/login" class="pill">Entrer dans LABUSE →</a></p>"""))
    return HTMLResponse(_page("paiement interrompu", """
<h1>Paiement interrompu</h1><p class="sous">rien n'a été débité</p>
<p style="text-align:center;font-size:12.5px">Pour reprendre : connectez-vous simplement sur
<a href="/login">la porte</a> avec votre email et votre mot de passe — le paiement se
relancera automatiquement. Rien n'a été débité.</p>"""))


# ── E1 · reset mot de passe ──

@router.get("/reset", include_in_schema=False)
def reset_page(token: str = ""):
    if not token:
        return HTMLResponse(_page("mot de passe oublié", """
<h1>Réinitialisation</h1><p class="sous">le lien s'obtient auprès de votre contact LABUSE</p>
<p style="text-align:center;font-size:12.5px">Écrivez à votre contact LABUSE : un lien de
réinitialisation valable une heure vous sera transmis directement.</p>"""))
    return HTMLResponse(_page("nouveau mot de passe", f"""
<h1>Nouveau mot de passe</h1><p class="sous">choisissez-le soigneusement</p>
<form method="post" action="/reset">
<input type="hidden" name="token" value="{html.escape(token)}">
<label for="password">Nouveau mot de passe (10 caractères minimum)</label>
<input id="password" name="password" type="password" minlength="10" required autocomplete="new-password" autofocus>
<button type="submit">Enregistrer</button></form>"""))


@router.post("/reset-demande", include_in_schema=False)
async def reset_demande():
    # Refonte 22/07 : AUCUN email automatique — le lien de reset se génère côté admin
    # (`labuse compte-reset-lien email`) et s'envoie à la main. Réponse identique quoi
    # qu'il arrive (anti-énumération conservée).
    return HTMLResponse(_page("mot de passe oublié", """
<h1>Réinitialisation</h1><p class="sous">le lien s'obtient auprès de votre contact LABUSE</p>
<p style="text-align:center;font-size:12.5px">Écrivez à votre contact LABUSE (l'adresse de
votre échange initial) : un lien de réinitialisation valable une heure vous sera transmis
directement.</p>"""))


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
    from ..facturation import ConfigError, traiter_webhook
    payload = await request.body()
    try:
        r = traiter_webhook(db, payload, request.headers.get("stripe-signature"))
    except ConfigError as e:
        log.error("webhook stripe : %s", e)
        return JSONResponse({"detail": "webhook non configuré"}, status_code=503)
    except Exception as e:  # noqa: BLE001 — signature invalide comprise
        log.warning("webhook stripe REJETÉ : %s", type(e).__name__)
        return JSONResponse({"detail": "signature invalide"}, status_code=400)
    return {"ok": True, **{k: v for k, v in r.items() if k != "compte_id"}}


# ── E3 · pages légales (drafts SOLIDES — relecture Vic obligatoire, avocat recommandé
#     avant premières signatures : noté au rapport ; non bloquant pour construire) ──

_EDITEUR = ("Victor L. — entrepreneur individuel (EI) · La Réunion, France.<br>"
            "Adresse et SIREN : <b>[À COMPLÉTER par Vic — adresse officielle EI + SIREN]</b> · "
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

<h2>5. Durée et résiliation</h2>
<p>Abonnement mensuel, tacitement reconduit, résiliable à tout moment avec effet à la fin de
la période en cours (aucun remboursement prorata). LABUSE peut résilier avec un préavis de
30 jours ; en cas d'arrêt du service, les sommes de la période non servie sont remboursées.</p>

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
Sous-traitants : Stripe (paiement), Resend (emails transactionnels), hébergeur du serveur
(UE). Pas de prospection automatisée, pas de revente de données.</p>

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
Stripe Payments Europe Ltd. Emails transactionnels : Resend.</p>
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
    tok = request.cookies.get(COOKIE) or ""
    if not tok.startswith("u."):
        return {"mode": "pilote"}      # session pilote (pré-bascule) — pas de compte
    from ..comptes import session_utilisateur
    u = session_utilisateur(db, tok[2:])
    if not u:
        return JSONResponse({"detail": "session expirée"}, status_code=401)
    return {"mode": "compte", "role": u["role"], "statut_compte": u["statut_compte"]}


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
<h1>Rapport Flash</h1><p class="sous">une parcelle · un PDF sourcé · 79 € — paiement unique</p>
<div style="border:1px solid #1E2A23;border-radius:10px;padding:14px;margin-top:6px">
<p style="margin:0;font-size:13px;color:#ECF5EF"><span style="font-family:ui-monospace,monospace">
{html.escape(parcelle['idu'][8:10])} {html.escape(parcelle['idu'][10:])}</span>
 · {html.escape(parcelle['commune'])} · {int(parcelle['m2'] or 0):,} m²</p>
<p style="margin:8px 0 0;font-size:12px;color:#8FA69A">Le rapport : identité et plan de la
parcelle, zonage et règles, risques connus, marché (DVF), permis voisins — chaque donnée
avec sa source et sa date (Sourcé / Estimé). Pré-analyse sur données publiques : ne
remplace ni certificat d'urbanisme ni conseil notarial.</p></div>
<form method="post" action="/flash">
<input type="hidden" name="idu" value="{html.escape(parcelle['idu'])}">
<button type="submit">Payer 79 € et générer le rapport →</button></form>
<p class="note">Paiement unique par Stripe. Le lien de téléchargement (valable 30 jours)
s'affiche dès la génération — quelques secondes. <a href="/flash">changer de parcelle</a></p>"""))
    introuvable = ('<p class="err">Parcelle introuvable — vérifiez l\'IDU (14 caractères).</p>'
                   if idu and not parcelle else "")
    return HTMLResponse(_page("rapport Flash", f"""
<h1>Rapport Flash</h1><p class="sous">une parcelle · un PDF sourcé · 79 € — paiement unique</p>
{note_annule}{introuvable}
<form method="get" action="/flash">
<label for="idu">Identifiant de parcelle (IDU, 14 caractères)</label>
<input id="idu" name="idu" type="text" minlength="14" maxlength="14" required autofocus
  style="width:100%;background:none;border:0;border-bottom:1px solid #1E2A23;color:#ECF5EF;
  font:14px ui-monospace,monospace;padding:8px 2px;outline:none" placeholder="97415000CW0658">
<button type="submit">Vérifier la parcelle →</button></form>
<p class="note">L'IDU figure sur cadastre.gouv.fr (commune + section + numéro) — ou
demandez-le à votre contact LABUSE. Le rapport est généré sur la parcelle EXACTE.</p>"""))


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
    return HTMLResponse(_page("génération du rapport", f"""
<h1>Rapport en préparation</h1><p class="sous">paiement reçu — génération en cours</p>
<div id="etat" style="text-align:center;font-size:12.5px;color:#8FA69A;margin-top:10px">
<span class="pill">génération…</span></div>
<script>
const sid = {session_id!r};
async function poll() {{
  try {{
    const r = await fetch('/flash/statut?session_id=' + encodeURIComponent(sid));
    const d = await r.json();
    const el = document.getElementById('etat');
    if (d.statut === 'generee' && d.lien) {{
      el.innerHTML = '<a class="pill" href="' + d.lien + '">Télécharger votre rapport (PDF) →</a>' +
        '<p style="font-size:11px;color:#5C7268;margin-top:12px">Lien valable 30 jours — ' +
        'conservez le PDF. Reçu et facture : dans l\\'email Stripe.</p>';
      return;
    }}
    if (d.statut === 'erreur') {{
      el.innerHTML = '<p style="color:#E8695A">La génération a rencontré un problème — ' +
        'elle va être retentée automatiquement. Si rien ne vient, écrivez à votre contact ' +
        'LABUSE avec votre reçu Stripe : le rapport vous sera fourni.</p>';
    }}
  }} catch (e) {{}}
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
