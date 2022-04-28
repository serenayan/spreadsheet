import unittest
from sheets.formula import *

class TestFormula(unittest.TestCase):
    def test_formula_to_string_add(self):
        tree = formula_parse("=5 + 5")
        str = formula_to_string(tree)
        self.assertEqual(str, "=5+5")

    def test_formula_to_string_string(self):
        tree = formula_parse('="foo"')
        str = formula_to_string(tree)
        self.assertEqual(str, '="foo"')

    def test_formula_to_string_parens(self):
        tree = formula_parse("=( 5 )")
        str = formula_to_string(tree)
        self.assertEqual(str, "=(5)")

    def test_formula_to_string_cell(self):
        tree = formula_parse("=A5")
        str = formula_to_string(tree)
        self.assertEqual(str, "=A5")

    def test_formula_to_string_cell(self):
        tree = formula_parse("=Sheet1!A5")
        str = formula_to_string(tree)
        self.assertEqual(str, "=Sheet1!A5")

    def test_formula_to_string_concat(self):
        tree = formula_parse("=5 & 5")
        str = formula_to_string(tree)
        self.assertEqual(str, "=5&5")

        tree = formula_parse("=5&6&7")
        str = formula_to_string(tree)
        self.assertEqual(str, "=5&6&7")

    def test_formula_rename_sheet_not_found(self):
        tree = formula_parse("='Sheet3'!A5+5")
        str = formula_rename_sheet(tree, "Sheet1", "Sheet2")
        self.assertEqual(str, "='Sheet3'!A5+5")

    def test_formula_rename_sheet_found(self):
        tree = formula_parse("='Sheet3'!A5+'Sheet 4'!A5+Sheet1!A5")
        str = formula_rename_sheet(tree, "Sheet1", "Sheet2")
        self.assertEqual(str, "=Sheet3!A5+'Sheet 4'!A5+Sheet2!A5")