#!/usr/bin/env python3
"""Idempotent live repair for missing `users` auth/referral/billing columns.

Adds only missing columns/index/foreign key metadata and never drops data.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, inspect, text

REQUIRED_COLUMNS = {
    "email_verified": "BOOLEAN DEFAULT FALSE",
    "referral_code": "VARCHAR(16)",
    "referred_by": "VARCHAR(36)",
    "stripe_customer_id": "VARCHAR(255)",
}


def _execute(conn, sql: str) -> None:
    conn.execute(text(sql))


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair missing users columns for live DBs")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""), help="SQLAlchemy DATABASE_URL")
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL is required (env or --database-url)", file=sys.stderr)
        return 1

    engine = create_engine(args.database_url)
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "users" not in tables:
            print("users table does not exist; nothing to repair.")
            return 0

        columns = {c["name"] for c in inspector.get_columns("users")}
        dialect = engine.dialect.name

        for col, ddl in REQUIRED_COLUMNS.items():
            if col in columns:
                print(f"OK: users.{col} exists")
                continue
            _execute(conn, f"ALTER TABLE users ADD COLUMN {col} {ddl}")
            print(f"ADDED: users.{col}")

        inspector = inspect(conn)
        indexes = {idx.get("name") for idx in inspector.get_indexes("users")}
        fks = {fk.get("name") for fk in inspector.get_foreign_keys("users")}

        if "ix_users_referral_code" not in indexes:
            _execute(conn, "CREATE UNIQUE INDEX ix_users_referral_code ON users (referral_code)")
            print("ADDED: ix_users_referral_code")
        else:
            print("OK: ix_users_referral_code exists")

        if "uq_users_stripe_customer_id" not in indexes:
            _execute(conn, "CREATE UNIQUE INDEX uq_users_stripe_customer_id ON users (stripe_customer_id)")
            print("ADDED: uq_users_stripe_customer_id")
        else:
            print("OK: uq_users_stripe_customer_id exists")

        if "fk_users_referred_by_users" not in fks:
            if dialect in {"mysql", "mariadb"}:
                _execute(
                    conn,
                    "ALTER TABLE users ADD CONSTRAINT fk_users_referred_by_users "
                    "FOREIGN KEY (referred_by) REFERENCES users(id)",
                )
            else:
                _execute(
                    conn,
                    "ALTER TABLE users ADD CONSTRAINT fk_users_referred_by_users "
                    "FOREIGN KEY (referred_by) REFERENCES users(id)",
                )
            print("ADDED: fk_users_referred_by_users")
        else:
            print("OK: fk_users_referred_by_users exists")

    print("Live user-column repair complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
