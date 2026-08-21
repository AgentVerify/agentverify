import requests as http

FIXED_ORIGIN = "https://search.example.test/api"


def fetch_url(url: str):
    return http.get(url)


def fixed_search(query: str):
    return http.get(FIXED_ORIGIN + "?q=" + query)


def nested_fetch(url: str):
    def inner():
        return http.get(url)

    return inner()
