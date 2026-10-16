"""The app must refuse to start with a missing or placeholder secret."""
import pytest

from app import create_app, validate_secrets
from config import Config

GOOD = {"SECRET_KEY": "a" * 8 + "f3b9c1d47e2a6058", "SECURITY_PASSWORD_SALT": "9d8c7b6a5f4e3d2c1b0a"}


class Prod(Config):
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SECRET_KEY = GOOD["SECRET_KEY"]
    SECURITY_PASSWORD_SALT = GOOD["SECURITY_PASSWORD_SALT"]


def test_valid_secrets_pass():
    validate_secrets(GOOD)


@pytest.mark.parametrize("name", ["SECRET_KEY", "SECURITY_PASSWORD_SALT"])
def test_missing_secret_is_rejected(name):
    with pytest.raises(RuntimeError, match=f"{name} is not set"):
        validate_secrets({**GOOD, name: None})


@pytest.mark.parametrize("bad", ["short", "change-me-to-a-long-random-string", "dev-secret-key-change-me", "your_secret_key_here"])
def test_weak_or_placeholder_secret_is_rejected(bad):
    with pytest.raises(RuntimeError, match="placeholder or too short"):
        validate_secrets({**GOOD, "SECRET_KEY": bad})


def test_create_app_refuses_to_start_without_secret():
    class NoSecret(Prod):
        SECRET_KEY = None

    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        create_app(NoSecret)


def test_create_app_starts_with_strong_secrets():
    assert create_app(Prod).config["SECRET_KEY"] == GOOD["SECRET_KEY"]
