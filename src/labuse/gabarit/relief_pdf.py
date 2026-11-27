"""Axonométrie imprimée du maillage et des emprises de la scène Gabarit (repère local EPSG:2975)."""
import base64
from io import BytesIO
import math

import numpy as np
from affine import Affine
from PIL import Image, ImageColor, ImageDraw
from rasterio.features import rasterize
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .plan_svg import C_BATI, C_CONTOUR, C_EXCL, C_RETRAIT, C_ZONE, _legende_html


def _polygones(parts):
    return [Polygon(p["ext"], p.get("trous", [])) for p in parts if len(p["ext"]) >= 3]


def _altitudes(faces, x, y):
    """Interpolation barycentrique sur les triangles effectivement présents, lacunes comprises."""
    sommets = np.asarray(faces["vertices"], dtype=float)
    tri = sommets[np.asarray(faces["triangles"])]
    pas = faces["pas_m"]
    xmin, ymax = sommets[:, 0].min(), sommets[:, 1].max()
    centre = tri.mean(axis=1)
    u, v = (centre[:, 0] - xmin) / pas, (ymax - centre[:, 1]) / pas
    col, ligne = u.astype(int), v.astype(int)
    index = np.full((ligne.max() + 1, col.max() + 1, 2), -1)
    index[ligne, col, (u - col < v - ligne).astype(int)] = np.arange(len(tri))
    u, v = (x - xmin) / pas, (ymax - y) / pas
    col, ligne = np.floor(u).astype(int), np.floor(v).astype(int)
    n, m = index.shape[:2]
    face = index[ligne.clip(0, n - 1), col.clip(0, m - 1), (u - col < v - ligne).astype(int)]
    valide = (ligne >= 0) & (ligne < n) & (col >= 0) & (col < m) & (face >= 0)
    normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normales /= normales[:, 2, None]
    nx, ny, _ = np.moveaxis(normales[face], -1, 0)
    ax, ay, az = np.moveaxis(tri[face, 0], -1, 0)
    z = az - nx * (x - ax) - ny * (y - ay)
    lumiere = (0.45 * nx + 0.35 * ny + 0.8) / np.sqrt(nx * nx + ny * ny + 1)
    return np.where(valide, z, np.nan), np.clip(0.72 + 0.33 * lumiere, 0.58, 1.05)


def _image(scene, exemple, hauteur, projet=None):
    faces = scene["terrain"].get("faces_parcelle") or {}
    parc = unary_union(_polygones(scene["contour_cadastral"] or scene["contour_gabarit"]))
    if parc.is_empty or not faces.get("triangles"):
        return None

    # L'axe long de la parcelle utilise la largeur du papier, avec une vue oblique de 25°.
    coins = np.asarray(parc.minimum_rotated_rectangle.exterior.coords)[:-1]
    cotes = np.roll(coins, -1, axis=0) - coins
    dx, dy = cotes[np.argmax(np.linalg.norm(cotes, axis=1))]
    angle = math.atan2(dy, dx) % math.pi - math.radians(25)
    co, si = math.cos(angle), math.sin(angle)
    cadre = parc.buffer(max(3, parc.length * 0.018))
    pts = np.concatenate([np.asarray(p.exterior.coords) for p in
                          (cadre.geoms if cadre.geom_type == "MultiPolygon" else [cadre])])
    u, v = pts[:, 0]*co + pts[:, 1]*si, -pts[:, 0]*si + pts[:, 1]*co
    pas = max(np.ptp(u)/1250, np.ptp(v)/900, 0.015)
    w, h = int(np.ceil(np.ptp(u)/pas))+2, int(np.ceil(np.ptp(v)/pas))+2
    tr = Affine.rotation(math.degrees(angle)) * Affine.translation(u.min()-pas, v.max()+pas) * Affine.scale(pas, -pas)
    rows, cols = np.indices((h, w))
    x, y = tr * (cols + 0.5, rows + 0.5)
    sol, ombre = _altitudes(faces, x, y)

    def masque(formes):
        return rasterize([(g, 1) for g in formes], out_shape=(h, w), transform=tr,
                         dtype="uint8").astype(bool) if formes else np.zeros((h, w), bool)

    valide = np.isfinite(sol) & masque([cadre])
    if not valide.any():
        return None
    # Texture en coordonnées terrain. La même transformation conserve les trous et parties disjointes.
    couleur = np.full((h, w, 3), [215, 219, 209], dtype="uint8")
    couleur[masque([parc])] = [190, 203, 183]
    for cle, teinte in (("reculs", C_RETRAIT), ("zone_implantation", C_ZONE), ("exclusions", C_EXCL)):
        ici = masque(_polygones(scene[cle]))
        couleur[ici] = 0.7 * np.array(ImageColor.getrgb(teinte)) + 0.3 * couleur[ici]
    if scene["reculs"]:
        bandes = unary_union(_polygones(scene["reculs"]))
        couleur[masque([bandes.boundary.buffer(pas)])] = ImageColor.getrgb(C_RETRAIT)
    couleur[masque([parc.boundary.buffer(pas*1.25)])] = ImageColor.getrgb(C_CONTOUR)
    if projet is not None:
        couleur[masque([projet])] = [180, 211, 255]
        couleur[masque([projet.boundary.buffer(2 * pas)])] = [24, 95, 163]
    sommet = sol.copy()
    objet = np.zeros((h, w), dtype=int)
    if exemple is not None and hauteur:
        ici = masque([exemple])
        sommet[ici] += hauteur
        objet[ici] = 1
        couleur[ici] = ImageColor.getrgb(C_ZONE)
    for i, bati in enumerate(scene["batiments"], 2):
        ici = masque(_polygones(bati["empreinte"]))
        couleur[ici] = ImageColor.getrgb(C_BATI)
        if bati["volume"] and bati["pied_m"] is not None and bati["hauteur_m"]:
            sommet[ici] = np.maximum(sol[ici], bati["pied_m"] + bati["hauteur_m"])
            objet[ici] = i
    couleur = (couleur * np.where(objet > 0, 1, ombre)[:, :, None]).clip(0, 255).astype("uint8")

    # Projection orthographique avec la même échelle en XY et Z. Chaque colonne est une coupe
    # verticale, parcourue du fond vers l'observateur pour respecter les occultations.
    tilt = math.radians(36)
    def projection(z):
        return rows * math.sin(tilt) - (z - sol[valide].min()) * math.cos(tilt) / pas
    haut, bas = projection(sommet), projection(sol)
    ymin, ymax = haut[valide].min(), bas[valide].max()
    # Cas d'une parcelle minuscule avec une hauteur importante : borner aussi l'axe vertical.
    echelle = min(1., 950 / max(ymax - ymin, 1))
    def pixels(a):
        return np.rint(np.where(valide, (a-ymin)*echelle, 0)).astype(int)
    haut, bas = pixels(haut), pixels(bas)
    image = Image.new("RGB", (w, int(np.ceil((ymax-ymin)*echelle))+1), "white")
    dessin = ImageDraw.Draw(image)
    for j in range(h):
        actifs = np.flatnonzero(valide[j])
        for i in actifs:
            y1 = haut[j, i]
            meme = j > 0 and valide[j-1, i] and objet[j-1, i] == objet[j, i]
            y0 = haut[j-1, i] if meme else bas[j, i]
            if j and valide[j-1, i] and objet[j-1, i] and not meme:
                dessin.line((i, haut[j-1, i], i, bas[j-1, i]), fill=(33, 132, 101) if objet[j-1, i] == 1 else (103, 113, 124))
            if not meme and objet[j, i]:
                dessin.line((i, y0, i, y1), fill=(33, 132, 101) if objet[j, i] == 1 else (103, 113, 124))
                y0 = y1
            dessin.line((i, y0, i, y1), fill=tuple(couleur[j, i]))
    if echelle < 1:
        image = image.resize((max(1, round(w*echelle)), image.height), Image.Resampling.LANCZOS)
    return image


def vue_relief_pdf(scene, gr, sommets=None):
    """Figure autonome et légende. L'exemple de construction conserve le plafond du PDF."""
    if not scene or not scene.get("disponible"):
        return None
    from shapely.affinity import translate
    from .scene import _geom_2975
    zone = _polygones(scene["zone_implantation"])
    hauteur = gr.hauteurReglementaireM
    forme = _geom_2975(gr.exempleEmpriseGeoJSON)
    ox, oy = scene["origine_2975"]
    exemple = translate(forme, -ox, -oy) if forme is not None else None
    projet = None
    if sommets is not None:
        projet = translate(Polygon(sommets), -ox, -oy)
        exemple = None
    image = _image(scene, exemple, hauteur, projet)
    if image is None:
        return None
    out = BytesIO()
    image.save(out, format="PNG")
    data = base64.b64encode(out.getvalue()).decode("ascii")
    leg = [(C_ZONE, "Zone d’implantation")] if zone else []
    if projet is not None:
        leg.append(("#185fa3", "Implantation dessinée au sol"))
    if exemple is not None:
        leg.append(("#218465", f"Exemple indicatif · {gr.exempleEmpriseM2:g} m² au sol · hauteur {hauteur:g} m".replace(".", ",")))
    for cle, couleur, label in (("reculs", C_RETRAIT, "Bandes de recul"), ("batiments", C_BATI, "Bâti existant"),
                                ("exclusions", C_EXCL, "Exclusions")):
        if scene[cle]:
            leg.append((couleur, label))
    leg.append((C_CONTOUR, "Limite cadastrale"))
    maille = scene["meta"].get("maille_m")
    source = (f" · maille source {maille:g} m".replace(".", ",") if maille else "")
    return (f'<img alt="Terrain en relief, bâtiments et règles d’implantation" '
            f'style="display:block;width:100%;height:auto;max-height:100mm;object-fit:contain" '
            f'src="data:image/png;base64,{data}">' +
            _legende_html(f"Relief IGN{source} · échelle verticale réelle · altitudes REUN89.", leg))
