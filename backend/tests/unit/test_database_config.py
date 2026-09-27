import pytest

from app.core import database
from app.core.settings import Settings


def _use(monkeypatch: pytest.MonkeyPatch, **values: object) -> None:
    settings = Settings(_env_file=None, **values)  # type: ignore[call-arg]
    monkeypatch.setattr(database, "get_settings", lambda: settings)


def test_tls_ca_is_passed_to_the_driver_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, db_ssl_ca="/srv/ca.pem")

    assert database.connect_args() == {"ssl": {"ca": "/srv/ca.pem"}}


def test_no_tls_arguments_without_a_ca(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch)

    assert database.connect_args() == {}


def test_missing_database_url_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch)

    with pytest.raises(RuntimeError, match="APP_DATABASE_URL is not set"):
        database.database_url()
