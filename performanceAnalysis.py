from sheets import *
import cProfile
import pstats
from sheets import cell
from sheets.utils import *
import json
import io

def create_square_workbook_json(N: int):
    # This function creates a workbook with the following properties:
    # Each cell (1, X) is defined as 1.
    # Each cell (X, 1) is defined as 1.
    # All other cells (X, Y) are defined as (X+1, Y) + (X,Y+1)
    cell_contents = {}

    # Set contents of top row and left column
    for i in range(1, N + 1):
        location = coordinates_to_location((1, i))
        cell_contents[location] = "1"
        location = coordinates_to_location((i, 1))
        cell_contents[location] = "1"
    # Set contents of inner cells
    for i in range(2, N + 1):
        for j in range(2, N + 1):
            location = coordinates_to_location((1, i))
            top = coordinates_to_location((i, j - 1))
            left = coordinates_to_location((i - 1, j))
            cell_contents[location] = f'{top}+{left}'

    s = json.dumps({
        "sheets": [{
            "name": "Sheet1",
            "cell-contents": cell_contents
        }]
    })
    fp = io.StringIO(s)
    return fp

def test_load_workbook_speed():
    for i in range(100, 2000, 100):
        fp = create_square_workbook_json(i)
        w = Workbook.load_workbook(fp)

def test_copy_sheet_speed():
    fp = create_square_workbook_json(500)
    w = Workbook.load_workbook(fp)
    for i in range(10):
        (index, name1) = w.copy_sheet("Sheet1")

def test_rename_sheet_speed():
    fp = create_square_workbook_json(500)
    w = Workbook.load_workbook(fp)
    for i in range(500):
        if i%2==0:
            w.rename_sheet("Sheet1", "Sheet2")
        else:
            w.rename_sheet("Sheet2", "Sheet1")

def test_move_cells_speed():
    fp = create_square_workbook_json(500)
    w = Workbook.load_workbook(fp)
    for i in range(500, 0, -1):
        start = coordinates_to_location((i, 1))
        end = coordinates_to_location((i, 500))
        new_start = coordinates_to_location((i+1, 1))
        w.move_cells("Sheet1", start, end, new_start)

def test_copy_cells_speed():
    fp = create_square_workbook_json(500)
    w = Workbook.load_workbook(fp)
    for i in range(500, 0, -1):
        start = coordinates_to_location((i, 1))
        end = coordinates_to_location((i, 500))
        new_start = coordinates_to_location((i+1, 1))
        w.copy_cells("Sheet1", start, end, new_start)    


if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.enable()

    # test_load_workbook_speed()

    test_copy_sheet_speed() # this is really slow

    # test_rename_sheet_speed()

    # test_move_cells_speed()

    # test_copy_cells_speed()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()
