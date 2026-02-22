# Python Layered Architecture Skeleton

A skeleton Python application demonstrating **clean layered architecture** using idiomatic Python patterns. It is aimed at teams who are comfortable writing Python — particularly for data science — but who want to bring the same structural discipline to their codebases that is common in enterprise ecosystems such as C# .NET.

The worked example models a country metrics comparison tool: country records are read from a repository, metrics are computed by a domain service, and comparison results are written back to a second repository. The same domain logic is surfaced via a console application and a REST API implemented as an Azure Function.

---

## Why bother with layers?

Data science code often starts as notebooks or flat scripts. This is perfectly reasonable for exploratory work, but as a project matures it creates real problems:

- **Tight coupling** — database queries, business logic, and output formatting are tangled together, making any one of them hard to change without breaking the others.
- **Untestable logic** — business rules that live alongside SQL queries or `print` statements cannot easily be run in isolation.
- **No clear seams** — swapping a CSV file for a database, or a script for an API, requires rewriting large portions of code rather than swapping one component.

Layered architecture solves these problems by establishing clear rules about what each part of the code is allowed to know about.

---

## Architecture overview

The application is divided into four layers. The arrows show the direction of allowed imports — outer layers depend on inner ones, never the reverse.

```
┌─────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                   │
│                                                         │
│   presentation/console/         presentation/           │
│   main.py                       azure_functions/        │
│   (CLI entry point)             function_app.py         │
│                                 (Azure Functions API)   │
│                                                         │
│   • Parses user input / HTTP requests                   │
│   • Converts domain exceptions to user-facing messages  │
│   • Acts as the Composition Root (wires dependencies)   │
└───────────────────┬─────────────────────────────────────┘
                    │ imports
                    ▼
┌─────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                        │
│                                                         │
│   domain/models.py       domain/repositories.py         │
│   domain/exceptions.py   domain/services.py             │
│                                                         │
│   • Pure Python — no framework or infrastructure deps   │
│   • Defines what the application does (business rules)  │
│   • Defines repository interfaces (Protocols)           │
│   • Knows nothing about databases, HTTP, or files       │
└───────────────────▲─────────────────────────────────────┘
                    │ imports
┌───────────────────┴─────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                    │
│                                                         │
│   infrastructure/mssql_country_repository.py            │
│   infrastructure/mssql_comparison_repository.py         │
│                                                         │
│   • Concrete implementations of the domain Protocols    │
│   • Owns all database/file/network concerns             │
│   • Can be swapped without touching the domain layer    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      TEST LAYER                         │
│                                                         │
│   tests/fakes/            tests/domain/                 │
│   fake_country_repo.py    test_comparison_service.py    │
│   fake_comparison_repo.py                               │
│   tests/conftest.py                                     │
│                                                         │
│   • Like a second presentation layer: uses the domain   │
│     directly and injects its own fake repositories      │
│   • No database, no network — pure unit tests           │
└─────────────────────────────────────────────────────────┘
```

### The one rule

> **The domain layer must not import from infrastructure or presentation.**

Everything else follows from this. Because the domain layer defines repository *interfaces* (Protocols) rather than implementations, it can describe what it needs from a database without knowing anything about databases.

---

## Project structure

```
python-app-structure/
│
├── pyproject.toml                          # Project metadata, deps, pytest config
│
├── domain/                                 # Inner layer — no external imports
│   ├── models.py                           # Dataclass entities (Country, CountryComparison)
│   ├── exceptions.py                       # Domain-specific exceptions
│   ├── repositories.py                     # Repository interfaces (typing.Protocol)
│   └── services.py                         # Business logic (ComparisonService)
│
├── infrastructure/                         # Outer layer — imports domain, not presentation
│   ├── mssql_country_repository.py         # Reads country reference data from SQL Server
│   └── mssql_comparison_repository.py      # Persists computed comparisons to SQL Server
│
├── presentation/
│   ├── console/
│   │   └── main.py                         # CLI entry point and Composition Root
│   └── azure_functions/
│       ├── function_app.py                 # Azure Functions REST API and Composition Root
│       └── host.json                       # Azure Functions runtime configuration
│
└── tests/
    ├── conftest.py                         # Shared fixtures — test Composition Root
    ├── fakes/
    │   ├── fake_country_repository.py      # In-memory fake (not a mock)
    │   └── fake_comparison_repository.py   # In-memory fake
    └── domain/
        └── test_comparison_service.py      # Unit tests for ComparisonService
```

---

## Key Python patterns

### Protocols instead of abstract base classes

In C# you would write an `ICountryRepository` interface. In Python the idiomatic equivalent is `typing.Protocol` (PEP 544):

```python
# domain/repositories.py
from typing import Protocol
from domain.models import Country

class CountryRepository(Protocol):
    def get_by_code(self, code: str) -> Country | None: ...
    def list_all(self) -> list[Country]: ...
```

Concrete implementations satisfy the Protocol **structurally** — they do not need to inherit from it. A type checker (mypy, pyright) verifies compatibility at every call site. This is duck typing with static guarantees.

```python
# infrastructure/mssql_country_repository.py
class MssqlCountryRepository:           # No inheritance needed
    def get_by_code(self, code: str) -> Country | None:
        ...                             # Type checker confirms this satisfies the Protocol
```

### Constructor injection

The service declares its dependencies in `__init__`, exactly as in C#. The caller decides which concrete implementations to supply:

```python
# domain/services.py
class ComparisonService:
    def __init__(
        self,
        country_repository: CountryRepository,
        comparison_repository: ComparisonRepository,
    ) -> None:
        self._countries = country_repository
        self._comparisons = comparison_repository
```

There is no DI container. In most Python applications, explicit constructor injection wired at the entry point is simpler and more readable than a container. The entry point itself becomes the Composition Root.

### Dataclasses as domain entities

Domain entities are plain `@dataclass` objects — no ORM decorators, no framework dependencies. Derived metrics are expressed as `@property`, keeping the stored data minimal:

```python
# domain/models.py
@dataclass
class Country:
    population: int
    area_km2: float
    gdp_usd_billions: float
    ...

    @property
    def gdp_per_capita(self) -> float:
        return (self.gdp_usd_billions * 1_000_000_000) / self.population

    @property
    def population_density(self) -> float:
        return self.population / self.area_km2
```

### The Composition Root

Each entry point is the *only* module that imports from both `domain` and `infrastructure`. It wires the dependency graph and then hands control to the service. In `main.py`:

```python
# presentation/console/main.py
connection_string = os.environ.get("DB_CONNECTION_STRING", _DEFAULT_CONNECTION_STRING)
country_repo    = MssqlCountryRepository(connection_string)
comparison_repo = MssqlComparisonRepository(connection_string)
service         = ComparisonService(country_repo, comparison_repo)
```

The `tests/conftest.py` is the Composition Root for the test suite, substituting fakes for real repositories:

```python
# tests/conftest.py
@pytest.fixture()
def comparison_service(fake_country_repo, fake_comparison_repo):
    return ComparisonService(fake_country_repo, fake_comparison_repo)
```

### Fakes, not mocks

The test doubles are *fakes* — real, working in-memory implementations of the repository Protocols:

```python
# tests/fakes/fake_comparison_repository.py
class FakeComparisonRepository:
    def __init__(self) -> None:
        self._store: dict[int, CountryComparison] = {}
        self._next_id: int = 1

    def save(self, comparison: CountryComparison) -> CountryComparison:
        comparison.id = self._next_id
        self._next_id += 1
        self._store[comparison.id] = comparison
        return comparison
```

Tests written against a fake verify **observable outcomes** (`assert result.gdp_per_capita_ratio == pytest.approx(expected)`) rather than call sequences (`mock.assert_called_once_with(...)`). This makes them more robust to internal refactoring.

---

## The country comparison example

### Domain model

Two entities live in `domain/models.py`:

| Entity | Purpose |
|---|---|
| `Country` | Reference data: code, name, population, area, GDP, life expectancy. Derived properties (`gdp_per_capita`, `population_density`) computed on the fly. |
| `CountryComparison` | Persisted result: four metrics relating country X to country Y as ratios or deltas. |

### Two repository protocols

The split between two Protocols reflects two distinct data responsibilities:

```
CountryRepository      — read-only access to reference data
                          get_by_code(code)  →  Country | None
                          list_all()         →  list[Country]

ComparisonRepository   — write/read access to computed results
                          save(comparison)   →  CountryComparison (with id)
                          get_by_id(id)      →  CountryComparison | None
                          list_all()         →  list[CountryComparison]
```

Because `CountryRepository` is read-only in the Protocol, the domain service is explicit about the fact that it never needs to create or modify country records. The concrete `MssqlCountryRepository` does have an `add` method — but that is a concrete detail used only by the Composition Root for seeding data, invisible to the service.

### Business logic in the service

`ComparisonService.compare()` in `domain/services.py` contains all the business rules:

1. Reject a request to compare a country with itself.
2. Resolve both country codes — raise `CountryNotFoundError` if either is missing.
3. Compute the four comparison metrics from the domain properties.
4. Persist the result via `ComparisonRepository` and return it.

None of this logic knows whether it is running behind an HTTP endpoint, a console prompt, or a test runner.

### Presentation: two entry points, same service

**Console** (`presentation/console/main.py`) — seeds a few countries directly through the concrete repository type, then calls `service.compare()` for several pairs and prints the results.

**Azure Functions** (`presentation/azure_functions/function_app.py`) — exposes the same service over HTTP using the Python v2 programming model:

| Method | Route | Action |
|---|---|---|
| `GET` | `/api/countries` | List all countries |
| `POST` | `/api/comparisons` | Run a comparison (`{"country_x": "GBR", "country_y": "USA"}`) |
| `GET` | `/api/comparisons` | List all saved comparisons |
| `GET` | `/api/comparisons/{id}` | Retrieve one comparison |

Domain exceptions (`CountryNotFoundError`, `SameCountryComparisonError`) are caught at the HTTP boundary and mapped to appropriate status codes (404, 422). The domain layer never sees an `HttpRequest` or an `HttpResponse`.

---

## Running the tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run the test suite
pytest

# Run with coverage
pytest --cov --cov-report=term-missing
```

All 23 tests run against in-memory fakes and complete in under a second with no SQL Server dependency.

## Running the console app

```bash
# Set your SQL Server connection string
export DB_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=metrics;Trusted_Connection=yes;Encrypt=no;"

python -m presentation.console.main
```

The Microsoft ODBC Driver for SQL Server must be installed separately. See the [Microsoft documentation](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) for installation instructions for your platform.

---

## Testing conventions

### Test naming convention

In .NET, the common idiom is a three-part method name:

```
Compare_WithUnknownCountryX_ThrowsCountryNotFoundError
```

This carries all the context in one name because test methods are often flat. The equivalent in Python snake_case is entirely valid and not anti-Pythonic:

```python
def test_compare_with_unknown_country_x_raises_country_not_found_error(): ...
```

However, our tests are class-based, and the class already names the operation under test (`TestCompare`, `TestListComparisons`). That makes the first segment redundant within a class, so the convention naturally collapses to **two parts**, separated by a double underscore to preserve visual structure:

```
test_<state_under_test>__<expected_result>
```

The double underscore is the Python-idiomatic way to retain the .NET convention's scannability without repeating information the class already provides:

```python
class TestCompare:
    def test_valid_pair__returns_comparison_with_assigned_id(self, ...): ...
    def test_valid_pair__gdp_per_capita_ratio_is_x_over_y(self, ...):    ...
    def test_unknown_country_code__raises_country_not_found_error(self, ...): ...
    def test_same_country_codes__raises_same_country_comparison_error(self, ...): ...
```

This pays off particularly in pytest's output, where the full path reads as a sentence: `TestCompare::test_unknown_country_code__raises_country_not_found_error`. Combined with parametrize suffixes, names like `test_unknown_country_code__raises_country_not_found_error[GBR-ZZZ-ZZZ]` are unambiguous without being verbose.

---

### Arrange-Act-Assert (AAA)

In .NET, the AAA pattern is applied uniformly: every test method opens with a block of setup code, so the `// Arrange` comment actively helps the reader locate where setup ends and the action begins. In pytest the picture is different, because the fixture system moves the Arrange step *outside* the test body entirely. By the time execution enters a test function, the repositories are already populated and the service is already wired — the fixture parameter declaration is the Arrange step, stated once and shared.

Adding `# Arrange / # Act / # Assert` comments to a two-line test adds more noise than signal:

```python
# Noisy: the comments describe structure that is already obvious
def test_returns_comparison_with_assigned_id(self, comparison_service):
    # Arrange: handled by fixture
    # Act
    result = comparison_service.compare("GBR", "USA")
    # Assert
    assert result.id > 0
```

The comments earn their place when a test has **substantial per-test setup** that cannot reasonably live in a shared fixture — typically scenario or integration-style tests that establish a specific initial state. See `TestScenarios` in `tests/domain/test_comparison_service.py` for a concrete example:

```python
def test_comparisons_against_a_benchmark_reflect_real_world_ordering(self) -> None:
    # Arrange: three countries spanning a wide development range,
    # seeded into a fresh repository independent of the shared fixtures.
    norway   = Country("NOR", "Norway",    5_391_369,   385_207,  482.0, 83.2)
    brazil   = Country("BRA", "Brazil",  214_326_223, 8_515_767, 1_610.0, 75.9)
    ethiopia = Country("ETH", "Ethiopia", 117_876_227, 1_104_300,   111.3, 67.8)

    country_repo = FakeCountryRepository([norway, brazil, ethiopia])
    service = ComparisonService(country_repo, FakeComparisonRepository())

    # Act: compare each country against Brazil as a midpoint benchmark.
    nor_vs_bra = service.compare("NOR", "BRA")
    eth_vs_bra = service.compare("ETH", "BRA")

    # Assert: direction of each metric should reflect known real-world ordering.
    assert nor_vs_bra.gdp_per_capita_ratio > 1.0
    assert eth_vs_bra.gdp_per_capita_ratio < 1.0
    ...
```

This test constructs its own repositories (rather than using the `comparison_service` fixture) precisely because the data is meaningful to the scenario — Brazil as a deliberate midpoint benchmark — and would be confusing as shared state. The AAA comments help the reader understand the structure of a test that is long enough to lose that structure without them.

The practical rule: if a test body is long enough that you have to scroll to find the assertion, add the comments. If you can read the whole test in one glance, the comments are clutter.

---

### Parametrized tests

In xUnit you attach multiple `[InlineData(...)]` attributes to a single `[Theory]` method to run the same test body with different inputs. pytest provides `@pytest.mark.parametrize` for exactly the same purpose:

| .NET (xUnit) | Python (pytest) |
|---|---|
| `[Theory]` | `@pytest.mark.parametrize(...)` |
| `[InlineData("GBR", "USA", "ZZZ")]` | `("GBR", "USA", "ZZZ"),` in the parameter list |
| One method, N test runs | One method, N test runs |
| Named in output as the method name | Named as `test_name[param1-param2-...]` |

A parametrized test is most valuable when you have several nearly-identical test methods that differ only in their inputs. The two "country not found" tests from the first draft — one for a missing X country, one for a missing Y country — are a natural target:

```python
# Before: two separate methods, identical structure
def test_raises_when_country_x_not_found(self, ...):
    with pytest.raises(CountryNotFoundError) as exc_info:
        comparison_service.compare("ZZZ", "USA")
    assert exc_info.value.code == "ZZZ"

def test_raises_when_country_y_not_found(self, ...):
    with pytest.raises(CountryNotFoundError) as exc_info:
        comparison_service.compare("GBR", "ZZZ")
    assert exc_info.value.code == "ZZZ"

# After: one method, two cases, pytest names them automatically:
#   test_raises_with_correct_code_when_country_not_found[ZZZ-USA-ZZZ]
#   test_raises_with_correct_code_when_country_not_found[GBR-ZZZ-ZZZ]
@pytest.mark.parametrize("x_code, y_code, missing_code", [
    ("ZZZ", "USA", "ZZZ"),  # x is unknown
    ("GBR", "ZZZ", "ZZZ"),  # y is unknown
])
def test_raises_with_correct_code_when_country_not_found(
    self, comparison_service, x_code, y_code, missing_code
):
    with pytest.raises(CountryNotFoundError) as exc_info:
        comparison_service.compare(x_code, y_code)
    assert exc_info.value.code == missing_code
```

Parametrize is also well-suited to testing the same formula across multiple data points, as in `TestMetricCalculations`, where the GDP per capita ratio and life expectancy delta are each verified for three different country pairs. The pairs are chosen deliberately to cover positive ratios, negative ratios, and near-zero values — not just to add volume, but to demonstrate that the formula behaves correctly across the full range of inputs the service will encounter.

One caution: parametrize can obscure *why* each case exists if the values are not self-explanatory. Prefer descriptive parameter names and, where the significance of a case is not obvious from the values alone, add a short inline comment beside each tuple.

---

## Swapping a component

The value of this architecture becomes tangible when requirements change. Some examples:

**Replace SQL Server with PostgreSQL** — write a `PostgresCountryRepository` that satisfies the `CountryRepository` Protocol, update the two lines in the Composition Root. Zero changes to `domain/` or `tests/`.

**Replace Azure Functions with FastAPI** — add a `presentation/api/` package with FastAPI route handlers that call the same `ComparisonService`. Zero changes to `domain/` or `infrastructure/`.

**Add a new metric to the comparison** — add the field to `CountryComparison`, compute it in `ComparisonService.compare()`, add a column to the SQL Server schema in `MssqlComparisonRepository`. The presentation layer picks up the new field automatically via the serialisation helpers.

In each case, the change is confined to the layer responsible for that concern.
