import arcpy
import os
import sys
import traceback
import pythonaddins

from src.util.helper import get_scratch_gdb, clear_scratch_gdb
from src.config.schema import default_schemas

import logging
logger = logging.getLogger(__name__)


def generate_here_route(**kwargs):
    """
    Generate a route feature from HERE link segments.
    :param kwargs:
    :return:
    """
    logger.info("Start generating HERE route features...")

    here_link = kwargs.get('here_link', None)
    route_id_field = kwargs.get('route_id_field', None)
    output_here_route = kwargs.get('output_here_route', None)
    check_gaps = kwargs.get('check_gaps', True)
    check_non_monotonic_routes = kwargs.get('check_non_monotonic_routes', True)
    only_generate_continuous_routes = kwargs.get('only_generate_continuous_routes', True)
    only_generate_monotonic_routes = kwargs.get('only_generate_monotonic_routes', True)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    # Intermediate output
    here_route_raw = os.path.join(scratch_gdb, 'here_route_raw')
    here_route_tbg = os.path.join(scratch_gdb, 'here_route_tbg')

    # Create Route
    arcpy.CreateRoutes_lr(here_link, route_id_field, here_route_raw, "LENGTH", "#", "#", "LOWER_LEFT")

    # Check gaps
    multi_part_routes = []
    if check_gaps:
        logger.info("Checking gaps along routes...")
        with arcpy.da.SearchCursor(here_route_raw, [route_id_field, 'SHAPE@']) as sCur:
            for row in sCur:
                rid = row[0]
                shape = row[1]

                if shape.isMultipart:
                    arcpy.AddMessage("Gap(s) detected on route: '{0}'".format(rid))
                    if rid not in multi_part_routes:
                        multi_part_routes.append(rid)
        del sCur

    if len(multi_part_routes):
        logger.warning("Please fix gaps detected on routes listed above before continuing.")

        msg = "Gaps are detected on routes listed above! Do you want to continue anyway? \n " \
              "(Click 'Yes' to continue. Click 'No' to quit. No output will be generated.)"
        logger.info(msg)

        if pythonaddins.MessageBox(msg, "Checking gaps along routes", 4) == 'No':
            logger.info("User selected 'No'. Quit the run. No output is generated.")
            if arcpy.Exists(output_here_route):
                arcpy.Delete_management(output_here_route)
            sys.exit()
        logger.info("User selected 'Yes' to continue.")

    # Check monotonic
    non_monotonic_routes = []
    if check_non_monotonic_routes:
        logger.info("Checking non-monotonic routes...")
        non_monotonic_routes = detect_non_monotonic_routes(here_route_raw, route_id_field)
        for route in non_monotonic_routes:
            arcpy.AddMessage("Non-monotonic route (id: '{0}') is found!".format(route))

    if len(non_monotonic_routes) > 0:
        msg = "Non-monotonic routes are found! Do you want to generate route features anyway? \n " \
              "(Click 'Yes' to continue. Click 'No' to quit. No output will be generated.)"
        logger.info(msg)

        if pythonaddins.MessageBox(msg, "Checking non-monotonic routes", 4) == 'No':
            logger.info("User selected 'No'. Quit the run. No output is generated.")
            if arcpy.Exists(output_here_route):
                arcpy.Delete_management(output_here_route)
            sys.exit()
        logger.info("User selected 'Yes' to continue.")

    # TODO: add ability to compare the length of generated HERE route features and DOT route features


    if not only_generate_continuous_routes and not only_generate_monotonic_routes:
        arcpy.CopyFeatures_management(here_route_raw, output_here_route)
        return


    rid_tbr = []
    if only_generate_continuous_routes and len(multi_part_routes):
        logger.info('Only continuous routes will be generated in the output...')
        for route in multi_part_routes:
            rid_tbr.append("'{0}'".format(route))

    if only_generate_monotonic_routes and len(non_monotonic_routes):
        logger.info('Only continuous routes will be generated in the output...')
        for route in non_monotonic_routes:
            rid_tbr.append("'{0}'".format(route))

    where_clause = "{0} NOT IN ({1})".format(route_id_field, ','.join(rid_tbr)) if len(rid_tbr) else "1=1"
    arcpy.MakeFeatureLayer_management(here_route_raw, here_route_tbg, where_clause=where_clause)
    arcpy.CopyFeatures_management(here_route_tbg, output_here_route)


def linear_reference_here_link_along_route(**kwargs):
    """
    Linear referencing link feature along route
    :param kwargs:
    :return:
    """
    logger.info("Start locating HERE link features along HERE route...")

    here_route = kwargs.get('here_route', None)
    route_id_field = kwargs.get('route_id_field', None)
    here_link = kwargs.get('here_link', None)
    output_here_link_event = kwargs.get('output_here_link_event', None)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    # Intermediate outputs
    here_link_for_locate= os.path.join(scratch_gdb, 'here_link_for_locate')
    here_link_along_route_locate_table = os.path.join(scratch_gdb, 'here_link_along_route_locate_table')

    arcpy.CopyFeatures_management(here_link, here_link_for_locate)

    # arcpy.MakeFeatureLayer_management(here_link, here_link_for_locate_lyr)
    arcpy.AddField_management(here_link_for_locate, 'TSSID', 'LONG')
    arcpy.CalculateField_management(here_link_for_locate, 'TSSID', '!%s!' % arcpy.Describe(here_link_for_locate).OIDFieldName, 'PYTHON')

    arcpy.LocateFeaturesAlongRoutes_lr(here_link_for_locate, here_route, route_id_field, '0 Meters', here_link_along_route_locate_table,
                                       'RID LINE FMEAS TMEAS')

    arcpy.JoinField_management(here_link_for_locate, 'TSSID', here_link_along_route_locate_table, 'TSSID', ['RID', 'FMEAS', 'TMEAS'])

    # Get links that are correctly located to the candidate route
    here_link_for_locate_lyr = 'here_link_for_locate_lyr'
    arcpy.MakeFeatureLayer_management(here_link_for_locate, here_link_for_locate_lyr)
    arcpy.SelectLayerByAttribute_management(here_link_for_locate_lyr, 'NEW_SELECTION', "{1} IS NOT NULL AND {0} = {1}".format(route_id_field, 'RID'))

    out_here_link_fields = []
    for field in arcpy.ListFields(here_link_for_locate_lyr):
        if field.name.lower() not in ['objectid', 'shape', 'shape_length']:
            out_here_link_fields.append(field.name)

    field_mappings = arcpy.FieldMappings()
    for field in out_here_fields + ['RID', 'FMEAS', 'TMEAS']:
        # arcpy.AddMessage("{0}".format(field))
        field_map = arcpy.FieldMap()
        field_map.addInputField(here_link_for_locate_lyr, field)
        field_name = field_map.outputField
        field_name.name = field if field != 'RID' else 'DOT_RID'
        field_name.aliasName = field if field != 'RID' else 'DOT_RID'
        field_map.outputField = field_name
        field_mappings.addFieldMap(field_map)

    arcpy.FeatureClassToFeatureClass_conversion(here_link_for_locate_lyr, os.path.dirname(output_here_link_event),
                                                os.path.basename(output_here_link_event),
                                                field_mapping=field_mappings)


"""
Head up! In our use cases, if two consecutive vertices have the same m-value, that route is still considered
monotonic (increasing/decreasing with levels). If you want to exclude those routes in the output, you can just
replace the “<=” and “>=” in line 20 & 23 with “<” and “>”
"""
def detect_non_monotonic_routes(route, route_id_field_name):
    sCur = arcpy.SearchCursor(route)
    LoopRouteList = []
    for sRec in sCur:
        shape = sRec.shape
        if not measure_strictly_aligned(shape):
            LoopRouteList.append(sRec.getValue(route_id_field_name))
    return LoopRouteList

def measure_strictly_aligned(shape):
    measure_list = []
    for part_num in xrange(0, shape.partCount):
        for pnt in shape.getPart(part_num):
            if pnt:
                # If the pnt is None, this represents an interior ring
                measure_list.append(pnt.M)
    return strictly_increasing_or_with_levels(measure_list) or strictly_decreasing_or_with_levels(measure_list)

def strictly_increasing_or_with_levels(L):
    return all(x<=y for x, y in zip(L, L[1:]))

def strictly_decreasing_or_with_levels(L):
    return all(x>=y for x, y in zip(L, L[1:]))



if __name__ == '__main__':
    # Get parameters
    match_candidate_table = arcpy.GetParameterAsText(0)
    here_link = arcpy.GetParameterAsText(1)
    here_link_id_field = arcpy.GetParameterAsText(2)
    conf_lvl_thld = arcpy.GetParameterAsText(3)
    output_here_route = arcpy.GetParameterAsText(4)
    output_here_link_event = arcpy.GetParameterAsText(5)
    check_gaps = arcpy.GetParameter(6)
    only_generate_continuous_routes = arcpy.GetParameter(7)
    check_non_monotonic_routes = arcpy.GetParameter(8)
    only_generate_monotonic_routes = arcpy.GetParameter(9)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    SECTION = "candidate_table"
    schemas = default_schemas.get(SECTION)

    candidate_table_here_lid_field = schemas.get('here_lid_field')
    candidate_table_here_st_name_field = schemas.get('here_st_name_field')
    candidate_table_here_cnty_id_field = schemas.get('here_cnty_id_field')
    candidate_table_dot_rid_field = schemas.get('dot_rid_field')
    candidate_table_dot_rt_name_field = schemas.get('dot_rt_name_field')
    candidate_table_dot_cnty_id_field = schemas.get('dot_cnty_id_field')
    candidate_table_conf_lvl_field = schemas.get('conf_lvl_field')
    candidate_table_verified_match_field = schemas.get('verified_match_field')
    candidate_table_false_match_field = schemas.get('false_match_field')

    candidate_table_fields = [candidate_table_here_lid_field, candidate_table_here_st_name_field,
                              candidate_table_here_cnty_id_field, candidate_table_dot_rid_field,
                              candidate_table_dot_rt_name_field, candidate_table_dot_cnty_id_field,
                              candidate_table_conf_lvl_field, candidate_table_verified_match_field,
                              candidate_table_false_match_field]

    conf_lvl_options = ['Medium', 'High', 'User Confirmed']

    # Temporary output
    match_candidate_above_conf_lvl_thld_tabv = 'match_candidate_above_conf_lvl_thld_tbv'
    match_candidate_above_conf_lvl_thld = os.path.join(scratch_gdb, 'match_candidate_above_conf_lvl_thld')
    match_candidate_above_conf_lvl_thld_frq = os.path.join(scratch_gdb, 'match_candidate_above_conf_lvl_thld_frq')
    here_link_copy = os.path.join(scratch_gdb, 'here_link_copy')
    here_link_above_conf_lvl_thld = os.path.join(scratch_gdb, 'here_link_above_conf_lvl_thld')
    here_link_above_conf_lvl_w_rid = os.path.join(scratch_gdb, 'here_link_above_conf_lvl_w_rid')

    try:
        # Get match candidate of interest
        conf_lvl_tbv = []
        for i in range(conf_lvl_options.index(conf_lvl_thld), len(conf_lvl_options)):
            conf_lvl_tbv.append("'{0}'".format(conf_lvl_options[i]))

        where_clause = "{0} IN ({1})".format(candidate_table_conf_lvl_field, ','.join(conf_lvl_tbv))
        arcpy.MakeTableView_management(match_candidate_table, match_candidate_above_conf_lvl_thld_tabv,
                                       where_clause=where_clause)

        arcpy.CopyRows_management(match_candidate_above_conf_lvl_thld_tabv, match_candidate_above_conf_lvl_thld)

        # Check if there any duplicate of match candidates on link id and route id
        arcpy.Frequency_analysis(match_candidate_above_conf_lvl_thld, match_candidate_above_conf_lvl_thld_frq,
                                 frequency_fields=[candidate_table_here_lid_field, candidate_table_dot_rid_field])

        link_route_match_duplicates_dict = {}
        with arcpy.da.SearchCursor(match_candidate_above_conf_lvl_thld_frq,
                                   [candidate_table_here_lid_field, candidate_table_dot_rid_field, 'FREQUENCY']) as sCur:
            for row in sCur:
                here_lid = row[0]
                dot_rid = row[1]
                frq = row[2]

                if frq > 1:
                    if here_lid not in link_route_match_duplicates_dict.keys():
                        link_route_match_duplicates_dict[here_lid] = []
                    if dot_rid not in link_route_match_duplicates_dict[here_lid]:
                        link_route_match_duplicates_dict[here_lid].append(dot_rid)
                    logger.info("Multiple records exist for the match between HERE link (id: '{0}') and DOT route (id: {1})!".format(here_lid, dot_rid))

        del sCur

        if len(link_route_match_duplicates_dict.keys()):
            logger.warning("Please remove all match candidate duplicates listed above before continue!")
            sys.exit()

        # Join one-to-many link route candidates to here link features
        arcpy.CopyFeatures_management(here_link, here_link_copy)

        out_here_fields = []
        for field in arcpy.ListFields(here_link):
            if field.name.lower() not in ['objectid', 'shape', 'shape_length']:
                out_here_fields.append(field.name)

        # Do one-to-many joining by 'Make Query Table'
        here_link_above_conf_lvl_thld_lyr = 'here_link_above_conf_lvl_thld_lyr'
        try:
            # Assumes 'here_link_id_field' and 'candidate_table_here_lid_field' are the same type
            arcpy.MakeQueryTable_management([here_link_copy, match_candidate_above_conf_lvl_thld],
                                            here_link_above_conf_lvl_thld_lyr, 'ADD_VIRTUAL_KEY_FIELD',
                                            where_clause='{0}.{1} = {2}.{3}'.format(os.path.basename(here_link_copy), here_link_id_field,
                                                                                    os.path.basename(match_candidate_above_conf_lvl_thld), candidate_table_here_lid_field))
        except:
            # If they are not the same type, add and use the 'TSS_LID' field (String type)
            arcpy.AddField_management(here_link_copy, 'TSS_LID', 'TEXT', field_length=255)
            arcpy.CalculateField_management(here_link_copy, 'TSS_LID', '!%s!' % candidate_table_here_lid_field, 'PYTHON')
            arcpy.MakeQueryTable_management([here_link_copy, match_candidate_above_conf_lvl_thld],
                                            here_link_above_conf_lvl_thld_lyr, 'ADD_VIRTUAL_KEY_FIELD',
                                            where_clause='{0}.{1} = {2}.{3}'.format(os.path.basename(here_link_copy), 'TSS_LID',
                                                                                    os.path.basename(match_candidate_above_conf_lvl_thld), candidate_table_here_lid_field))

        arcpy.CopyFeatures_management(here_link_above_conf_lvl_thld_lyr, here_link_above_conf_lvl_thld)

        # Format output query table
        # Keep fields originally from the HERE link feature class and the assigned route id field from the match candidate table
        field_mappings = arcpy.FieldMappings()

        for field in out_here_fields:
            field_map = arcpy.FieldMap()
            field_map.addInputField(here_link_above_conf_lvl_thld, '{0}_{1}'.format(os.path.basename(here_link_copy), field))
            field_name = field_map.outputField
            field_name.name = field
            field_name.aliasName = field
            field_map.outputField = field_name
            field_mappings.addFieldMap(field_map)

        field_map = arcpy.FieldMap()
        field_map.addInputField(here_link_above_conf_lvl_thld,
                                '{0}_{1}'.format(os.path.basename(match_candidate_above_conf_lvl_thld), candidate_table_dot_rid_field))
        field_name = field_map.outputField
        field_name.name = candidate_table_dot_rid_field
        field_name.aliasName = candidate_table_dot_rid_field
        field_map.outputField = field_name

        field_mappings.addFieldMap(field_map)

        arcpy.FeatureClassToFeatureClass_conversion(here_link_above_conf_lvl_thld, scratch_gdb,
                                                    os.path.basename(here_link_above_conf_lvl_w_rid),
                                                    field_mapping=field_mappings)

        # Generate HERE route
        generate_here_route(
            here_link = here_link_above_conf_lvl_w_rid,
            route_id_field = candidate_table_dot_rid_field,
            output_here_route = output_here_route,
            check_gaps = check_gaps,
            check_non_monotonic_routes = check_non_monotonic_routes,
            only_generate_continuous_routes = only_generate_continuous_routes,
            only_generate_monotonic_routes = only_generate_monotonic_routes
        )

        # Linear referencing HERE links on HERE route
        linear_reference_here_link_along_route(
            here_route=output_here_route,
            route_id_field=candidate_table_dot_rid_field,
            here_link=here_link_above_conf_lvl_w_rid,
            output_here_link_event=output_here_link_event
        )

    except Exception, err:
        logger.error("Error: {0}".format(err.args[0]))
        logger.error(traceback.format_exc())

        if arcpy.Exists(output_here_route):
            arcpy.Delete_management(output_here_route)

        if arcpy.Exists(output_here_link_event):
            arcpy.Delete_management(output_here_link_event)

    finally:
        clear_scratch_gdb(scratch_gdb)
        pass