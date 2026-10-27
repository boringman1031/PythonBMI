import unittest
from datetime import date

from app import app, bmi_guidance, goal_progress, military_status


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。</em>", page)
        self.assertIn("計算你的 BMI", page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)

    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def assert_military_kinds(self, today, cases):
        for bmi, height, kind in cases:
            with self.subTest(bmi=bmi, height=height):
                status = military_status(bmi, height, today)
                self.assertEqual(status and status["kind"], kind)

    def test_military_status_before_2026_revision(self):
        self.assert_military_kinds(date(2026, 10, 30), [
            (14.9, 170, "exempt"),
            (15.0, 170, None),
            (16.4, 170, None),
            (16.5, 170, "standard"),
            (31.5, 170, "standard"),
            (31.6, 170, None),
            (35.0, 170, None),
            (35.1, 170, "exempt"),
            (22.0, 154, "exempt"),
            (22.0, 157, None),
            (22.0, 158, "standard"),
            (22.0, 195, "standard"),
            (22.0, 196, "exempt"),
        ])

    def test_military_status_after_2026_revision(self):
        self.assert_military_kinds(date(2026, 10, 31), [
            (14.9, 170, "standard"),
            (45.0, 170, "standard"),
            (45.1, 170, "exempt"),
            (22.0, 144, "exempt"),
            (22.0, 145, "standard"),
            (22.0, 200, "standard"),
        ])

    def test_military_notice(self):
        response = self.client.post("/", data={"height": "140", "weight": "40"})
        self.assertIn("符合免役體位", response.get_data(as_text=True))
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("符合常備役體位", page)
        self.assertNotIn("符合免役體位", page)

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)

    def test_without_target_has_no_goal(self):
        response = self.client.post("/", data={"height": "170", "weight": "65", "target": ""})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertNotIn("目標體重", page)
        self.assertNotIn("goal-notice", page)

    def test_goal_progress(self):
        lose = goal_progress(80 / 1.7 ** 2, 1.7, 80, 22)
        self.assertEqual((lose["gap"], lose["target_weight"], lose["summary"]), ("5.7", "63.6", "需減少約 16.4 kg"))
        gain = goal_progress(50 / 1.7 ** 2, 1.7, 50, 20)
        self.assertEqual((gain["direction"], gain["summary"]), ("gain", "需增加約 7.8 kg"))
        achieved = goal_progress(65 / 1.7 ** 2, 1.7, 65, 22.5)
        self.assertEqual(achieved["direction"], "achieved")
        self.assertTrue(achieved["healthy"])
        self.assertFalse(goal_progress(22, 1.7, 63.6, 18.4)["healthy"])
        self.assertFalse(goal_progress(22, 1.7, 63.6, 24)["healthy"])

    def test_goal_notice(self):
        response = self.client.post("/", data={"height": "170", "weight": "80", "target": "22"})
        page = response.get_data(as_text=True)
        self.assertIn("27.7", page)
        self.assertIn("目標 BMI 22.0，相差 5.7", page)
        self.assertIn("目標體重約 63.6 kg，需減少約 16.4 kg", page)
        self.assertNotIn("不在健康體位範圍", page)

        response = self.client.post("/", data={"height": "170", "weight": "65", "target": "22.5"})
        self.assertIn("已達成目標", response.get_data(as_text=True))

        response = self.client.post("/", data={"height": "170", "weight": "65", "target": "26"})
        self.assertIn("不在健康體位範圍", response.get_data(as_text=True))

    def test_invalid_target_keeps_inputs(self):
        for target in ["abc", "0", "-5", "inf", "nan"]:
            with self.subTest(target=target):
                response = self.client.post("/", data={"height": "170", "weight": "65", "target": target})
                page = response.get_data(as_text=True)
                self.assertIn("請輸入大於 0 的有效目標 BMI。", page)
                self.assertIn('aria-describedby="target-error"', page)
                self.assertIn('value="170"', page)
                self.assertIn('value="65"', page)
                self.assertIn(f'value="{target}"', page)
                self.assertNotIn("YOUR RESULT", page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)


if __name__ == "__main__":
    unittest.main()
