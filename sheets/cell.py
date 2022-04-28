
from copy import deepcopy
from typing import Callable, Optional, Any, Set, Tuple, Union
import decimal
from lark import LarkError
import lark
from lark.visitors import Interpreter, Visitor
from sheets.function import FunctionRegistry
from sheets.sheet_range import Contents


from .utils import absolute_location_to_location, cell_value_type, convert_to_decimal, \
    convert_to_str, get_sheet_name, string_to_error, strip_trailing_zeros, zero_value
from .cell_error import CellError, CellErrorType
from .formula import formula_parse, formula_rename_sheet


CellReference = Tuple[str, str]


class Cell:
    def __init__(self,
                 reference: CellReference,
                 contents: Optional[Union[str, Contents]],
                 get_cell_value: Callable[[str,
                                           str],
                                          Any]):
        self._reference = reference
        self._dependencies = None
        self._tree = None
        self._value = None
        self._get_cell_value = get_cell_value
        self.__set_contents(contents)
        # Immediately recompute the value of the cell. This behavior is useful for testing
        # the behavior of Cell.
        #
        # Immediately recomputing the value may initially result in an incorrect value
        # if and only if the cell is part of a circular reference. If the cell is not
        # part of a circular reference, then the value of all directly or indirectly
        # dependent cells will not change when the value of this cell is changed. If this
        # cell is part of a circular reference, then its value will later be changed to
        # a CIRCULAR_REFERENCE error.
        self.recompute_value()

    def __set_contents(self, contents: Optional[Union[str, Contents]]) -> None:
        if isinstance(contents, Contents):
            self._contents = str(contents)
            self._tree = contents.tree()
            self.calculate_dependencies()
            return
        if contents is None or contents.strip() == "":
            self._contents = None
        else:
            self._contents = contents.strip()
        if self._contents is not None:
            if self._contents.startswith('='):
                try:
                    self._tree = formula_parse(self._contents)
                except LarkError:
                    pass
        self.calculate_dependencies()

    def contents(self) -> Optional[str]:
        return self._contents

    def tree(self) -> Optional[lark.Tree]:
        return deepcopy(self._tree)

    def value(self) -> Any:
        return self._value

    def rename_sheet(self, old: str, new: str):
        if self._reference[0].lower() == old.lower():
            self._reference = (old.lower(), self._reference[1])
        if self._tree is not None:
            updated = formula_rename_sheet(self._tree, old, new)
            self.__set_contents(updated)

    def calculate_dependencies(self):
        if self._tree is None:
            self._dependencies = []
            return
        dependencies = set()
        DependencyFinder(
            dependencies,
            self._reference[0]).visit(
            self._tree)

        self._dependencies = list(dependencies)

    def dependencies(self):
        if self._dependencies is None:
            self.calculate_dependencies()
        return self._dependencies

    def mark_cyclical(self) -> None:
        self._value = CellError(
            CellErrorType.CIRCULAR_REFERENCE,
            "A cell is part of a circular reference.")

    def _recompute_formula(self) -> None:
        if self._tree is None:
            self._value = CellError(
                CellErrorType.PARSE_ERROR,
                "A formula doesn't parse successfully.")
            return

        def get_cell_value(sheet, location):
            if sheet is None:
                sheet = self._reference[0]
            if (sheet.lower(), location.upper()) == self._reference:
                return CellError(
                    CellErrorType.CIRCULAR_REFERENCE,
                    "A cell is part of a circular reference.")
            return self._get_cell_value(sheet, location)

        v = FormulaInterpreter(get_cell_value).visit(self._tree)
        if isinstance(v, decimal.Decimal):
            if v.is_normal() or v.is_zero():
                self._value = strip_trailing_zeros(v)
            else:
                self._value = str(v)
        else:
            self._value = v

    def recompute_value(self) -> None:
        if self._contents is None:
            self._value = None
        elif self._contents[0] == "'":
            self._value = self._contents[1:]
        elif self._contents[0] == "=":
            self._recompute_formula()
        else:
            # Attempt to parse the string as an error.
            self._value = string_to_error(self._contents)
            if self._value is not None:
                return

            if self._contents.lower() == "true":
                self._value = True
                return

            if self._contents.lower() == "false":
                self._value = False
                return

            # Attempt to parse the string as a number.
            # If parsing fails, then assume that the value is a string.
            try:
                d = decimal.Decimal(self._contents)
                if d.is_normal() or d.is_zero():
                    self._value = strip_trailing_zeros(d)
                else:
                    self._value = str(d)
            except decimal.InvalidOperation:
                self._value = self._contents


class DependencyFinder(Visitor):
    def __init__(self, dependencies: Set[CellReference], sheet_name: str):
        self.sheet_name = sheet_name
        self.dependencies = dependencies

    def cell(self, tree):
        if len(tree.children) == 2:
            sheet = str(tree.children[0]).lower()
            if tree.children[0].type == 'QUOTED_SHEET_NAME':
                sheet = sheet[1:-1]
            loc = str(tree.children[1]).upper()
        else:
            sheet = self.sheet_name.lower()
            loc = str(tree.children[0]).upper()
        self.dependencies.add((sheet, loc))

# pylint: disable=no-self-use
class FormulaInterpreter(Interpreter):

    def __init__(self, get_cell_value: Callable[[str, str], Any]):
        self._get_cell_value = get_cell_value

    def error(self, tree):
        err = string_to_error(tree.children[0])
        assert err is not None
        return err

    def bool(self, tree):
        if str(tree.children[0]).lower() == "true":
            return True
        if str(tree.children[0]).lower() == "false":
            return False
        raise ValueError("unreachable")

    def number(self, tree):
        d = decimal.Decimal(tree.children[0])
        assert(d.is_normal() or d.is_zero())
        return strip_trailing_zeros(d)

    def string(self, tree):
        return tree.children[0][1:-1]

    def parens(self, tree):
        return self.visit(tree.children[0])

    def expr_list(self, tree):
        if len(tree.children) == 2:
            if tree.children[1].data == 'expr_list':
                return [tree.children[0], *self.visit(tree.children[1])]
            return [tree.children[0], tree.children[1]]
        return [tree.children[0]]

    def function_call(self, tree):
        name = str(tree.children[0])
        args = []
        if len(tree.children) == 2:
            if tree.children[1].data != 'expr_list':
                args = [tree.children[1]]
            else:
                args = self.visit(tree.children[1])
            args = list(map(lambda t: lambda: self.visit(t), args))
        registry = FunctionRegistry()
        func = registry.find(name)
        if func is None:
            return CellError(CellErrorType.BAD_NAME, f'function "{name}" not found')
        value = func(args)
        if isinstance(value, lark.Tree):
            return self.visit(value)
        return value

    def cell(self, tree):
        sheet = None
        location = None
        if len(tree.children) == 2:
            sheet = get_sheet_name(tree).lower()
            location = str(tree.children[1])
        else:
            location = str(tree.children[0])
        try:
            location = absolute_location_to_location(location)
            return self._get_cell_value(sheet, location)
        except (KeyError, ValueError):
            return CellError(CellErrorType.BAD_REFERENCE,
                             "A cell-reference is invalid in some way.")

    def bool_expr(self, tree):
        value1 = self.visit(tree.children[0])
        op = str(tree.children[1])
        value2 = self.visit(tree.children[2])
        # If either value is an error, propogate it higher...
        if isinstance(value1, CellError):
            return value1
        if isinstance(value2, CellError):
            return value2
        # If both values are None, convert them both to zero so
        # that all operations are well defined.
        if value1 is None and value2 is None:
            value1 = decimal.Decimal(0)
            value2 = decimal.Decimal(0)
        # If one value is None, convert it to the zero value that
        # corresponds with the type of the other.
        if value1 is None:
            value1 = zero_value(cell_value_type(value2))
        if value2 is None:
            value2 = zero_value(cell_value_type(value1))
        # Replace value with the CellValueType value corresponding
        # with their type so that bool > str and str > number
        type1 = cell_value_type(value1)
        type2 = cell_value_type(value2)
        if type1 != type2:
            value1 = type1
            value2 = type2
        # Convert strings to lowercase so they are compared in a case-insensitive
        # manner
        if isinstance(value1, str) and isinstance(value2, str):
            value1 = value1.lower()
            value2 = value2.lower()

        ops = {
            "=": lambda a, b: a == b,
            "==": lambda a, b: a == b,
            "<>": lambda a, b: a != b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
        }
        assert op in ops
        func = ops[op]
        return func(value1, value2)

    def concat_expr(self, tree):
        # If the left value is a CellError, return the error,
        # otherwise, convert the value to a string.
        value1 = self.visit(tree.children[0])
        if isinstance(value1, CellError):
            return value1
        value1 = convert_to_str(value1)

        # If the right value is a CellError, return the error,
        # otherwise, convert the value to a string.
        value2 = self.visit(tree.children[1])
        if isinstance(value2, CellError):
            return value2
        value2 = convert_to_str(value2)

        return value1 + value2

    def unary_op(self, tree) -> Union[CellError, decimal.Decimal]:
        # If the value is a CellError, return the error.
        # If the value cannot be parsed as an Decimal, return
        # a TYPE_ERROR.
        value = convert_to_decimal(self.visit(tree.children[1]))
        if isinstance(value, CellError):
            return value

        operator = str(tree.children[0])
        assert operator in ["+", "-"]
        if operator == "+":
            return value
        if operator == "-":
            return value.__neg__()
        raise ValueError("unreachable")

    def mul_expr(self, tree) -> Union[CellError, decimal.Decimal]:
        # If the value is a CellError, return the error.
        # If the value cannot be parsed as an Decimal, return
        # a TYPE_ERROR.
        value1 = convert_to_decimal(self.visit(tree.children[0]))
        if isinstance(value1, CellError):
            return value1

        # If the value is a CellError, return the error.
        # If the value cannot be parsed as an Decimal, return
        # a TYPE_ERROR.
        value2 = convert_to_decimal(self.visit(tree.children[2]))
        if isinstance(value2, CellError):
            return value2

        operator = tree.children[1]
        assert(operator in ["*", "/"])
        if operator == "*":
            return value1 * value2
        if operator == "/":
            if value2 == decimal.Decimal(0):
                return CellError(
                    CellErrorType.DIVIDE_BY_ZERO,
                    "A divide-by-zero was encountered during evaluation.")
            return value1 / value2
        raise ValueError("unreachable")

    def add_expr(self, tree) -> Union[CellError, decimal.Decimal]:
        # If the value is a CellError, return the error.
        # If the value cannot be parsed as an Decimal, return
        # a TYPE_ERROR.
        value1 = convert_to_decimal(self.visit(tree.children[0]))
        if isinstance(value1, CellError):
            return value1

        # If the value is a CellError, return the error.
        # If the value cannot be parsed as an Decimal, return
        # a TYPE_ERROR.
        value2 = convert_to_decimal(self.visit(tree.children[2]))
        if isinstance(value2, CellError):
            return value2

        operator = tree.children[1]
        assert(operator in ["+", "-"])
        if operator == "+":
            return value1 + value2
        if operator == "-":
            return value1 - value2
        raise ValueError("unreachable")
