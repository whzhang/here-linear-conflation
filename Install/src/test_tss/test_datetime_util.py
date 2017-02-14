import unittest
from datetime import datetime
import src.tss.datetime_util as datetime_util
import mock

class DatetimeUtilTestCase(unittest.TestCase):

    def test_truncate_date_time(self):
        self.assertEqual(datetime_util.truncate_datetime(None), None)
        self.assertEqual(datetime_util.truncate_datetime(datetime(2010, 1, 2)), datetime(2010, 1, 2))
        self.assertEqual(datetime_util.truncate_datetime(datetime(2010, 1, 2, 3, 4, 5, 6)), datetime(2010, 1, 2))

    @mock.patch('src.tss.datetime_util.time')
    def test_get_datetime_stamp(self, mocktime):
        datetime_util.get_datetime_stamp()
        mocktime.strftime.assert_called_with("%m%d%H%M%S")

    def test_format_sql_date(self):
        test_date = datetime(2010, 1, 2, 3, 4, 5, 6)
        self.assertEqual(datetime_util.format_sql_date(test_date, "FileGdb"), "date '2010-01-02 03:04:05'")
        self.assertEqual(datetime_util.format_sql_date(test_date, "Oracle"), "TO_DATE('2010-01-02 03:04:05','YYYY-MM-DD HH24:MI:SS')")
        self.assertEqual(datetime_util.format_sql_date(test_date, "SQL Server"), "'2010-01-02 03:04:05'")
        self.assertRaises(Exception, datetime_util.format_sql_date, test_date, "Wrong DbType")

    def test_get_maximum_date(self):
        date1, date2 = datetime(2010, 1, 2, 3, 4, 5, 6), datetime(2011, 1, 2, 3, 4, 5, 6)
        self.assertEqual(datetime_util.get_maximum_date([date1, date2]), date2)
        self.assertEqual(datetime_util.get_maximum_date([date1, date2, None]), date2)

if __name__ == '__main__':
    unittest.main()
