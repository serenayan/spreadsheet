from typing import Set, Tuple
import os
import re
from functools import reduce
import lark
from lark.visitors import Visitor, Transformer

from sheets.utils import get_sheet_name, translate_cell_ref

def quote_sheet_name(sheet_name: str):
    if len(sheet_name) <= 2:
        raise ValueError("invalid sheet name")
    if sheet_name[0] == "'" and sheet_name[-1] == "'":
        sheet_name = sheet_name[1:-1]
    if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", sheet_name) is not None:
        return sheet_name
    return f"'{sheet_name}'"


def formula_parse(formula: str):
    if formula_parse.parser is None:
        path = os.path.dirname(__file__)
        formula_parse.parser = lark.Lark.open(
            f'{path}/formulas.lark', start='formula')
    return formula_parse.parser.parse(formula)

formula_parse.parser = None

# pylint: disable=no-self-use
class _FormulaStringifier(Transformer):
    def __default_token__(self, token):
        return str(token)

    def __default__(self, data, children, meta):
        return reduce(lambda a, b: a + b, children, "")

    def concat_expr(self, children):
        return children[0] + '&' + children[1]

    def parens(self, children):
        return '(' + children[0] + ')'

    def expr_list(self, children):
        if len(children) == 2:
            return children[0] + "," + children[1]
        return children[0]

    def function_call(self, children):
        if len(children) == 2:
            return children[0] + "(" + children[1] + ")"
        return children[0] + "()"

    def cell(self, children):
        if len(children) == 2:
            return children[0] + '!' + children[1]
        return children[0]


def formula_to_string(tree: lark.Tree):
    return '=' + _FormulaStringifier().transform(tree)


class _RenameSheetTransformer(Transformer):
    def __init__(self, old: str, new: str):
        super().__init__()
        self.old = old
        self.new = new

    def cell(self, children):
        if len(children) == 2:
            sheet_name = str(children[0])
            if children[0].type == 'QUOTED_SHEET_NAME':
                sheet_name = sheet_name[1:-1]
            if self.old.lower() == sheet_name.lower():
                sheet_name = self.new
            sheet_name = quote_sheet_name(sheet_name)
            return lark.Tree('cell', [sheet_name, children[1]])
        return lark.Tree('cell', children)

class _TranslateTransformer(Transformer):
    def __init__(self, offset: Tuple[int, int]):
        super().__init__()
        self.offset = offset

    def cell(self, children):
        if len(children) == 2:
            return lark.Tree('cell', [children[0], translate_cell_ref(children[1], self.offset)])
        return lark.Tree('cell', [translate_cell_ref(children[0], self.offset)])

class _SheetDependenciesVisitor(Visitor):
    def __init__(self, dependencies: Set[str]):
        self.dependencies = dependencies

    def cell(self, tree):
        if len(tree.children) == 2:
            sheet = get_sheet_name(tree)
            self.dependencies.add(sheet.lower())

def formula_rename_sheet(tree: lark.Tree, old: str, new: str):
    sheet_dependencies = set()
    _SheetDependenciesVisitor(sheet_dependencies).visit(tree)
    if old.lower() in sheet_dependencies:
        tree = _RenameSheetTransformer(old, new).transform(tree)
    return formula_to_string(tree)

def formula_translate(tree: lark.Tree, offset: Tuple[int, int]) -> Tuple[str, lark.Tree]:
    tree = _TranslateTransformer(offset).transform(tree)
    return (formula_to_string(tree), tree)
