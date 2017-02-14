import unittest
import src.tss.ags.geometry_util as geometry_util


class GeometryUtilTestCase(unittest.TestCase):

    def test_angle_between_two_vectors(self):
        self.assertAlmostEqual(geometry_util.angle_between_two_vectors([1, 1], [1, 0]), 45)
        self.assertAlmostEqual(geometry_util.angle_between_two_vectors([1, 1], [0, -1]), 135)
        self.assertAlmostEqual(geometry_util.angle_between_two_vectors([0, -1], [1, 1]), 135)
        self.assertAlmostEqual(geometry_util.angle_between_two_vectors([1, 1, 1], [1, 0, 1]), 35.2643896827)

    def test_angle_larger_than_pi(self):
        self.assertFalse(geometry_util.angle_larger_than_pi([1, 1], [1, 0]))
        self.assertTrue(geometry_util.angle_larger_than_pi([0, -1], [1, 1]))
        self.assertFalse(geometry_util.angle_larger_than_pi([1, 1], [0, -1]))

    def test_geodesic_angle_to_circular_angle(self):
        angle = 45
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "N"), 45)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "E"), 315)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "S"), 225)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "W"), 135)
        angle = 135
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "N"), 135)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "E"), 45)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "S"), 315)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "W"), 225)
        angle = 225
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "N"), 225)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "E"), 135)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "S"), 45)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "W"), 315)
        angle = 315
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "N"), 315)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "E"), 225)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "S"), 135)
        self.assertEqual(geometry_util.geodesic_angle_to_circular_angle(angle, "W"), 45)

    def test_geodesic_angle_to_direction(self):
        self.assertEqual(geometry_util.geodesic_angle_to_direction(0), "North")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(22.5), "North")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(30), "NorthEast")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(67.5), "NorthEast")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(100), "East")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(112.5), "East")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(140), "SouthEast")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(157.5), "SouthEast")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(170), "South")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(180), "South")

        self.assertEqual(geometry_util.geodesic_angle_to_direction(-1), "North")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-22.5), "NorthWest")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-30), "NorthWest")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-67.5), "West")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-100), "West")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-112.5), "SouthWest")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-140), "SouthWest")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-157.5), "South")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-170), "South")
        self.assertEqual(geometry_util.geodesic_angle_to_direction(-180), "South")



if __name__ == '__main__':
    unittest.main()
