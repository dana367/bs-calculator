from quart_db import Connection


async def migrate(connection: Connection) -> None:
    await connection.execute("PRAGMA foreign_keys = ON;")

    await connection.execute(
        """CREATE TABLE calculations (
                id INTEGER PRIMARY KEY,
                stock_price FLOAT NOT NULL,
                strike_price FLOAT NOT NULL,
                time_to_maturity FLOAT NOT NULL,
                risk_free_rate FLOAT NOT NULL,
                dividend_yield FLOAT NOT NULL,
                volatility FLOAT NOT NULL,
                call_option_price FLOAT NOT NULL,
                put_option_price FLOAT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )""",
    )

    await connection.execute(
        """CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE
        )""",
    )

    await connection.execute(
        """CREATE TABLE calculation_history (
                id INTEGER PRIMARY KEY,
                calculation_id INTEGER REFERENCES calculations(id) ON DELETE CASCADE,
                action TEXT NOT NULL,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                performed_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )""",
    )


async def valid_migration(connection: Connection) -> bool:
    return True
