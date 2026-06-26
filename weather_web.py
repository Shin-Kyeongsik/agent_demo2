from __future__ import annotations

import base64
import html
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from open_meteo_hourly_today import fetch_today_hourly_weather, search_location
from plot_today_temperature import render_temperature_chart


HOST = "127.0.0.1"
PORT = 8000


def format_location(location: dict[str, object]) -> str:
    parts = [
        str(location.get("name", "")),
        str(location.get("admin1", "")),
        str(location.get("country", "")),
    ]
    return ", ".join(part for part in parts if part)


def build_summary(rows: list[dict[str, object]], timezone: str) -> dict[str, object]:
    temperatures = [float(row["temperature_c"]) for row in rows]
    try:
        now = datetime.now(ZoneInfo(timezone)).replace(tzinfo=None)
    except ZoneInfoNotFoundError:
        now = datetime.now()

    current = min(rows, key=lambda row: abs(row["time"] - now))
    hottest_index = temperatures.index(max(temperatures))
    coldest_index = temperatures.index(min(temperatures))

    return {
        "current": current,
        "high": rows[hottest_index],
        "low": rows[coldest_index],
    }


def render_page(
    query: str = "",
    location_label: str = "",
    timezone: str = "Asia/Seoul",
    rows: list[dict[str, object]] | None = None,
    chart_data_uri: str = "",
    error: str = "",
) -> str:
    rows = rows or []
    escaped_query = html.escape(query)
    escaped_error = html.escape(error)
    escaped_location = html.escape(location_label)
    summary = build_summary(rows, timezone) if rows else None

    cards = ""
    if summary:
        current = summary["current"]
        high = summary["high"]
        low = summary["low"]
        cards = f"""
        <section class="metrics" aria-label="weather summary">
          <div class="metric">
            <span>현재</span>
            <strong>{html.escape(str(current["temperature_c"]))}°C</strong>
            <small>{html.escape(str(current["weather"]))}</small>
          </div>
          <div class="metric">
            <span>최고</span>
            <strong>{html.escape(str(high["temperature_c"]))}°C</strong>
            <small>{high["time"]:%H:%M}</small>
          </div>
          <div class="metric">
            <span>최저</span>
            <strong>{html.escape(str(low["temperature_c"]))}°C</strong>
            <small>{low["time"]:%H:%M}</small>
          </div>
          <div class="metric">
            <span>강수확률</span>
            <strong>{html.escape(str(current["precipitation_probability_percent"]))}%</strong>
            <small>현재 시간</small>
          </div>
        </section>
        """

    table_rows = ""
    for row in rows:
        table_rows += f"""
          <tr>
            <td>{row["time"]:%H:%M}</td>
            <td>{html.escape(str(row["temperature_c"]))}°C</td>
            <td>{html.escape(str(row["weather"]))}</td>
            <td>{html.escape(str(row["humidity_percent"]))}%</td>
            <td>{html.escape(str(row["precipitation_probability_percent"]))}%</td>
            <td>{html.escape(str(row["wind_speed_kmh"]))} km/h</td>
          </tr>
        """

    result = ""
    if rows and chart_data_uri:
        result = f"""
        <section class="result">
          <div class="result-heading">
            <h2>{escaped_location}</h2>
            <p>{rows[0]["time"]:%Y-%m-%d} 기준</p>
          </div>
          {cards}
          <div class="chart-panel">
            <img src="{chart_data_uri}" alt="{escaped_location} 오늘 시간별 기온 그래프">
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>시간</th>
                  <th>기온</th>
                  <th>날씨</th>
                  <th>습도</th>
                  <th>강수확률</th>
                  <th>풍속</th>
                </tr>
              </thead>
              <tbody>{table_rows}</tbody>
            </table>
          </div>
        </section>
        """

    error_html = ""
    if error:
        error_html = f'<p class="error" role="alert">{escaped_error}</p>'

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>오늘 날씨 검색</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f4;
      --surface: #ffffff;
      --text: #202124;
      --muted: #656b73;
      --line: #dfe3e6;
      --accent: #d9480f;
      --accent-dark: #a63a0d;
      --teal: #0f766e;
      --shadow: 0 16px 40px rgba(33, 37, 41, 0.10);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.85), rgba(246, 247, 244, 0.96)),
        var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo",
        "Segoe UI", sans-serif;
    }}

    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 40px 0;
    }}

    .topbar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 24px;
    }}

    h1, h2, p {{
      margin: 0;
    }}

    h1 {{
      font-size: clamp(28px, 5vw, 48px);
      line-height: 1.05;
      letter-spacing: 0;
    }}

    .date {{
      color: var(--muted);
      font-size: 14px;
      white-space: nowrap;
    }}

    .search {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 14px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}

    input {{
      min-width: 0;
      height: 48px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 14px;
      font-size: 16px;
      color: var(--text);
      background: #fff;
    }}

    button {{
      height: 48px;
      border: 0;
      border-radius: 6px;
      padding: 0 18px;
      background: var(--accent);
      color: #fff;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }}

    button:hover {{
      background: var(--accent-dark);
    }}

    .error {{
      margin-top: 14px;
      padding: 12px 14px;
      border: 1px solid #f1b5a4;
      border-radius: 6px;
      color: #8a2410;
      background: #fff3ee;
    }}

    .result {{
      margin-top: 28px;
    }}

    .result-heading {{
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 14px;
    }}

    .result-heading h2 {{
      font-size: 26px;
      letter-spacing: 0;
    }}

    .result-heading p {{
      color: var(--muted);
      font-size: 14px;
    }}

    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}

    .metric {{
      min-height: 108px;
      display: grid;
      align-content: space-between;
      gap: 8px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}

    .metric span,
    .metric small {{
      color: var(--muted);
      font-size: 13px;
    }}

    .metric strong {{
      font-size: 26px;
      line-height: 1;
      color: var(--teal);
    }}

    .chart-panel {{
      padding: 12px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}

    .chart-panel img {{
      display: block;
      width: 100%;
      height: auto;
      border-radius: 4px;
    }}

    .table-wrap {{
      margin-top: 16px;
      overflow-x: auto;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }}

    th, td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
    }}

    th {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      background: #fafafa;
    }}

    tr:last-child td {{
      border-bottom: 0;
    }}

    @media (max-width: 720px) {{
      main {{
        width: min(100% - 24px, 1120px);
        padding: 24px 0;
      }}

      .topbar,
      .result-heading {{
        display: block;
      }}

      .date,
      .result-heading p {{
        margin-top: 8px;
      }}

      .search {{
        grid-template-columns: 1fr;
      }}

      button {{
        width: 100%;
      }}

      .metrics {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="topbar">
      <h1>오늘 날씨 검색</h1>
      <p class="date">Open-Meteo</p>
    </header>
    <form class="search" method="get" action="/">
      <input
        name="location"
        value="{escaped_query}"
        placeholder="예: 서울, 부산, Tokyo, New York"
        autocomplete="off"
        required
      >
      <button type="submit">검색</button>
    </form>
    {error_html}
    {result}
  </main>
</body>
</html>"""


class WeatherRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        query_params = parse_qs(parsed.query)
        query = query_params.get("location", [""])[0].strip()

        rows: list[dict[str, object]] = []
        location_label = ""
        timezone = "Asia/Seoul"
        chart_data_uri = ""
        error = ""

        if query:
            try:
                location = search_location(query)
                location_label = format_location(location)
                timezone = str(location["timezone"])
                rows = fetch_today_hourly_weather(
                    latitude=float(location["latitude"]),
                    longitude=float(location["longitude"]),
                    timezone=timezone,
                )
                chart_bytes = render_temperature_chart(
                    rows,
                    title=f"{location_label} 오늘 1시간 간격 기온",
                )
                chart_base64 = base64.b64encode(chart_bytes).decode("ascii")
                chart_data_uri = f"data:image/png;base64,{chart_base64}"
            except Exception as exc:
                error = str(exc)

        html_body = render_page(
            query=query,
            location_label=location_label,
            timezone=timezone,
            rows=rows,
            chart_data_uri=chart_data_uri,
            error=error,
        ).encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_body)))
        self.end_headers()
        self.wfile.write(html_body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), WeatherRequestHandler)
    print(f"날씨 검색 웹 서버 실행 중: http://{HOST}:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
