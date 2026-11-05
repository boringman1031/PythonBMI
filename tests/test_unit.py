import unittest
from datetime import date

from bmi import InvalidMeasurement, bmi_guidance, calculate_bmi, military_status


class CalculateBmiTests(unittest.TestCase):
    def test_calculates_from_centimeters_and_kilograms(self):
        self.assertAlmostEqual(calculate_bmi(170, 65), 22.491, places=3)

    def test_unusable_values_report_the_responsible_field(self):
        for height, weight, field in [
            (1e-300, 65, "height"),
            (1e308, 65, "height"),
            (1, 1e308, "weight"),
        ]:
            with self.subTest(height=height, weight=weight):
                with self.assertRaises(InvalidMeasurement) as caught:
                    calculate_bmi(height, weight)
                self.assertEqual(caught.exception.field, field)


class BmiGuidanceTests(unittest.TestCase):
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


class MilitaryStatusTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
