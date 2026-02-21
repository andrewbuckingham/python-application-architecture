"""Unit tests for ComparisonService.

Naming convention
-----------------
Tests follow a two-part pattern within each class:

    test_<state_under_test>__<expected_result>

The double underscore separates the condition from the outcome, giving
each name the same information as the .NET idiom
`Method_WithCondition_ReturnsResult`, but without repeating the method
name that is already expressed by the class.

The shared `comparison_service` fixture (see conftest.py) acts as the
Arrange step for most tests. Explicit Arrange-Act-Assert comments are
reserved for the longer scenario tests in TestScenarios, where the setup
is substantial enough to need signposting.
"""
import pytest

from domain.exceptions import (
    ComparisonNotFoundError,
    CountryNotFoundError,
    SameCountryComparisonError,
)
from domain.models import Country
from domain.services import ComparisonService
from tests.conftest import DEU, GBR, USA
from tests.fakes.fake_comparison_repository import FakeComparisonRepository
from tests.fakes.fake_country_repository import FakeCountryRepository


class TestCompare:
    # Simple happy-path assertion: call the method once, assert a single fact
    # about the returned object. The fixture handles all setup; the test body
    # is intentionally minimal.
    def test_valid_pair__returns_comparison_with_assigned_id(
        self, comparison_service: ComparisonService
    ) -> None:
        result = comparison_service.compare("GBR", "USA")
        assert result.id > 0

    # Computed metric check: verify that one output field equals the expected
    # formula. Only one metric is tested here; TestMetricCalculations below
    # covers the same pattern across multiple country pairs.
    def test_valid_pair__gdp_per_capita_ratio_is_x_over_y(
        self, comparison_service: ComparisonService
    ) -> None:
        result = comparison_service.compare("GBR", "USA")
        expected = GBR.gdp_per_capita / USA.gdp_per_capita
        assert result.gdp_per_capita_ratio == pytest.approx(expected, rel=1e-6)

    # Persistence round-trip: verify that the result written by compare() can
    # be read back in full via a separate service call.
    def test_valid_pair__result_is_retrievable_by_id(
        self, comparison_service: ComparisonService
    ) -> None:
        result = comparison_service.compare("GBR", "USA")
        retrieved = comparison_service.get_comparison(result.id)
        assert retrieved.country_x_code == "GBR"
        assert retrieved.country_y_code == "USA"

    # Parameterised error condition: the same exception must be raised whether
    # the unknown code is in position X or position Y. One Parameterised test
    # replaces two near-identical methods and names each run automatically
    # (e.g. test_unknown_country_code__raises_...[ZZZ-USA-ZZZ]).
    @pytest.mark.parametrize("x_code, y_code, missing_code", [
        ("ZZZ", "USA", "ZZZ"),  # x is unknown
        ("GBR", "ZZZ", "ZZZ"),  # y is unknown
    ])
    def test_unknown_country_code__raises_country_not_found_error(
        self,
        comparison_service: ComparisonService,
        x_code: str,
        y_code: str,
        missing_code: str,
    ) -> None:
        with pytest.raises(CountryNotFoundError) as exc_info:
            comparison_service.compare(x_code, y_code)
        assert exc_info.value.code == missing_code

    # Parameterised guard condition: a validation rule that applies uniformly
    # to any value in a set. Parametrize confirms the rule is not accidentally
    # hard-coded to one specific input.
    @pytest.mark.parametrize("code", ["GBR", "USA", "DEU"])
    def test_same_country_codes__raises_same_country_comparison_error(
        self, comparison_service: ComparisonService, code: str
    ) -> None:
        with pytest.raises(SameCountryComparisonError):
            comparison_service.compare(code, code)


class TestGetComparison:
    # Error case for a separate service method. Kept in its own class so that
    # the test output groups by the operation under test.
    def test_nonexistent_id__raises_comparison_not_found_error(
        self, comparison_service: ComparisonService
    ) -> None:
        with pytest.raises(ComparisonNotFoundError) as exc_info:
            comparison_service.get_comparison(999)
        assert exc_info.value.comparison_id == 999


class TestListComparisons:
    # Boundary / empty-state test: verify correct behaviour before any data
    # exists. Catches off-by-one errors and uninitialised-state bugs.
    def test_empty_repository__returns_empty_list(
        self, comparison_service: ComparisonService
    ) -> None:
        assert comparison_service.list_comparisons() == []

    # Populated-state test: verify that every saved item is returned and none
    # are dropped or duplicated.
    def test_multiple_comparisons_saved__returns_all(
        self, comparison_service: ComparisonService
    ) -> None:
        comparison_service.compare("GBR", "USA")
        comparison_service.compare("DEU", "GBR")
        results = comparison_service.list_comparisons()
        assert len(results) == 2
        pairs = {(r.country_x_code, r.country_y_code) for r in results}
        assert pairs == {("GBR", "USA"), ("DEU", "GBR")}


class TestMetricCalculations:
    """Parameterised tests that verify a computed metric across multiple country
    pairs, rather than pinning the formula to a single example. The same
    pattern can be applied to any of the four metrics on CountryComparison.
    """

    _COUNTRIES = {c.code: c for c in [GBR, USA, DEU]}

    # Parameterised metric: the same formula is asserted for several country
    # pairs, including the reverse direction (DEU-GBR), to guard against a
    # result that happens to pass for one pair but uses the wrong operand order.
    @pytest.mark.parametrize("x_code, y_code", [
        ("GBR", "USA"),
        ("USA", "DEU"),
        ("DEU", "GBR"),
    ])
    def test_valid_pair__gdp_per_capita_ratio_equals_x_divided_by_y(
        self, comparison_service: ComparisonService, x_code: str, y_code: str
    ) -> None:
        expected = self._COUNTRIES[x_code].gdp_per_capita / self._COUNTRIES[y_code].gdp_per_capita
        result = comparison_service.compare(x_code, y_code)
        assert result.gdp_per_capita_ratio == pytest.approx(expected, rel=1e-6)


class TestScenarios:
    """Longer scenario tests that warrant explicit Arrange-Act-Assert structure.

    These tests construct their own repositories rather than using the shared
    conftest fixture, because the data is specific to the scenario.
    """

    # Scenario / integration-style test: exercises multiple service calls in
    # sequence and asserts relationships between results rather than exact
    # values. Uses explicit AAA comments because the setup is substantial enough
    # to lose structure without them. Constructs its own service instance so
    # the country data (chosen deliberately to span a wide development range)
    # is not confused with the generic shared fixture data.
    def test_wide_development_range__ratio_ordering_reflects_real_world_gdp_ranking(
        self,
    ) -> None:
        # Arrange: three countries spanning a wide development range,
        # seeded into a fresh repository independent of the shared fixtures.
        norway   = Country("NOR", "Norway",    5_391_369,   385_207,  482.0, 83.2)
        brazil   = Country("BRA", "Brazil",  214_326_223, 8_515_767, 1_610.0, 75.9)
        ethiopia = Country("ETH", "Ethiopia", 117_876_227, 1_104_300,   111.3, 67.8)

        country_repo = FakeCountryRepository([norway, brazil, ethiopia])
        comparison_repo = FakeComparisonRepository()
        service = ComparisonService(country_repo, comparison_repo)

        # Act: compare each country against Brazil as a midpoint benchmark.
        nor_vs_bra = service.compare("NOR", "BRA")
        eth_vs_bra = service.compare("ETH", "BRA")

        # Assert: the direction of each metric should reflect known real-world
        # ordering — Norway is wealthier and longer-lived than Brazil, Ethiopia
        # is poorer and shorter-lived.
        assert nor_vs_bra.gdp_per_capita_ratio > 1.0
        assert eth_vs_bra.gdp_per_capita_ratio < 1.0
        assert nor_vs_bra.life_expectancy_delta > 0
        assert eth_vs_bra.life_expectancy_delta < 0

        # Both results must be independently retrievable from the repository.
        assert service.get_comparison(nor_vs_bra.id) is not None
        assert service.get_comparison(eth_vs_bra.id) is not None
        assert len(service.list_comparisons()) == 2
