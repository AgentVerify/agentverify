import requests as http

http = object()


def fetch_url(url: str):
    return http.get(url)
