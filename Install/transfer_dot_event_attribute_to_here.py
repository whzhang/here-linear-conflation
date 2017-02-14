import arcpy
import os
import traceback

from src.tss.ags.field_util import get_field_details
from src.tss.ags import build_numeric_in_sql_expression, build_string_in_sql_expression
from src.util.helper import get_scratch_gdb, clear_scratch_gdb
from src.config.schema import default_schemas

import logging
logger = logging.getLogger(__name__)

measure_decimal_places = 3

def transfer_dot_event_attribute_to_here(**kwargs):
    logger.info("Start transferring DOT event attributes to HERE...")

    dot_event = kwargs.get('dot_event', None)
    dot_event_rid_field = kwargs.get('dot_event_rid_field', None)
    dot_event_fmeas_field = kwargs.get('dot_event_fmeas_field', None)
    dot_event_tmeas_field = kwargs.get('dot_event_tmeas_field', None)
    dot_event_fd_field = kwargs.get('dot_event_fd_field', None)
    dot_event_td_field = kwargs.get('dot_event_td_field', None)
    fields_to_transfer = kwargs.get('fields_to_transfer', None)
    here_route = kwargs.get('here_route', None)
    here_route_rid_field = kwargs.get('here_route_rid_field', None)
    dot_route = kwargs.get('dot_route', None)
    dot_route_rid_field = kwargs.get('dot_route_rid_field', None)
    dot_route_fd_field = kwargs.get('dot_route_fd_field', None)
    dot_route_td_field = kwargs.get('dot_route_td_field', None)
    output_event_feature = kwargs.get('output_event_feature', None)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    # intermediate outputs
    active_dot_network_layer = 'active_{0}'.format(os.path.basename(dot_route))
    active_dot_event = os.path.join(scratch_gdb, 'active_dot_event')
    dot_event_tbt = os.path.join(scratch_gdb, 'dot_event_tbt')
    dot_event_tbl = os.path.join(scratch_gdb, 'dot_event_tbl')
    here_event_lyr = os.path.join(scratch_gdb, 'here_event_lyr')

    # get HERE route info
    here_route_info_dict = {}
    with arcpy.da.SearchCursor(here_route, [here_route_rid_field, 'SHAPE@']) as sCur:
        for row in sCur:
            here_rid = row[0]
            shape = row[1]

            if shape is None:
                continue

            if here_rid not in here_route_info_dict.keys():
                here_route_info_dict[here_rid] = {}

            here_route_info_dict[here_rid]['length'] = shape.length
            here_route_info_dict[here_rid]['mmax'] = shape.extent.MMax
            here_route_info_dict[here_rid]['mmin'] = shape.extent.MMin
    del sCur

    # get DOT route info (only those match HERE routes)
    active_where_clause = "1=1" if not dot_route_fd_field or not dot_route_td_field else \
        "({start_date_field} is null or {start_date_field} <= CURRENT_TIMESTAMP) and " \
        "({end_date_field} is null or {end_date_field} > CURRENT_TIMESTAMP)".format(
            start_date_field=dot_route_fd_field,
            end_date_field=dot_route_td_field)
    arcpy.MakeFeatureLayer_management(dot_route, active_dot_network_layer, active_where_clause)

    dot_route_info_dict = {}
    with arcpy.da.SearchCursor(active_dot_network_layer, [dot_route_rid_field, 'SHAPE@']) as sCur:
        for row in sCur:
            dot_rid = row[0]
            shape = row[1]

            if shape is None:
                continue

            if dot_rid not in here_route_info_dict.keys():
                continue

            if dot_rid not in dot_route_info_dict.keys():
                dot_route_info_dict[dot_rid] = {}

            dot_route_info_dict[dot_rid]['length'] = shape.length
            dot_route_info_dict[dot_rid]['mmax'] = shape.extent.MMax
            dot_route_info_dict[dot_rid]['mmin'] = shape.extent.MMin
    del sCur

    # translate dot event into HERE event layer
    active_where_clause = "1=1" if not dot_route_fd_field or not dot_route_td_field else \
        "({start_date_field} is null or {start_date_field} <= CURRENT_TIMESTAMP) and " \
        "({end_date_field} is null or {end_date_field} > CURRENT_TIMESTAMP)".format(
            start_date_field=dot_event_fd_field,
            end_date_field=dot_event_td_field)
    arcpy.MakeFeatureLayer_management(dot_event, active_dot_event, active_where_clause)

    dot_event_rid_field_details = get_field_details(active_dot_event, dot_event_rid_field)
    where_clause = build_string_in_sql_expression(dot_event_rid_field, dot_route_info_dict.keys()) \
        if dot_event_rid_field_details['field_type'] == 'TEXT' else build_numeric_in_sql_expression(dot_event_rid_field, dot_route_info_dict.keys())

    arcpy.FeatureClassToFeatureClass_conversion(active_dot_event, scratch_gdb, os.path.basename(dot_event_tbt), where_clause)

    dot_event_fmeas_field_details = get_field_details(dot_event_tbt, dot_event_fmeas_field)
    dot_event_fmeas_field_adjusted = 'ADJUSTED_{0}'.format(dot_event_fmeas_field)
    arcpy.AddField_management(dot_event_tbt, dot_event_fmeas_field_adjusted, dot_event_fmeas_field_details['field_type'])

    if dot_event_tmeas_field:
        dot_event_tmeas_field_details = get_field_details(dot_event_tbt, dot_event_tmeas_field)
        dot_event_tmeas_field_adjusted = 'ADJUSTED_{0}'.format(dot_event_tmeas_field)
        arcpy.AddField_management(dot_event_tbt, dot_event_tmeas_field_adjusted, dot_event_tmeas_field_details['field_type'])

        fields = [dot_event_rid_field, dot_event_fmeas_field, dot_event_tmeas_field, dot_event_fmeas_field_adjusted, dot_event_tmeas_field_adjusted]
        with arcpy.da.UpdateCursor(dot_event_tbt, fields) as uCur:
            for row in uCur:
                rid = row[0]
                fmeas = row[1]
                tmeas = row[2]

                dot_route_length = dot_route_info_dict[rid]['length']
                dot_route_mmax = dot_route_info_dict[rid]['mmax']
                dot_route_mmin = dot_route_info_dict[rid]['mmin']
                here_route_length = here_route_info_dict[rid]['length']
                here_route_mmax = here_route_info_dict[rid]['mmax']
                here_route_mmin = here_route_info_dict[rid]['mmin']

                dot_here_length_ratio = dot_route_length / here_route_length
                here_measure_length_ratio = abs(here_route_mmax - here_route_mmin) / here_route_length
                dot_measure_length_ratio = abs(dot_route_mmax - dot_route_mmin) / dot_route_length

                row[3] = round((fmeas - dot_route_mmin) / dot_measure_length_ratio / dot_here_length_ratio * here_measure_length_ratio + here_route_mmin, measure_decimal_places)
                row[4] = round((tmeas - dot_route_mmin) / dot_measure_length_ratio / dot_here_length_ratio * here_measure_length_ratio + here_route_mmin, measure_decimal_places)

                uCur.updateRow(row)
        del uCur

        props = '{0} {1} {2} {3}'.format(dot_event_rid_field, 'LINE', dot_event_fmeas_field_adjusted, dot_event_tmeas_field_adjusted)
        arcpy.CopyRows_management(dot_event_tbt, dot_event_tbl)
        arcpy.MakeRouteEventLayer_lr(here_route, here_route_rid_field, dot_event_tbl, props, here_event_lyr)

        field_mappings = arcpy.FieldMappings()
        for field in [dot_event_rid_field, dot_event_fmeas_field_adjusted, dot_event_tmeas_field_adjusted] + fields_to_transfer:
            field_map = arcpy.FieldMap()
            field_map.addInputField(here_event_lyr, field)
            field_name = field_map.outputField
            if field == dot_event_fmeas_field_adjusted:
                field_name.name = dot_event_fmeas_field
                field_name.aliasName = dot_event_fmeas_field
            elif field == dot_event_tmeas_field_adjusted:
                field_name.name = dot_event_tmeas_field
                field_name.aliasName = dot_event_tmeas_field
            elif field == dot_event_fmeas_field:
                field_name.name = 'DOT_{0}'.format(dot_event_fmeas_field)
                field_name.aliasName = 'DOT_{0}'.format(dot_event_fmeas_field)
            elif field == dot_event_tmeas_field:
                field_name.name = 'DOT_{0}'.format(dot_event_tmeas_field)
                field_name.aliasName = 'DOT_{0}'.format(dot_event_tmeas_field)
            else:
                field_name.name = field
                field_name.aliasName = field
            field_map.outputField = field_name
            field_mappings.addFieldMap(field_map)

        arcpy.FeatureClassToFeatureClass_conversion(here_event_lyr, os.path.dirname(output_event_feature),
                                                    os.path.basename(output_event_feature), field_mapping=field_mappings)

    else:
        fields = [dot_event_rid_field, dot_event_fmeas_field, dot_event_fmeas_field_adjusted]
        with arcpy.da.UpdateCursor(dot_event_tbt, fields) as uCur:
            for row in uCur:
                rid = row[0]
                fmeas = row[1]

                dot_route_length = dot_route_info_dict[rid]['length']
                dot_route_mmax = dot_route_info_dict[rid]['mmax']
                dot_route_mmin = dot_route_info_dict[rid]['mmin']
                here_route_length = here_route_info_dict[rid]['length']
                here_route_mmax = here_route_info_dict[rid]['mmax']
                here_route_mmin = here_route_info_dict[rid]['mmin']

                dot_here_length_ratio = dot_route_length / here_route_length
                here_measure_length_ratio = abs(here_route_mmax - here_route_mmin) / here_route_length
                dot_measure_length_ratio = abs(dot_route_mmax - dot_route_mmin) / dot_route_length
                row[2] = round((fmeas + dot_route_mmin) / dot_measure_length_ratio / dot_here_length_ratio * here_measure_length_ratio + here_route_mmin, measure_decimal_places)

                uCur.updateRow(row)
        del uCur

        props = '{0} {1} {2}'.format(dot_event_rid_field, 'POINT', dot_event_fmeas_field_adjusted)
        arcpy.CopyRows_management(dot_event_tbt, dot_event_tbl)
        arcpy.MakeRouteEventLayer_lr(here_route, here_route_rid_field, dot_event_tbl, props, here_event_lyr)

        field_mappings = arcpy.FieldMappings()
        for field in [dot_event_rid_field, dot_event_fmeas_field_adjusted] + fields_to_transfer:
            field_map = arcpy.FieldMap()
            field_map.addInputField(here_event_lyr, field)
            field_name = field_map.outputField
            if field == dot_event_fmeas_field_adjusted:
                field_name.name = dot_event_fmeas_field
                field_name.aliasName = dot_event_fmeas_field
            elif field == dot_event_fmeas_field:
                field_name.name = 'DOT_{0}'.format(dot_event_fmeas_field)
                field_name.aliasName = 'DOT_{0}'.format(dot_event_fmeas_field)
            else:
                field_name.name = field
                field_name.aliasName = field
            field_map.outputField = field_name
            field_mappings.addFieldMap(field_map)

        arcpy.FeatureClassToFeatureClass_conversion(here_event_lyr, os.path.dirname(output_event_feature),
                                                    os.path.basename(output_event_feature), field_mapping=field_mappings)

    logger.info("Finish transferring DOT event attributes to HERE...")


if __name__ == '__main__':
    # Get parameters
    dot_event = arcpy.GetParameterAsText(0)
    dot_event_rid_field = arcpy.GetParameterAsText(1)
    dot_event_fmeas_field = arcpy.GetParameterAsText(2)
    dot_event_tmeas_field = arcpy.GetParameterAsText(3)
    dot_event_fd_field = arcpy.GetParameterAsText(4)
    dot_event_td_field = arcpy.GetParameterAsText(5)
    fields_to_transfer = arcpy.GetParameterAsText(6).split(';')
    here_route = arcpy.GetParameterAsText(7)
    here_route_rid_field = arcpy.GetParameterAsText(8)
    dot_route = arcpy.GetParameterAsText(9)
    dot_route_rid_field = arcpy.GetParameterAsText(10)
    dot_route_fd_field = arcpy.GetParameterAsText(11)
    dot_route_td_field = arcpy.GetParameterAsText(12)
    output_event_feature = arcpy.GetParameterAsText(13)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    output_schema_name = 'xref_table'
    schemas = default_schemas.get(output_schema_name)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    try:
        transfer_dot_event_attribute_to_here(
            dot_event=dot_event,
            dot_event_rid_field=dot_event_rid_field,
            dot_event_fmeas_field=dot_event_fmeas_field,
            dot_event_tmeas_field=dot_event_tmeas_field,
            dot_event_fd_field=dot_event_fd_field,
            dot_event_td_field=dot_event_td_field,
            fields_to_transfer=fields_to_transfer,
            here_route=here_route,
            here_route_rid_field=here_route_rid_field,
            dot_route=dot_route,
            dot_route_rid_field=dot_route_rid_field,
            dot_route_fd_field=dot_route_fd_field,
            dot_route_td_field=dot_route_td_field,
            output_event_feature=output_event_feature
        )

    except Exception, err:
        logger.error("Error: {0}".format(err.args[0]))
        logger.error(traceback.format_exc())

    finally:
        # clear_scratch_gdb(scratch_gdb)
        pass
