import math
from datetime import date

from flask import Flask, render_template, request

app = Flask(__name__)


def bmi_guidance(bmi):
    if bmi < 18.5:
        return {
            "label": "體重過輕",
            "tone": "low",
            "advice": "留意是否攝取足夠且均衡的營養，規律進食並搭配適度肌力活動；若體重持續下降，建議諮詢醫師或營養師。",
        }
    if bmi < 24:
        return {
            "label": "健康體位",
            "tone": "healthy",
            "advice": "維持均衡飲食與規律運動，並持續留意睡眠及生活習慣，幫助保持健康體位。",
        }
    if bmi < 27:
        return {
            "label": "體重過重",
            "tone": "high",
            "advice": "可從減少含糖飲料、增加蔬菜與日常活動量開始，循序建立適合自己的健康習慣。",
        }
    return {
        "label": "肥胖",
        "tone": "high",
        "advice": "建議與醫師或營養師討論適合自己的飲食及運動計畫，並留意血壓、血糖等健康指標。",
    }


# 《體位區分標準》中與 BMI、身高相關的常備役及免役條件，依施行日期由新到舊排列。
MILITARY_STANDARDS = [
    {
        "effective": date(2026, 10, 31),
        "exempt": (lambda bmi, height: bmi > 45 or height <= 144, "BMI 大於 45，或身高 144 公分以下"),
        "standard": (lambda bmi, height: bmi <= 45 and height > 144, "BMI 45 以下，且身高超過 144 公分"),
    },
    {
        "effective": date.min,
        "exempt": (
            lambda bmi, height: bmi < 15 or bmi > 35 or height <= 154 or height >= 196,
            "BMI 小於 15 或大於 35，或身高 154 公分以下、196 公分以上",
        ),
        "standard": (
            lambda bmi, height: 16.5 <= bmi <= 31.5 and 158 <= height <= 195,
            "BMI 介於 16.5 至 31.5，且身高 158 至 195 公分",
        ),
    },
]

MILITARY_STATUS_LABELS = {"exempt": "免役體位", "standard": "常備役體位"}


def military_status(bmi, height, today=None):
    today = today or date.today()
    standard = next(s for s in MILITARY_STANDARDS if today >= s["effective"])
    for kind in ("exempt", "standard"):
        matches, criteria = standard[kind]
        if matches(bmi, height):
            return {"kind": kind, "label": MILITARY_STATUS_LABELS[kind], "criteria": criteria}
    return None


# 油表式儀表的刻度範圍與色段，超出範圍時指針停在端點。
GAUGE_MIN, GAUGE_MAX = 10, 40
GAUGE_SEGMENTS = [
    ("low", GAUGE_MIN, 18.5),
    ("healthy", 18.5, 24),
    ("high", 24, 27),
    ("obese", 27, GAUGE_MAX),
]


def bmi_gauge(bmi):
    clamped = min(max(bmi, GAUGE_MIN), GAUGE_MAX)
    span = GAUGE_MAX - GAUGE_MIN
    return {
        "span": span,
        "angle": round((clamped - GAUGE_MIN) / span * 180 - 90, 2),
        "segments": [
            {"tone": tone, "start": start - GAUGE_MIN, "length": end - start}
            for tone, start, end in GAUGE_SEGMENTS
        ],
        "ticks": [
            {
                "label": f"{value:g}",
                "x": round(100 - 98 * math.cos(math.pi * (value - GAUGE_MIN) / span), 1),
                "y": round(103 - 98 * math.sin(math.pi * (value - GAUGE_MIN) / span), 1),
            }
            for value in (GAUGE_MIN, 18.5, 24, 27, GAUGE_MAX)
        ],
    }


def goal_progress(bmi, height_meters, weight, target):
    target_weight = target * height_meters * height_meters
    change = round(target_weight - weight, 1)
    gap = round(round(bmi, 1) - target, 1)
    if gap == 0:
        direction, summary = "achieved", "已達成目標"
    elif gap < 0:
        direction, summary = "gain", f"需增加約 {change:.1f} kg"
    else:
        direction, summary = "lose", f"需減少約 {-change:.1f} kg"
    return {
        "target": f"{target:.1f}",
        "gap": f"{abs(gap):.1f}",
        "target_weight": f"{target_weight:.1f}",
        "direction": direction,
        "summary": summary,
        "healthy": 18.5 <= target < 24,
    }


def parse_positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


@app.route("/", methods=["GET", "POST"])
def index():
    height_input = ""
    weight_input = ""
    target_input = ""
    errors = {}
    result = None

    if request.method == "POST":
        height_input = request.form.get("height", "").strip()
        weight_input = request.form.get("weight", "").strip()
        target_input = request.form.get("target", "").strip()
        height = parse_positive_number(height_input)
        weight = parse_positive_number(weight_input)
        target = parse_positive_number(target_input) if target_input else None

        if height is None:
            errors["height"] = "請輸入大於 0 的有效身高（公分）。"
        if weight is None:
            errors["weight"] = "請輸入大於 0 的有效體重（公斤）。"
        if target_input and target is None:
            errors["target"] = "請輸入大於 0 的有效目標 BMI。"

        if not errors:
            height_meters = height / 100
            height_squared = height_meters * height_meters
            if not math.isfinite(height_squared) or height_squared == 0:
                errors["height"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
            else:
                bmi = weight / height_squared
                if not math.isfinite(bmi) or bmi == 0:
                    errors["weight"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
                else:
                    displayed_bmi = round(bmi, 1)
                    result = {
                        "bmi": f"{displayed_bmi:.1f}",
                        **bmi_guidance(displayed_bmi),
                        "gauge": bmi_gauge(displayed_bmi),
                        "military": military_status(bmi, height),
                        "goal": goal_progress(bmi, height_meters, weight, target) if target else None,
                    }

    return render_template(
        "index.html",
        height_input=height_input,
        weight_input=weight_input,
        target_input=target_input,
        errors=errors,
        result=result,
    )


if __name__ == "__main__":
    app.run(debug=True)
