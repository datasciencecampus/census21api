"""Examples as integration and regression tests."""

import pytest

from census21api import CensusAPI


def test_issue_39_blocked_pairs_gets_400_error():
    """
    Originally, this was about catching blocked pairs.

    See https://github.com/datasciencecampus/census21api/issues/39 for
    details on the original issue.

    As of 2024-02-16, it seems that blocked pairs now give a 400 error.
    This test now checks for that.
    """

    population_type = "UR_HH"
    area_type = "nat"
    dimensions = ("economic_activity_status_12a", "industry_current_88a")

    api = CensusAPI()

    with pytest.warns(UserWarning, match="Status code: 400"):
        table = api.query_table(population_type, area_type, dimensions)

    assert table is None
