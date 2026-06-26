from __future__ import annotations

import json
import ssl
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


WEATHER_CODE_LABELS = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "상고대 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
    96: "우박을 동반한 뇌우",
    99: "강한 우박을 동반한 뇌우",
}


LOCATION_ALIASES = {
    "서울": "Seoul",
    "서울시": "Seoul",
    "부산": "Busan",
    "부산시": "Busan",
    "인천": "Incheon",
    "인천시": "Incheon",
    "대구": "Daegu",
    "대구시": "Daegu",
    "대전": "Daejeon",
    "대전시": "Daejeon",
    "광주": "Gwangju",
    "광주시": "Gwangju",
    "울산": "Ulsan",
    "울산시": "Ulsan",
    "세종": "Sejong",
    "세종시": "Sejong",
    "제주": "Jeju City",
    "제주시": "Jeju City",
    "수원": "Suwon",
    "용인": "Yongin",
    "고양": "Goyang",
    "성남": "Seongnam",
    "청주": "Cheongju",
    "전주": "Jeonju",
    "천안": "Cheonan",
    "포항": "Pohang",
    "창원": "Changwon",
}


def normalize_location_name(location: str) -> str:
    return LOCATION_ALIASES.get(location.strip(), location.strip())


def create_ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ImportError:
        return None

    return ssl.create_default_context(cafile=certifi.where())


def fetch_today_hourly_weather(
    latitude: float,
    longitude: float,
    timezone: str = "Asia/Seoul",
) -> list[dict[str, object]]:
    """Return today's hourly weather from Open-Meteo."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "wind_speed_10m",
            ]
        ),
        "forecast_days": 1,
        "timezone": timezone,
    }

    url = f"{OPEN_METEO_FORECAST_URL}?{urlencode(params)}"
    with urlopen(url, timeout=10, context=create_ssl_context()) as response:
        payload = json.load(response)

    hourly = payload["hourly"]
    rows = []
    for index, time_text in enumerate(hourly["time"]):
        rows.append(
            {
                "time": datetime.fromisoformat(time_text),
                "temperature_c": hourly["temperature_2m"][index],
                "humidity_percent": hourly["relative_humidity_2m"][index],
                "precipitation_probability_percent": hourly[
                    "precipitation_probability"
                ][index],
                "precipitation_mm": hourly["precipitation"][index],
                "weather": WEATHER_CODE_LABELS.get(
                    hourly["weather_code"][index],
                    f"알 수 없음({hourly['weather_code'][index]})",
                ),
                "wind_speed_kmh": hourly["wind_speed_10m"][index],
            }
        )

    return rows


def search_location(location: str, language: str = "ko") -> dict[str, object]:
    """Return the best Open-Meteo geocoding match for a location name."""
    normalized_location = normalize_location_name(location)
    params = {
        "name": normalized_location,
        "count": 1,
        "language": language,
        "format": "json",
    }

    url = f"{OPEN_METEO_GEOCODING_URL}?{urlencode(params)}"
    with urlopen(url, timeout=10, context=create_ssl_context()) as response:
        payload = json.load(response)

    results = payload.get("results", [])
    if not results:
        raise ValueError(f"위치를 찾을 수 없습니다: {location}")

    result = results[0]
    return {
        "name": result["name"],
        "country": result.get("country", ""),
        "admin1": result.get("admin1", ""),
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "timezone": result.get("timezone", "auto"),
    }


def main() -> None:
    # 서울시청 좌표입니다. 다른 지역은 위도/경도를 바꾸면 됩니다.
    weather_rows = fetch_today_hourly_weather(
        latitude=37.5665,
        longitude=126.9780,
        timezone="Asia/Seoul",
    )

    for row in weather_rows:
        print(
            f"{row['time']:%Y-%m-%d %H:%M} | "
            f"{row['weather']} | "
            f"{row['temperature_c']}°C | "
            f"습도 {row['humidity_percent']}% | "
            f"강수확률 {row['precipitation_probability_percent']}% | "
            f"강수량 {row['precipitation_mm']}mm | "
            f"풍속 {row['wind_speed_kmh']}km/h"
        )


if __name__ == "__main__":
    main()
