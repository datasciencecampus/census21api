import requests
import json

url = 'https://api.beta.ons.gov.uk/v1/population-types/UR/census-observations?area-type=ctry,E92000001&dimensions=health_in_general,highest_qualification'

def get(url):
    return requests.request("GET", url)

def print_json(response):
    print(json.dumps(response.json(), indent=2))

result = get(url)
