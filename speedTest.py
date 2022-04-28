from sheets import *
import cProfile
import pstats
from sheets import cell
from sheets.utils import *
import json
import io


def workbook_from_json(w):
    s = json.dumps(w)
    fp = io.StringIO(s)
    return Workbook.load_workbook(fp)


def create_square_workbook():
    # This function creates a workbook with the following properties:
    # Each cell (1, X) is defined as 1.
    # Each cell (X, 1) is defined as 1.
    # All other cells (X, Y) are defined as (X+1, Y) + (X,Y+1)
    N = 100
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
    return workbook_from_json({
        "sheets": [{
            "name": "Sheet1",
            "cell-contents": cell_contents
        }]
    })


def test_workbook_speed_refA1():
    w = Workbook()
    w.new_sheet("Sheet1")
    M = 100
    N = 100
    for i in range(1, M + 1):
        for ii in range(1, N + 1):
            w.set_cell_contents(
                "Sheet1", coordinates_to_location(
                    (i, ii)), "=A1 + 1")
    w.set_cell_contents("Sheet1", "A1", "1")
    w.set_cell_contents("Sheet1", "A1", "2")


def test_workbook_speed_ref_col1():
    w = Workbook()
    w.new_sheet("Sheet1")
    M = 20
    N = 20
    for i in range(1, M + 1):
        for ii in range(1, N + 1):
            temp = "=" + "A" + str(ii) + "+1"
            w.set_cell_contents(
                "Sheet1", coordinates_to_location(
                    (i, ii)), temp)
    w.set_cell_contents("Sheet1", "A1", "1")
    w.set_cell_contents("Sheet1", "A1", "2")


def test_update_speed_A1():
    w = Workbook()
    w.new_sheet("Sheet1")
    M = 100
    N = 1
    for i in range(2, M + 1):
        for ii in range(1, N + 1):
            col = number_to_column(i - 1)
            temp = "=" + col + str(ii) + "+1"
            w.set_cell_contents(
                "Sheet1", coordinates_to_location(
                    (i, ii)), temp)
    w.set_cell_contents("Sheet1", "A1", "1")

    profiler = cProfile.Profile()
    profiler.enable()
    w.set_cell_contents("Sheet1", "A1", "2")
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    print(w.get_cell_value("Sheet1", "B1"))
    stats.print_stats()


def test_update_speed_col1():
    w = Workbook()
    w.new_sheet("Sheet1")

    M = 5
    N = 5

    for i in range(1, M + 1):
        for ii in range(1, N + 1):
            if i == 1:
                temp2 = "A" + str(ii)
                w.set_cell_contents("Sheet1", temp2, "1")
            else:
                col = number_to_column(i - 1)
                temp = "=" + col + str(ii) + "+1"
                w.set_cell_contents(
                    "Sheet1", coordinates_to_location(
                        (i, ii)), temp)

    profiler = cProfile.Profile()
    profiler.enable()
    w.set_cell_contents("Sheet1", "A1", "2")
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    print(w.get_cell_value("Sheet1", "B1"))
    stats.print_stats()


if __name__ == '__main__':
    # create_square_workbook()
    profiler = cProfile.Profile()
    profiler.enable()
    test_workbook_speed_ref_col1()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats()
