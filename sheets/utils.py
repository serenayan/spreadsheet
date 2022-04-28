import re
import decimal
from typing import Optional, Any, Tuple, Union
from enum import IntEnum

from sheets.cell_error import CellError, CellErrorType


class CellValueType(IntEnum):
    NONE = 0
    NUMBER = 1
    STRING = 2
    BOOL = 3

def cell_value_type(v: Any) -> CellValueType:
    if v is None:
        return CellValueType.NONE
    if isinstance(v, decimal.Decimal):
        return CellValueType.NUMBER
    if isinstance(v, str):
        return CellValueType.STRING
    if isinstance(v, bool):
        return CellValueType.BOOL
    raise ValueError("unreachable")

def zero_value(t: CellValueType) -> Any:
    return [None, decimal.Decimal(0), "", False][t]

def absolute_location_to_location(loc: str) -> str:
    '''
    Strip absolute modifiers out of the given location ande return the result.

    Args:
        loc: the absolute location.

    Returns:
        The equivalent location without absolute modifiers. For example, given the
        absolute location `$D$4`, this function would return `D4`.
    '''
    return loc.replace("$","")

def get_sheet_name(tree) -> str:
    sheet = str(tree.children[0])
    if tree.children[0].type == 'QUOTED_SHEET_NAME':
        sheet = sheet[1:-1]
    return sheet

def is_valid_sheet_name(name: str) -> bool:
    if not isinstance(name, str):
        return False
    if name.strip() != name:
        return False
    return re.match(r"^[a-zA-Z0-9.?!,:;!@#$%^&*()-_ ]+$", name) is not None

def strip_trailing_zeros(d: decimal.Decimal):
    s = str(d)
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    return decimal.Decimal(s)


def convert_to_decimal(x: Any) -> Union[CellError, decimal.Decimal]:
    if x is None:
        return decimal.Decimal(0)
    if isinstance(x, (CellError, decimal.Decimal)):
        return x
    if isinstance(x, bool):
        return decimal.Decimal(1) if x else decimal.Decimal(0)
    if isinstance(x, str):
        try:
            return decimal.Decimal(x.strip())
        except decimal.InvalidOperation:
            return CellError(CellErrorType.TYPE_ERROR,
                "A value of the wrong type was encountered during evaluation.")
    return CellError(CellErrorType.TYPE_ERROR,
        "A value of the wrong type was encountered during evaluation.")


def string_to_error(s: str) -> Optional[CellError]:
    # Attempt to parse the string as an error.
    errors = {
        "#ERROR!": CellError(
            CellErrorType.PARSE_ERROR,
            "A formula doesn't parse successfully."),
        "#CIRCREF!": CellError(
            CellErrorType.CIRCULAR_REFERENCE,
            "A cell is part of a circular reference."),
        "#REF!": CellError(
            CellErrorType.BAD_REFERENCE,
            "A cell-reference is invalid in some way."),
        "#NAME?": CellError(
            CellErrorType.BAD_NAME,
            "Unrecognized function name."),
        "#VALUE!": CellError(
            CellErrorType.TYPE_ERROR,
            "A value of the wrong type was encountered during evaluation."),
        "#DIV/0!": CellError(
            CellErrorType.DIVIDE_BY_ZERO,
            "A divide-by-zero was encountered during evaluation."),
    }
    if s.upper() in errors:
        return errors[s.upper()]
    return None

def convert_to_bool(x: Any) -> Union[CellError, bool]:
    if x is None:
        return False
    if isinstance(x, (bool, CellError)):
        return x
    if isinstance(x, str):
        if x.lower() == "true":
            return True
        if x.lower() == "false":
            return False
        return CellError(CellErrorType.TYPE_ERROR, "failed to convert string to bool")
    if isinstance(x, decimal.Decimal):
        return not x.is_zero()
    raise ValueError("unreachable")

def convert_to_str(x: Any) -> Optional[str]:
    if x is None:
        return ""
    if isinstance(x, bool):
        return "TRUE" if x else "FALSE"
    if isinstance(x, decimal.Decimal):
        return str(strip_trailing_zeros(x))
    return str(x)


def column_to_number(col: str) -> int:
    # This function converts column values like "AA" to integer values

    col = col[::-1]  # Reverse order of characters
    column_as_int = 0

    for i, c in enumerate(col):
        column_as_int += (ord(c) - ord('A') + 1) * 26**(i)

    return column_as_int


def number_to_column(col: int) -> str:
    column_as_char = ''

    while True:
        col = col - 1
        mod = col % 26
        column_as_char += (chr(mod + ord("A")))
        if col < 26:
            break
        col = col // 26
    column_as_char = column_as_char[::-1]
    return column_as_char

def in_range(coord: Tuple[int, int], start: Tuple[int, int], end: Tuple[int, int]):
    return start[0] <= coord[0] and coord[0] <= end[0] \
       and start[1] <= coord[1] and coord[1] <= end[1]

def location_to_coordinates(location: str) -> Tuple[int, int]:
    ''' This function takes in a location string (like "A1" or "ZZ44") and returns a tuple containg
    the coordinates in integers
    '''
    location = location.upper()

    if re.match(r"^[A-Z]{1,4}[1-9][0-9]{0,3}$", location) is None:
        raise ValueError("Invalid cell location.")

    splitat = 1
    for i in range(len(location)):
        if location[i + 1].isdigit() is False:
            splitat += 1
        else:
            break

    column_index, row_index = location[:splitat], location[splitat:]

    # Convert Both Row and Colum indexes to integers
    row_index = int(row_index)
    column_index = column_to_number(column_index)

    coordinate_tuple = (column_index, row_index)

    return coordinate_tuple


def coordinates_to_location(coordinates: Tuple[int, int]) -> str:
    (col, row) = coordinates
    if col <= 0 or row <= 0:
        raise ValueError("invalid cell coordinates")
    return f"{number_to_column(col)}{row}"

def translate_cell_ref(cell_ref: str, offset: Tuple[int, int]):
    match = re.match(r"(\$?)([A-Za-z]+)(\$?)([1-9][0-9]*)", cell_ref)
    lock_col = len(match.group(1)) > 0
    col = column_to_number(match.group(2)) + (0 if lock_col else offset[0])
    lock_row = len(match.group(3)) > 0
    row = int(match.group(4)) + (0 if lock_row else offset[1])
    if 0 >= col or col > 9999 or 0 >= row or row > 9999:
        return "#REF!"
    return f"{'?' if lock_col else ''}{number_to_column(col)}{'?' if lock_row else ''}{row}"


def cell_range_to_list(cell_range: str):
    #Converts a range of cells to a list of cells
    
    # Parse range input and return False in not a range
    splitat = cell_range.find(":")
    if splitat == -1:
        return False

    splitat2 = splitat+1
    loc1, loc2 = cell_range[:splitat], cell_range[splitat2:]

    #Convert to coordinates
    coord1 = location_to_coordinates(loc1)
    coord2 = location_to_coordinates(loc2)

    #Generate cell list
    list_cells = []
    #initial = ((min(coord1[0], coord2[0])), min(coord1[1], coord2[1]))
    #list_cells.append(coordinates_to_location(initial))
    for i in  range(min(coord1[0], coord2[0]), max(coord1[0], coord2[0])+1):
        for ii in range(min(coord1[1], coord2[1]), max(coord1[1], coord2[1])+1):
            temp = coordinates_to_location((i,ii))
            list_cells.append(temp)

    #final = (max(coord1[0], coord2[0])), max(coord1[1], coord2[1])
    #list_cells.append(coordinates_to_location(final))
    return list_cells

def location_list_to_matrix(cells: list):
    mat = []
    last_col = -1
    for cell_loc in cells:
        coordinate = location_to_coordinates(cell_loc)
        if last_col != coordinate[0]:
            mat.append([])
            last_col = coordinate[0]
        mat[-1].append(coordinates_to_location(coordinate))
    return mat
    

 