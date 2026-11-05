import math
from datetime import date


class InvalidMeasurement(ValueError):
    """身高或體重無法算出有效的 BMI；field 指出是哪個欄位造成的。"""

    def __init__(self, field):
        super().__init__(field)
        self.field = field


def calculate_bmi(height_cm, weight_kg):
    height_meters = height_cm / 100
    # 不可改用 ** 2：浮點數溢位時會丟 OverflowError，而不是得到 inf。
    height_squared = height_meters * height_meters
    if not math.isfinite(height_squared) or height_squared == 0:
        raise InvalidMeasurement("height")
    bmi = weight_kg / height_squared
    if not math.isfinite(bmi) or bmi == 0:
        raise InvalidMeasurement("weight")
    return bmi


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
