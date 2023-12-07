"""Script to check whether our constants for the API are up to date."""


from census21api import CensusAPI
from census21api.constants import (
    AREA_TYPES_BY_POPULATION_TYPE,
    DIMENSIONS_BY_POPULATION_TYPE,
    POPULATION_TYPES,
)


def _check_population_types():
    """Check that we have all the population types."""

    api = CensusAPI()
    available_pop_types = api._get_population_types()

    assert available_pop_types == set(POPULATION_TYPES), "\n".join(
        (
            "Population types do not match.",
            f"Available: {', '.join(sorted(available_pop_types))}",
            f"Recorded: {', '.join(sorted(POPULATION_TYPES))}",
        )
    )

    print("✅ Population types up to date.")


def _check_feature_by_population_type(feature):
    """Check we have the feature sets for each population type."""

    api = CensusAPI()

    text = " ".join(feature.split("-")).capitalize()
    recorded_by_population_type = (
        AREA_TYPES_BY_POPULATION_TYPE
        if feature == "area-types"
        else DIMENSIONS_BY_POPULATION_TYPE
    )

    for pop_type in POPULATION_TYPES:
        metadata = api.query_feature(pop_type, feature)
        available = set(metadata["id"])
        recorded = recorded_by_population_type[pop_type]

        assert available == set(recorded), "\n".join(
            (
                f"{text} for population type {pop_type} do not match.",
                f"Available: {', '.join(sorted(available))}",
                f"Recorded:  {', '.join(sorted(recorded))}",
            )
        )

    print(f"✅ {text} by population type up to date.")


def main():
    """Check all the API constants."""

    _check_population_types()
    _check_feature_by_population_type("area-types")
    _check_feature_by_population_type("dimensions")


if __name__ == "__main__":
    main()
