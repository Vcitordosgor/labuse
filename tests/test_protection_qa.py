"""M7 — voie QA prod : allowlist d'IPs exemptées du rate-limit (jamais dev_mode global)."""
from __future__ import annotations


def test_allowlist_qa_exempte_seulement_les_ips_listees(monkeypatch):
    from labuse import config
    from labuse.api import protection

    class Req:
        method = "GET"
        cookies: dict = {}
        headers: dict = {}
        class url:  # noqa: N801
            path = "/parcels/97400000AA0001"
        class client:  # noqa: N801
            host = "203.0.113.7"

    monkeypatch.setenv("LABUSE_QA_ALLOWLIST", "203.0.113.7")
    config.get_settings.cache_clear()
    s = config.get_settings()
    assert "203.0.113.7" in {x.strip() for x in s.qa_allowlist.split(",")}
    assert protection.ip_reelle(Req()) == "203.0.113.7"
    # une autre IP n'est PAS exemptée
    monkeypatch.setenv("LABUSE_QA_ALLOWLIST", "198.51.100.1")
    config.get_settings.cache_clear()
    assert protection.ip_reelle(Req()) not in {x.strip() for x in config.get_settings().qa_allowlist.split(",")}
    monkeypatch.delenv("LABUSE_QA_ALLOWLIST")
    config.get_settings.cache_clear()
