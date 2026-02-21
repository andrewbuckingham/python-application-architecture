"""Microsoft SQL Server implementation of CountryRepository.

Uses pyodbc with the Microsoft ODBC Driver for SQL Server.
A typical connection string for local development:

    Driver={ODBC Driver 18 for SQL Server};
    Server=localhost;
    Database=metrics;
    Trusted_Connection=yes;
    Encrypt=no;

For Azure SQL Database, use:

    Driver={ODBC Driver 18 for SQL Server};
    Server=<server>.database.windows.net;
    Database=metrics;
    Authentication=ActiveDirectoryInteractive;
    Encrypt=yes;

The `add` method is intentionally NOT part of the CountryRepository
Protocol – it exists on the concrete class and is used by the Composition
Root to seed reference data. The domain service only ever sees the
read-only Protocol.
"""
from contextlib import contextmanager
from typing import Generator

import pyodbc

from domain.models import Country


class MssqlCountryRepository:
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._initialise_schema()

    # ------------------------------------------------------------------
    # CountryRepository protocol implementation (read-only)
    # ------------------------------------------------------------------

    def get_by_code(self, code: str) -> Country | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, code, name, population, area_km2, "
                "gdp_usd_billions, life_expectancy "
                "FROM countries WHERE code = ?",
                (code.upper(),),
            ).fetchone()
        return _row_to_country(row) if row else None

    def list_all(self) -> list[Country]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, code, name, population, area_km2, "
                "gdp_usd_billions, life_expectancy FROM countries"
            ).fetchall()
        return [_row_to_country(row) for row in rows]

    # ------------------------------------------------------------------
    # Setup method – NOT part of the Protocol, used by Composition Root
    # ------------------------------------------------------------------

    def add(self, country: Country) -> Country:
        """Insert a country record if one with that code does not already exist."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM countries WHERE code = ?",
                (country.code.upper(),),
            ).fetchone()
            if existing:
                country.id = existing[0]
                return country
            row = conn.execute(
                "INSERT INTO countries "
                "    (code, name, population, area_km2, gdp_usd_billions, life_expectancy) "
                "OUTPUT INSERTED.id "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    country.code.upper(),
                    country.name,
                    country.population,
                    country.area_km2,
                    country.gdp_usd_billions,
                    country.life_expectancy,
                ),
            ).fetchone()
            country.id = row[0]
        return country

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _initialise_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                IF OBJECT_ID('countries', 'U') IS NULL
                CREATE TABLE countries (
                    id               INT IDENTITY(1,1) PRIMARY KEY,
                    code             NVARCHAR(3)   NOT NULL UNIQUE,
                    name             NVARCHAR(200) NOT NULL,
                    population       BIGINT        NOT NULL,
                    area_km2         FLOAT         NOT NULL,
                    gdp_usd_billions FLOAT         NOT NULL,
                    life_expectancy  FLOAT         NOT NULL
                )
            """)

    @contextmanager
    def _connect(self) -> Generator[pyodbc.Connection, None, None]:
        conn = pyodbc.connect(self._connection_string)
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _row_to_country(row: pyodbc.Row) -> Country:
    return Country(
        id=row[0],
        code=row[1],
        name=row[2],
        population=row[3],
        area_km2=row[4],
        gdp_usd_billions=row[5],
        life_expectancy=row[6],
    )
