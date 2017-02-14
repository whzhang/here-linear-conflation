import unittest
import src.tss.ags.fieldvalue_util as fieldvalue_util


class FieldValueUtilTestCase(unittest.TestCase):

    def setUp(self):
        import os
        test_gdb = r"..\data\test.gdb"
        self.table = os.path.join(test_gdb, "test_table")
        self.temp_table = os.path.join(test_gdb, "temp_table")

    def test_get_maximum_id(self):
        self.assertEqual(fieldvalue_util.get_maximum_id(self.table, "OBJECTID"), 4)

    def test_get_minimum_value(self):
        self.assertEqual(fieldvalue_util.get_minimum_value(self.table, "NumberField", "NumberField > 2"), 3)

    def test_populate_auto_increment_id(self):
        import arcpy
        arcpy.env.overwriteOutput = True
        arcpy.CopyRows_management(self.table, self.temp_table)
        with arcpy.da.InsertCursor(self.temp_table, ["TextField"]) as iCursor:
            iCursor.insertRow(("x",))
            iCursor.insertRow(("y",))
            iCursor.insertRow(("z",))
        fieldvalue_util.populate_auto_increment_id(self.temp_table, "NumberField", existing_max_id=4)
        self.assertEqual(fieldvalue_util.get_maximum_id(self.temp_table, "NumberField"), 7)

if __name__ == '__main__':
    unittest.main()
