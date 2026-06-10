#!/usr/bin/env python3
"""Generate a concise Garmin CN sleep report for the previous night."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HEALTH_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HEALTH_DIR))

from garmin_auth import get_client
from garmin_data import (
    fetch_body_battery,
    fetch_heart_rate,
    fetch_hrv,
    fetch_sleep,
    fetch_stress,
    fetch_summary,
)


TZ = ZoneInfo("Asia/Shanghai")


def fmt_duration(seconds):
    if seconds is None:
        return "暂缺"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分钟"


def fmt_time(ms):
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, TZ).strftime("%H:%M")


def day_item(items, date):
    for item in items or []:
        if item.get("date") == date:
            return item
    return {}


def latest_item(items):
    return (items or [{}])[-1] if items else {}


def sleep_quality(score):
    if score is None:
        return "暂缺"
    if score >= 90:
        return f"{score}，优秀"
    if score >= 80:
        return f"{score}，良好"
    if score >= 60:
        return f"{score}，一般"
    return f"{score}，偏差"


def get_raw_sleep(client, date):
    try:
        return client.get_sleep_data(date) or {}
    except Exception:
        return {}


def build_report(client, today=None):
    today = today or datetime.now(TZ).date()
    yesterday = today - timedelta(days=1)
    today_s = today.isoformat()
    yesterday_s = yesterday.isoformat()

    sleep_result = fetch_sleep(client, start=yesterday_s, end=today_s).get("sleep", [])
    hrv_result = fetch_hrv(client, days=2).get("hrv", [])
    bb_result = fetch_body_battery(client, days=2).get("body_battery", [])
    hr_result = fetch_heart_rate(client, days=2).get("heart_rate", [])
    stress_result = fetch_stress(client, days=2).get("stress", [])
    summary_result = fetch_summary(client, days=2)

    sleep = day_item(sleep_result, today_s)
    if not sleep.get("sleep_time_seconds"):
        sleep = day_item(sleep_result, yesterday_s)

    raw_today = get_raw_sleep(client, today_s)
    raw_yesterday = get_raw_sleep(client, yesterday_s)
    raw = raw_today if (raw_today.get("dailySleepDTO") or {}).get("sleepTimeSeconds") else raw_yesterday
    raw_dto = raw.get("dailySleepDTO") or {}
    raw_date = raw_dto.get("calendarDate") or sleep.get("date") or today_s

    start_time = fmt_time(raw_dto.get("sleepStartTimestampGMT"))
    end_time = fmt_time(raw_dto.get("sleepEndTimestampGMT"))

    sleep_seconds = sleep.get("sleep_time_seconds") or raw_dto.get("sleepTimeSeconds")
    deep_seconds = sleep.get("deep_sleep_seconds") or raw_dto.get("deepSleepSeconds")
    light_seconds = sleep.get("light_sleep_seconds") or raw_dto.get("lightSleepSeconds")
    rem_seconds = sleep.get("rem_sleep_seconds") or raw_dto.get("remSleepSeconds")
    awake_seconds = sleep.get("awake_seconds") or raw_dto.get("awakeSleepSeconds")
    score = sleep.get("sleep_score")
    if score is None:
        score = (raw_dto.get("sleepScores") or {}).get("overall", {}).get("value")
    restless = sleep.get("restless_periods")
    if restless is None:
        restless = raw.get("restlessMomentsCount")

    avg_hrv = sleep.get("avg_hrv") or raw.get("avgOvernightHrv")
    avg_resp = sleep.get("avg_respiration") or raw_dto.get("averageRespirationValue")
    avg_sleep_hr = sleep.get("avg_hr") or raw_dto.get("avgHeartRate") or raw_dto.get("averageHeartRate")
    avg_sleep_stress = raw_dto.get("avgSleepStress")
    avg_spo2 = raw_dto.get("averageSpO2Value")
    low_spo2 = raw_dto.get("lowestSpO2Value")

    hrv_today = day_item(hrv_result, raw_date) or latest_item(hrv_result)
    hrv_status = hrv_today.get("status")
    weekly_hrv = hrv_today.get("weekly_avg")
    bb_today = day_item(bb_result, today_s) or latest_item(bb_result)
    hr_today = day_item(hr_result, today_s) or latest_item(hr_result)
    stress_today = day_item(stress_result, today_s) or latest_item(stress_result)
    activities = (summary_result.get("activities") or []) if isinstance(summary_result, dict) else []

    lines = [
        "昨晚睡眠报告（Garmin CN）",
        "",
        f"日期：{yesterday_s} 晚 -> {today_s} 早",
        f"主睡眠：{start_time or '暂缺'} -> {end_time or '暂缺'}",
        f"总睡眠：{fmt_duration(sleep_seconds)}",
        f"睡眠评分：{sleep_quality(score)}",
        "",
        "睡眠结构：",
        f"- 深睡：{fmt_duration(deep_seconds)}",
        f"- 浅睡：{fmt_duration(light_seconds)}",
        f"- REM：{fmt_duration(rem_seconds)}",
        f"- 清醒：{fmt_duration(awake_seconds)}",
        f"- Restless：{restless if restless is not None else '暂缺'} 次",
        "",
        "夜间指标：",
        f"- HRV：{avg_hrv if avg_hrv is not None else '暂缺'} ms"
        + (f"，状态 {hrv_status}" if hrv_status else "")
        + (f"，周均 {weekly_hrv} ms" if weekly_hrv is not None else ""),
        f"- 睡眠平均心率：{avg_sleep_hr if avg_sleep_hr is not None else '暂缺'} bpm；今日静息心率：{hr_today.get('resting_hr', '暂缺')} bpm",
        f"- 呼吸率：{avg_resp if avg_resp is not None else '暂缺'} 次/分钟",
        f"- 睡眠压力：{avg_sleep_stress if avg_sleep_stress is not None else '暂缺'}；今日平均压力：{stress_today.get('avg_stress', '暂缺')}",
        f"- Body Battery：充电 +{bb_today.get('charged', '暂缺')}，最高 {bb_today.get('highest', '暂缺')}，最低 {bb_today.get('lowest', '暂缺')}",
        f"- SpO2：平均 {avg_spo2 if avg_spo2 is not None else '暂缺'}%，最低 {low_spo2 if low_spo2 is not None else '暂缺'}%",
        "",
        "判断：",
    ]

    if sleep_seconds is None:
        lines.extend([
            "- 今天 Garmin CN 暂未同步到完整睡眠数据，先不强行判断恢复质量。",
            "- 可用指标有限，建议等手表/APP 再同步后复查。",
        ])
    else:
        hours = sleep_seconds / 3600
        if hours < 6:
            lines.append("- 恢复质量偏弱，主要短板是睡眠时长不足。")
        elif score is not None and score >= 80:
            lines.append("- 恢复质量不错，睡眠评分和结构整体可用。")
        else:
            lines.append("- 恢复质量一般，今天注意主观疲劳和专注度。")

        if hrv_status and hrv_status != "BALANCED":
            lines.append("- HRV 不在平衡状态，今天训练强度建议保守。")
        elif avg_hrv is not None:
            lines.append("- HRV 没有明显异常，可以按体感安排日常强度。")

        if activities:
            last = activities[-1]
            distance = last.get("distance_meters")
            activity_note = last.get("activity_name") or last.get("activity_type")
            if distance:
                lines.append(f"- 近期有 {distance / 1000:.0f}km 活动（{activity_note}），今天别叠太多负荷。")

        lines.append("- 今晚优先补足时长，尽量把总睡眠拉回 7 小时左右。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a Garmin CN sleep daily report")
    parser.add_argument(
        "--profile",
        choices=["cn"],
        default="cn",
        help="Only Garmin CN is supported for this report",
    )
    args = parser.parse_args()

    client = get_client(args.profile)
    if not client:
        print("Garmin CN 睡眠报告失败：认证不可用，请检查 Garmin CN 登录状态。")
        return 1

    print(build_report(client))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
