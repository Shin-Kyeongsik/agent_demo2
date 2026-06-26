from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from open_meteo_hourly_today import fetch_today_hourly_weather


OUTPUT_PATH = Path("today_temperature.png")


def configure_korean_font() -> None:
    preferred_fonts = ["AppleGothic", "Malgun Gothic", "NanumGothic"]
    available_fonts = {font.name for font in fm.fontManager.ttflist}

    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    plt.rcParams["axes.unicode_minus"] = False


def save_today_temperature_chart(
    latitude: float = 37.5665,
    longitude: float = 126.9780,
    timezone: str = "Asia/Seoul",
    output_path: Path = OUTPUT_PATH,
) -> Path:
    rows = fetch_today_hourly_weather(
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )

    chart_bytes = render_temperature_chart(rows)
    output_path.write_bytes(chart_bytes)

    return output_path


def render_temperature_chart(
    rows: list[dict[str, object]],
    title: str = "오늘 1시간 간격 기온",
) -> bytes:
    times = [row["time"] for row in rows]
    temperatures = [row["temperature_c"] for row in rows]

    configure_korean_font()

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(times, temperatures, marker="o", linewidth=2, color="#d9480f")
    ax.fill_between(times, temperatures, alpha=0.15, color="#d9480f")

    ax.set_title(title, fontsize=16, pad=16)
    ax.set_xlabel("시간")
    ax.set_ylabel("기온 (°C)")
    ax.grid(True, linestyle="--", alpha=0.35)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    fig.autofmt_xdate(rotation=45)

    min_temp = min(temperatures)
    max_temp = max(temperatures)
    ax.set_ylim(min_temp - 2, max_temp + 2)

    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=160)
    plt.close(fig)

    return buffer.getvalue()


def main() -> None:
    saved_path = save_today_temperature_chart()
    print(f"그래프 저장 완료: {saved_path.resolve()}")


if __name__ == "__main__":
    main()
