"""Base commune des connecteurs : client HTTP poli + test de connexion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import get_settings


@dataclass
class ConnectionTestResult:
    source: str
    ok: bool
    message: str
    status_code: int | None = None
    sample: Any | None = None

    def as_dict(self) -> dict:
        return {
            "source": self.source, "ok": self.ok, "message": self.message,
            "status_code": self.status_code, "sample": self.sample,
        }


class Connector:
    """Connecteur abstrait. `name` doit matcher data_sources.name."""

    name: str = ""
    #: endpoint cheap pour le test de connexion (souvent un GET minimal)
    test_url: str | None = None
    test_params: dict | None = None

    def __init__(self, timeout: float | None = None):
        self.timeout = timeout if timeout is not None else get_settings().http_timeout_s

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, headers={"User-Agent": "LA-BUSE/0.1 (+pre-qualification fonciere)"})

    def test_connection(self) -> ConnectionTestResult:
        """Tente l'appel réel et rapporte honnêtement (réseau souvent bloqué ici)."""
        if not self.test_url:
            return ConnectionTestResult(self.name, False, "Pas d'endpoint de test défini.")
        try:
            with self._client() as c:
                r = c.get(self.test_url, params=self.test_params or {})
            ok = r.status_code == 200
            sample = None
            if ok:
                ctype = r.headers.get("content-type", "")
                sample = (r.json() if "json" in ctype else r.text[:300])
            return ConnectionTestResult(
                self.name, ok,
                "OK" if ok else f"Réponse HTTP {r.status_code}",
                status_code=r.status_code, sample=sample,
            )
        except Exception as exc:  # réseau bloqué / timeout / DNS
            return ConnectionTestResult(self.name, False, f"Inatteignable : {type(exc).__name__}: {exc}")


class GenericGetConnector(Connector):
    """Connecteur de test générique : un GET simple paramétrable.

    Couvre le bouton « tester la connexion » pour les sources REST/WFS/ODS
    confirmées live au SPIKE, sans coder une classe par source. Succès = HTTP 200.
    """

    def __init__(self, name: str, test_url: str, test_params: dict | None = None,
                 timeout: float | None = None):
        super().__init__(timeout)
        self.name = name
        self.test_url = test_url
        self.test_params = test_params or {}
