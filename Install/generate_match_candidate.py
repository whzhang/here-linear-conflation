import arcpy
import os
import traceback
from datetime import datetime

from src.util.helper import get_scratch_gdb, clear_scratch_gdb
from src.tss.ags.geometry_util import angle_between_two_vectors
from src.tss.ags.field_util import get_field_details
from src.config.schema import default_schemas

import logging
logger = logging.getLogger(__name__)

round_decimal_places = 6

def generate_match_candidate(**kwargs):
    """
    Generate the HERE link and DOT Route match candidate table
    :param kwargs:
    :return:
    """

    here_link = kwargs.get('here_link', None)
    here_link_id_field = kwargs.get('here_link_id_field', None)
    here_st_name_field = kwargs.get('here_st_name_field', None)
    here_county_id_field = kwargs.get('here_county_id_field', None)
    dot_network = kwargs.get('dot_network', None)
    dot_network_rid_field = kwargs.get('dot_network_rid_field', None)
    dot_network_route_name_field = kwargs.get('dot_network_route_name_field', None)
    dot_network_county_id_field = kwargs.get('dot_network_county_id_field', None)
    dot_network_fdate_field = kwargs.get('dot_network_fdate_field', None)
    dot_network_tdate_field = kwargs.get('dot_network_tdate_field', None)
    output_table = kwargs.get('output_table', None)
    search_radius = kwargs.get('search_radius', None)
    angle_tolerance = kwargs.get('angle_tolerance', None)

    if here_link is None or not arcpy.Exists(here_link):
        logger.warning("HERE Link feature: '{0}' does not exist!".format(here_link))
        return

    if dot_network is None or not arcpy.Exists(dot_network):
        logger.warning("DOT Network feature: '{0}' does not exist!".format(dot_network))
        return

    # intermediate outputs
    here_link_sj_dot_network_raw= os.path.join(scratch_gdb, 'here_link_sj_dot_network_raw')
    here_link_sj_dot_network_valid = os.path.join(scratch_gdb, 'here_link_sj_dot_network_valid')
    here_link_sj_dot_network_valid_buffer = os.path.join(scratch_gdb, 'here_link_sj_dot_network_valid_buffer')
    here_link_sj_dot_network_valid_frq = os.path.join(scratch_gdb, 'here_link_sj_dot_network_valid_frq')

    active_dot_network_layer = os.path.join(scratch_gdb, 'active_{0}'.format(os.path.basename(dot_network)))
    dot_network_here_link_buffer_intersect_pnt = os.path.join(scratch_gdb, 'dot_network_here_link_buffer_intersect_pnt')
    dot_network_split = os.path.join(scratch_gdb, 'dot_network_split')
    dot_network_split_sj_here_link_buffer = os.path.join(scratch_gdb, 'dot_network_split_sj_here_link_buffer')
    dot_network_split_sj_here_link_buffer_valid = os.path.join(scratch_gdb, 'dot_network_split_sj_here_link_buffer_valid')
    dot_network_seg_within_here_link_buffer = os.path.join(scratch_gdb, 'dot_network_seg_within_here_link_buffer')

    here_link_sj_dot_network_raw_lyr = 'here_link_sj_dot_network_raw_lyr'

    output_table_frq = os.path.join(scratch_gdb, 'output_table_frq')

    # outputs
    output_schema_name = 'candidate_table'
    schemas = default_schemas.get(output_schema_name)
    output_workspace = os.path.dirname(output_table)
    output_table_name = os.path.basename(output_table)
    output_here_lid_field = schemas.get('here_lid_field')
    output_here_st_name_field = schemas.get('here_st_name_field')
    output_here_cnty_id_field = schemas.get('here_cnty_id_field')
    output_dot_rid_field = schemas.get('dot_rid_field')
    output_dot_rt_name_field = schemas.get('dot_rt_name_field')
    output_dot_cnty_id_field = schemas.get('dot_cnty_id_field')
    output_conf_lvl_field = schemas.get('conf_lvl_field')
    output_verified_match_field = schemas.get('verified_match_field')
    output_false_match_field = schemas.get('false_match_field')

    logger.info("Finish initiation")
    ####################################################################################################################


    ####################################################################################################################
    logger.info("[{0}] Start matching HERE links and DOT routes...".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S')))

    active_where_clause = "1=1" if not dot_network_fdate_field or not dot_network_fdate_field else \
        "({start_date_field} is null or {start_date_field} <= CURRENT_TIMESTAMP) and " \
        "({end_date_field} is null or {end_date_field} > CURRENT_TIMESTAMP)".format(
            start_date_field=dot_network_fdate_field,
            end_date_field=dot_network_tdate_field)

    arcpy.MakeFeatureLayer_management(dot_network, active_dot_network_layer, active_where_clause)

    # get links with one-to-one match and links with one-to-many match with the specified tolerance
    arcpy.SpatialJoin_analysis(here_link, active_dot_network_layer, here_link_sj_dot_network_raw, "JOIN_ONE_TO_MANY",
                               match_option="WITHIN_A_DISTANCE", search_radius=search_radius)

    arcpy.MakeFeatureLayer_management(here_link_sj_dot_network_raw, here_link_sj_dot_network_raw_lyr)
    arcpy.SelectLayerByAttribute_management(here_link_sj_dot_network_raw_lyr, 'NEW_SELECTION', '"JOIN_FID" <> -1')
    arcpy.CopyFeatures_management(here_link_sj_dot_network_raw_lyr, here_link_sj_dot_network_valid)

    arcpy.Frequency_analysis(here_link_sj_dot_network_valid, here_link_sj_dot_network_valid_frq, [here_link_id_field])
    arcpy.JoinField_management(here_link_sj_dot_network_raw, here_link_id_field, here_link_sj_dot_network_valid_frq, here_link_id_field, ['FREQUENCY'])

    # TODO: Wrap this into a function
    dot_network_rid_field_type = 'TEXT'
    dot_network_rid_field_length = 255

    for field in arcpy.ListFields(dot_network):
        if field.name == dot_network_rid_field:
            dot_network_rid_field_type = field.type
            dot_network_rid_field_length = field.length
            break

    if dot_network_rid_field_type == 'String':
        dot_network_rid_field_type = 'TEXT'
    elif dot_network_rid_field_type == 'Double':
        dot_network_rid_field_type = 'DOUBLE'
    elif dot_network_rid_field_type == 'Single':
        dot_network_rid_field_type = 'FLOAT'
    elif dot_network_rid_field_type == 'Integer':
        dot_network_rid_field_type = 'LONG'
    elif dot_network_rid_field_type == 'SmallInteger':
        dot_network_rid_field_type = 'SHORT'
    elif dot_network_rid_field_type == 'Date':
        dot_network_rid_field_type = 'DATE'

    here_lid_field_details = get_field_details(here_link, here_link_id_field)

    # Add 'TSS_RID' as an identifier of matched DOT route id for later comparison
    arcpy.AddField_management(here_link_sj_dot_network_valid, 'TSS_RID', field_type=dot_network_rid_field_type, field_length=dot_network_rid_field_length)
    arcpy.CalculateField_management(here_link_sj_dot_network_valid, 'TSS_RID', "!{0}!".format(dot_network_rid_field), "PYTHON_9.3")
    ####################################################################################################################

    ####################################################################################################################
    logger.info("[{0}] Filtering out false positive matches...".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S')))

    # filter out false positive matches
    arcpy.Buffer_analysis(here_link_sj_dot_network_valid, here_link_sj_dot_network_valid_buffer, search_radius)

    # head up! Here we rank Here link buffer higher than DOT network to guarantee the intersection point will be generated
    # for each pair of intersecting buffer and route
    arcpy.Intersect_analysis([[here_link_sj_dot_network_valid_buffer, 1], [active_dot_network_layer, 2]],
                             dot_network_here_link_buffer_intersect_pnt, cluster_tolerance='0.001 FEET', output_type='POINT')
    arcpy.SplitLineAtPoint_management(active_dot_network_layer, dot_network_here_link_buffer_intersect_pnt, dot_network_split, search_radius)
    arcpy.SpatialJoin_analysis(dot_network_split, here_link_sj_dot_network_valid_buffer,
                               dot_network_split_sj_here_link_buffer, "JOIN_ONE_TO_MANY", join_type='KEEP_COMMON', match_option="WITHIN")
    # We only want records whose dot rid equals 'TSS_RID'. If dot rid value does not equal to 'TSS_RID' value,
    # it means this route seg just accidentally within the link buffer but hasn't been found when spatial joining link and route.
    arcpy.FeatureClassToFeatureClass_conversion(dot_network_split_sj_here_link_buffer, scratch_gdb,
                                                os.path.basename(dot_network_split_sj_here_link_buffer_valid),
                                                where_clause="{0}={1}".format(dot_network_rid_field, 'TSS_RID'))

    # Dissolve on here link id and dot route id to get the dot network segment within the HERE link buffer
    arcpy.Dissolve_management(dot_network_split_sj_here_link_buffer_valid, dot_network_seg_within_here_link_buffer, [here_link_id_field, dot_network_rid_field])

    # ------------------------------------------------------------------------------------------------------------------
    here_linkid_geometry_dot_route_seg_dict_dict_dict = {}

    # Get link geometry
    with arcpy.da.SearchCursor(here_link_sj_dot_network_valid, [here_link_id_field, 'SHAPE@']) as sCur:
        for row in sCur:
            link_id, geometry = row

            if geometry is None:
                logger.warning("[{0}] Invalid geometry! Geometry of link {1} is NoneType!".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S'), link_id))
                continue

            if link_id not in here_linkid_geometry_dot_route_seg_dict_dict_dict.keys():
                here_linkid_geometry_dot_route_seg_dict_dict_dict[link_id] = {}
                here_linkid_geometry_dot_route_seg_dict_dict_dict[link_id]['link_geometry'] = {'link_firstPoint_x': geometry.firstPoint.X,
                                                                                               'link_firstPoint_y': geometry.firstPoint.Y,
                                                                                               'link_lastPoint_x': geometry.lastPoint.X,
                                                                                               'link_lastPoint_y': geometry.lastPoint.Y}
                here_linkid_geometry_dot_route_seg_dict_dict_dict[link_id]['route_segments'] = {}

    del sCur

    # Get geometry of route segments within link buffer
    with arcpy.da.SearchCursor(dot_network_seg_within_here_link_buffer, [here_link_id_field, dot_network_rid_field, 'SHAPE@']) as sCur:
        for row in sCur:
            link_id, dot_rid, geometry = row

            if link_id not in here_linkid_geometry_dot_route_seg_dict_dict_dict.keys():
                continue

            if geometry is None:
                logger.warning("[{0}] Invalid geometry! Geometry of route {1} segment within link {2} buffer is NoneType!".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S'), dot_rid, link_id))
                continue

            if dot_rid not in here_linkid_geometry_dot_route_seg_dict_dict_dict[link_id]['route_segments'].keys():
                here_linkid_geometry_dot_route_seg_dict_dict_dict[link_id]['route_segments'][dot_rid] = {'route_seg_firstPoint_x': geometry.firstPoint.X,
                                                                                                         'route_seg_firstPoint_y': geometry.firstPoint.Y,
                                                                                                         'route_seg_lastPoint_x': geometry.lastPoint.X,
                                                                                                         'route_seg_lastPoint_y': geometry.lastPoint.Y}

    del sCur
    # ------------------------------------------------------------------------------------------------------------------

    # Calculate angle
    arcpy.AddField_management(here_link_sj_dot_network_raw, 'TSS_Angle', "DOUBLE")
    with arcpy.da.UpdateCursor(here_link_sj_dot_network_raw, [here_link_id_field, dot_network_rid_field, 'TSS_Angle']) as uCur:
        for row in uCur:
            here_link_id = row[0]
            dot_route_id = row[1]
            if here_link_id not in here_linkid_geometry_dot_route_seg_dict_dict_dict.keys():
                continue
            elif dot_route_id not in here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'].keys():
                continue
            else:
                here_link_geometry_firstPoint_x = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['link_geometry']['link_firstPoint_x']
                here_link_geometry_firstPoint_y = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['link_geometry']['link_firstPoint_y']
                here_link_geometry_lastPoint_x = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['link_geometry']['link_lastPoint_x']
                here_link_geometry_lastPoint_y = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['link_geometry']['link_lastPoint_y']

                dot_route_seg_geometry_firstPoint_x = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'][dot_route_id]['route_seg_firstPoint_x']
                dot_route_seg_geometry_firstPoint_y = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'][dot_route_id]['route_seg_firstPoint_y']
                dot_route_seg_geometry_lastPoint_x = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'][dot_route_id]['route_seg_lastPoint_x']
                dot_route_seg_geometry_lastPoint_y = here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'][dot_route_id]['route_seg_lastPoint_y']

                try:
                    # A minimum six decimal places need to be used otherwise the angle return could be far from accurate
                    angle = angle_between_two_vectors((round(here_link_geometry_firstPoint_x - here_link_geometry_lastPoint_x, round_decimal_places),
                                                       round(here_link_geometry_firstPoint_y - here_link_geometry_lastPoint_y, round_decimal_places)),
                                                      (round(dot_route_seg_geometry_firstPoint_x - dot_route_seg_geometry_lastPoint_x, round_decimal_places),
                                                       round(dot_route_seg_geometry_firstPoint_y - dot_route_seg_geometry_lastPoint_y, round_decimal_places)))
                except:
                    # if it fails to calculate the angle for some reasons, report the error, skip this one, and continue
                    logger.warning("Failed to calculate the angle between link: '{0}' and route: '{1}'".format(here_link_id, dot_route_id))
                    logger.warning("here_link_geometry_firstPoint_x: {0}, here_link_geometry_firstPoint_y: {1}".format(here_link_geometry_firstPoint_x, here_link_geometry_firstPoint_y))
                    logger.warning("here_link_geometry_lastPoint_x: {0}, here_link_geometry_lastPoint_y: {1}".format(here_link_geometry_lastPoint_x, here_link_geometry_lastPoint_y))
                    logger.warning("dot_route_seg_geometry_firstPoint_x: {0}, dot_route_seg_geometry_firstPoint_y: {1}".format(dot_route_seg_geometry_firstPoint_x, dot_route_seg_geometry_firstPoint_y))
                    logger.warning("dot_route_seg_geometry_lastPoint_x: {0}, dot_route_seg_geometry_lastPoint_y: {1}".format(dot_route_seg_geometry_lastPoint_x, dot_route_seg_geometry_lastPoint_y))
                    logger.warning(" ")
                    continue

                if angle == -1: # It is likely there is zero vector, ignore and continue to the next one
                    continue
                if angle > 90:  # From angle of vectors to angle of non-directional lines
                    angle = 180 - angle

                here_linkid_geometry_dot_route_seg_dict_dict_dict[here_link_id]['route_segments'][dot_route_id]['angle'] = angle
                uCur.updateRow((here_link_id, dot_route_id, angle))

    del uCur
    ####################################################################################################################

    ####################################################################################################################
    logger.info("[{0}] Generating link route matching table...".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S')))

    # create link route matching table
    arcpy.CreateTable_management(output_workspace, output_table_name)
    arcpy.AddField_management(output_table, output_dot_rid_field, dot_network_rid_field_type, field_length=255)
    arcpy.AddField_management(output_table, output_here_lid_field, here_lid_field_details['field_type'], field_length=255)
    arcpy.AddField_management(output_table, output_dot_rt_name_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_dot_cnty_id_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_here_st_name_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_here_cnty_id_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_conf_lvl_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_verified_match_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_table, output_false_match_field, "TEXT", field_length=255)

    candidate_table_fields = [output_dot_rid_field, output_here_lid_field, output_dot_rt_name_field,
                              output_dot_cnty_id_field, output_here_st_name_field, output_here_cnty_id_field,
                              output_conf_lvl_field, output_verified_match_field, output_false_match_field]

    # Populate link route matching table
    bad_matches_dict = {}
    fields_of_interest = [dot_network_rid_field, here_link_id_field, dot_network_route_name_field, dot_network_county_id_field,
                          here_st_name_field, here_county_id_field, 'TSS_Angle', 'FREQUENCY']

    iCur = arcpy.da.InsertCursor(output_table, candidate_table_fields)
    with arcpy.da.SearchCursor(here_link_sj_dot_network_raw, fields_of_interest,
                               sql_clause = (None, 'ORDER BY {0}'.format(here_link_id_field))) as sCur:
        for row in sCur:
            dot_route_id = row[0]
            here_link_id = row[1]
            dot_route_name = row[2]
            dot_county_id = row[3]
            here_st_name = row[4]
            here_county_id = row[5]
            angle = row[6]
            frequency = row[7]

            # No match
            if dot_route_id is None or dot_route_id.strip() == "":
                iCur.insertRow((None, here_link_id, None, None, here_st_name, here_county_id, 'No Match', None, None))
                continue

            # Bad matches-------------------------------------------------------------------------------------------
            # If the link and route match is found but their angle is None, it means either the link and route seg
            # has bad geometry and their angle cannot be calculated. It is considered a bad match
            if angle is None or angle > angle_tolerance:
                # Bad and the only match
                if frequency == 1:
                    iCur.insertRow((None, here_link_id, None, None, here_st_name, here_county_id, 'No Match', None, None))
                    continue

                # Bad but not the only match
                if here_link_id not in bad_matches_dict.keys():
                    bad_matches_dict[here_link_id] = []

                bad_matches_dict[here_link_id].append(dot_route_id)

                if len(bad_matches_dict[here_link_id]) == frequency: # None of its matches is good
                    iCur.insertRow((None, here_link_id, None, None, here_st_name, here_county_id, 'No Match', None, None))

                continue
            # ------------------------------------------------------------------------------------------------------

            # Potential matches
            confidence = 'High' if frequency == 1 else 'Low'
            iCur.insertRow((dot_route_id, here_link_id, dot_route_name, dot_county_id, here_st_name, here_county_id, confidence, None, None))

    del iCur
    del sCur
    ####################################################################################################################

    ####################################################################################################################
    logger.info("[{0}] Apply one-to-one match knowledge...".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S')))

    dot_county_route_name_here_county_street_name_knowledge_dict = {}
    with arcpy.da.SearchCursor(output_table, candidate_table_fields,
                               where_clause="{0} = 'High'".format(output_conf_lvl_field)) as sCur:
        for row in sCur:
            # dot_route_id = row[0]
            # here_link_id = row[1]
            dot_route_name = row[2]
            dot_county_id = row[3]
            here_st_name = row[4]
            here_county_id = row[5]
            # confidence = row[6]
            # verified_match = row[7]
            # false_match = row[8]

            here_knowledge = '{0}-{1}'.format(here_county_id, here_st_name)
            dot_knowledge = '{0}-{1}'.format(dot_county_id, dot_route_name)

            if dot_knowledge not in dot_county_route_name_here_county_street_name_knowledge_dict.keys():
                dot_county_route_name_here_county_street_name_knowledge_dict[dot_knowledge] = []

            if here_knowledge not in dot_county_route_name_here_county_street_name_knowledge_dict[dot_knowledge]:
                dot_county_route_name_here_county_street_name_knowledge_dict[dot_knowledge].append(here_knowledge)

    del sCur

    arcpy.Frequency_analysis(output_table, output_table_frq, [output_here_lid_field])
    single_match_here_lid_list = []
    with arcpy.da.SearchCursor(output_table_frq, ['FREQUENCY', output_here_lid_field], where_clause="FREQUENCY = 1") as sCur:
        for row in sCur:
            here_lid = row[1]

            if here_lid not in single_match_here_lid_list:
                single_match_here_lid_list.append(here_lid)

    # Head up!: Opening simultaneous insert and/or update operations on the same workspace using different cursors
    # requires the start of an edit session.
    with arcpy.da.Editor(output_workspace) as editor:
        # Apply one-to-one match knowledge to one-to-many matches cases
        with arcpy.da.UpdateCursor(output_table, candidate_table_fields, where_clause="{0} = 'Low'".format(output_conf_lvl_field)) as uCur:
            for row in uCur:
                dot_route_id = row[0]
                here_link_id = row[1]
                dot_route_name = row[2]
                dot_county_id = row[3]
                here_st_name = row[4]
                here_county_id = row[5]
                confidence = row[6]
                verified_match = row[7]
                false_match = row[8]

                here_knowledge = '{0}-{1}'.format(here_county_id, here_st_name)
                dot_knowledge = '{0}-{1}'.format(dot_county_id, dot_route_name)

                # If this is the only match candidate for the link, bump the confidence level up to 'High'
                if here_link_id in single_match_here_lid_list:
                    confidence = 'High'
                    uCur.updateRow((dot_route_id, here_link_id, dot_route_name, dot_county_id, here_st_name,
                                    here_county_id, confidence, verified_match, false_match))
                    continue

                if dot_knowledge not in dot_county_route_name_here_county_street_name_knowledge_dict.keys():
                    continue

                if here_knowledge in dot_county_route_name_here_county_street_name_knowledge_dict[dot_knowledge]:
                    confidence = 'Medium'
                    uCur.updateRow((dot_route_id, here_link_id, dot_route_name, dot_county_id, here_st_name,
                                    here_county_id, confidence, verified_match, false_match))

    del uCur
    ####################################################################################################################

    logger.info("[{0}] Success! Output: {1}".format(datetime.now().strftime('%m/%d/%Y %H:%M:%S'), output_table))


if __name__ == '__main__':
    here_link = arcpy.GetParameterAsText(0)
    here_link_id_field = arcpy.GetParameterAsText(1)
    here_st_name_field = arcpy.GetParameterAsText(2)
    here_county_id_field = arcpy.GetParameterAsText(3)
    dot_network = arcpy.GetParameterAsText(4)
    dot_network_rid_field = arcpy.GetParameterAsText(5)
    dot_network_route_name_field = arcpy.GetParameterAsText(6)
    dot_network_county_id_field = arcpy.GetParameterAsText(7)
    dot_network_fdate_field = arcpy.GetParameterAsText(8)
    dot_network_tdate_field = arcpy.GetParameterAsText(9)
    output_table = arcpy.GetParameterAsText(10)
    search_radius = arcpy.GetParameterAsText(11)
    angle_tolerance = arcpy.GetParameter(12)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    try:
        generate_match_candidate(
            here_link=here_link,
            here_link_id_field=here_link_id_field,
            here_st_name_field=here_st_name_field,
            here_county_id_field=here_county_id_field,
            dot_network=dot_network,
            dot_network_rid_field=dot_network_rid_field,
            dot_network_route_name_field=dot_network_route_name_field,
            dot_network_county_id_field=dot_network_county_id_field,
            dot_network_fdate_field=dot_network_fdate_field,
            dot_network_tdate_field=dot_network_tdate_field,
            output_table=output_table,
            search_radius=search_radius,
            angle_tolerance=angle_tolerance
        )

    except Exception, err:
        logger.error("Error: {0}".format(err.args[0]))
        logger.error(traceback.format_exc())

        if arcpy.Exists(output_table):
            arcpy.Delete_management(output_table)

    finally:
        clear_scratch_gdb(scratch_gdb)
        pass