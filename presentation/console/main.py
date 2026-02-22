"""Console entry point – Composition Root for the CLI.

This is the only module that imports from both domain and infrastructure,
wiring them together before handing control to the service.

Set the DB_CONNECTION_STRING environment variable before running, e.g.:
    Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=metrics;Trusted_Connection=yes;Encrypt=no;
"""
import os

from domain.models import Country
from domain.services import ComparisonService
from infrastructure.mssql_comparison_repository import MssqlComparisonRepository
from infrastructure.mssql_country_repository import MssqlCountryRepository

_DEFAULT_CONNECTION_STRING = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=localhost;"
    "Database=metrics;"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
)


def main() -> None:
    connection_string = os.environ.get("DB_CONNECTION_STRING", _DEFAULT_CONNECTION_STRING)

    # --- Composition root: wire up the dependency graph ---
    country_repo = MssqlCountryRepository(connection_string)
    comparison_repo = MssqlComparisonRepository(connection_string)
    service = ComparisonService(country_repo, comparison_repo)

    # --- Seed reference data (uses the concrete type, not the Protocol) ---
    _seed_countries(country_repo)

    # --- Demo interaction ---
    print("=== Country Metrics Comparison ===\n")
    print("Countries loaded:")
    for c in service.list_countries():
        print(f"  {c.code}  {c.name:<20}  pop: {c.population:>12,}  "
              f"GDP/capita: ${c.gdp_per_capita:>10,.0f}  "
              f"life exp: {c.life_expectancy:.1f} yrs")

    print()
    for x_code, y_code in [("GBR", "USA"), ("DEU", "IND"), ("USA", "CHN")]:
        result = service.compare(x_code, y_code)
        print(f"[{result.id}] {result.country_x_code} vs {result.country_y_code}")
        print(f"     GDP/capita ratio:        {result.gdp_per_capita_ratio:.3f}")
        print(f"     Population ratio:        {result.population_ratio:.3f}")
        print(f"     Life expectancy delta:   {result.life_expectancy_delta:+.1f} yrs")
        print(f"     Pop. density ratio:      {result.population_density_ratio:.3f}")
        print()

    all_comparisons = service.list_comparisons()
    print(f"{len(all_comparisons)} comparison(s) saved.")


def _seed_countries(repo: MssqlCountryRepository) -> None:
    """Seed a small reference dataset.  Called from the Composition Root,
    which knows the concrete type and can call methods outside the Protocol."""
    countries = [
        Country("GBR", "United Kingdom",  67_026_292,   242_495,  3_131.0, 81.3),
        Country("USA", "United States",  331_000_000, 9_833_517, 25_463.0, 78.9),
        Country("DEU", "Germany",         84_270_625,   357_114,  4_082.0, 81.1),
        Country("IND", "India",        1_380_004_385, 3_287_263,  3_385.0, 70.8),
        Country("CHN", "China",        1_411_778_724, 9_596_960, 17_963.0, 77.4),
    ]
    for country in countries:
        repo.add(country)


if __name__ == "__main__":
    main()
