import decimal
import io
from typing import Any,  List, Tuple
import unittest
from unittest.mock import patch
from sheets import Workbook, CellError, CellErrorType
from sheets.graph import Graph


from sheets.utils import coordinates_to_location

class TestWorkbook(unittest.TestCase):

    def test_empty_workbook(self):
        w = Workbook()
        self.assertEqual(w.num_sheets(), 0)
        self.assertListEqual(w.list_sheets(), [])

    def test_new_sheet_default_name(self):
        w = Workbook()
        (index, name) = w.new_sheet()
        self.assertEqual(index, 0)
        self.assertEqual(name, "Sheet1")

        (index, name) = w.new_sheet()
        self.assertEqual(index, 1)
        self.assertEqual(name, "Sheet2")

    def test_rename_sheet(self):
        w = Workbook()
        (index, name) = w.new_sheet()
        self.assertEqual(index, 0)
        self.assertEqual(name, "Sheet1")

        (index, name) = w.new_sheet()
        self.assertEqual(index, 1)
        self.assertEqual(name, "Sheet2")
        w.set_cell_contents("Sheet2", "A1", "=Test!A1")
        value = w.get_cell_value("Sheet2", "A1")
        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.BAD_REFERENCE)

        w.rename_sheet("Sheet1", "Test")
        self.assertListEqual(w.list_sheets(), ["Test", "Sheet2"])
        value = w.get_cell_value("Sheet2", "A1")
        self.assertEqual(value, None)

    def test_new_sheet(self):
        w = Workbook()
        (index, name) = w.new_sheet("Hello")
        self.assertEqual(index, 0)
        self.assertEqual(name, "Hello")

        (index, name) = w.new_sheet()
        self.assertEqual(index, 1)
        self.assertEqual(name, "Sheet2")
    
    def test_copy_sheet(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "A2", "5")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "A1", "=Sheet1!A1+Sheet1!A2")

        (index1, name1) = w.copy_sheet("Sheet1")
        (index2, name2) = w.copy_sheet("Sheet2")
        (index3, name3) = w.copy_sheet("Sheet1")

        self.assertEqual(index1, 2)
        self.assertEqual(name3, "Sheet1_2")

        value1 = w._get_sheet(name1).get_cell_value("A1")
        self.assertEqual(value1, decimal.Decimal(5))
        
        value2 = w._get_sheet(name2).get_cell_value("A1")
        self.assertEqual(value2, decimal.Decimal(10))

    def test_update_order(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "1")
        w.set_cell_contents("Sheet1", "A2", "=A1+1")
        w.set_cell_contents("Sheet1", "A3", "=A2+1")
        self.assertEqual(w.get_cell_value("Sheet1", "A3"), decimal.Decimal("3"))
        w.set_cell_contents("Sheet1", "A1", "2")
        self.assertEqual(w.get_cell_value("Sheet1", "A2"), decimal.Decimal("3"))
        self.assertEqual(w.get_cell_value("Sheet1", "A3"), decimal.Decimal("4"))

    def test_copy_sheet_does_not_alias(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        
        (_, name) = w.copy_sheet("Sheet1")
        w.set_cell_contents(name, "A1", "6")
        val = w.get_cell_contents("Sheet1", "A1")
        self.assertEqual(val, "5")
        val = w.get_cell_contents(name, "A1")
        self.assertEqual(val, "6")

    def test_copy_sheet_triggers_update(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "A1", "=Sheet1_1!A1")
        value = w.get_cell_value("Sheet2", "A1")
        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.BAD_REFERENCE)
   
        (_, name) = w.copy_sheet("Sheet1")
        self.assertEqual(name, "Sheet1_1")
        value = w.get_cell_value("Sheet2", "A1")
        self.assertEqual(value, decimal.Decimal('5'))
   

    def test_set_cell_contents(self):
        w = Workbook()
        (_, name) = w.new_sheet()

        # check that numbers values work
        w.set_cell_contents(name, "A5", "42")
        contents = w.get_cell_contents(name, "A5")
        self.assertEqual(contents, "42")
        value = w.get_cell_value(name, "A5")
        self.assertEqual(value, decimal.Decimal(42))

        # check that basic formulas work
        w.set_cell_contents(name, "ZZF4", "foo")
        contents = w.get_cell_contents(name, "ZZF4")
        self.assertEqual(contents, "foo")
        value = w.get_cell_value(name, "ZZF4")
        self.assertEqual(value, "foo")

        # check that basic formulas work
        w.set_cell_contents(name, "BB42", "=2+2")
        contents = w.get_cell_contents(name, "BB42")
        self.assertEqual(contents, "=2+2")
        value = w.get_cell_value(name, "BB42")
        self.assertEqual(value, decimal.Decimal(4))

        # check that empty cells return none
        contents = w.get_cell_contents(name, "YY832")
        self.assertIsNone(contents)
        value = w.get_cell_value(name, "YY832")
        self.assertIsNone(value)

    def test_formula_same_sheet_reference(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "5")
        w.set_cell_contents("Sheet1", "B4", "=A5")
        value = w.get_cell_value("Sheet1", "B4")
        self.assertEqual(value, decimal.Decimal(5))

    def test_multiple_spreadsheets(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "5")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B4", "=Sheet1!A5")
        value = w.get_cell_value("Sheet2", "B4")
        self.assertEqual(value, decimal.Decimal(5))

    def test_build_dependency_graph(self):
        w = Workbook()
        g = w.build_dependency_graph()
        self.assertEqual(len(g.vertices()), 0)

        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "5")
        g = w.build_dependency_graph()
        self.assertEqual(len(g.vertices()), 1)
        self.assertEqual(g.out_neighbors(("sheet1","A5")), [])

        w.set_cell_contents("Sheet1", "B6", "=A5")
        g = w.build_dependency_graph()
        self.assertEqual(len(g.vertices()), 2)
        self.assertEqual(g.out_neighbors(("sheet1","B6")), [("sheet1","A5")])

        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "C3", "=Sheet1!A5+Sheet1!B6")
        g = w.build_dependency_graph()
        self.assertEqual(len(g.vertices()), 3)
        self.assertSetEqual(set(g.out_neighbors(("sheet2","C3"))), set([("sheet1","A5"), ("sheet1","B6")]))

    def test_build_cyclical_graph(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "=B5")
        w.set_cell_contents("Sheet1", "B5", "=A5")
        g = w.build_dependency_graph()
        components = g.strongly_connected_components()
        self.assertEqual(len(components), 1)
        self.assertEqual(set(components[0]), set([("sheet1","A5"), ("sheet1","B5")]))

    def test_build_noncyclical_graph(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "=C5")
        w.set_cell_contents("Sheet1", "B5", "=C5")
        g = w.build_dependency_graph()
        components = g.strongly_connected_components()
        self.assertEqual(len(components), 3)
                        
    def test_cell_update_noncyclical(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "5")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B4", "=Sheet1!A5")
        value = w.get_cell_value("Sheet2", "B4")
        self.assertEqual(value, decimal.Decimal(5))
        w.set_cell_contents("Sheet1", "A5", "4")
        value = w.get_cell_value("Sheet2", "B4")
        self.assertEqual(value, decimal.Decimal(4))

    def test_cell_update_cyclical(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "=B5")
        w.set_cell_contents("Sheet1", "B5", "=A5")
        w.set_cell_contents("Sheet1", "C5", "=A5+D5")
        w.set_cell_contents("Sheet1", "D5", "=E5")
        value = w.get_cell_value("Sheet1", "C5")
        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.CIRCULAR_REFERENCE)
        w.set_cell_contents("Sheet1", "E5", "4")
        value = w.get_cell_value("Sheet1", "D5")
        self.assertEqual(value, decimal.Decimal(4))

    def test_set_cell_contents_cyclical_self_reference(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "=A5")
        value = w.get_cell_value("Sheet1", "A5")
        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.CIRCULAR_REFERENCE)
        
    def test_set_cell_contents_cyclical(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A5", "=B4")
        w.set_cell_contents("Sheet1", "B4", "=A5")
        value1 = w.get_cell_value("Sheet1", "B4")
        value2 = w.get_cell_value("Sheet1", "A5")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.CIRCULAR_REFERENCE)
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)

    def test_rename_sheet(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.rename_sheet("Sheet1", "Sheet2")
        self.assertEqual(w.num_sheets(), 1)
        self.assertEqual(len(w.list_sheets()), 1)
        self.assertTrue("Sheet2" in w.list_sheets())

    def test_rename_sheet_not_found_raises(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        with self.assertRaises(KeyError):
            w.rename_sheet("Shet1", "Sheet1")
            
    def test_rename_sheet_invalid_raises(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        with self.assertRaises(ValueError):
            w.rename_sheet("Sheet1", "'Invalid'")

    def test_rename_sheet_duplicate_raises(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        with self.assertRaises(ValueError):
            w.rename_sheet("Sheet1", "Sheet2")

    def test_rename_sheet_preserves_case(self):
        w = Workbook()
        w.new_sheet("ShEeT1")
        self.assertEqual(w.list_sheets()[0], "ShEeT1")

    def test_rename_sheet_updates_references(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet1", "B2", "=Sheet1!A1+Sheet2!A1")
        w.set_cell_contents("Sheet2", "B2", "=Sheet1!A1+Sheet2!A1")
        w.rename_sheet("Sheet1","Sheet3")
        self.assertEqual(w.get_cell_contents("Sheet3", "B2"), "=Sheet3!A1+Sheet2!A1")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "=Sheet3!A1+Sheet2!A1")

    def test_rename_sheet_updates_references_adds_quotes(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet1", "B2", "=Sheet1!A1+Sheet2!A1")
        w.set_cell_contents("Sheet2", "B2", "=Sheet1!A1+Sheet2!A1")
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet 3", "B2"), "='Sheet 3'!A1+Sheet2!A1")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "='Sheet 3'!A1+Sheet2!A1")

    def test_rename_sheet_updates_references_remove_quotes(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet1", "B2", "='Sheet1'!A1+'Sheet2'!A1")
        w.set_cell_contents("Sheet2", "B2", "=Sheet1!A1+'Sheet2'!A1")
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet 3", "B2"), "='Sheet 3'!A1+Sheet2!A1")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "='Sheet 3'!A1+Sheet2!A1")

    def test_rename_sheet_updates_references_only_changes_quotes_of_affected_cells(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B2", "='Sheet2'!C4")
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "='Sheet2'!C4")

    def test_rename_sheet_preserves_parentheses(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B2", "=Sheet1!A1+((((5))))")
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "='Sheet 3'!A1+((((5))))")

    def test_rename_sheet_ignores_invalid_formula(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B2", "=Sheet1'!A1")
        w.set_cell_contents("Sheet2", "B3", "=1")
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "=Sheet1'!A1")

    def test_rename_sheet_fixes_dangling_references(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "Foo")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B2", "='Sheet 3'!A1")
        value = w.get_cell_value("Sheet2", "B2")
        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.BAD_REFERENCE)
        w.rename_sheet("Sheet1","Sheet 3")
        self.assertEqual(w.get_cell_contents("Sheet2", "B2"), "='Sheet 3'!A1")
        value = w.get_cell_value("Sheet2", "B2")
        self.assertEqual(value, "Foo")

    def test_rename_sheet(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "=Sheet1!B5")
        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "A1", "=Sheet1!B5")
        w.rename_sheet("Sheet1", "Sheet3")
        self.assertEqual(w.num_sheets(), 2)
        self.assertEqual(len(w.list_sheets()), 2)
        self.assertTrue("Sheet2" in w.list_sheets())

    def test_load_workbook(self):
        with open("tests/testdata/workbook_valid.json") as fp:
            w = Workbook.load_workbook(fp)
            self.assertEqual(len(w.list_sheets()), 2)
            self.assertTrue("Sheet1" in w.list_sheets())
            self.assertTrue("Sheet2" in w.list_sheets())
            self.assertEqual(w.get_cell_contents("Sheet1", "B1"), "5.3")
            self.assertEqual(w.get_cell_value("Sheet1", "C1"), decimal.Decimal("651.9"))
    
    def test_load_workbook_invalid_json(self):
        with open("tests/testdata/workbook_invalid_missing_sheets.json") as fp:
            with self.assertRaises(KeyError):
                Workbook.load_workbook(fp)

        with open("tests/testdata/workbook_invalid_missing_name.json") as fp:
            with self.assertRaises(KeyError):
                Workbook.load_workbook(fp)

        with open("tests/testdata/workbook_invalid_missing_cell_contents.json") as fp:
            with self.assertRaises(KeyError):
                Workbook.load_workbook(fp)

        with open("tests/testdata/workbook_invalid_type_sheets.json") as fp:
            with self.assertRaises(TypeError):
                Workbook.load_workbook(fp)
        
        with open("tests/testdata/workbook_invalid_type_sheets_elements.json") as fp:
            with self.assertRaises(TypeError):
                Workbook.load_workbook(fp)

        with open("tests/testdata/workbook_invalid_type_name.json") as fp:
            with self.assertRaises(TypeError):
                Workbook.load_workbook(fp)     
        
        with open("tests/testdata/workbook_invalid_type_cell_contents.json") as fp:
            with self.assertRaises(TypeError):
                Workbook.load_workbook(fp)     

        with open("tests/testdata/workbook_invalid_type_contents.json") as fp:
            with self.assertRaises(TypeError):
                Workbook.load_workbook(fp)

    def test_save_workbook(self):
        fp = io.StringIO("")
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "B5", "5")
        w.new_sheet("Sheet2")
        w.save_workbook(fp)
        self.assertEqual(fp.getvalue(), '{"sheets": [{"name": "Sheet1", "cell-contents": {"B5": "5"}}, {"name": "Sheet2", "cell-contents": {}}]}')

    def test_notify_cells_changed(self):
        queue = []
        def on_update(workbook, changed: List[Tuple[Any, Any]]):
            queue.append(changed)
        w = Workbook()
        w.notify_cells_changed(on_update)
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "A1", "1")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], ("Sheet1", "A1"))

        w.set_cell_contents("Sheet1", "A1", "2")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], ("Sheet1", "A1"))

        w.set_cell_contents("Sheet1", "A2", "=A1")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], ("Sheet1", "A2"))

        w.set_cell_contents("Sheet1", "A3", "=A1")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], ("Sheet1", "A3"))

        w.set_cell_contents("Sheet1", "A4", "4")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], ("Sheet1", "A4"))

        w.set_cell_contents("Sheet1", "A1", "3")
        self.assertEqual(len(queue), 1)
        changed = queue[0]
        queue.pop(0)
        self.assertEqual(len(changed), 3)
        self.assertTrue(("Sheet1", "A1") in changed)
        self.assertTrue(("Sheet1", "A2") in changed)
        self.assertTrue(("Sheet1", "A3") in changed)


    def test_updated_bad_reference_due_to_missing_sheet_then_add_sheet(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "=Sheet2!B5")
        value = w.get_cell_value("Sheet1", "A1")

        self.assertIsInstance(value, CellError)
        self.assertEqual(value.get_type(), CellErrorType.BAD_REFERENCE)

        w.new_sheet("Sheet2")
        w.set_cell_contents("Sheet2", "B5", "5")

        x = w.get_cell_value("Sheet1", "A1")
        self.assertEqual(x, 5)

        w.del_sheet("Sheet2")
        value2 = w.get_cell_value("Sheet1", "A1")

        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.BAD_REFERENCE)



    def test_workbook_extent(self):
        s = Workbook()
        s.new_sheet("Sheet1")

        (c,r) = s.get_sheet_extent("Sheet1")
        s.set_cell_contents("Sheet1","A1", "5")
        s.set_cell_contents("Sheet1","B2", "10")
        (c, r) = s.get_sheet_extent("Sheet1")
        self.assertEqual(r, 2)
        self.assertEqual(c, 2)

        s.set_cell_contents("Sheet1","F4", "1")
        (c, r) = s.get_sheet_extent("Sheet1")
        self.assertEqual(r, 4)
        self.assertEqual(c, 6)

        s.set_cell_contents("Sheet1","F4", "     ")
        (c,r) = s.get_sheet_extent("Sheet1")
        self.assertEqual(c, 2)
        self.assertEqual(r, 2)

        s.set_cell_contents("Sheet1","B2","  ")
        (c,r) = s.get_sheet_extent("Sheet1")
        self.assertEqual(c,1)
        self.assertEqual(r,1)

        s.set_cell_contents("Sheet1","A1","   ")
        (c,r) = s.get_sheet_extent("Sheet1")
        self.assertEqual(c,0)
        self.assertEqual(r,0)

        s.set_cell_contents("sHeEt1", "B2", "=20+4")
        (c,r) = s.get_sheet_extent("sHEEt1")
        self.assertEqual(c,2)
        self.assertEqual(r,2)

        s.set_cell_contents("sHeEt1", "B2", " ")
        s.set_cell_contents("Sheet1", "D14", "5")
        (c,r) = s.get_sheet_extent("sHEEt1")
        self.assertEqual(c,4)
        self.assertEqual(r,14)

        s.set_cell_contents("Sheet1", "D14", None)
        (c,r) = s.get_sheet_extent("sHEEt1")
        self.assertEqual(c,0)
        self.assertEqual(r,0)


    def test_negative_loop_reference(self):
        w = Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "a1", "=b1")
        w.set_cell_contents("Sheet1", "B1", "=-a1")

        value1 = w.get_cell_value("Sheet1","a1")
        value2 = w.get_cell_value("Sheet1","B1")

        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.CIRCULAR_REFERENCE)

        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)


    def test_diamond_dependency(self):
        w = Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "A1", "=B1+D1")
        
        w.set_cell_contents("Sheet1", "B1", "=C1+5")
        w.set_cell_contents("Sheet1", "D1", "=C1")

        w.set_cell_contents("Sheet1","C1","5")

        value1 = w.get_cell_value("Sheet1","A1")
        valueB1 = w.get_cell_value("Sheet1","B1")
        valueD1 = w.get_cell_value("Sheet1","D1")
        self.assertEqual(valueB1, 10)
        self.assertEqual(valueD1, 5)
        self.assertEqual(value1, 15)

        w.set_cell_contents("Sheet1","C1","10")

        valueB1 = w.get_cell_value("Sheet1","B1")
        value2 = w.get_cell_value("Sheet1","A1")
        valueD1 = w.get_cell_value("Sheet1","D1")
        self.assertEqual(valueD1, 10)
        self.assertEqual(value2, 25)
        self.assertEqual(valueB1, 15)


    def test_cell_self_reference(self):
        w = Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "A1", "=a1")
        
        value1 = w.get_cell_value("Sheet1","A1")

        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.CIRCULAR_REFERENCE)


    def test_cell_update_order(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")

        w.set_cell_contents("ShEEt1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "=a1+1")
        w.set_cell_contents("Sheet1","C1","=B1+1")

        w.set_cell_contents("ShEEt1", "D1", "=C1+1")
        w.set_cell_contents("Sheet1", "E1", "=D1+1")
        w.set_cell_contents("Sheet1","f1","=E1+1")

        w.set_cell_contents("ShEEt2", "A1", "=Sheet1!f1+1")
        w.set_cell_contents("Sheet2", "B1", "=A1+1")
        w.set_cell_contents("Sheet2","C1","=B1+1")

        value1 = w.get_cell_value("Sheet2","C1")
        self.assertEqual(value1, 13)

        w.set_cell_contents("ShEEt1", "A1", "10")
        value2 = w.get_cell_value("Sheet2","C1")
        self.assertEqual(value2, 18)

        w.set_cell_contents("Sheet2", "A1", "0")
        value3 = w.get_cell_value("Sheet2","C1")
        self.assertEqual(value3, 2)


    def test_delete_spreadsheet(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.new_sheet("Sheet2")

        w.del_sheet("Sheet1")
        w.del_sheet("sHEEt2")

        test = w.list_sheets()
        self.assertFalse(test)

    def test_copy_cells(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "2")
        w.set_cell_contents("Sheet1", "C1", "=A1*B1")
        w.copy_cells("Sheet1", "A1", "C1", "A2")
        w.set_cell_contents("Sheet1", "A2", "2")
        value1 = w.get_cell_value("Sheet1", "C2")
        self.assertEqual(value1, 4)

    def test_move_cells(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "2")
        w.set_cell_contents("Sheet1", "C1", "=A1*B1")
        w.move_cells("Sheet1", "A1", "C1", "A2")
        self.assertEqual(w.get_cell_value("Sheet1", "C1"), None)
        w.move_cells("Sheet1", "A2", "B2", "A3")
        self.assertEqual(w.get_cell_value("Sheet1", "C2"), 0)
        w.move_cells("Sheet1", "A3", "B3", "A2")
        self.assertEqual(w.get_cell_value("Sheet1", "C2"), 10)
        w.move_cells("Sheet1", "A2", "C2", "B2")
        self.assertEqual(w.get_cell_value("Sheet1", "D2"), 10)

    def test_move_cells_range(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "2")
        w.set_cell_contents("Sheet1", "C1", "=A1*B1")
        w.set_cell_contents("Sheet1", "A2", "1")
        w.set_cell_contents("Sheet1", "B2", "3")
        w.set_cell_contents("Sheet1", "C2", "=A2*B2")
        w.move_cells("Sheet1", "C2", "A1", "A3")
        self.assertEqual(w.get_cell_value("Sheet1", "C1"), None)
        self.assertEqual(w.get_cell_value("Sheet1", "C2"), None)
        self.assertEqual(w.get_cell_value("Sheet1", "C3"), 10)
        self.assertEqual(w.get_cell_value("Sheet1", "C4"), 3)

    def test_copy_cells_range(self):
        w = Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "2")
        w.set_cell_contents("Sheet1", "C1", "=A1*B1")
        w.set_cell_contents("Sheet1", "A2", "1")
        w.set_cell_contents("Sheet1", "B2", "3")
        w.set_cell_contents("Sheet1", "C2", "=A2*B2")
        w.copy_cells("Sheet1", "C2", "A1", "A3")
        self.assertEqual(w.get_cell_value("Sheet1", "C1"), 10)
        self.assertEqual(w.get_cell_value("Sheet1", "C2"), 3)
        self.assertEqual(w.get_cell_value("Sheet1", "C3"), 10)
        self.assertEqual(w.get_cell_value("Sheet1", "C4"), 3)

    def test_boolean_literals(self):
        wb = Workbook()
        wb.new_sheet()
        wb.set_cell_contents('Sheet1', 'A1', 'true')
        assert isinstance(wb.get_cell_value('Sheet1', 'A1'), bool)
        assert wb.get_cell_value('Sheet1', 'A1')

        wb.set_cell_contents('Sheet1', 'A2', '=FaLsE')
        assert isinstance(wb.get_cell_value('Sheet1', 'A2'), bool)
        assert not wb.get_cell_value('Sheet1', 'A2')

"""
    def test_error_order_priority(self):
        w=Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "B1", "5")
        w.set_cell_contents("Sheet1", "A1", "=B1/0")

        value1 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.DIVIDE_BY_ZERO)

        w.set_cell_contents("Sheet1", "B1", "=a1")
        value2 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)

        w.set_cell_contents("Sheet1", "B1", "Hello")
        w.set_cell_contents("Sheet1", "A1", "=B1/2")

        value1 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.TYPE_ERROR)

        w.set_cell_contents("Sheet1", "B1", "=a1")
        value2 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)


        w.set_cell_contents("Sheet1", "B1", "5")
        w.set_cell_contents("Sheet1", "A1", "=B1/hello")

        value1 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.PARSE_ERROR)

        w.set_cell_contents("Sheet1", "B1", "=a1")
        value2 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.PARSE_ERROR)

        w.set_cell_contents("Sheet1", "B1", "5")
        w.set_cell_contents("Sheet1", "A1", "Sheet2!B1")

        value1 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.BAD_REFERENCE)

        w.new_sheet("Sheet2")

        w.set_cell_contents("Sheet2", "B1", "=a1")
        value2 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)


        w.set_cell_contents("Sheet1", "zzzzz1", "5")
        w.set_cell_contents("Sheet1", "A1", "=zzzzz1")

        value1 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.BAD_REFERENCE)

        w.set_cell_contents("Sheet1", "zzzzz1", "=a1")
        value2 = w.get_cell_value("Sheet1","A1")
        self.assertIsInstance(value2, CellError)
        self.assertEqual(value2.get_type(), CellErrorType.CIRCULAR_REFERENCE)

    
    def test_cells_reference_out_of_bounds_value(self):
         #This might be the correct test, this is the expected behaviour if a cell is copied or moved
         #outside of valid areas
         w=Workbook()
         w.new_sheet("Sheet1")

         w.set_cell_contents("Sheet1", "A1", "=AAAAA1")
         w.set_cell_contents("Sheet1", "A2", "=A10000")
         w.set_cell_contents("Sheet1", "A3", "=-A1")
         w.set_cell_contents("Sheet1", "A4", "=A-1")

         t1 = w.get_cell_value("Sheet1","AAAAA1")
         t2 = w.get_cell_value("Sheet1","A10000")
         t3 = w.get_cell_value("Sheet1","-A1")
         t4 = w.get_cell_value("Sheet1","A-1")

         self.assertIsInstance(t1, CellError)
         self.assertIsInstance(t2, CellError)
         self.assertIsInstance(t3, CellError)
         self.assertIsInstance(t4, CellError)

         self.assertEqual(t1.get_type(), CellErrorType.BAD_REFERENCE)
         self.assertEqual(t2.get_type(), CellErrorType.BAD_REFERENCE)
         self.assertEqual(t3.get_type(), CellErrorType.BAD_REFERENCE)
         self.assertEqual(t4.get_type(), CellErrorType.BAD_REFERENCE)


    
    
    def test_cells_copymove_to_ref_error_positive_column(self):
        # Expected behavior is to have formulas generate a bad reference error when 
        # things go out of bounds

        w=Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "A1", "=A2+5")
        w.set_cell_contents("Sheet1", "A2", "=A3+5")
        w.set_cell_contents("Sheet1", "A3", "0")
        test = w.get_cell_value("Sheet1", "A2")
        self.assertEqual(test, 5)

        w.move_cells("Sheet1","A1","C1","ZZZy1")
        w.copy_cells("Sheet1","A1","C1","ZZZy2")

        value1 = w.get_cell_value("Sheet1","ZZZZ1")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.BAD_REFERENCE)

        value1 = w.get_cell_value("Sheet1","ZZZZ2")
        self.assertIsInstance(value1, CellError)
        self.assertEqual(value1.get_type(), CellErrorType.BAD_REFERENCE)


    def test_movecopy_with_absolute_cell_reference(self):
        w=Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "A2", "=$A$1")
        w.set_cell_contents("Sheet1", "A3", "=$A$1")
        
        w.copy_cells("Sheet1","A2","A2", "B2")
        w.move_cells("Sheet1","A3","A3", "B3")

        test1 = w.get_cell_value("Sheet1", "A2")
        test2 = w.get_cell_value("Sheet1", "A3")

        w.set_cell_contents("Sheet1", "A1", "10")

        self.assertEqual(test1, 10)
        self.assertEqual(test2, 10)


    def test_movecopy_with_mixed_cell_reference(self):
        w=Workbook()
        w.new_sheet("Sheet1")
        w.set_cell_contents("Sheet1", "A1", "5")
        w.set_cell_contents("Sheet1", "B1", "10")
        w.set_cell_contents("Sheet1", "A2", "=A$1")
        w.set_cell_contents("Sheet1", "A3", "=A$1")
        
        w.copy_cells("Sheet1","A2","A2", "B2")
        w.move_cells("Sheet1","A3","A3", "B3")

        test1 = w.get_cell_value("Sheet1", "A2")
        test2 = w.get_cell_value("Sheet1", "A3")

        self.assertEqual(test1, 10)
        self.assertEqual(test2, 10)


    def test_absolute_cell_reference(self):
        w=Workbook()
        w.new_sheet("Sheet1")

        w.set_cell_contents("Sheet1", "A1", "5")

        w.set_cell_contents("Sheet1", "A2", "=$A$1")
        w.set_cell_contents("Sheet1", "A3", "=$A$1")

        test1 = w.get_cell_value("Sheet1", "A2")
        test2 = w.get_cell_value("Sheet1", "A3")

        self.assertEqual(test1, 5)
        self.assertEqual(test2, 5)
"""









if __name__ == '__main__':
    unittest.main()
