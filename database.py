"""Small MySQL helpers shared by the bot and the local dashboard."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import mysql.connector

import config


def connect():
    return mysql.connector.connect(**config.configsql)


def _fetch_one(query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    connection = connect()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def get_player_by_discord_id(discord_id: int) -> dict[str, Any] | None:
    return _fetch_one(
        "SELECT playerName, DiscordIDWhitelist FROM players "
        "WHERE DiscordIDWhitelist = %s LIMIT 1",
        (str(discord_id),),
    )


def get_whitelisted_player(discord_id: int) -> dict[str, Any] | None:
    player = _fetch_one(
        "SELECT playerName, playerWallet FROM players "
        "WHERE DiscordIDWhitelist = %s LIMIT 1",
        (str(discord_id),),
    )
    if player:
        player.setdefault("playerWallet", 0)
    return player


def get_player_by_name(player_name: str) -> dict[str, Any] | None:
    return _fetch_one(
        "SELECT playerName, DiscordIDWhitelist FROM players "
        "WHERE playerName = %s LIMIT 1",
        (player_name,),
    )


def player_exists(player_name: str) -> bool:
    return _fetch_one(
        "SELECT 1 AS found FROM players WHERE playerName = %s LIMIT 1",
        (player_name,),
    ) is not None


def transaction_reference_exists(reference: str) -> bool:
    return _fetch_one(
        "SELECT 1 AS found FROM topup_transactions "
        "WHERE ref_code = %s LIMIT 1",
        (reference,),
    ) is not None


def add_topup_transaction(
    player_name: str,
    amount: int,
    payment_method: str,
    reference: str,
) -> None:
    connection = connect()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO topup_transactions "
            "(playerName, amount, payment_method, processed, ref_code) "
            "VALUES (%s, %s, %s, 0, %s)",
            (player_name, amount, payment_method, reference),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_topup_summary(limit: int = 200) -> dict[str, Any]:
    """Return read-only totals and recent rows, adapting to the table columns."""
    connection = connect()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT COUNT(*) AS transaction_count, "
            "COALESCE(SUM(amount), 0) AS amount_total, "
            "COALESCE(SUM(CASE WHEN processed = 0 THEN 1 ELSE 0 END), 0) "
            "AS pending_count, "
            "COALESCE(SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END), 0) "
            "AS processed_count "
            "FROM topup_transactions"
        )
        totals = cursor.fetchone() or {}

        cursor.execute("SELECT * FROM topup_transactions LIMIT 0")
        available = {column[0] for column in (cursor.description or [])}
        visible_columns = [
            name
            for name in (
                "id",
                "playerName",
                "amount",
                "payment_method",
                "processed",
                "ref_code",
                "created_at",
                "createdAt",
                "timestamp",
            )
            if name in available
        ]

        recent: list[dict[str, Any]] = []
        if visible_columns:
            order_column = next(
                (
                    name
                    for name in ("created_at", "createdAt", "timestamp", "id")
                    if name in available
                ),
                None,
            )
            fields = ", ".join(f"`{name}`" for name in visible_columns)
            order = f" ORDER BY `{order_column}` DESC" if order_column else ""
            cursor.execute(
                f"SELECT {fields} FROM topup_transactions{order} LIMIT %s",
                (max(1, min(int(limit), 500)),),
            )
            recent = cursor.fetchall() or []

        cursor.execute(
            "SELECT payment_method, COUNT(*) AS transaction_count, "
            "COALESCE(SUM(amount), 0) AS amount_total "
            "FROM topup_transactions GROUP BY payment_method"
        )
        methods = cursor.fetchall() or []

        return {
            "totals": _json_values(totals),
            "methods": [_json_values(row) for row in methods],
            "recent": [_json_values(row) for row in recent],
        }
    finally:
        cursor.close()
        connection.close()


def _json_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_values(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat(sep=" ")
        except TypeError:
            return value.isoformat()
    return value
