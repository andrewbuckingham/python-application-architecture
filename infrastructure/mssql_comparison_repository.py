"""Microsoft SQL Server implementation of ComparisonRepository.

Uses pyodbc with the Microsoft ODBC Driver for SQL Server.
See mssql_country_repository.py for connection string examples.
"""
from contextlib import contextmanager
from typing import Generator

import pyodbc

from domain.models import CountryComparison


class MssqlComparisonRepository:
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._initialise_schema()

    # ------------------------------------------------------------------
    # ComparisonRepository protocol implementation
    # ------------------------------------------------------------------

    def get_by_id(self, comparison_id: int) -> CountryComparison | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, country_x_code, country_y_code, "
                "gdp_per_capita_ratio, population_ratio, "
                "life_expectancy_delta, population_density_ratio "
                "FROM comparisons WHERE id = ?",
                (comparison_id,),
            ).fetchone()
        return _row_to_comparison(row) if row else None

    def list_all(self) -> list[CountryComparison]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, country_x_code, country_y_code, "
                "gdp_per_capita_ratio, population_ratio, "
                "life_expectancy_delta, population_density_ratio "
                "FROM comparisons"
            ).fetchall()
        return [_row_to_comparison(row) for row in rows]

    def save(self, comparison: CountryComparison) -> CountryComparison:
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO comparisons "
                "    (country_x_code, country_y_code, gdp_per_capita_ratio, "
                "     population_ratio, life_expectancy_delta, population_density_ratio) "
                "OUTPUT INSERTED.id "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    comparison.country_x_code,
                    comparison.country_y_code,
                    comparison.gdp_per_capita_ratio,
                    comparison.population_ratio,
                    comparison.life_expectancy_delta,
                    comparison.population_density_ratio,
                ),
            ).fetchone()
            comparison.id = row[0]
        return comparison

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _initialise_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                IF OBJECT_ID('comparisons', 'U') IS NULL
                CREATE TABLE comparisons (
                    id                       INT IDENTITY(1,1) PRIMARY KEY,
                    country_x_code           NVARCHAR(3) NOT NULL,
                    country_y_code           NVARCHAR(3) NOT NULL,
                    gdp_per_capita_ratio     FLOAT       NOT NULL,
                    population_ratio         FLOAT       NOT NULL,
                    life_expectancy_delta    FLOAT       NOT NULL,
                    population_density_ratio FLOAT       NOT NULL
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


def _row_to_comparison(row: pyodbc.Row) -> CountryComparison:
    return CountryComparison(
        id=row[0],
        country_x_code=row[1],
        country_y_code=row[2],
        gdp_per_capita_ratio=row[3],
        population_ratio=row[4],
        life_expectancy_delta=row[5],
        population_density_ratio=row[6],
    )
