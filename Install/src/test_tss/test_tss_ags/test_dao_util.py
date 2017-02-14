import unittest
import src.tss.ags.dao_util as dao_util
import mock


class DaoUtilTestCase(unittest.TestCase):

    def setUp(self):
        import os
        test_gdb = r"..\data\test.gdb"
        self.table = os.path.join(test_gdb, "test_table")
        self.temp_table = os.path.join(test_gdb, "temp_table")

    @mock.patch('src.tss.ags.dao_util.arcpy')
    def test_clearWSLocks(self, mockarcpy):
        mockarcpy.Exists.return_value = True
        mockarcpy.Compact_management.return_value = True
        self.assertEqual(dao_util.clearWSLocks("workspace"), "Workspace (workspace) clear to continue...")
        mockarcpy.Exists.assert_called_with("workspace")
        mockarcpy.Compact_management.assert_called_with("workspace")

        mockarcpy.Exists.return_value = False
        self.assertEqual(dao_util.clearWSLocks("workspace"), "!!!!!!!! ERROR WITH WORKSPACE workspace !!!!!!!!")

    def test_build_numeric_in_sql_expression(self):
        self.assertEqual(dao_util.build_numeric_in_sql_expression("field", [1, 2, 3, 4]), "field in (1,2,3,4)")
        self.assertEqual(dao_util.build_numeric_in_sql_expression("field", []), "1=2")

    def test_build_string_in_sql_expression(self):
        self.assertEqual(dao_util.build_string_in_sql_expression("field", ["a", "b", "c", "d"]), "field in ('a','b','c','d')")
        self.assertEqual(dao_util.build_string_in_sql_expression("field", []), "1=2")

    def test_subset_data_exist(self):
        self.assertEqual(dao_util.subset_data_exist(self.table, "1=1"), True)
        self.assertEqual(dao_util.subset_data_exist(self.table, "1=2"), False)
        self.assertEqual(dao_util.subset_data_exist(self.table, "TextField='a'"), True)
        self.assertEqual(dao_util.subset_data_exist(self.table, "TextField='e'"), False)

    def test_delete_subset_data(self):
        import datetime
        import arcpy
        arcpy.env.overwriteOutput = True
        arcpy.CopyRows_management(self.table, self.temp_table)
        self.assertEqual(int(arcpy.GetCount_management(self.table).getOutput(0)), 4)
        with arcpy.da.InsertCursor(self.temp_table, ["TextField", "NumberField", "DateField"]) as iCursor:
            iCursor.insertRow(("x", 999, datetime.datetime(2010, 10, 4)))
        self.assertEqual(int(arcpy.GetCount_management(self.temp_table).getOutput(0)), 5)
        dao_util.delete_subset_data(self.temp_table, "TextField='x'")
        self.assertEqual(int(arcpy.GetCount_management(self.temp_table).getOutput(0)), 4)
        self.assertFalse(dao_util.subset_data_exist(self.temp_table, "TextField='x'"))

    def test_delete_identical_only_keep_min_oid(self):
        import datetime
        import arcpy
        arcpy.env.overwriteOutput = True
        arcpy.CopyRows_management(self.table, self.temp_table)
        self.assertEqual(int(arcpy.GetCount_management(self.table).getOutput(0)), 4)
        with arcpy.da.InsertCursor(self.temp_table, ["TextField", "NumberField", "DateField"]) as iCursor:
            iCursor.insertRow(("d", 999, datetime.datetime(2010, 10, 4)))
        self.assertEqual(int(arcpy.GetCount_management(self.temp_table).getOutput(0)), 5)
        dao_util.delete_identical_only_keep_min_oid(self.temp_table, "TextField")
        self.assertEqual(int(arcpy.GetCount_management(self.temp_table).getOutput(0)), 4)
        self.assertFalse(dao_util.subset_data_exist(self.temp_table, "NumberField=999"))

    def test_get_count(self):
        self.assertEqual(dao_util.get_count(self.table), 4)

if __name__ == '__main__':
    unittest.main()
