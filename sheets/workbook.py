
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, TextIO, Tuple
import json

from .spreadsheet import Spreadsheet
from .utils import is_valid_sheet_name
from .graph import Graph
from .cell import CellReference

NotifyFunction = Callable[['Workbook', Iterable[CellReference]], None]


class UpdateContext:
    # UpdateContext is intended to wrap all cell value update
    # operations to ensure that the proper methods are called in the
    # right order every time any cell value may be changed.
    #
    # with UpdateContext(self):
    #   // execute update
    #
    # Before the update is executed, this object saves a 'flattened'
    # version of the Workbook. After the update is executed, this object
    # recomputes all values and saves another 'flattened' version of
    # the workbook. Finally, this object triggers a notification for
    # all cells whose value was changed as part of the update.
    def __init__(self, workbook: 'Workbook', updated: Optional[List[CellReference]] = None):
        self.workbook = workbook
        self.updated = updated
        self.prev = {}
        self.curr = {}

    def __enter__(self):
        # This method is called before the contents of the 'with' block.
        # All we do is save a flattened version of the workbook.
        self.prev = self.workbook.snapshot_flat()

    def __exit__(self, _type, _value, _traceback):
        # This method is called after the contents of the 'with' block.
        # Here, we recompute all values in the workbook, flatten the
        # workbook, and used the `prev` and `curr` values to call all
        # notify functions with all changed values.
        self.workbook._recompute_all_values(self.updated)
        self.curr = self.workbook.snapshot_flat()
        self.workbook._notify(self.prev, self.curr)


class Workbook:
    # A workbook containing zero or more named spreadsheets.
    #
    # Any and all operations on a workbook that may affect calculated cell
    # values should cause the workbook's contents to be updated properly.
    def __init__(self):
        # Initialize a new empty workbook.
        self.spreadsheets: List[Spreadsheet] = []
        self.notify_functions: List[NotifyFunction] = []
        self.count: int = 0

    def num_sheets(self) -> int:
        # Return the number of spreadsheets in the workbook.
        return len(self.spreadsheets)

    @classmethod
    def load_workbook(cls, fp: TextIO) -> 'Workbook':
        # This is a static method (not an instance method) to load a workbook
        # from a text file or file-like object in JSON format, and return the
        # new Workbook instance.  Note that the _caller_ of this function is
        # expected to have opened the file; this function merely reads the file.
        #
        # If the contents of the input cannot be parsed by the Python json
        # module then a json.JSONDecodeError should be raised by the method.
        # (Just let the json module's exceptions propagate through.)  Similarly,
        # if an IO read error occurs (unlikely but possible), let any raised
        # exception propagate through.
        #
        # If any expected value in the input JSON is missing (e.g. a sheet
        # object doesn't have the "cell-contents" key), raise a KeyError with
        # a suitably descriptive message.
        #
        # If any expected value in the input JSON is not of the proper type
        # (e.g. an object instead of a list, or a number instead of a string),
        # raise a TypeError with a suitably descriptive message.
        workbook = json.loads(fp.read())

        if not isinstance(workbook, dict):
            raise TypeError("dictionary does not exists")

        if "sheets" not in workbook:
            raise KeyError("Missing 'sheets' key in file")

        sheets = workbook["sheets"]

        if not isinstance(sheets, list):
            raise TypeError("sheets is not a list")

        new_workbook = Workbook()

        with UpdateContext(new_workbook):
            for sheet in sheets:

                if not isinstance(sheet["name"], str):
                    raise TypeError("Sheets key is invalid data type")

                if not isinstance(sheet["cell-contents"], dict):
                    raise TypeError("cell-contents key is invalid data type")

                new_workbook.new_sheet(sheet["name"])
                cell_contents = sheet["cell-contents"]

                for location in cell_contents:
                    if not isinstance(location, str):
                        raise TypeError("Invalid cell location data type")

                    if not isinstance(cell_contents[location], str):
                        raise TypeError("Invalid cell contents data type")

                    new_workbook._get_sheet(
                        sheet["name"]).set_cell_contents(
                        location, cell_contents[location])

        return new_workbook

    def save_workbook(self, fp: TextIO) -> None:
        # Instance method (not a static/class method) to save a workbook to a
        # text file or file-like object in JSON format.  Note that the _caller_
        # of this function is expected to have opened the file; this function
        # merely writes the file.
        #
        # If an IO write error occurs (unlikely but possible), let any raised
        # exception propagate through.
        saved_sheets = []
        result = {}

        for sheet in self.spreadsheets:
            saved_sheets.append(sheet.save_spreadsheet())

        result = {"sheets": saved_sheets}

        workbook = json.dumps(result)

        fp.write(workbook)

    # pylint: disable=too-many-arguments
    def move_cells(self, sheet_name: str, start_location: str,
            end_location: str, to_location: str, to_sheet: Optional[str] = None) -> None:
        # Move cells from one location to another, possibly moving them to
        # another sheet.  All formulas in the area being moved will also have
        # all relative and mixed cell-references updated by the relative
        # distance each formula is being copied.
        #
        # Cells in the source area (that are not also in the target area) will
        # become empty due to the move operation.
        #
        # The start_location and end_location specify the corners of an area of
        # cells in the sheet to be moved.  The to_location specifies the
        # top-left corner of the target area to move the cells to.
        #
        # Both corners are included in the area being moved; for example,
        # copying cells A1-A3 to B1 would be done by passing
        # start_location="A1", end_location="A3", and to_location="B1".
        #
        # The start_location value does not necessarily have to be the top left
        # corner of the area to move, nor does the end_location value have to be
        # the bottom right corner of the area; they are simply two corners of
        # the area to move.
        #
        # This function works correctly even when the destination area overlaps
        # the source area.
        #
        # The sheet name matches are case-insensitive; the text must match but
        # the case does not have to.
        #
        # If to_sheet is None then the cells are being moved to another
        # location within the source sheet.
        #
        # If any specified sheet name is not found, a KeyError is raised.
        # If any cell location is invalid, a ValueError is raised.
        #
        # If the target area would extend outside the valid area of the
        # spreadsheet (i.e. beyond cell ZZZZ9999), a ValueError is raised, and
        # no changes are made to the spreadsheet.
        #
        # If a formula being moved contains a relative or mixed cell-reference
        # that will become invalid after updating the cell-reference, then the
        # cell-reference is replaced with a #REF! error-literal in the formula.
        with UpdateContext(self):
            src_sheet = self._get_sheet(sheet_name)
            cells = src_sheet.cut_cells(start_location, end_location)
            dst_sheet = self._get_sheet(to_sheet or sheet_name)
            dst_sheet.paste_cells(to_location, cells)

    # pylint: disable=too-many-arguments
    def copy_cells(self, sheet_name: str, start_location: str,
            end_location: str, to_location: str, to_sheet: Optional[str] = None) -> None:
        # Copy cells from one location to another, possibly copying them to
        # another sheet.  All formulas in the area being copied will also have
        # all relative and mixed cell-references updated by the relative
        # distance each formula is being copied.
        #
        # Cells in the source area (that are not also in the target area) are
        # left unchanged by the copy operation.
        #
        # The start_location and end_location specify the corners of an area of
        # cells in the sheet to be copied.  The to_location specifies the
        # top-left corner of the target area to copy the cells to.
        #
        # Both corners are included in the area being copied; for example,
        # copying cells A1-A3 to B1 would be done by passing
        # start_location="A1", end_location="A3", and to_location="B1".
        #
        # The start_location value does not necessarily have to be the top left
        # corner of the area to copy, nor does the end_location value have to be
        # the bottom right corner of the area; they are simply two corners of
        # the area to copy.
        #
        # This function works correctly even when the destination area overlaps
        # the source area.
        #
        # The sheet name matches are case-insensitive; the text must match but
        # the case does not have to.
        #
        # If to_sheet is None then the cells are being copied to another
        # location within the source sheet.
        #
        # If any specified sheet name is not found, a KeyError is raised.
        # If any cell location is invalid, a ValueError is raised.
        #
        # If the target area would extend outside the valid area of the
        # spreadsheet (i.e. beyond cell ZZZZ9999), a ValueError is raised, and
        # no changes are made to the spreadsheet.
        #
        # If a formula being copied contains a relative or mixed cell-reference
        # that will become invalid after updating the cell-reference, then the
        # cell-reference is replaced with a #REF! error-literal in the formula.
        with UpdateContext(self):
            src_sheet = self._get_sheet(sheet_name)
            cells = src_sheet.copy_cells(start_location, end_location)
            dst_sheet = self._get_sheet(to_sheet or sheet_name)
            dst_sheet.paste_cells(to_location, cells)

    def notify_cells_changed(self, notify_function: NotifyFunction) -> None:
        # Request that all changes to cell values in the workbook are reported
        # to the specified notify_function.  The values passed to the notify
        # function are the workbook, and an iterable of 2-tuples of strings,
        # of the form ([sheet name], [cell location]).  The notify_function is
        # expected not to return any value; any return-value will be ignored.
        #
        # Multiple notification functions may be registered on the workbook;
        # functions will be called in the order that they are registered.
        #
        # A given notification function may be registered more than once; it
        # will receive each notification as many times as it was registered.
        #
        # If the notify_function raises an exception while handling a
        # notification, this will not affect workbook calculation updates or
        # calls to other notification functions.
        #
        # A notification function is expected to not mutate the workbook or
        # iterable that it is passed to it.  If a notification function violates
        # this requirement, the behavior is undefined.
        self.notify_functions.append(notify_function)

    def rename_sheet(self, sheet_name: str, new_sheet_name: str) -> None:
        # Rename the specified sheet to the new sheet name.  Additionally, all
        # cell formulas that referenced the original sheet name are updated to
        # reference the new sheet name (using the same case as the new sheet
        # name, and single-quotes iff [if and only if] necessary).
        #
        # The sheet_name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # As with new_sheet(), the case of the new_sheet_name is preserved by
        # the workbook.
        #
        # If the sheet_name is not found, a KeyError is raised.
        #
        # If the new_sheet_name is an empty string or is otherwise invalid, a
        # ValueError is raised.
        if not is_valid_sheet_name(new_sheet_name):
            raise ValueError("The new sheet name is invalid.")
        if self._get_sheet_index(sheet_name) is None:
            raise KeyError(
                f"A sheet with the name \"{sheet_name}\" does not exist")
        if self._get_sheet_index(new_sheet_name) is not None:
            raise ValueError(
                "A spreadsheet with the name \"{new_sheet_name}\" already exists.")

        with UpdateContext(self):
            for sheet in self.spreadsheets:
                sheet.rename_sheet(sheet_name, new_sheet_name)

    def move_sheet(self, sheet_name: str, index: int) -> None:
        # Move the specified sheet to the specified index in the workbook's
        # ordered sequence of sheets.  The index can range from 0 to
        # workbook.num_sheets() - 1.  The index is interpreted as if the
        # specified sheet were removed from the list of sheets, and then
        # re-inserted at the specified index.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        #
        # If the index is outside the valid range, an IndexError is raised.
        current_index = self._get_sheet_index(sheet_name)
        if current_index is None:
            raise KeyError("move_sheet: specified sheet name is not found")
        if index >= self.num_sheets():
            raise IndexError("index is outside the valid range")

        # Remove the spreadsheet at the current_index and insert it at the
        # given index.
        self.spreadsheets.insert(index, self.spreadsheets.pop(current_index))

    def copy_sheet(self, sheet_name: str) -> Tuple[int, str]:
        # Make a copy of the specified sheet, storing the copy at the end of the
        # workbook's sequence of sheets.  The copy's name is generated by
        # appending "_1", "_2", ... to the original sheet's name (preserving the
        # original sheet name's case), incrementing the number until a unique
        # name is found.  As usual, "uniqueness" is determined in a
        # case-insensitive manner.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # The copy should be added to the end of the sequence of sheets in the
        # workbook.  Like new_sheet(), this function returns a tuple with two
        # elements:  (0-based index of copy in workbook, copy sheet name).  This
        # allows the function to report the new sheet's name and index in the
        # sequence of sheets.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        current_index = self._get_sheet_index(sheet_name)
        if current_index is None:
            raise KeyError("copy_sheet: specified sheet name is not found")

        copy_name = sheet_name + '_1'
        index = self._get_sheet_index(copy_name)
        count = 2
        while index is not None:
            copy_name = sheet_name + '_' + str(count)
            count += 1
            index = self._get_sheet_index(copy_name)

        (copy_index, copy_name) = self.new_sheet(copy_name)
        with UpdateContext(self):
            self._get_sheet(copy_name).copy_sheet(self._get_sheet(sheet_name))
        return (copy_index, copy_name)

    def build_dependency_graph(self) -> Graph:
        # Construct a directed graph in adjacency list form where each vertex
        # is a string representing a cell location and there is a directed edge
        # from each cell to the cells that the value of the cell depends on.
        # Note that cell with no dependencies are still part of the graph, but
        # they have an empty adjacency list.
        result = {}
        for sheet in self.spreadsheets:
            result.update(sheet.build_dependency_graph())
        return Graph[CellReference](result)

    def snapshot_flat(self) -> Dict[Tuple[str, str], Any]:
        # Return a 'flat' representation of the Workbook as a single dict
        # object.
        result = {}
        for sheet in self.spreadsheets:
            result.update(sheet.snapshot())
        return result

    def list_sheets(self) -> List[str]:
        # Return a list of the spreadsheet names in the workbook, with the
        # capitalization specified at creation, and in the order that the sheets
        # appear within the workbook.
        #
        # In this project, the sheet names appear in the order that the user
        # created them; later, when the user is able to move and copy sheets,
        # the ordering of the sheets in this function's result will also reflect
        # such operations.
        #
        # A user should be able to mutate the return-value without affecting the
        # workbook's internal state.
        return list(map(lambda s: s.name(), self.spreadsheets))

    def _notify(self, prev: Dict[CellReference, Any],
                curr: Dict[CellReference, Any]):
        # Given a dict of the previous value of all cells and a dict of the current
        # value of all cells, calls all registered notify_functions on any values
        # that differ between prev and current.
        #
        # Any keys found in `prev` but not `curr` are treated as a
        # Some -> None transition. Any key found in `curr` but not `prev` are
        # treated as a None -> Some transition. All values found in both `prev`
        # and `curr` are only treated as changes if the value differs between
        # `prev` and `curr`.
        #
        # This is a very naiive notification function, but it is trivially correct.
        # All optimizations should be performed by reducing the number of values
        # passed into this function.
        changed: Set[CellReference] = set()
        prev_key_set = set(prev.keys())
        curr_key_set = set(curr.keys())

        # Add all values that are in `prev` or `curr` but not both
        changed.update(prev_key_set.symmetric_difference(curr_key_set))

        # Add all values that differ between `prev` and `curr`.
        for key in prev_key_set.intersection(curr_key_set):
            if prev[key] != curr[key]:
                changed.add(key)

        # Call notify functions in the order they were registered and catch
        # and ignore all exceptions that occur.
        changed = list(changed)
        if len(changed) > 0:
            for notify_func in self.notify_functions:
                try:
                    notify_func(self, changed)
                # pylint: disable=broad-except
                except BaseException:
                    pass

    def new_sheet(self, sheet_name: Optional[str] = None) -> Tuple[int, str]:
        # Add a new sheet to the workbook.  If the sheet name is specified, it
        # must be unique.  If the sheet name is None, a unique sheet name is
        # generated.  "Uniqueness" is determined in a case-insensitive manner,
        # but the case specified for the sheet name is preserved.
        #
        # The function returns a tuple with two elements:
        # (0-based index of sheet in workbook, sheet name).  This allows the
        # function to report the sheet's name when it is auto-generated.
        #
        # If the spreadsheet name is an empty string (not None), or it is
        # otherwise invalid, a ValueError is raised.
        self.count += 1
        if sheet_name is None:
            sheet_name = f"Sheet{self.count}"
        else:
            if not is_valid_sheet_name(sheet_name):
                raise ValueError("The sheet name is invalid.")
            i = self._get_sheet_index(sheet_name)
            if i is not None:
                raise ValueError(
                    f"A sheet with the name \"{sheet_name}\" already exists.")

        # Create a new spreadsheet. Recompute cell values and notify registered
        # handlers about any changed values.
        with UpdateContext(self):
            self.spreadsheets.append(
                Spreadsheet(
                    sheet_name,
                    self.get_cell_value))

        index = len(self.spreadsheets) - 1
        return (index, sheet_name)

    def _get_sheet_index(self, sheet_name: str) -> Optional[int]:
        # Return the index of the sheet with the given sheet_name or None if no
        # such spreadsheet exists. Note that the sheet_name is
        # case-insensitive.
        for i, sheet in enumerate(self.spreadsheets):
            if sheet_name.lower() == sheet.name().lower():
                return i
        return None

    def _get_sheet(self, sheet_name: str) -> Spreadsheet:
        # Return the sheet with the given sheet_name or raises a KeyError if no
        # such spreadsheet exists. Note that the sheet_name is
        # case-insensitive.
        for sheet in self.spreadsheets:
            if sheet_name.lower() == sheet.name().lower():
                return sheet
        raise KeyError(
            f"A sheet with the name \"{sheet_name}\" does not exist")

    def del_sheet(self, sheet_name: str) -> None:
        # Delete the spreadsheet with the specified name.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        if self._get_sheet_index(sheet_name) is None:
            raise KeyError(
                f"A sheet with the name \"{sheet_name}\" does not exist")

        # Delete the spreadsheet with the given name. Recompute cell values
        # and notify registered handlers about any changed values.
        with UpdateContext(self):
            index = self._get_sheet_index(sheet_name.lower())
            del self.spreadsheets[index]

    def get_sheet_extent(self, sheet_name: str) -> Tuple[int, int]:
        # Return a tuple (num-cols, num-rows) indicating the current extent of
        # the specified spreadsheet.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        return self._get_sheet(sheet_name).extent()

    def set_cell_contents(self, sheet_name: str, location: str,
                          contents: Optional[str]) -> None:
        # Set the contents of the specified cell on the specified sheet.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.  Additionally, the cell location can be
        # specified in any case.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        # If the cell location is invalid, a ValueError is raised.
        #
        # A cell may be set to "empty" by specifying a contents of None.
        #
        # Leading and trailing whitespace are removed from the contents before
        # storing them in the cell.  Storing a zero-length string "" (or a
        # string composed entirely of whitespace) is equivalent to setting the
        # cell contents to None.
        #
        # If the cell contents appear to be a formula, and the formula is
        # invalid for some reason, this method does not raise an exception;
        # rather, the cell's value will be a CellError object indicating the
        # naure of the issue.
        reference = (sheet_name.lower(), location.upper())
        with UpdateContext(self, updated=[reference]):
            self._get_sheet(sheet_name).set_cell_contents(location, contents)

    def _recompute_all_values(self, updated: Optional[List[CellReference]]):

        # Compute all strongly connected components and mark all cells in a
        # component with more than 1 vertex as cyclical.
        g = self.build_dependency_graph().transpose()
        if updated is not None:
            g = g.reachable(updated)
        components = g.strongly_connected_components()
        cyclical = []
        non_cyclical = []
        for component in components:
            if len(component) == 1:
                for reference in component:
                    non_cyclical.append(reference)
            else:
                for reference in component:
                    cyclical.append(reference)

        for reference in cyclical:
            self.__mark_cyclical(*reference)

        # compute a subgraph containing all vertices not part of a
        # strong connected component. This subgraph is a DAG. Sort the
        # vertices in topological order and recompute the value of all cells
        # in topological order.
        g2 = g.subgraph(non_cyclical)
        update_order = g2.topological_sort()
        for reference in update_order:
            sheet, loc = reference
            try:
                if self._get_sheet(sheet).get_cell(loc):
                    self._get_sheet(sheet).get_cell(loc).recompute_value()
            except KeyError:
                pass
        # if (reference == modified_cell):
        #   break

    def __mark_cyclical(self, sheet_name: str, location: str) -> None:
        self._get_sheet(sheet_name).mark_cyclical(location)

    def get_cell_contents(
            self,
            sheet_name: str,
            location: str) -> Optional[str]:
        # Return the contents of the specified cell on the specified sheet.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.  Additionally, the cell location can be
        # specified in any case.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        # If the cell location is invalid, a ValueError is raised.
        #
        # Any string returned by this function will not have leading or trailing
        # whitespace, as this whitespace will have been stripped off by the
        # set_cell_contents() function.
        #
        # This method will never return a zero-length string; instead, empty
        # cells are indicated by a value of None.
        return self._get_sheet(sheet_name).get_cell_contents(location)

    def get_cell_value(self, sheet_name: str, location: str) -> Any:
        # Return the evaluated value of the specified cell on the specified
        # sheet.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.  Additionally, the cell location can be
        # specified in any case.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        # If the cell location is invalid, a ValueError is raised.
        #
        # The value of empty cells is None.  Non-empty cells may contain a
        # value of str, decimal.Decimal, or CellError.
        #
        # Decimal values will not have trailing zeros to the right of any
        # decimal place, and will not include a decimal place if the value is a
        # whole number.  For example, this function would not return
        # Decimal('1.000'); rather it would return Decimal('1').
        return self._get_sheet(sheet_name).get_cell_value(location)

    def sort_region(self, sheet_name: str, start_location: str, end_location: str, sort_cols: List[int]):
        # Sort the specified region of a spreadsheet with a stable sort, using
        # the specified columns for the comparison.
        #
        # The sheet name match is case-insensitive; the text must match but the
        # case does not have to.
        #
        # The start_location and end_location specify the corners of an area of
        # cells in the sheet to be sorted.  Both corners are included in the
        # area being sorted; for example, sorting the region including cells B3
        # to J12 would be done by specifying start_location="B3" and
        # end_location="J12".
        #
        # The start_location value does not necessarily have to be the top left
        # corner of the area to sort, nor does the end_location value have to be
        # the bottom right corner of the area; they are simply two corners of
        # the area to sort.
        #
        # The sort_cols argument specifies one or more columns to sort on.  Each
        # element in the list is the one-based index of a column in the region,
        # with 1 being the leftmost column in the region.  A column's index in
        # this list may be positive to sort in ascending order, or negative to
        # sort in descending order.  For example, to sort the region B3..J12 on
        # the first two columns, but with the second column in descending order,
        # one would specify sort_cols=[1, -2].
        #
        # The sorting implementation is a stable sort:  if two rows compare as
        # "equal" based on the sorting columns, then they will appear in the
        # final result in the same order as they are at the start.
        #
        # If multiple columns are specified, the behavior is as one would
        # expect:  the rows are ordered on the first column indicated in
        # sort_cols; when multiple rows have the same value for the first
        # column, they are then ordered on the second column indicated in
        # sort_cols; and so forth.
        #
        # No column may be specified twice in sort_cols; e.g. [1, 2, 1] or
        # [2, -2] are both invalid specifications.
        #
        # The sort_cols list may not be empty.  No index may be 0, or refer
        # beyond the right side of the region to be sorted.
        #
        # If the specified sheet name is not found, a KeyError is raised.
        # If any cell location is invalid, a ValueError is raised.
        # If the sort_cols list is invalid in any way, a ValueError is raised.
        with UpdateContext(self):
            self._get_sheet(sheet_name).sort_region(start_location, end_location, sort_cols)
