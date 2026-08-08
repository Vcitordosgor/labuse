"""M-C (F6) — durcissement de la validation du logo SVG (marque.valider_logo).

La garde ne couvrait que <script> ; un SVG peut aussi exécuter du JS via onload=/on*=,
<foreignObject> (HTML embarqué) ou une URI javascript:. Sans risque tant que le logo est
servi en base64 dans WeasyPrint, mais à durcir AVANT tout affichage inline.
"""
from __future__ import annotations

import pytest

from labuse.marque import valider_logo

_LEGIT = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


def test_svg_legitime_accepte():
    assert valider_logo(_LEGIT, "image/svg+xml") == "image/svg+xml"


@pytest.mark.parametrize("payload", [
    b'<svg><script>alert(1)</script></svg>',
    b'<svg onload="alert(1)"></svg>',
    b'<svg><rect onmouseover="x()"/></svg>',
    b'<svg><foreignObject><body>x</body></foreignObject></svg>',
    b'<svg><a xlink:href="javascript:alert(1)">x</a></svg>',
])
def test_svg_actif_refuse(payload):
    with pytest.raises(ValueError):
        valider_logo(payload, "image/svg+xml")


def test_png_toujours_accepte():
    png_magic = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    assert valider_logo(png_magic, "image/png") == "image/png"
