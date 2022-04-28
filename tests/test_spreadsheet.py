import unittest
from sheets import spreadsheet
from sheets.spreadsheet import Spreadsheet

class TestSpreadsheet(unittest.TestCase):

    def test_name(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)
        self.assertEqual(s.name(), "Test")
        
    def test_extent(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)
        s.set_cell_contents("A1", "5")
        s.set_cell_contents("B2", "10")
        (c, r) = s.extent()
        self.assertEqual(r, 2)
        self.assertEqual(c, 2)

        s.set_cell_contents("F4", "1")
        (c, r) = s.extent()
        self.assertEqual(r, 4)
        self.assertEqual(c, 6)

        s.set_cell_contents("F4", "     ")
        (c,r) = s.extent()
        self.assertEqual(c, 2)
        self.assertEqual(r, 2)

        s.set_cell_contents("B2","  ")
        (c,r) = s.extent()
        self.assertEqual(c,1)
        self.assertEqual(r,1)

        s.set_cell_contents("A1","   ")
        (c,r) = s.extent()
        self.assertEqual(c,0)
        self.assertEqual(r,0)

        s.set_cell_contents("D14","5")
        (c,r) = s.extent()
        self.assertEqual(c, 4)
        self.assertEqual(r,14)
        

    def test_set_cell_contents(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)
        


    def test_get_cell_contents(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)

        s.set_cell_contents("A1", "5")
        cont = s.get_cell_contents("A1")
        self.assertEqual(cont, "5")

        s.set_cell_contents("ZZ24", "Hello")
        cont = s.get_cell_contents("ZZ24")
        self.assertEqual(cont, "Hello")
        

    def test_get_cell_value(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)


    def test_save_spreadsheet(self):
        get_cell_value = lambda sheet, location: None
        s = Spreadsheet("Test", get_cell_value)

        s.set_cell_contents("A1", "'123")
        s.set_cell_contents("B1", "5.3")
        s.set_cell_contents("C1", "=A1*B1")

        cont = s.save_spreadsheet()
        self.assertEqual(cont, {"name":"Test", "cell-contents":{"A1":"'123","B1":"5.3","C1":"=A1*B1"}})