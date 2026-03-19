import runpy
import sys
import types


def test_main_exits_without_token(monkeypatch):
    fake_bot = types.SimpleNamespace(run=lambda token: None)
    fake_app = types.SimpleNamespace(create_application=lambda settings: (fake_bot, None, None, None))
    fake_config = types.SimpleNamespace(
        load_settings=lambda: types.SimpleNamespace(token="YOUR_BOT_TOKEN"),
    )
    fake_dotenv = types.SimpleNamespace(load_dotenv=lambda **kwargs: None)

    monkeypatch.setitem(sys.modules, "app", fake_app)
    monkeypatch.setitem(sys.modules, "config", fake_config)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)

    try:
        runpy.run_module("main", run_name="__main__")
    except SystemExit as exc:
        assert str(exc) == "Please set DISCORD_TOKEN env var"
    else:
        raise AssertionError("SystemExit was not raised")


def test_main_runs_bot_with_token(monkeypatch):
    calls = []
    fake_bot = types.SimpleNamespace(run=lambda token: calls.append(token))
    fake_app = types.SimpleNamespace(create_application=lambda settings: (fake_bot, None, None, None))
    fake_config = types.SimpleNamespace(
        load_settings=lambda: types.SimpleNamespace(token="secret-token"),
    )
    fake_dotenv = types.SimpleNamespace(load_dotenv=lambda **kwargs: None)

    monkeypatch.setitem(sys.modules, "app", fake_app)
    monkeypatch.setitem(sys.modules, "config", fake_config)
    monkeypatch.setitem(sys.modules, "dotenv", fake_dotenv)

    runpy.run_module("main", run_name="__main__")

    assert calls == ["secret-token"]
