import unittest
from sheets.utils import *

class TestUtils(unittest.TestCase):

    def test_column_to_number(self):
        x = column_to_number("A")
        self.assertEqual(x , 1)

        x = column_to_number("D")
        self.assertEqual(x, 4)

        x = column_to_number("AZ")
        self.assertEqual(x, 52)

        x = column_to_number("ZZ")
        self.assertEqual(x, 702)



    def test_number_to_column(self):
        x = number_to_column(1)
        self.assertEqual(x, "A")

        x = number_to_column(4)
        self.assertEqual(x, "D")

        x = number_to_column(52)
        self.assertEqual(x, "AZ")

        x = number_to_column(702)
        self.assertEqual(x, "ZZ")

    def test_location_to_coordinates(self):
        x = location_to_coordinates("A1")
        self.assertEqual(x, (1,1))

        x = location_to_coordinates("AZ22")
        self.assertEqual(x, (52,22))

        x = location_to_coordinates("ZZ5")
        self.assertEqual(x, (702, 5))

        x = location_to_coordinates("d4")
        self.assertEqual(x, (4,4))

        with self.assertRaises(ValueError):
            location_to_coordinates("*G")

        with self.assertRaises(ValueError):
            location_to_coordinates("GG-179")

        x = location_to_coordinates("AAA999")
        self.assertEqual(x, (703,999))

    def test_cell_range_to_list(self):
        test = cell_range_to_list("A1:B1")
        self.assertEqual(test, ["A1","B1"])

        test = cell_range_to_list("A1:C5")
        self.assertEqual(test, ["A1","A2","A3","A4","A5","B1","B2","B3","B4","B5","C1","C2","C3","C4","C5"])

        test = cell_range_to_list("C1:A5")
        self.assertEqual(test, ["A1","A2","A3","A4","A5","B1","B2","B3","B4","B5","C1","C2","C3","C4","C5"])

if __name__ == '__main__':
    unittest.main()
