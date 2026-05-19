#!/usr/bin/env python3
"""Idempotent live schema repair for production drift.

Adds missing columns/indexes for critical runtime tables and never drops data.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

from sqlalchemy import create_engine, inspect, text

TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "name": "VARCHAR(255) NULL",
        "plan": "VARCHAR(32) DEFAULT 'free'",
        "monthly_content_used": "INT DEFAULT 0",
        "auto_post_enabled": "BOOLEAN DEFAULT FALSE",
        "auto_reply_enabled": "BOOLEAN DEFAULT FALSE",
        "preferred_language": "VARCHAR(10) DEFAULT 'en'",
        "timezone": "VARCHAR(64) DEFAULT 'UTC'",
        "notification_preferences": "JSON NULL",
        "email_verified": "BOOLEAN DEFAULT FALSE",
        "referral_code": "VARCHAR(16) NULL",
        "stripe_customer_id": "VARCHAR(255) NULL",
    },
    "user_api_keys": {
        "key_name": "VARCHAR(128) NOT NULL DEFAULT ''",
        "encrypted_key": "TEXT NULL",
        "is_active": "BOOLEAN DEFAULT TRUE",
        "usage_count": "VARCHAR(20) DEFAULT '0'",
        "last_used_at": "DATETIME NULL",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "DATETIME NULL",
    },
    "user_integrations": {
        "platform": "VARCHAR(64) NOT NULL DEFAULT ''",
        "encrypted_access_token": "TEXT NULL",
        "encrypted_refresh_token": "TEXT NULL",
        "token_expires_at": "DATETIME NULL",
        "is_connected": "BOOLEAN DEFAULT FALSE",
        "connected_at": "DATETIME NULL",
        "platform_username": "VARCHAR(255) NULL",
        "scopes": "TEXT NULL",
        "auto_post_enabled": "BOOLEAN DEFAULT FALSE",
        "auto_reply_enabled": "BOOLEAN DEFAULT FALSE",
        "low_risk_auto_reply": "BOOLEAN DEFAULT FALSE",
        "oauth_state": "VARCHAR(255) NULL",
        "oauth_code_verifier": "VARCHAR(255) NULL",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "DATETIME NULL",
    },
    "webapps": {
        "name": "VARCHAR(255) NOT NULL DEFAULT ''",
        "url": "VARCHAR(512) NOT NULL DEFAULT ''",
        "description": "TEXT NOT NULL",
        "category": "VARCHAR(128) NOT NULL DEFAULT ''",
        "target_audience": "VARCHAR(512) NOT NULL DEFAULT ''",
        "key_features": "JSON NULL",
        "is_active": "BOOLEAN DEFAULT TRUE",
        "scraped_data": "JSON NULL",
        "brand_voice": "TEXT NULL",
        "market_location": "VARCHAR(255) NULL",
        "content_goals": "TEXT NULL",
        "scraper_source_urls": "JSON NULL",
        "media_assets": "JSON NULL",
    },
    "content": {
        "platform": "VARCHAR(64) NOT NULL DEFAULT ''",
        "status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
        "title": "VARCHAR(512) NOT NULL DEFAULT ''",
        "caption": "TEXT NOT NULL",
        "hashtags": "JSON NULL",
        "media_urls": "JSON NULL",
        "generation_metadata": "JSON NULL",
        "views": "INT DEFAULT 0",
        "likes": "INT DEFAULT 0",
        "comments": "INT DEFAULT 0",
        "shares": "INT DEFAULT 0",
        "clicks": "INT DEFAULT 0",
        "ctr": "FLOAT DEFAULT 0",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    },
    "analytics": {
        "platform": "VARCHAR(64) NOT NULL DEFAULT ''",
        "date": "DATE NULL",
        "posts": "INT DEFAULT 0",
        "views": "INT DEFAULT 0",
        "likes": "INT DEFAULT 0",
        "comments": "INT DEFAULT 0",
        "shares": "INT DEFAULT 0",
        "clicks": "INT DEFAULT 0",
        "ctr": "FLOAT DEFAULT 0",
        "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
    },
}

TABLE_INDEXES: dict[str, list[tuple[str, str]]] = {
    "users": [("ix_users_referral_code", "referral_code"), ("ix_users_stripe_customer_id", "stripe_customer_id")],
    "user_api_keys": [("ix_user_api_keys_user_key", "user_id, key_name"), ("ix_user_api_keys_active", "user_id, is_active")],
    "user_integrations": [("ix_user_integrations_user_platform", "user_id, platform"), ("ix_user_integrations_oauth_state", "oauth_state")],
    "webapps": [("ix_webapps_user_id", "user_id"), ("ix_webapps_is_active", "user_id, is_active")],
    "content": [("ix_content_user_webapp_platform", "user_id, webapp_id, platform"), ("ix_content_status", "user_id, status")],
    "analytics": [("ix_analytics_user_platform_date", "user_id, platform, date")],
}


def _exec(conn, sql: str) -> None:
    conn.execute(text(sql))


def _ensure_columns(conn, table: str, columns: dict[str, str], existing: set[str]) -> None:
    for name, ddl in columns.items():
        if name in existing:
            print(f"OK: {table}.{name}")
            continue
        _exec(conn, f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        print(f"ADDED: {table}.{name}")


def _ensure_indexes(conn, table: str, indexes: Iterable[tuple[str, str]], existing: set[str]) -> None:
    for index_name, column_expr in indexes:
        if index_name in existing:
            print(f"OK: {index_name}")
            continue
        _exec(conn, f"CREATE INDEX {index_name} ON {table} ({column_expr})")
        print(f"ADDED: {index_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair live schema drift safely")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""), help="DATABASE_URL")
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        return 1

    engine = create_engine(args.database_url)
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())

        for table_name, cols in TABLE_COLUMNS.items():
            if table_name not in tables:
                print(f"WARN: table '{table_name}' does not exist; skipping.")
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            _ensure_columns(conn, table_name, cols, existing_cols)

            inspector = inspect(conn)
            existing_indexes = {idx.get("name") for idx in inspector.get_indexes(table_name)}
            _ensure_indexes(conn, table_name, TABLE_INDEXES.get(table_name, []), existing_indexes)

    print("Schema repair completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
