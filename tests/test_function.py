# Test function.py

import unittest
from sheets.function import *
from sheets import Workbook, CellError, CellErrorType
from sheets.cell import Cell
import decimal
import io
from typing import Any,  List, Tuple
import unittest
from unittest.mock import patch


class TestFunction(unittest.TestCase):

    def test_empty(self):
        pass

    def test_min(self):
        get_cell_value = lambda sheet, location: None

        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "1")
        w.set_cell_contents("Sheet1", "B1", "2")
        w.set_cell_contents("Sheet1", "C1", "3")
        c = Cell(("Sheet1", "D1"), "=MIN(C1:A1)", get_cell_value)
        # self.assertEqual(c.value(), 1)
        # w.set_cell_contents("Sheet1", "D1", "=MIN(C1:A1)")
        # self.assertEqual(w.get_cell_value("Sheet1", "D1"), 1)

        w.set_cell_contents("Sheet1", "A2", "1")
        w.set_cell_contents("Sheet1", "B2", "2")
        w.set_cell_contents("Sheet1", "C2", "what")
        c = Cell(("Sheet1", "D2"), "=MIN(C2:A2)", get_cell_value)
        # self.assertIsInstance(c.value(), CellError)
        # w.set_cell_contents("Sheet1", "D2", "=min(C2:A2)")
        # self.assertIsInstance(w.get_cell_value("Sheet1", "D2"), CellError)
        # w.set_cell_contents("Sheet1", "D3", "=min(C3:A3)")
        # self.assertIsInstance(w.get_cell_value("Sheet1", "D3"), CellError)

if __name__ == '__main__':
    unittest.main()
