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
def st_observations(draw, max_nrows=5):
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
def st_feature_queries(draw):
    """Create a feature metadata query pack for testing."""

    population_type = draw(st.sampled_from(POPULATION_TYPES))
    endpoint = draw(st.sampled_from(("area-types", "dimensions")))

    items_by_population_type = (
        AREA_TYPES_BY_POPULATION_TYPE
        if endpoint == "area-types"
        else DIMENSIONS_BY_POPULATION_TYPE
    )
    possible_items = items_by_population_type[population_type]
    items = draw(st.lists(st.sampled_from(possible_items), unique=True))

    result = {"items": [{"id": item} for item in possible_items]}

    return population_type, endpoint, items, result


@st.composite
def st_population_types(draw, include_interested=False):
    """Sample a set of population types and their metadata."""

    population_types = draw(st.lists(st.text(), min_size=1, unique=True))
    json_metadata = [
        {
            "name": population_type,
            "label": draw(st.text()),
            "description": draw(st.text()),
            "type": "microdata",
        }
        for population_type in population_types
    ]

    if not include_interested:
        return population_types, json_metadata

    interested = draw(
        st.sets(st.sampled_from(population_types), min_size=1).map(sorted)
    )

    return population_types, json_metadata, interested


@st.composite
def st_category_queries(draw, feature=None):
    """Create a category metadata query pack for testing."""

    population_type = draw(st.sampled_from(POPULATION_TYPES))
    feature = feature or draw(st.sampled_from(("area-types", "dimensions")))
    num_categories = draw(st.integers(1, 5))

    if feature == "area-types":
        item = draw(
            st.sampled_from(AREA_TYPES_BY_POPULATION_TYPE[population_type])
        )
        categories = [
            {
                "id": draw(st.text()),
                "label": draw(st.text()),
                "area_type": item,
            }
            for _ in range(num_categories)
        ]

    if feature == "dimensions":
        item = draw(
            st.sampled_from(DIMENSIONS_BY_POPULATION_TYPE[population_type])
        )
        categories = [
            {"id": draw(st.text()), "label": draw(st.text())}
            for _ in range(num_categories)
        ]

    return population_type, item, categories
