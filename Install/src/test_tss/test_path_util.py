import unittest
import src.tss.path_util as path_util
import mock


class PathUtilTestCase(unittest.TestCase):

    def test_get_parent_directory(self):
        test_path = r"C:\Dir1\Dir2\Dir3\test.txt"
        self.assertEqual(path_util.get_parent_directory(test_path), r"C:\Dir1\Dir2\Dir3")
        self.assertEqual(path_util.get_parent_directory(test_path, 1), r"C:\Dir1\Dir2\Dir3")
        self.assertEqual(path_util.get_parent_directory(test_path, 2), r"C:\Dir1\Dir2")
        self.assertEqual(path_util.get_parent_directory(test_path, 3), r"C:\Dir1")

    @mock.patch('src.tss.path_util.os.path')
    def test_get_user_directory(self, mockpath):
        path_util.get_user_directory()
        mockpath.expanduser.assert_called_with("~")


if __name__ == '__main__':
    unittest.main()
