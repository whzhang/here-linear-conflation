import arcpy
from ags import transform_dataset_keep_fields, build_string_in_sql_expression, build_numeric_in_sql_expression, delete_subset_data

# Intermediate data
two_d_network = "two_d_network"
two_d_simplify_network = "two_d_simplify_network"
generated_loop_intersections = "generated_loop_intersections"

import logging
logger = logging.getLogger(__name__)

class IntersectionEvent(object):

    def __init__(self, **kwargs):
        self.network = kwargs.get("network", None)
        self.intersection_event = kwargs.get("intersection_event", None)
        self.intersection_filter_layer = kwargs.get("intersection_filter_layer", None)
        self.intersection_id_field = kwargs.get("intersection_id_field", None)
        self.network_route_id_field = kwargs.get("network_route_id_field", None)
        self.loop_intersection = kwargs.get("loop_intersection", None)
        self.search_radius = kwargs.get("search_radius", None)
        logger.info("Finished init")

    def create_intersection_event(self):
        try:
            self.detect_intersections()
            logger.info("Finished detecting the intersections")
            self.populate_intersection_id()
            logger.info("Finished populating the intersection ids")
            self.adjust_output_schema()
            logger.info("Finished adjusting the schema")
            self.detect_loop_intersection()
            logger.info("Finished detecting the loop intersections")
        except Exception:
            import traceback
            logger.info(traceback.format_exc())
        return self.intersection_event

    def detect_intersections(self):
        outputZFlag = arcpy.env.outputZFlag
        outputMFlag = arcpy.env.outputMFlag
        arcpy.env.outputZFlag = "Disabled"
        arcpy.env.outputMFlag = "Disabled"

        arcpy.CopyFeatures_management(self.network, two_d_network)
        if arcpy.Exists(two_d_simplify_network):
            # the automatic overwrite doesn't work very well with simplifyLine, have to manually delete
            arcpy.Delete_management(two_d_simplify_network)
        arcpy.SimplifyLine_cartography(two_d_network, two_d_simplify_network, "POINT_REMOVE", "999999 meters")
        logger.info("Finished simplify network")

        arcpy.FeatureVerticesToPoints_management(two_d_simplify_network, self.intersection_event, "ALL")
        self.filter_out_none_intersections()

        with arcpy.da.SearchCursor(self.intersection_event, ["SHAPE@XY", self.network_route_id_field]) as sCursor:
            xy__rid_list_dict = {}
            for sRow in sCursor:
                xy_tuple, route_id = sRow[0], sRow[1]
                if xy_tuple not in xy__rid_list_dict:
                    xy__rid_list_dict[xy_tuple] = []
                xy__rid_list_dict[xy_tuple].append(route_id)

        xy_type_dict = {}
        arcpy.AddField_management(self.intersection_event, "INTER_SHAPE_TYPE", "TEXT")
        with arcpy.da.UpdateCursor(self.intersection_event, ["SHAPE@XY", "INTER_SHAPE_TYPE"]) as uCursor:
            for uRow in uCursor:
                xy= uRow[0]
                rid_list = xy__rid_list_dict[xy]
                length = len(rid_list)
                if length == 1:
                    xy_type_dict[xy] = "DELETE"  # Dangle points or loop skeleton, not real intersections, need to be deleted
                elif length == 2:
                    if rid_list[0] == rid_list[1]:
                        xy_type_dict[xy] = "CIRCULAR INTERSECTIONS"  # The loop intersection point
                    else:
                        xy_type_dict[xy] = "TRUE INTERSECTIONS"
                elif length >= 3:
                    unique_length = len(set(rid_list))
                    if unique_length == length:
                        xy_type_dict[xy] = "TRUE INTERSECTIONS"
                    elif unique_length == 1:
                        xy_type_dict[xy] = "CIRCULAR INTERSECTIONS"
                    else:
                        xy_type_dict[xy] = "CONCURRENT INTERSECTIONS OR OTHERS"

                if xy_type_dict[xy] in ["DELETE"]:
                    # the circle intersections don't get detected in consistent way using this method,
                    # let intersect_analysis handle them
                    uCursor.deleteRow()
                    continue

                uRow[1] = xy_type_dict[xy]
                uCursor.updateRow(uRow)

        arcpy.DeleteIdentical_management(self.intersection_event, arcpy.Describe(self.intersection_event).shapeFieldName)
        logger.info("Finished converting simplified network to intersections")

        # Filter out cases that a circle is simplified as a line, a point is falsely generated
        arcpy.AddField_management(self.intersection_event, "TSS_ID", "FLOAT")
        arcpy.CalculateField_management(self.intersection_event, "TSS_ID", "!%s!" % arcpy.Describe(self.intersection_event).OIDFieldName, "PYTHON")
        potential_loop_intersections = "potential_loop_intersections"
        potential_loop_intersections_locate = "potential_loop_intersections_locate"
        potential_loop_intersections_locate_fq = "potential_loop_intersections_locate_fq"
        arcpy.Select_analysis(self.intersection_event, potential_loop_intersections, "INTER_SHAPE_TYPE='CIRCULAR INTERSECTIONS'")
        arcpy.LocateFeaturesAlongRoutes_lr(potential_loop_intersections, self.network, self.network_route_id_field, self.search_radius, potential_loop_intersections_locate, "RID POINT MEAS", "ALL")
        arcpy.Frequency_analysis(potential_loop_intersections_locate, potential_loop_intersections_locate_fq, ["TSS_ID"])
        with arcpy.da.SearchCursor(potential_loop_intersections_locate_fq, "TSS_ID", "FREQUENCY = 2") as sCursor:
            right_loop_tssids = [sRow[0] for sRow in sCursor]
        with arcpy.da.SearchCursor(potential_loop_intersections, "TSS_ID") as sCursor:
            wrong_loop_tssids = [sRow[0] for sRow in sCursor if sRow[0] not in right_loop_tssids]
        delete_subset_data(self.intersection_event, build_numeric_in_sql_expression("TSS_ID", wrong_loop_tssids))
        arcpy.Select_analysis(potential_loop_intersections, generated_loop_intersections, build_numeric_in_sql_expression("TSS_ID", right_loop_tssids))

        # Append dangle intersections, this is handle cases that some DOTs might not have network snapping very well
        # TODO: verify this
        dangle_intersection = self.detect_dangle_intersections(self.network, self.intersection_event)
        arcpy.Append_management(dangle_intersection, self.intersection_event, "NO_TEST")
        arcpy.Delete_management(dangle_intersection)

        # Filter out the points not intersecting the actual routes
        # filter_intersection_layer = "filter_intersection_layer"
        # arcpy.MakeFeatureLayer_management(self.intersection_event, filter_intersection_layer)
        # arcpy.SelectLayerByLocation_management(filter_intersection_layer, "INTERSECT", self.network, self.search_radius, "NEW_SELECTION")
        # arcpy.SelectLayerByAttribute_management(filter_intersection_layer, "SWITCH_SELECTION")
        # arcpy.DeleteRows_management(filter_intersection_layer)
        # arcpy.Delete_management(filter_intersection_layer)
        # Note: simply select by location won't work because it creates different output as locate feature along route, which just sucks
        # Have to do one more locate feature along route here to make sure every thing is good
        filter_locate_route = "filter_locate_route"
        arcpy.LocateFeaturesAlongRoutes_lr(self.intersection_event, self.network, self.network_route_id_field, self.search_radius,
                                           filter_locate_route, "RID POINT MEAS", "#", "NO_DISTANCE", "#", "NO_FIELDS")
        with arcpy.da.SearchCursor(filter_locate_route, "INPUTOID") as sCursor:
            located_oids = [sRow[0] for sRow in sCursor]
        with arcpy.da.UpdateCursor(self.intersection_event, "OID@") as uCursor:
            for uRow in uCursor:
                if uRow[0] not in located_oids:
                    uCursor.deleteRow()


        arcpy.DeleteIdentical_management(self.intersection_event, arcpy.Describe(self.intersection_event).shapeFieldName)

        logger.info("Finished appending dangle intersections to output intersections")

        arcpy.env.outputZFlag = outputZFlag
        arcpy.env.outputMFlag = outputMFlag
        arcpy.Delete_management(two_d_simplify_network)
        arcpy.Delete_management("%s_Pnt" % two_d_simplify_network)
        arcpy.Delete_management(two_d_network)

        return self.intersection_event

    def detect_dangle_intersections(self, network, simplify_intersection):
        # This is a custom codes for GDOT because not all routes snap very well
        intersect_intersections = "intersect_intersections"
        intersect_intersections_mutli = "intersect_intersections_mutli"
        additional_intersection_layer = "additional_intersection_layer"
        arcpy.Intersect_analysis(network, intersect_intersections_mutli, "ONLY_FID", self.search_radius, "POINT")
        arcpy.MultipartToSinglepart_management(intersect_intersections_mutli, intersect_intersections)
        arcpy.MakeFeatureLayer_management(intersect_intersections, additional_intersection_layer, "")
        # Note: one tricky thing here is the tolerance has been 2 meters ...
        # This is a bug in SelectLayerByLocation tool. Although if you do it in ArcMap menu, it works.
        # But the search radius has to be set to a larger value to work in the selectLayerByLocation
        # TODO: verify this
        arcpy.SelectLayerByLocation_management(additional_intersection_layer, "INTERSECT", simplify_intersection, "4 Meters", "NEW_SELECTION")
        arcpy.DeleteRows_management(additional_intersection_layer)

        arcpy.Delete_management(intersect_intersections_mutli)

        return intersect_intersections

    def filter_out_none_intersections(self):
        if self.intersection_filter_layer:
            arcpy.MakeFeatureLayer_management(self.intersection_event, "intersection_event_layer")
            arcpy.SelectLayerByLocation_management("intersection_event_layer", "INTERSECT", self.intersection_filter_layer, self.search_radius)
            arcpy.SelectLayerByAttribute_management("intersection_event_layer", "SWITCH_SELECTION")
            if int(arcpy.GetCount_management("intersection_event_layer").getOutput(0)) > 0:
                arcpy.DeleteRows_management("intersection_event_layer")

    def populate_intersection_id(self):
        arcpy.AddField_management(self.intersection_event, self.intersection_id_field, "TEXT", "", "", 20)
        with arcpy.da.UpdateCursor(self.intersection_event, self.intersection_id_field) as cursor:
            max_id = 0
            for row in cursor:
                max_id += 1
                row[0] = "%s" % max_id
                cursor.updateRow(row)

    def adjust_output_schema(self):
        transform_dataset_keep_fields(self.intersection_event, [self.intersection_id_field])

    def detect_loop_intersection(self):
        if self.loop_intersection is None:
            return
        intersection_event_layer = "intersection_event_layer"
        arcpy.MakeFeatureLayer_management(self.intersection_event, intersection_event_layer, "")
        arcpy.SelectLayerByLocation_management(intersection_event_layer, "INTERSECT", generated_loop_intersections, self.search_radius)
        arcpy.CopyFeatures_management(intersection_event_layer, self.loop_intersection, "")
        # # The loop intersection is mostly for future usage
        # locate_table = "locate_table"
        # arcpy.LocateFeaturesAlongRoutes_lr(self.intersection_event, self.network, self.network_route_id_field, self.search_radius, locate_table, "RID POINT MEAS", "ALL")
        # intersection__route_id_list_dict = {}
        # with arcpy.da.SearchCursor(locate_table, [self.intersection_id_field, "RID"]) as sCursor:
        #     for sRow in sCursor:
        #         intersection_id, route_id = sRow
        #         if intersection_id not in intersection__route_id_list_dict:
        #             intersection__route_id_list_dict[intersection_id] = []
        #         intersection__route_id_list_dict[intersection_id].append(route_id)
        # loop_intersection_ids = []
        # for intersection_id, route_id_list in intersection__route_id_list_dict.items():
        #     if len(route_id_list) != len(set(route_id_list)):
        #         loop_intersection_ids.append(intersection_id)
        # arcpy.Select_analysis(self.intersection_event, self.loop_intersection, build_string_in_sql_expression(self.intersection_id_field, loop_intersection_ids))