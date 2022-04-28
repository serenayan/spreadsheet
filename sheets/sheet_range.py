from copy import deepcopy
from typing import Dict, Optional, Tuple
import lark
from sheets.formula import formula_parse, formula_translate
from sheets.utils import column_to_number

class Contents:
    '''
    Contents represents the contents of a cell. The contents object has no
    mutating methods, so it is safe to be referenced by many different cells.
    The Contents object
    '''
    def __init__(self, contents: str, tree: Optional[lark.Tree]):
        self._contents = contents
        self._tree = tree
        if self._tree is None and self._contents.startswith("="):
            self._tree = formula_parse(self._contents)

    def tree(self) -> lark.Tree:
        return deepcopy(self._tree)

    def translated(self, offset: Tuple[int, int]) -> 'Contents':
        '''
        Return the cell translated by the given offset.
        Raises:
            ValueError - If the translated cell would be outside ZZZZ9999
        '''
        if self._tree is not None:
            (contents, tree) = formula_translate(self._tree, offset)
            return Contents(contents, tree)
        return self

    def __str__(self):
        return self._contents

class SheetRange:
    '''
    SheetRange represents a range of cells within a sheet. It is meant to
    be used as an intermediate representation by the copy and move
    operations.
    '''
    def __init__(self, origin: Tuple[int, int], cells: Dict[Tuple[int, int], Contents]):
        self._origin = origin
        self._cells = cells

    def origin(self) -> Tuple[int, int]:
        return self._origin

    def cells(self) -> Dict[Tuple[int, int], Contents]:
        return self._cells

    def translated(self, origin: Tuple[int, int]) -> 'SheetRange':
        '''
        Raises:
            ValueError - If any cell is out of bounds after
        '''
        offset = (origin[0] - self._origin[0], origin[1] - self._origin[1])
        cells = {}
        for coords, contents in self._cells.items():
            coords_lst = list(coords)
            coords_lst[0] += offset[0]
            coords_lst[1] += offset[1]
            coords = tuple(coords_lst)
            if coords[0] > column_to_number('ZZZZ') or coords[1] > 9999:
                raise ValueError("Out of bounds")
            cells[coords] = contents.translated(offset)
        return cells
    