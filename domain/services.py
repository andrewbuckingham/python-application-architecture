"""Comparison service – pure business logic.

The service depends only on the repository *Protocols*, never on concrete
implementations. Both repositories are injected through the constructor,
mirroring C# constructor-based DI with multiple interface dependencies.
"""
from domain.exceptions import (
    ComparisonNotFoundError,
    CountryNotFoundError,
    SameCountryComparisonError,
)
from domain.models import Country, CountryComparison
from domain.repositories import ComparisonRepository, CountryRepository


class ComparisonService:
    def __init__(
        self,
        country_repository: CountryRepository,
        comparison_repository: ComparisonRepository,
    ) -> None:
        self._countries = country_repository
        self._comparisons = comparison_repository

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def compare(self, country_x_code: str, country_y_code: str) -> CountryComparison:
        """Compute metrics between two countries and persist the result."""
        if country_x_code == country_y_code:
            raise SameCountryComparisonError(country_x_code)

        x = self._resolve_country(country_x_code)
        y = self._resolve_country(country_y_code)

        comparison = CountryComparison(
            country_x_code=x.code,
            country_y_code=y.code,
            gdp_per_capita_ratio=x.gdp_per_capita / y.gdp_per_capita,
            population_ratio=x.population / y.population,
            life_expectancy_delta=x.life_expectancy - y.life_expectancy,
            population_density_ratio=x.population_density / y.population_density,
        )
        return self._comparisons.save(comparison)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_comparison(self, comparison_id: int) -> CountryComparison:
        comparison = self._comparisons.get_by_id(comparison_id)
        if comparison is None:
            raise ComparisonNotFoundError(comparison_id)
        return comparison

    def list_comparisons(self) -> list[CountryComparison]:
        return self._comparisons.list_all()

    def list_countries(self) -> list[Country]:
        return self._countries.list_all()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_country(self, code: str) -> Country:
        country = self._countries.get_by_code(code)
        if country is None:
            raise CountryNotFoundError(code)
        return country
