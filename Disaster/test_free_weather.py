"""
Simple test for free weather API (wttr.in) used by the app.
Returns True if a basic request succeeds and returns JSON structure.
"""
from urllib.parse import quote
import requests


def test_free_weather_api() -> bool:
    try:
        location = quote("Delhi, India")
        url = f"https://wttr.in/{location}?format=j1"
        resp = requests.get(url, timeout=(3, 8))
        resp.raise_for_status()
        data = resp.json()
        return isinstance(data, dict) and "current_condition" in data
    except Exception:
        return False


if __name__ == "__main__": 
    ok = test_free_weather_api()
    print("OK" if ok else "FAIL")