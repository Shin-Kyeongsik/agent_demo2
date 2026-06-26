# Open-Meteo Weather Search

Open-Meteo API로 입력한 위치의 오늘 시간별 날씨를 가져오고, Matplotlib으로 기온 그래프를 만들어 웹 페이지에 표시하는 Python 예제입니다.

## 기능

- 위치명 입력 기반 날씨 검색
- Open-Meteo Geocoding API로 위도/경도 조회
- Open-Meteo Forecast API로 오늘 1시간 간격 날씨 조회
- Matplotlib 기온 그래프 생성
- 표준 라이브러리 HTTP 서버 기반 웹 페이지 제공

## 설치

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 실행

```bash
env MPLCONFIGDIR=.matplotlib XDG_CACHE_HOME=.cache .venv/bin/python weather_web.py
```

브라우저에서 http://127.0.0.1:8000/ 을 열고 위치를 입력합니다.

## CLI 예제

오늘 시간별 날씨 출력:

```bash
.venv/bin/python open_meteo_hourly_today.py
```

서울 기준 기온 그래프 PNG 저장:

```bash
env MPLCONFIGDIR=.matplotlib XDG_CACHE_HOME=.cache .venv/bin/python plot_today_temperature.py
```
