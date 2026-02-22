"""Shared PyTest fixtures – the Composition Root for the test suite.

Fixtures create fakes and wire them into services, mirroring exactly what
the real entry points do with real repositories.
"""
import pytest

from domain.models import Country
from domain.services import ComparisonService
from tests.fakes.fake_comparison_repository import FakeComparisonRepository
from tests.fakes.fake_country_repository import FakeCountryRepository


# ---------------------------------------------------------------------------
# Reusable country data
# ---------------------------------------------------------------------------

GBR = Country("GBR", "United Kingdom",  67_026_292,   242_495,  3_131.0, 81.3)
USA = Country("USA", "United States",  331_000_000, 9_833_517, 25_463.0, 78.9)
DEU = Country("DEU", "Germany",         84_270_625,   357_114,  4_082.0, 81.1)


# ---------------------------------------------------------------------------
# Repository fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_country_repo() -> FakeCountryRepository:
    """Country repository pre-seeded with a small reference dataset."""
    return FakeCountryRepository(countries=[GBR, USA, DEU])


@pytest.fixture()
def fake_comparison_repo() -> FakeComparisonRepository:
    """Empty comparison repository."""
    return FakeComparisonRepository()


# ---------------------------------------------------------------------------
# Service fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def comparison_service(
    fake_country_repo: FakeCountryRepository,
    fake_comparison_repo: FakeComparisonRepository,
) -> ComparisonService:
    """ComparisonService wired with both fake repositories."""
    return ComparisonService(fake_country_repo, fake_comparison_repo)
