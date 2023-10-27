You can find a link to the Create a Custom Dataset web interface [here]( https://www.ons.gov.uk/datasets/create).


# The Unofficial Python Wrapper for the '2021 England and Wales Census' Create a Custom Dataset Tool


## Overview

This project presents the "Unofficial Python Wrapper for the 2021 England and Wales Census Create a Custom Dataset Tool," developed by the 2023 cohort of ONS (Office for National Statistics) data engineering/architecture apprentices. The primary goal of this project is to simplify and streamline the process of accessing and working with data from the 2021 England and Wales Census API.

This Python wrapper provides a set of tools and functions to interact with the Census API, enabling users to query data, retrieve available parameters, and generate data summaries for analysis. It offers a more user-friendly and efficient way to work with the Census data, particularly for data engineering and analysis tasks.

## Features

The Python wrapper for the 2021 England and Wales Census Create a Custom Dataset Tool offers the following features:

- **Query the Census API:** Easily retrieve data from the Census API by specifying search parameters, including population types, dimensions, and area types.

- **Retrieve Available Parameters:** Access the available parameters for population types, area types, and dimensions to understand the data structure.

- **Generate Data Summaries:** Create data summaries by grouping data by dimensions or area types, providing both absolute counts and proportions normalized by the total.

- **Flexible and Configurable:** The wrapper is designed to be flexible, allowing you to specify the parameters you need for your analysis.

- **Easy to use interface.

## Getting Started

### Software

python3.8 or higher, with pip, numpy and pandas.

### Usage

Here's a basic example of how to use the Python wrapper to query the Census API:

## Using the interface, as shown by the 'interface_example.ipynb'.

## Alternatively:
```python
from census_api_wrapper import APIWrapper

# Create an instance of the APIWrapper
census_api = APIWrapper()

# Retrieve available population types
population_types = census_api.get_population_types_available()
print("Available Population Types:", population_types)

# Query the API to get data
data = census_api.query_api(search_pop_type="UR", search_dimensions="age,sex", search_area_type="OA")
print(data)
```

Please refer to the project's documentation or code comments for more detailed information on how to use the wrapper's functions effectively.

## Contribution

This project is open-source, and contributions from the community are welcome. If you want to contribute to the project, please follow these steps:

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/your-feature-name`).
3. Make your changes and commit them (`git commit -m 'Add feature'`).
4. Push to the branch (`git push origin feature/your-feature-name`).
5. Open a pull request.

Please make sure to follow the project's coding standards and maintain a clean commit history for easier code review.

## License

#### MIT License

Copyright (c) Office for National Statistics

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact

For questions, feedback, or inquiries about this project, you can contact the developers and maintainers of this project:

You can also open an issue on this repository, and we will get back to you as soon as possible.

