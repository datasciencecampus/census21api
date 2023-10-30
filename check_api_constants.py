"""Script to check whether our constants for the API are up to date."""

import requests

from census21api import (
    API_ROOT,
    AREA_TYPES_BY_POPULATION_TYPE,
    DIMENSIONS_BY_POPULATION_TYPE,
    POPULATION_TYPES,
)


def _check_population_types():
    """Check that we have all the population types."""

    url = f"{API_ROOT}?limit=100"
    response = requests.get(url, verify=True)
    data = response.json()

    available_pop_types = set(
        item["name"] for item in data["items"] if item["type"] == "microdata"
    )

    assert available_pop_types == set(POPULATION_TYPES), "\n".join(
        (
            "Population types do not match.",
            f"Available: {', '.join(available_pop_types)}",
            f"Recorded: {', '.join(POPULATION_TYPES)}",
        )
    )

    print("✅ Population types up to date.")


def _check_area_types_by_population_type():
    """Check that we have the area types for each population type."""

    for pop_type in POPULATION_TYPES:
        url = "/".join((API_ROOT, pop_type, "area-types?limit=100"))
        response = requests.get(url, verify=True)
        data = response.json()

        available_area_types = set(item["id"] for item in data["items"])
        recorded_area_types = AREA_TYPES_BY_POPULATION_TYPE[pop_type]

        assert available_area_types == set(recorded_area_types), "\n".join(
            (
                f"Area types for population type {pop_type} do not match.",
                f"Available: {', '.join(available_area_types)}",
                f"Recorded: {', '.join(recorded_area_types)}",
            )
        )

    print("✅ Area types by population type up to date.")


def _check_dimensions_by_population_type():
    """Check that we have the dimensions for each population type."""

    for pop_type in POPULATION_TYPES:
        url = "/".join((API_ROOT, pop_type, "dimensions?limit=500"))
        response = requests.get(url, verify=True)
        data = response.json()

        available_dimensions = set(item["id"] for item in data["items"])
        recorded_dimensions = DIMENSIONS_BY_POPULATION_TYPE[pop_type]

        assert available_dimensions == set(recorded_dimensions), "\n".join(
            (
                f"Dimensions for population type {pop_type} do not match.",
                f"Available: {', '.join(available_dimensions)}",
                f"Recorded: {', '.join(recorded_dimensions)}",
            )
        )

    print("✅ Dimensions by population type up to date.")


def main():
    """Check all the API constants."""

    _check_population_types()
    _check_area_types_by_population_type()
    _check_dimensions_by_population_type()


if __name__ == "__main__":
    main()
