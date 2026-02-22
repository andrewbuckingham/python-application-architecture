"""Azure Functions presentation layer (Python v2 programming model).

Module-level initialisation wires the dependency graph once when the
worker starts. Each function converts HTTP concerns into domain calls.

Set DB_CONNECTION_STRING in local.settings.json (local) or the Function
App's Application Settings (Azure), for example:
    Driver={ODBC Driver 18 for SQL Server};Server=<host>;Database=metrics;Trusted_Connection=yes;

For Azure SQL Database use:
    Driver={ODBC Driver 18 for SQL Server};Server=<server>.database.windows.net;
    Database=metrics;Authentication=ActiveDirectoryMsi;Encrypt=yes;

Deployment note
---------------
Azure Functions v2 (Python) expects the entry point at the project root
by default. For deployment you have two options:
  1. Place this file at the root (rename to function_app.py).
  2. Keep it here and set `"scriptFile"` in host.json to point here.
"""
import json
import logging
import os

import azure.functions as func

from domain.exceptions import InvalidOperationError, NotFoundError
from domain.services import ComparisonService
from infrastructure.mssql_comparison_repository import MssqlComparisonRepository
from infrastructure.mssql_country_repository import MssqlCountryRepository

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Composition root – runs once when the Function worker starts
# ---------------------------------------------------------------------------
_connection_string = os.environ["DB_CONNECTION_STRING"]
_country_repo = MssqlCountryRepository(_connection_string)
_comparison_repo = MssqlComparisonRepository(_connection_string)
_service = ComparisonService(_country_repo, _comparison_repo)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ---------------------------------------------------------------------------
# GET /api/countries
# ---------------------------------------------------------------------------
@app.route(route="countries", methods=["GET"])
def list_countries(req: func.HttpRequest) -> func.HttpResponse:
    countries = _service.list_countries()
    return _json_ok([_country_to_dict(c) for c in countries])


# ---------------------------------------------------------------------------
# POST /api/comparisons
# Body: { "country_x": "GBR", "country_y": "USA" }
# ---------------------------------------------------------------------------
@app.route(route="comparisons", methods=["POST"])
def create_comparison(req: func.HttpRequest) -> func.HttpResponse:
    payload, err = _parse_json(req)
    if err:
        return err

    x = str(payload.get("country_x", "")).strip().upper()
    y = str(payload.get("country_y", "")).strip().upper()

    if not x or not y:
        return _error("'country_x' and 'country_y' are required.", 400)

    try:
        comparison = _service.compare(x, y)
        return _json_response(_comparison_to_dict(comparison), 201)
    except NotFoundError as exc:
        return _error(str(exc), 404)
    except InvalidOperationError as exc:
        return _error(str(exc), 422)


# ---------------------------------------------------------------------------
# GET /api/comparisons
# ---------------------------------------------------------------------------
@app.route(route="comparisons", methods=["GET"])
def list_comparisons(req: func.HttpRequest) -> func.HttpResponse:
    comparisons = _service.list_comparisons()
    return _json_ok([_comparison_to_dict(c) for c in comparisons])


# ---------------------------------------------------------------------------
# GET /api/comparisons/{comparison_id}
# ---------------------------------------------------------------------------
@app.route(route="comparisons/{comparison_id}", methods=["GET"])
def get_comparison(req: func.HttpRequest) -> func.HttpResponse:
    comparison_id, err = _parse_id(req, "comparison_id")
    if err:
        return err

    try:
        comparison = _service.get_comparison(comparison_id)
        return _json_ok(_comparison_to_dict(comparison))
    except NotFoundError as exc:
        return _error(str(exc), 404)


# ---------------------------------------------------------------------------
# Helpers – HTTP plumbing only, no business logic
# ---------------------------------------------------------------------------

def _country_to_dict(country) -> dict:
    return {
        "id": country.id,
        "code": country.code,
        "name": country.name,
        "population": country.population,
        "area_km2": country.area_km2,
        "gdp_usd_billions": country.gdp_usd_billions,
        "life_expectancy": country.life_expectancy,
        "gdp_per_capita": round(country.gdp_per_capita, 2),
        "population_density": round(country.population_density, 2),
    }


def _comparison_to_dict(c) -> dict:
    return {
        "id": c.id,
        "country_x": c.country_x_code,
        "country_y": c.country_y_code,
        "gdp_per_capita_ratio": round(c.gdp_per_capita_ratio, 4),
        "population_ratio": round(c.population_ratio, 4),
        "life_expectancy_delta": round(c.life_expectancy_delta, 2),
        "population_density_ratio": round(c.population_density_ratio, 4),
    }


def _json_response(body, status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
    )


def _json_ok(body) -> func.HttpResponse:
    return _json_response(body, 200)


def _error(message: str, status_code: int) -> func.HttpResponse:
    return _json_response({"error": message}, status_code)


def _parse_json(req: func.HttpRequest) -> tuple[dict, func.HttpResponse | None]:
    try:
        return req.get_json(), None
    except ValueError:
        return {}, _error("Request body must be valid JSON.", 400)


def _parse_id(req: func.HttpRequest, param: str) -> tuple[int, func.HttpResponse | None]:
    raw = req.route_params.get(param)
    try:
        return int(raw), None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0, _error(f"{param} must be an integer.", 400)
