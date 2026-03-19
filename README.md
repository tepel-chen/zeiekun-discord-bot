# zeiekun-discord-bot

## Environment Setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

`.env` に以下を設定します。

- `DISCORD_TOKEN`
- `DISCORD_GUILD_ID`
- `CTF_CREATOR_ROLE_ID`
- `CTF_ROLE_ID`
- `CTF_CATEGORY`
- `ARCHIVE_CATEGORY`

起動:

```bash
python main.py
```

## Test

```bash
python -m pytest -q
```

`pytest.ini` により coverage も出力されます。HTML レポートは `htmlcov/index.html` です。

## Migration

DB migration には Alembic を使っています。

適用:

```bash
python -m alembic upgrade head
```

新しい migration 作成:

```bash
python -m alembic revision -m "describe change"
```

Bot 起動時にも `head` まで自動適用されます。
