import arcpy
import pythonaddins
import os
import traceback

from src.util.helper import get_scratch_gdb, clear_scratch_gdb
from src.config.schema import default_schemas

import logging
logger = logging.getLogger(__name__)

measure_decimal_places = 3

def generate_link_route_xref_table(**kwargs):
    logger.info("Start generating the XREF table...")

    here_route = kwargs.get('here_route', None)
    here_route_rid_field = kwargs.get('here_route_rid_field', None)
    here_link_event = kwargs.get('here_link_event', None)
    here_link_event_lid_field = kwargs.get('here_link_event_lid_field', None)
    here_link_event_rid_field = kwargs.get('here_link_event_rid_field', None)
    here_link_event_fmeas_field = kwargs.get('here_link_event_fmeas_field', None)
    here_link_event_tmeas_field = kwargs.get('here_link_event_tmeas_field', None)
    dot_route = kwargs.get('dot_route', None)
    dot_route_rid_field = kwargs.get('dot_route_rid_field', None)
    dot_route_fd_field = kwargs.get('dot_route_fd_field', None)
    dot_route_td_field = kwargs.get('dot_route_td_field', None)
    output_xref_table = kwargs.get('output_xref_table', None)

    output_schema_name = 'xref_table'
    schemas = default_schemas.get(output_schema_name)

    output_here_lid_field = schemas.get('here_lid_field')
    output_dot_rid_field = schemas.get('dot_rid_field')
    output_fmeas_field = schemas.get('fmeas_field')
    output_tmeas_field = schemas.get('tmeas_field')

    # Intermediate output
    active_dot_network_layer = 'active_{0}'.format(os.path.basename(dot_route))


    link_route_measure_dict = {}
    with arcpy.da.SearchCursor(here_link_event, [here_link_event_lid_field, here_link_event_rid_field,
                                                 here_link_event_fmeas_field, here_link_event_tmeas_field]) as sCur:
        for row in sCur:
            here_lid = row[0]
            here_rid = row[1]
            here_fmeas = row[2]
            here_tmeas = row[3]

            if here_lid not in link_route_measure_dict.keys():
                link_route_measure_dict[here_lid] = {}

            if here_rid not in link_route_measure_dict[here_lid].keys():
                link_route_measure_dict[here_lid][here_rid] = {}

            link_route_measure_dict[here_lid][here_rid]['fmeas'] = here_fmeas
            link_route_measure_dict[here_lid][here_rid]['tmeas'] = here_tmeas

    del sCur

    here_route_dict = {}
    with arcpy.da.SearchCursor(here_route, [here_route_rid_field, 'SHAPE@']) as sCur:
        for row in sCur:
            here_rid = row[0]
            shape = row[1]

            if shape is None:
                continue

            if here_rid not in here_route_dict.keys():
                here_route_dict[here_rid] = {}

            here_route_dict[here_rid]['length'] = shape.length
            here_route_dict[here_rid]['mmax'] = shape.extent.MMax
            here_route_dict[here_rid]['mmin'] = shape.extent.MMin

    del sCur

    dot_route_dict = {}
    active_where_clause = "1=1" if not dot_route_fd_field or not dot_route_td_field else \
        "({start_date_field} is null or {start_date_field} <= CURRENT_TIMESTAMP) and " \
        "({end_date_field} is null or {end_date_field} > CURRENT_TIMESTAMP)".format(
            start_date_field=dot_route_fd_field,
            end_date_field=dot_route_td_field)
    arcpy.MakeFeatureLayer_management(dot_route, active_dot_network_layer, active_where_clause)
    with arcpy.da.SearchCursor(active_dot_network_layer, [dot_route_rid_field, 'SHAPE@']) as sCur:
        for row in sCur:
            dot_rid = row[0]
            shape = row[1]

            if shape is None:
                continue

            if dot_rid not in dot_route_dict.keys():
                dot_route_dict[dot_rid] = {}

            dot_route_dict[dot_rid]['length'] = shape.length
            dot_route_dict[dot_rid]['mmax'] = shape.extent.MMax
            dot_route_dict[dot_rid]['mmin'] = shape.extent.MMin

    del sCur

    # create XREF table
    arcpy.CreateTable_management(os.path.dirname(output_xref_table), os.path.basename(output_xref_table))
    arcpy.AddField_management(output_xref_table, output_here_lid_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_xref_table, output_dot_rid_field, "TEXT", field_length=255)
    arcpy.AddField_management(output_xref_table, output_fmeas_field, "DOUBLE")
    arcpy.AddField_management(output_xref_table, output_tmeas_field, "DOUBLE")

    xref_table_fields = [output_here_lid_field, output_dot_rid_field, output_fmeas_field, output_tmeas_field]

    with arcpy.da.InsertCursor(output_xref_table, xref_table_fields) as iCur:
        for here_lid, here_route_info in link_route_measure_dict.items():
            for here_rid, here_link_measures in here_route_info.items():
                here_fmeas = here_link_measures['fmeas']
                here_tmeas = here_link_measures['tmeas']

                here_route_length = here_route_dict[here_rid]['length'] if here_rid in here_route_dict.keys() else None
                here_route_mmax = here_route_dict[here_rid]['mmax'] if here_rid in here_route_dict.keys() else None
                here_route_mmin = here_route_dict[here_rid]['mmin'] if here_rid in here_route_dict.keys() else None
                dot_route_length = dot_route_dict[here_rid]['length'] if here_rid in dot_route_dict.keys() else None
                dot_route_mmax = dot_route_dict[here_rid]['mmax'] if here_rid in dot_route_dict.keys() else None
                dot_route_mmin = dot_route_dict[here_rid]['mmin'] if here_rid in dot_route_dict.keys() else None

                if here_route_length is None or here_route_mmax is None or here_route_mmin is None:
                    arcpy.AddWarning("HERE route '{0}' has invalid geometry!".format(here_rid))
                    arcpy.AddWarning("### Details: {0}, {1}, {2} ###".format(here_route_length, here_route_mmax, here_route_mmin))
                    continue
                if dot_route_length is None or dot_route_mmax is None or dot_route_mmin is None:
                    arcpy.AddWarning("DOT route '{0}' has invalid geometry!".format(here_rid))
                    arcpy.AddWarning("### Details: {0}, {1}, {2} ###".format(dot_route_length, dot_route_mmax, dot_route_mmin))
                    continue

                here_dot_length_ratio = here_route_length / dot_route_length
                here_measure_length_ratio = abs(here_route_mmax - here_route_mmin) / here_route_length
                dot_measure_length_ratio = abs(dot_route_mmax - dot_route_mmin) / dot_route_length

                adjusted_here_fmeas = round((here_fmeas - here_route_mmin) / here_measure_length_ratio / here_dot_length_ratio * dot_measure_length_ratio + dot_route_mmin, measure_decimal_places)
                adjusted_here_tmeas = round((here_tmeas - here_route_mmin) / here_measure_length_ratio / here_dot_length_ratio * dot_measure_length_ratio + dot_route_mmin, measure_decimal_places)

                iCur.insertRow((here_lid, here_rid, adjusted_here_fmeas, adjusted_here_tmeas))

    logger.info("The XREF table has been generated successfully! '{0}'".format(output_xref_table))


if __name__ == '__main__':
    # Get parameters
    here_route = arcpy.GetParameterAsText(0)
    here_route_rid_field = arcpy.GetParameterAsText(1)
    here_link_event = arcpy.GetParameterAsText(2)
    here_link_event_lid_field = arcpy.GetParameterAsText(3)
    here_link_event_rid_field = arcpy.GetParameterAsText(4)
    here_link_event_fmeas_field = arcpy.GetParameterAsText(5)
    here_link_event_tmeas_field = arcpy.GetParameterAsText(6)
    dot_route = arcpy.GetParameterAsText(7)
    dot_route_rid_field = arcpy.GetParameterAsText(8)
    dot_route_fd_field = arcpy.GetParameterAsText(9)
    dot_route_td_field = arcpy.GetParameterAsText(10)
    output_xref_table = arcpy.GetParameterAsText(11)

    scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
    scratch_gdb = get_scratch_gdb(scratch_folder)

    arcpy.env.workspace = scratch_gdb
    arcpy.env.overwriteOutput = True

    try:
        generate_link_route_xref_table(
            here_route=here_route,
            here_route_rid_field=here_route_rid_field,
            here_link_event=here_link_event,
            here_link_event_lid_field=here_link_event_lid_field,
            here_link_event_rid_field=here_link_event_rid_field,
            here_link_event_fmeas_field=here_link_event_fmeas_field,
            here_link_event_tmeas_field=here_link_event_tmeas_field,
            dot_route=dot_route,
            dot_route_rid_field=dot_route_rid_field,
            dot_route_fd_field=dot_route_fd_field,
            dot_route_td_field=dot_route_td_field,
            output_xref_table=output_xref_table
        )
    except Exception, err:
        logger.error("Error: {0}".format(err.args[0]))
        logger.error(traceback.format_exc())

    finally:
        clear_scratch_gdb(scratch_gdb)
        pass


