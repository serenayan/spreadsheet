from typing import Any, Dict, List, Optional, Tuple, Callable

from .sheet_range import Contents, SheetRange
from .utils import in_range, location_to_coordinates, coordinates_to_location
from .cell import Cell
# import numpy as np


class Spreadsheet:

    def __init__(self, name: str, get_cell_value: Callable[[str, str], Any]):
        self._name = name
        self.cell_contents: Dict[Tuple[int, int], Cell] = {}
        self._get_cell_value = get_cell_value

    def name(self):
        # Return the name of the sheet in the original casing.
        return self._name

    def extent(self) -> Tuple[int, int]:
        if len(self.cell_contents.keys()) == 0:
            return (0, 0)
        # Return a tuple (num-cols, num-rows) indicating the current extent of
        # the specified spreadsheet.
        coordinates = list(self.cell_contents.keys())
        col_min, row_min = coordinates[0]
        col_max, row_max = coordinates[0]

        for coordinate in coordinates:
            col, row = coordinate

            if col < col_min:
                col_min = col
            elif col > col_max:
                col_max = col

            if row < row_min:
                row_min = row
            elif row > row_max:
                row_max = row

        col_extent = col_max
        row_extent = row_max
        extent = (col_extent, row_extent)

        return extent

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        result = {}
        for coords, cell in self.cell_contents.items():
            vertex = (
                self.name().lower(),
                coordinates_to_location(coords).upper())
            result[vertex] = cell.dependencies()
        return result

    def set_cell_contents(
            self,
            location: str,
            contents: Optional[str]) -> None:
        # Set the contents of the specified cell on the specified sheet.
        #
        # The cell location can be specified in any case. If the cell location
        # is invalid, a ValueError is raised.
        #
        # A cell may be set to "empty" by specifying a contents of None.
        #
        # Leading and trailing whitespace are removed by the cell.  Storing a
        # zero-length string "" (or a string composed entirely of whitespace)
        # is equivalent to setting the cell contents to None.
        #
        # If the cell contents appear to be a formula, and the formula is
        # invalid for some reason, this method does not raise an exception;
        # rather, the cell's value will be a CellError object indicating the
        # naure of the issue.

        # Get coordinate location of cells
        cell_coordinates = location_to_coordinates(location)

        if contents is None:
            self.cell_contents.pop(cell_coordinates)
            return

        # Remove extra whitespace
        contents = contents.strip()

        # Add Dictionary element or remove
        if contents == "":
            self.cell_contents.pop(cell_coordinates)
        else:
            reference = (self.name().lower(), location.upper())
            self.cell_contents[cell_coordinates] = Cell(
                reference, contents, self._get_cell_value)

    def get_cell(self, location: str) -> Optional[Cell]:
        cell_coordinates = location_to_coordinates(location)
        if cell_coordinates not in self.cell_contents:
            return None
        return self.cell_contents[cell_coordinates]

    def mark_cyclical(self, location: str) -> None:
        cell = self.get_cell(location)
        if cell is None:
            raise RuntimeError("An empty cell cannot be cyclical")
        cell.mark_cyclical()

    def get_cell_contents(self, location: str) -> Optional[str]:
        # The cell location can be specified in any case. If the cell location
        # is invalid, a ValueError is raised.
        #
        # Any string returned by this function will not have leading or trailing
        # whitespace, as this whitespace will have been stripped off by the
        # set_cell_contents() function.
        #
        # This method will never return a zero-length string; instead, empty
        # cells are indicated by a value of None.

        cell_coordinates = location_to_coordinates(location)

        if cell_coordinates not in self.cell_contents:
            return None
        cell = self.cell_contents[cell_coordinates]
        cell_contents = cell.contents()
        return cell_contents

    def snapshot(self) -> Dict[Tuple[str, str], Any]:
        result = {}
        for coords, cell in self.cell_contents.items():
            key = (self.name(), coordinates_to_location(coords))
            result[key] = cell.value()
        return result

    def rename_sheet(self, old: str, new: str):
        if self.name().lower() == old.lower():
            self._name = new
        for cell in self.cell_contents.values():
            cell.rename_sheet(old, new)

    def copy_sheet(self, other: 'Spreadsheet'):
        for coord, cell in other.cell_contents.items():
            self.set_cell_contents(
                coordinates_to_location(coord),
                cell.contents())

    def copy_cells(self, start_location: str, end_location: str) -> SheetRange:
        start_coord = location_to_coordinates(start_location)
        end_coord = location_to_coordinates(end_location)
        min_coord = (min(start_coord[0], end_coord[0]), min(start_coord[1], end_coord[1]))
        max_coord = (max(start_coord[0], end_coord[0]), max(start_coord[1], end_coord[1]))
        cells = {}
        for coord, cell in self.cell_contents.copy().items():
            if in_range(coord, min_coord, max_coord):
                cells[coord] = Contents(cell.contents(), cell.tree())
        return SheetRange(min_coord, cells)

    def cut_cells(self, start_location: str, end_location: str) -> SheetRange:
        result = self.copy_cells(start_location, end_location)
        for key in result.cells().keys():
            self.cell_contents.pop(key)
        return result

    def paste_cells(self, to_location: str, cells: SheetRange):
        origin = location_to_coordinates(to_location)
        translated = cells.translated(origin)
        for coord, contents in translated.items():
            reference = (self.name().lower(), coordinates_to_location(coord).upper())
            self.cell_contents[coord] = Cell(reference, contents, self._get_cell_value)

    def get_cell_value(self, location: str) -> Any:
        # Return the evaluated value of the specified cell on the specified
        # sheet.
        #
        # he cell location can be specified in any case. If the cell location
        # is invalid, a ValueError is raised.
        #
        # The value of empty cells is None.  Non-empty cells may contain a
        # value of str, decimal.Decimal, or CellError.
        #
        # Decimal values will not have trailing zeros to the right of any
        # decimal place, and will not include a decimal place if the value is a
        # whole number.  For example, this function would not return
        # Decimal('1.000'); rather it would return Decimal('1').
        cell_coordinates = location_to_coordinates(location)

        if cell_coordinates not in self.cell_contents:
            return None
        cell = self.cell_contents[cell_coordinates]
        cell_value = cell.value()
        return cell_value

    def save_spreadsheet(self) -> Dict[str, str]:
        # Return a diction of sheet name and cell contents in a format read for
        # JSON export

        result = {}
        cell_cont = {}

        for coords, cell in self.cell_contents.items():
            key = coordinates_to_location(coords)
            cell_cont[key] = cell.contents()

        result = {"name": self.name(), "cell-contents": cell_cont}

        return result

    def sort_region(self, start_location: str, end_location: str, sort_cols: List[int]) -> None:
        loc_lst = cell_range_to_list(start_location + ':' + end_location)
        loc_mat = location_list_to_matrix(loc_lst)
        sort_key = []
        for col in sort_cols:
            loc_col = loc_mat[col]
            value_col = [self.get_cell_value(l) for l in loc_col]
            sort_key.append(value_col)
        # ind = np.lexsort(sort_key)
        # new_loc_mat = loc_mat.T[ind].T
        
