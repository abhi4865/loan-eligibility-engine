"""Shared PostgreSQL connection and query helpers for the Lambda handlers."""

import os

import psycopg2


def get_connection():
    """Open a PostgreSQL connection using the current environment settings."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
    )


def run_query(query, params=None, *, fetch=False):
    """Run and commit one query, returning rows when fetch=True."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchall() if fetch else None
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
