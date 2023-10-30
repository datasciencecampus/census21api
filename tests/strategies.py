"""Composite strategies for our unit tests."""

from hypothesis import strategies as st

from census21api.constants import (
    AREA_TYPES_BY_POPULATION_TYPE,
    DIMENSIONS_BY_POPULATION_TYPE,
    POPULATION_TYPES,
)


@st.composite
def st_table_queries(draw):
    """Create a set of table query parameters for a test."""

    population_type = draw(st.sampled_from(POPULATION_TYPES))

    area_types_available = AREA_TYPES_BY_POPULATION_TYPE[population_type]
    area_type = draw(st.sampled_from(area_types_available))

    dimensions_available = DIMENSIONS_BY_POPULATION_TYPE[population_type]
    dimensions = draw(
        st.lists(st.sampled_from(dimensions_available), min_size=1, max_size=3)
    )

    return population_type, area_type, dimensions


@st.composite
def st_observations(draw, max_nrows=10):
    """Create a set of observations for a test."""

    _, area_type, dimensions = draw(st_table_queries())

    nrows = draw(st.integers(1, max_nrows))
    observations = []
    for _ in range(nrows):
        observation = {}
        observation["dimensions"] = [
            {"option": draw(st.text()), "option_id": draw(st.text())}
            for _ in dimensions
        ]
        observation["observation"] = draw(st.integers())

        observations.append(observation)

    return observations


@st.composite
def st_records_and_queries(draw, max_nrows=10):
    """Create a set of records and query parameters to go with them."""

    population_type, area_type, dimensions = draw(st_table_queries())

    nrows = draw(st.integers(1, max_nrows))
    records = []
    for _ in range(nrows):
        record = (
            draw(st.text()),
            *(draw(st.text()) for _ in dimensions),
            draw(st.integers()),
        )
        records.append(record)

    return records, population_type, area_type, dimensions


@st.composite
def st_area_types_info_and_queries(draw):
    """Create the parameters and response for an area type query."""

    population_type = draw(st.sampled_from(POPULATION_TYPES))

    area_types_available = AREA_TYPES_BY_POPULATION_TYPE[population_type]
    area_types = draw(
        st.lists(
            st.sampled_from(area_types_available),
            min_size=0,
            max_size=5,
            unique=True,
        )
    )

    area_types_info = {
        "items": [
            {
                "id": area_type,
                "label": st.text(),
                "description": st.text(),
                "total_count": st.integers(),
                "hierarchy_order": st.integers(),
            }
            for area_type in area_types_available
        ]
    }

    return area_types_info, population_type, area_types
