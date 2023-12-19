"""Examples as integration and regression tests."""

import pytest

from census21api import CensusAPI


def test_issue_39_blocked_pairs():
    """https://github.com/datasciencecampus/census21api/issues/39"""

    population_type = "UR_HH"
    area_type = "nat"
    dimensions = ("economic_activity_status_12a", "industry_current_88a")

    api = CensusAPI()

    with pytest.warns(UserWarning, match="blocked pair"):
        table = api.query_table(population_type, area_type, dimensions)

    assert table is None
