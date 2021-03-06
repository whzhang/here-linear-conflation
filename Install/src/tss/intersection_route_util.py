import arcpy
import os
from itertools import permutations
import logging
logger = logging.getLogger(__name__)

# Intermediate data
intersections_along_route = "intersections_along_route"
inter_route_join = "inter_route_join"

# Intermediate fields
intersection_rid_field = "RID"
intersection_meas_field = "MEAS"


class IntersectionRouteEvent(object):

    def __init__(self, **kwargs):
        self.network = kwargs.get("network", None)
        self.network_route_id_field = kwargs.get("network_route_id_field", None)

        self.intersection_event = kwargs.get("intersection_event", None)
        self.intersection_id_field = kwargs.get("intersection_id_field", None)

        self.intersection_route_event = kwargs.get("intersection_route_event")
        self.intersection_route_on_rid_field = kwargs.get("intersection_route_on_rid_field", None)
        self.intersection_route_on_measure_field = kwargs.get("intersection_route_on_measure_field", None)
        self.intersection_route_at_rid_field = kwargs.get("intersection_route_at_rid_field", None)

        self.measure_scale = kwargs.get("measure_scale", 3)
        self.search_radius = kwargs.get("search_radius", "0.5 Meters")

    def create_intersection_route_event(self):
        self.create_intersection_route_event_table()
        logger.info("Finished creating intersection route event table")
        self.populate_intersection_route_event_table()
        logger.info("Finished populating intersection route event table")
        self.clear_intermediate_data()
        logger.info("Finished clearing intermediate data")
        return self.intersection_route_event

    def create_intersection_route_event_table(self):
        # Create Intersections Routes table from intersections_table
        arcpy.CreateTable_management(os.path.dirname(self.intersection_route_event) or arcpy.env.workspace, os.path.basename(self.intersection_route_event))
        arcpy.AddField_management(self.intersection_route_event, self.intersection_id_field, "TEXT", "", "", 20)
        arcpy.AddField_management(self.intersection_route_event, self.intersection_route_on_rid_field, "TEXT", "", "", 20)
        arcpy.AddField_management(self.intersection_route_event, self.intersection_route_on_measure_field, "DOUBLE")
        arcpy.AddField_management(self.intersection_route_event, self.intersection_route_at_rid_field, "TEXT", "", "", 20)

    def populate_intersection_route_event_table(self):
        arcpy.LocateFeaturesAlongRoutes_lr(self.intersection_event, self.network, self.network_route_id_field, self.search_radius,
                                           intersections_along_route, "%s Point %s" % (intersection_rid_field, intersection_meas_field),
                                           "ALL", "NO_DISTANCE")
        logger.info("Finished locating features along routes")
        inter__route__measure_dict = {}
        with arcpy.da.SearchCursor(intersections_along_route, (self.intersection_id_field, intersection_rid_field, intersection_meas_field)) as sCursor:
            for sRow in sCursor:
                intersection_id, route_id, measure = sRow[0], sRow[1], round(sRow[2], int(self.measure_scale))
                if intersection_id not in inter__route__measure_dict:
                    inter__route__measure_dict[intersection_id] = {}
                if route_id not in inter__route__measure_dict[intersection_id]:
                    inter__route__measure_dict[intersection_id][route_id] = []
                # Note: it is set to a list to handle cases that intersection locating on a route twice, like loop
                inter__route__measure_dict[intersection_id][route_id].append(measure)

        # Heads up! Here is a workaround code. Some routes do not have measures.
        # The locate feature along route won't create any records for that route
        # In order to get all the route id pairs, we will have to do another spatial join
        arcpy.SpatialJoin_analysis(self.intersection_event, self.network, inter_route_join, "JOIN_ONE_TO_MANY", "KEEP_ALL", "" , "INTERSECT", self.search_radius)
        inter__route_list_dict = {}
        with arcpy.da.SearchCursor(inter_route_join, [self.intersection_id_field, self.network_route_id_field]) as sCursor:
            for sRow in sCursor:
                intersection_id, route_id = sRow[0], sRow[1]
                if intersection_id not in inter__route_list_dict:
                    inter__route_list_dict[intersection_id] = []
                inter__route_list_dict[intersection_id].append(route_id)

        with arcpy.da.InsertCursor(self.intersection_route_event, (self.intersection_id_field, self.intersection_route_on_rid_field, self.intersection_route_at_rid_field, self.intersection_route_on_measure_field)) as iCursor:
            for intersection_id, route_list in inter__route_list_dict.items():
                if len(route_list) == 1:
                    # Note: this is added to handle loop route
                    on_route_id, at_route_id = route_list * 2
                    for route_measure in inter__route__measure_dict[intersection_id][on_route_id]:
                        iCursor.insertRow((intersection_id, on_route_id, at_route_id, route_measure))
                else:
                    for on_route_id, at_route_id in permutations(route_list, 2):
                        if intersection_id in inter__route__measure_dict and on_route_id in inter__route__measure_dict[intersection_id]:
                            for route_measure in inter__route__measure_dict[intersection_id][on_route_id]:
                                iCursor.insertRow((intersection_id, on_route_id, at_route_id, route_measure))
                        else:
                            iCursor.insertRow((intersection_id, on_route_id, at_route_id, None))
        return self.intersection_route_event

    def clear_intermediate_data(self):
        to_be_deleted_items = [intersections_along_route, inter_route_join]
        for item in to_be_deleted_items:
            arcpy.Delete_management(item)