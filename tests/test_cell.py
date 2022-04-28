import decimal
import unittest
from sheets.cell import Cell, CellError, CellErrorType
from decimal import Decimal

class TestCell(unittest.TestCase):

    def test_invalid_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=5+", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.PARSE_ERROR)

    def test_function_call_bad_name(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=FOO()", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_NAME)

    def test_function_call_or(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=OR()", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)
        c = Cell(("Sheet1", "A1"), "=OR(FALSE)", get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), "=OR(TRUE)", get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), "=OR(FALSE,TRUE)", get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), "=OR(FALSE,FALSE,TRUE)", get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '=OR(52)', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '=OR("True")', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '=OR("Hello")', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)

    def test_function_call_and(self):
        # TODO: rileyoneil
        pass

    def test_function_call_not(self):
        # TODO: rileyoneil
        pass

    def test_function_call_xor(self):
        # TODO: rileyoneil=
        pass

    def test_function_call_exact(self):
        get_cell_value = lambda sheet, location: "Foo"
        c = Cell(("Sheet1", "A1"), '=EXACT(A1,"BAR")', get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), '=EXACT(A1,"FOO")', get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), '=EXACT(A1,"Foo")', get_cell_value)
        self.assertEqual(c.value(), True)
        # c = Cell(("Sheet1", "A1"), '=EXACT(A2:A5,B2:B5)', get_cell_value)
        # self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)

    def test_function_call_indirect(self):
        get_cell_value = lambda sheet, location: "Foo"
        c = Cell(("Sheet1", "A1"), '=INDIRECT("A2")', get_cell_value)
        self.assertEqual(c.value(), "Foo")

    def test_function_call_choose(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=CHOOSE(1.000,TRUE,FALSE)', get_cell_value)
        self.assertEqual(c.value(), True)

    def test_non_normal_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), 'Infinity', get_cell_value)
        self.assertEqual(c.value(), "Infinity")
        c = Cell(("Sheet1", "A1"), '-Infinity', get_cell_value)
        self.assertEqual(c.value(), "-Infinity")
        c = Cell(("Sheet1", "A1"), 'NaN', get_cell_value)
        self.assertEqual(c.value(), "NaN")
        c = Cell(("Sheet1", "A1"), '=1*"Infinity"', get_cell_value)
        self.assertEqual(c.value(), "Infinity")
        c = Cell(("Sheet1", "A1"), '=1*"-Infinity"', get_cell_value)
        self.assertEqual(c.value(), "-Infinity")
        c = Cell(("Sheet1", "A1"), '=1*"NaN"', get_cell_value)
        self.assertEqual(c.value(), "NaN")

    def test_text_value(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "foo", get_cell_value)
        self.assertEqual(c.value(), "foo")
    
    def test_decimal_value(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "5", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))
        self.assertEqual(str(c.value()), "5")

    def test_bool_value(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "TrUe", get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), "=TrUe", get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), "FaLSE", get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), "=FaLSE", get_cell_value)
        self.assertEqual(c.value(), False)

    def test_bool_expr(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '="12" > 12', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '="TRUE" > FALSE', get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), '=FALSE < TRUE', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '="a" < "["', get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), '="BLUE" = "blue"', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '="BLUE" < "blue"', get_cell_value)
        self.assertEqual(c.value(), False)   
        c = Cell(("Sheet1", "A1"), '="BLUE" > "blue"', get_cell_value)
        self.assertEqual(c.value(), False)
        c = Cell(("Sheet1", "A1"), '=A2 = A3', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '=A2 = 0', get_cell_value)
        self.assertEqual(c.value(), True)
        c = Cell(("Sheet1", "A1"), '=A2 = 1', get_cell_value)
        self.assertEqual(c.value(), False)
        
    def test_strip_trailing_zeros_after_decimal(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "50.00", get_cell_value)
        self.assertEqual(c.value(), Decimal(50))
        self.assertEqual(str(c.value()), "50")

    def test_keep_trailing_zeros_before_decimal(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "500", get_cell_value)
        self.assertEqual(c.value(), Decimal(500))
        self.assertEqual(str(c.value()), "500")

    def test_quoted_string(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "'500", get_cell_value)
        self.assertEqual(c.value(), "500")

    def test_numeric_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=5", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

    def test_string_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '="foo"', get_cell_value)
        self.assertEqual(c.value(), "foo")

    def test_parens_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=(5)", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

    def test_concat_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '="foo"&"bar"', get_cell_value)
        self.assertEqual(c.value(), "foobar")

        c = Cell(("Sheet1", "A1"), '=4&5', get_cell_value)
        self.assertEqual(c.value(), "45")

    def test_div_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=5/2', get_cell_value)
        self.assertEqual(c.value(), decimal.Decimal("2.5"))

    def test_error_string(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '#REF!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

        c = Cell(("Sheet1", "A1"), '#ref!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_concat_formula_propogates_errors(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=#REF!&"test"', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)
        c = Cell(("Sheet1", "A1"), '="test"&#REF!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_unary_formula_propogates_errors(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=-#REF!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_mul_formula_propogates_errors(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=5*#REF!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)
        c = Cell(("Sheet1", "A1"), '=#REF!*5', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_add_formula_propogates_errors(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=5+#REF!', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)
        c = Cell(("Sheet1", "A1"), '=#REF!+5', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_unary_formula_fails_on_string(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=-"foo"', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)

    def test_add_formula_fails_on_string(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=5+"foo"', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)
        c = Cell(("Sheet1", "A1"), '="foo"+5', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)

    def test_mul_formula_fails_on_string(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), '=5*"foo"', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)
        c = Cell(("Sheet1", "A1"), '="foo"*5', get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.TYPE_ERROR)

    def test_concat_formula_trailing_zeros(self):
        def get_cell_value(sheet, location):
            if location == "A3":
                return decimal.Decimal("1.01")
            elif location == "B4":
                return decimal.Decimal("0.01")
            else:
                return None
        c = Cell(("Sheet1", "A1"), '=(A3-B4)&"Riley"', get_cell_value)
        self.assertEqual(c.value(), "1Riley")
          
    def test_cell_formula(self):
        get_cell_value = lambda sheet, location: Decimal(5)
        c = Cell(("Sheet1", "A1"), "=Sheet1!A5", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

    def test_error_literal_formula(self):
        get_cell_value = lambda sheet, location: Decimal(5)
        c = Cell(("Sheet1", "A1"), "=#REF!", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_invalid_reference_formula(self):
        def get_cell_value(sheet, location):
           raise KeyError
        c = Cell(("Sheet1", "A1"), "=Sheet2!A1", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.BAD_REFERENCE)

    def test_quoted_cell_formula(self):
        def get_cell_value(sheet, location):
            self.assertEqual(sheet, "sheet1")
            self.assertEqual(location, "A5")
            return Decimal(5)
        c = Cell(("Sheet1", "A1"), "='Sheet1'!A5", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

    def test_division_by_zero_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=5/0", get_cell_value)
        self.assertIsInstance(c.value(), CellError)
        self.assertEqual(c.value().get_type(), CellErrorType.DIVIDE_BY_ZERO)

    def test_unary_op_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=-5", get_cell_value)
        self.assertEqual(c.value(), Decimal(-5))

        c = Cell(("Sheet1", "A1"), '=+"5"', get_cell_value)
        self.assertEqual(c.value(), Decimal(+5))

    def test_mult_expr_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=2*3", get_cell_value)
        self.assertEqual(c.value(), Decimal(6))

        c = Cell(("Sheet1", "A1"), '=2*"3"', get_cell_value)
        self.assertEqual(c.value(), Decimal(6))

        c = Cell(("Sheet1", "A1"), '="2"*"3"', get_cell_value)
        self.assertEqual(c.value(), Decimal(6))

    def test_add_expr_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=2+3", get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

        c = Cell(("Sheet1", "A1"), '=2+"3"', get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

        c = Cell(("Sheet1", "A1"), '="2"+"3"', get_cell_value)
        self.assertEqual(c.value(), Decimal(5))

    def test_expr_formula(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "=2+3*4", get_cell_value)
        self.assertEqual(c.value(), Decimal(14))

        c = Cell(("Sheet1", "A1"), "=(2+3)*4", get_cell_value)
        self.assertEqual(c.value(), Decimal(20))
    
    def test_dependencies(self):
        get_cell_value = lambda sheet, location: None
        c = Cell(("Sheet1", "A1"), "5", get_cell_value)
        self.assertListEqual(c.dependencies(), [])
        c = Cell(("Sheet1", "A1"), "=5", get_cell_value)
        self.assertListEqual(c.dependencies(), [])
        c = Cell(("Sheet1", "A1"), "=A5", get_cell_value)
        self.assertListEqual(c.dependencies(), [("sheet1", "A5")])
        c = Cell(("Sheet1", "A1"), "=Sheet2!A5", get_cell_value)
        self.assertListEqual(c.dependencies(), [("sheet2","A5")])
        c = Cell(("Sheet1", "A1"), "='4 * (3 - 2)'!A5", get_cell_value)
        self.assertListEqual(c.dependencies(), [("4 * (3 - 2)","A5")])
        c = Cell(("Sheet1", "A1"), "='A5!A5'!A5", get_cell_value)
        self.assertListEqual(c.dependencies(), [("a5!a5", "A5")])
        c = Cell(("Sheet1", "A1"), "=5+(4*Sheet2!A5)-A3", get_cell_value)
        self.assertListEqual(sorted(c.dependencies()), sorted([("sheet1", "A3"), ("sheet2","A5")]))

    def test_expr_formula(self):
         
        def get_cell_value(sheet, location):
            if f"{sheet}!{location}" == "sheet1!A3":
                return decimal.Decimal(5)
            elif f"{sheet}!{location}" == "sheet2!B4":
                return decimal.Decimal(3)
            else:
                return None

        c = Cell(("Sheet1", "A1"), "=Sheet1!A3 + Sheet2!B4", get_cell_value)
        self.assertEqual(c.value(), Decimal(8))

if __name__ == '__main__':
    unittest.main()
