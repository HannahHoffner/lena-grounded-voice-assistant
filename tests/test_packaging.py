"""Regressionstests für die installierbare LENA-Distribution."""

from pathlib import Path

import app.config as config


def test_installed_root_is_used_when_checkout_has_no_data(monkeypatch, tmp_path: Path) -> None:
    """Die Wheel-Installation findet ihre unter dem Umgebungspräfix liegenden Daten."""
    package_root = tmp_path / "site-packages"
    installed_root = tmp_path / "environment"
    kb_path = installed_root / "data" / "canonical" / "offers.json"
    kb_path.parent.mkdir(parents=True)
    kb_path.write_text("{}", encoding="utf-8")

    fake_module = package_root / "app" / "config.py"
    monkeypatch.setattr(config, "__file__", str(fake_module))
    monkeypatch.setattr(config.sys, "prefix", str(installed_root))

    assert config._resolve_app_root() == installed_root.resolve()


def test_checkout_root_has_priority_over_environment(monkeypatch, tmp_path: Path) -> None:
    """Editable Installationen verwenden weiterhin Daten aus ihrem Checkout."""
    checkout_root = tmp_path / "checkout"
    kb_path = checkout_root / "data" / "canonical" / "offers.json"
    kb_path.parent.mkdir(parents=True)
    kb_path.write_text("{}", encoding="utf-8")

    fake_module = checkout_root / "app" / "config.py"
    monkeypatch.setattr(config, "__file__", str(fake_module))
    monkeypatch.setattr(config.sys, "prefix", str(tmp_path / "environment"))

    assert config._resolve_app_root() == checkout_root.resolve()
