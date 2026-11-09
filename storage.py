import asyncio
import json
import os

from config import DATA_FILE

_lock = asyncio.Lock()


def _load() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp = f"{DATA_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp, DATA_FILE)


async def get_user(user_id) -> dict | None:
    async with _lock:
        return _load().get(str(user_id))


async def set_user(user_id, phone, token, refresh_token) -> None:
    async with _lock:
        db = _load()
        db[str(user_id)] = {"phone": phone, "token": token, "refreshToken": refresh_token}
        _save(db)


async def delete_user(user_id) -> None:
    async with _lock:
        db = _load()
        db.pop(str(user_id), None)
        _save(db)


async def save_tokens(user_id, res) -> None:
    if not res or not res.get("newTokens"):
        return
    async with _lock:
        db = _load()
        user = db.get(str(user_id))
        if not user:
            return
        user["token"] = res["newTokens"]["t"]
        user["refreshToken"] = res["newTokens"]["rt"]
        _save(db)


async def count_users() -> int:
    async with _lock:
        return len(_load())
