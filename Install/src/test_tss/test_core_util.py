import unittest
import src.tss.core_util as core_util

class CoreUtilTestCase(unittest.TestCase):

    def test_extract_number_from_string(self):
        self.assertEqual(core_util.extract_number_from_string("1 meters"), [1])
        self.assertEqual(core_util.extract_number_from_string("1 and 1"), [1, 1])
        self.assertEqual(core_util.extract_number_from_string("there are 2 records"), [2])

    def test_linear_units_to_mile(self):
        self.assertEqual(core_util.linear_units_to_mile("1 Centimeters"), 6.21371e-6)
        self.assertEqual(core_util.linear_units_to_mile("1 Feet"), 0.000189394)
        self.assertEqual(core_util.linear_units_to_mile("1 Inches"), 1.5783e-5)
        self.assertEqual(core_util.linear_units_to_mile("1 Kilometers"), 0.621371)
        self.assertEqual(core_util.linear_units_to_mile("1 Meters"), 0.000621371)
        self.assertEqual(core_util.linear_units_to_mile("1 Miles"), 1)
        self.assertEqual(core_util.linear_units_to_mile("1 Millimeters"), 6.2137e-7)
        self.assertEqual(core_util.linear_units_to_mile("1 Nautical Miles"), 1.15078)
        self.assertRaises(Exception, core_util.linear_units_to_mile, "1 decimal")


if __name__ == '__main__':
    unittest.main()
