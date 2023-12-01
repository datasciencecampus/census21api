# `census21api`: a Python interface for the ONS "Create a Custom Dataset" API

## Overview

This repository contains the unofficial Python interface for the 2021 England
and Wales Census
["Create a Custom Dataset" tool](https://www.ons.gov.uk/datasets/create). This
interface was developed by the 2023 cohort of ONS (Office for National
Statistics) data engineering/architecture apprentices with support from the ONS
Data Science Campus.

The primary goal of this project is to simplify and streamline the process of
accessing and working with data from the 2021 England and Wales Census API.

The `census21api` package provides a core class through which users can
interact with the Census API, enabling users to query tables and retrieve
metadata in a programmatic way. It offers a more user-friendly and efficient
way to work with the Census data, particularly for data engineering and
analysis tasks.

## Getting Started

### Installation

Currently, the `census21api` package is only installable through GitHub. We
also require Python 3.8 or higher.

To install from GitHub via `pip`:

```bash
$ python -m pip install census21api@git+https://github.com/datasciencecampus/census21api
```

Or directly from source:

```bash
$ git clone https://github.com/datasciencecampus/census21api.git
$ cd census21api
$ python -m pip install .
```

### Usage

Here's a basic example of how to use the `CensusAPI` class to retrieve a table:

```python
>>> from census21api import CensusAPI
>>> 
>>> api = CensusAPI()
>>> 
>>> # Specify a population type, area type, and some dimensions
>>> # See `census21api.constants` for a list of options
>>> population_type = "UR_HH"
>>> area_type = "ctry"
>>> dimensions = ("sex", "hh_deprivation_housing")
>>> 
>>> # Submit the parameters to the table querist method
>>> table = api.query_table(population_type, area_type, dimensions)
>>> print(table)
         ctry sex hh_deprivation_housing     count population_type
0   E92000001   1                     -8         0           UR_HH
1   E92000001   1                      0  24993178           UR_HH
2   E92000001   1                      1   3340293           UR_HH
3   E92000001   2                     -8         0           UR_HH
4   E92000001   2                      0  23890474           UR_HH
5   E92000001   2                      1   3280355           UR_HH
6   W92000004   1                     -8         0           UR_HH
7   W92000004   1                      0   1457330           UR_HH
8   W92000004   1                      1    100914           UR_HH
9   W92000004   2                     -8         0           UR_HH
10  W92000004   2                      0   1391731           UR_HH
11  W92000004   2                      1    101574           UR_HH

```

## Limitations

The `CensusAPI` class includes a variety of methods to interact with the API in
a very flexible way. However, there are still some limitations when compared
with the web interface; these come from the API itself, which is still in
development.

If you notice something wrong or something missing, consider making a
contribution or opening an issue.

### Blocked dimension combinations

Some combinations of columns (dimensions) cannot be queried at once. See #39
for an example. This is a deliberate block put in place by the developers of
the API.

### Some columns are missing

Despite the stringent statistical disclosure control all public ONS tables go
through, some dimensions are not available in the API. For instance, you cannot
query tables containing age data despite being able to create them through the
web interface. Again, this is a deliberate choice by the developers and may be
subject to change.

## Contributing

This project is open-source, and contributions from the community are welcome.
If you want to contribute to the project, please follow these steps:

1. Fork the repository and clone your fork.
2. Install the development dependencies for the package with
   `python -m pip install -e ".[dev]"`.
2. Create your feature branch.
3. Make your changes, including writing property-based tests and documentation
   for your new feature.
4. Commit and push to the branch on your fork.
5. Open a pull request and request a review.

Please make sure to follow the project's coding standards and maintain a clean
commit history for easier code review.

## Contact

For questions, feedback, or inquiries about this project, please open an issue
and we will get back to you as soon as possible.
