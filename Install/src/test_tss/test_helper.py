import unittest
import src.tss.helper as helper

class HelperTestCase(unittest.TestCase):

    def test_first_or_default(self):
        def match_func(input):
            return input > 3
        self.assertEqual(helper.first_or_default([1, 2, 3, 4, 5], match_func), 4)
        self.assertEqual(helper.first_or_default([1, 2, 3], match_func), None)


if __name__ == '__main__':
    unittest.main()
