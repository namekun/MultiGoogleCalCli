"""Tests for multicalcli.config."""

import json
import os

import pytest

from multicalcli import config


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect config dirs to a temporary directory."""
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "ACCOUNTS_DIR", tmp_path / "accounts")
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(config, "CLIENT_SECRET_FILE", tmp_path / "client_secret.json")
    return tmp_path


class TestValidateAccountName:
    def test_valid_names(self):
        assert config.validate_account_name("myaccount") == "myaccount"
        assert config.validate_account_name("my-account") == "my-account"
        assert config.validate_account_name("my_account_2") == "my_account_2"

    def test_invalid_names(self):
        with pytest.raises(ValueError):
            config.validate_account_name("../evil")
        with pytest.raises(ValueError):
            config.validate_account_name("my account")
        with pytest.raises(ValueError):
            config.validate_account_name("account/sub")


class TestLoadSaveConfig:
    def test_load_creates_default(self, tmp_config):
        cfg = config.load_config()
        assert cfg["default_account"] is None
        assert cfg["display"]["military_time"] is True
        assert (tmp_config / "config.json").exists()

    def test_save_and_load_roundtrip(self, tmp_config):
        cfg = {"default_account": "test", "display": {"military_time": False}}
        config.save_config(cfg)
        loaded = config.load_config()
        assert loaded["default_account"] == "test"
        assert loaded["display"]["military_time"] is False

    def test_config_file_permissions(self, tmp_config):
        config.save_config(config.DEFAULT_CONFIG)
        stat = os.stat(tmp_config / "config.json")
        assert stat.st_mode & 0o777 == 0o600


class TestListAccountNames:
    def test_empty(self, tmp_config):
        assert config.list_account_names() == []

    def test_with_accounts(self, tmp_config):
        acc_dir = tmp_config / "accounts" / "alice"
        acc_dir.mkdir(parents=True)
        (acc_dir / "token.json").write_text("{}")

        acc_dir2 = tmp_config / "accounts" / "bob"
        acc_dir2.mkdir(parents=True)
        (acc_dir2 / "token.json").write_text("{}")

        names = config.list_account_names()
        assert names == ["alice", "bob"]

    def test_ignores_dirs_without_token(self, tmp_config):
        acc_dir = tmp_config / "accounts" / "incomplete"
        acc_dir.mkdir(parents=True)
        # No token.json
        assert config.list_account_names() == []


class TestGetClientSecret:
    def test_global_fallback(self, tmp_config):
        secret = {"installed": {"client_id": "test"}}
        (tmp_config / "client_secret.json").write_text(json.dumps(secret))
        result = config.get_client_secret()
        assert result["installed"]["client_id"] == "test"

    def test_per_account_override(self, tmp_config):
        # Global secret
        (tmp_config / "client_secret.json").write_text(
            json.dumps({"installed": {"client_id": "global"}})
        )
        # Per-account secret
        acc_dir = tmp_config / "accounts" / "special"
        acc_dir.mkdir(parents=True)
        (acc_dir / "client_secret.json").write_text(
            json.dumps({"installed": {"client_id": "special"}})
        )
        result = config.get_client_secret("special")
        assert result["installed"]["client_id"] == "special"

    def test_returns_none_when_missing(self, tmp_config):
        assert config.get_client_secret() is None
