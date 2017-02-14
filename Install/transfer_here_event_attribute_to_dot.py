import arcpy
import os
import traceback

from src.util.helper import get_scratch_gdb, clear_scratch_gdb
from src.config.schema import default_schemas
from src.tss.ags.field_util import get_field_details

import logging
logger = logging.getLogger(__name__)


def transfer_here_event_attribute_to_dot(**kwargs):
    logger.info("Start transferring HERE event attributes to DOT...")

    here_event = kwargs.get('here_event', None)
    here_event_lid_field = kwargs.get('here_event_lid_field', None)
    fields_to_transfer = kwargs.get('fields_to_transfer', [])
    xref_table = kwargs.get('xref_table', None)
    dot_route = kwargs.get('dot_route', None)
    dot_route_rid_field = kwargs.get('dot_route_rid_field', None)
    dot_route_fd_field = kwargs.get('dot_route_fd_field', None)
    dot_route_td_field = kwargs.get('dot_route_td_field', None)
    output_event_feature = kwargs.get('output_event_feature', None)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    output_schema_name = 'xref_table'
    schemas = default_schemas.get(output_schema_name)

    xref_here_lid_field = schemas.get('here_lid_field')
    xref_dot_rid_field = schemas.get('dot_rid_field')
    xref_fmeas_field = schemas.get('fmeas_field')
    xref_tmeas_field = schemas.get('tmeas_field')

    # intermediate outputs
    here_event_copy = os.path.join(scratch_gdb, 'here_event_copy')
    xref_table_copy = os.path.join(scratch_gdb, 'xref_table_copy')
    here_event_w_rid_meas_raw = os.path.join(scratch_gdb, 'here_event_w_rid_meas_raw')
    here_event_w_rid_meas = os.path.join(scratch_gdb, 'here_event_w_rid_meas')
    active_dot_network_layer = 'active_{0}'.format(os.path.basename(dot_route))
    here_event_lyr = os.path.join(scratch_gdb, 'here_event_lyr')

    # prepare here event for join. Need to convert the link id field in the input HERE event to the same type of the one
    # in the xref table to make sure they can be joined together correctly
    arcpy.Copy_management(xref_table, xref_table_copy)
    arcpy.CopyFeatures_management(here_event, here_event_copy)
    xref_here_lid_field_details = get_field_details(xref_table_copy, xref_here_lid_field)
    tss_here_lid_field = 'TSS_{0}'.format(here_event_lid_field)
    arcpy.AddField_management(here_event_copy, tss_here_lid_field, xref_here_lid_field_details['field_type'], field_length=255)
    arcpy.CalculateField_management(here_event_copy, tss_here_lid_field, "!{0}!".format(here_event_lid_field), "PYTHON_9.3")

    here_event_w_rid_meas_lyr = 'here_event_w_rid_meas_lyr'
    arcpy.MakeQueryTable_management([here_event_copy, xref_table_copy],
                                    here_event_w_rid_meas_lyr, 'ADD_VIRTUAL_KEY_FIELD',
                                    where_clause='{0}.{1} = {2}.{3}'.format(os.path.basename(here_event_copy), tss_here_lid_field,
                                                                            os.path.basename(xref_table_copy), xref_here_lid_field))

    arcpy.CopyFeatures_management(here_event_w_rid_meas_lyr, here_event_w_rid_meas_raw)

    field_mappings = arcpy.FieldMappings()

    if here_event_lid_field not in fields_to_transfer:
        fields_to_transfer.append(here_event_lid_field)

    for field in fields_to_transfer:
        field_map = arcpy.FieldMap()
        field_map.addInputField(here_event_w_rid_meas_raw, '{0}_{1}'.format(os.path.basename(here_event_copy), field))
        field_name = field_map.outputField
        field_name.name = field
        field_name.aliasName = field
        field_map.outputField = field_name
        field_mappings.addFieldMap(field_map)

    for field in [xref_dot_rid_field, xref_fmeas_field, xref_tmeas_field]:
        field_map = arcpy.FieldMap()
        field_map.addInputField(here_event_w_rid_meas_raw, '{0}_{1}'.format(os.path.basename(xref_table_copy), field))
        field_name = field_map.outputField
        field_name.name = field
        field_name.aliasName = field
        field_map.outputField = field_name
        field_mappings.addFieldMap(field_map)

    arcpy.FeatureClassToFeatureClass_conversion(here_event_w_rid_meas_raw, scratch_gdb, os.path.basename(here_event_w_rid_meas), field_mapping=field_mappings)

    # translate here event into DOT event layer
    active_where_clause = "1=1" if not dot_route_fd_field or not dot_route_td_field else \
        "({start_date_field} is null or {start_date_field} <= CURRENT_TIMESTAMP) and " \
        "({end_date_field} is null or {end_date_field} > CURRENT_TIMESTAMP)".format(
            start_date_field=dot_route_fd_field,
            end_date_field=dot_route_td_field)
    arcpy.MakeFeatureLayer_management(dot_route, active_dot_network_layer, active_where_clause)

    props = '{0} {1} {2} {3}'.format(xref_dot_rid_field, 'LINE', xref_fmeas_field, xref_tmeas_field)
    arcpy.MakeRouteEventLayer_lr(active_dot_network_layer, dot_route_rid_field, here_event_w_rid_meas, props, here_event_lyr)

    arcpy.FeatureClassToFeatureClass_conversion(here_event_lyr, os.path.dirname(output_event_feature),
                                                os.path.basename(output_event_feature))

    logger.info("Finish transferring HERE event attributes to DOT...")


if __name__ == '__main__':
    # Get parameters
    here_event = arcpy.GetParameterAsText(0)
    here_event_lid_field = arcpy.GetParameterAsText(1)
    fields_to_transfer = arcpy.GetParameterAsText(2).split(';') # parameter retrieved as a string separated by semi-comma, convert it to list
    xref_table = arcpy.GetParameterAsText(3)
    dot_route = arcpy.GetParameterAsText(4)
    dot_route_rid_field = arcpy.GetParameterAsText(5)
    dot_route_fd_field = arcpy.GetParameterAsText(6)
    dot_route_td_field = arcpy.GetParameterAsText(7)
    output_event_feature = arcpy.GetParameterAsText(8)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    try:
        transfer_here_event_attribute_to_dot(
            here_event=here_event,
            here_event_lid_field=here_event_lid_field,
            fields_to_transfer=fields_to_transfer,
            xref_table=xref_table,
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

