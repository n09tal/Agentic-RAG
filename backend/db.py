import psycopg


def database_is_reachable(database_url: str) -> bool:
    try:
        with psycopg.connect(database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.OperationalError:
        return False