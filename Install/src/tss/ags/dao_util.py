import arcpy
import os

def clearWSLocks(inputWS):
    """
    Attempts to clear locks on a workspace, returns stupid message.
    """
    if all([arcpy.Exists(inputWS), arcpy.Compact_management(inputWS), arcpy.Exists(inputWS)]):
        return 'Workspace (%s) clear to continue...' % inputWS
    else:
        return '!!!!!!!! ERROR WITH WORKSPACE %s !!!!!!!!' % inputWS

def build_numeric_in_sql_expression(field_name, value_list):
    """
    Build a "in" sql string based on the input field name and value list
    :param field_name:
    :param value_list:
    :return:
    """
    return "%s in (%s)" % (field_name, ",".join(str(value) for value in value_list)) if len(value_list) > 0 else "1=2"


def build_string_in_sql_expression(field_name, value_list):
    """
    Build a "in" sql string based on the input field name and value list
    :param field_name:
    :param value_list:
    :return:
    """
    return "%s in (%s)" % (field_name, ",".join("'" + value + "'" for value in value_list)) if len(value_list) > 0 else "1=2"

def subset_data_exist(data, where_clause):
    """
    Check if data exists with the input where clause
    :param data:
    :param where_clause:
    :return:
    """
    with arcpy.da.SearchCursor(data, "OID@", where_clause) as sCursor:
        try:
            sCursor.next()
            return True
        except StopIteration:
            return False

def delete_subset_data(data, where_clause):
    """
    Delete the records that meets the where clause
    :param data:
    :param where_clause:
    """
    with arcpy.da.UpdateCursor(data, "OID@", where_clause) as uCursor:
        for uRow in uCursor:
            uCursor.deleteRow()

def delete_identical_only_keep_min_oid(data, fields, xy_tolerance="0 Meters"):
    """
    Similar to the DeleteIdentical function in arcpy. This tool goes one more step to only keep the records with the
    smaller id
    :param data:
    :param fields:
    :param xy_tolerance:
    """
    identical_table = "in_memory\\identical_table"
    arcpy.FindIdentical_management(data, identical_table, fields, xy_tolerance, "", "ONLY_DUPLICATES")
    fseq_list = []
    delete_oid_list = []
    sCursor = arcpy.SearchCursor(identical_table, "", "", "FEAT_SEQ;IN_FID", "IN_FID A")
    for sRow in sCursor:
        feat_seq, in_fid = sRow.getValue("FEAT_SEQ"), sRow.getValue("IN_FID")
        if feat_seq not in fseq_list:
            fseq_list.append(feat_seq)
        else:
            delete_oid_list.append(in_fid)
    del sCursor
    oid_field = arcpy.Describe(data).OIDFieldName
    if len(delete_oid_list) != 0:
        where_clause = build_numeric_in_sql_expression(oid_field, delete_oid_list)
        delete_subset_data(data, where_clause)


def get_count(data):
    """
    Wrapper for GetCount_management
    :param data:
    :return:
    """
    return int(arcpy.GetCount_management(data).getOutput(0))

def get_full_table_name(table_name, workspace):
    """
    Qualify the table name and return the full path of the table
    :param table_name:
    :param workspace:
    :return:
    """
    if not ".sde" in workspace:
        return os.path.join(workspace, table_name)
    else:
        parsed_string = arcpy.ParseTableName(table_name, workspace)
        parsed_list = [item.strip() for item in parsed_string.split(",")]
        parsed_table_name = ".".join([item for item in parsed_list if item])
        return os.path.join(workspace, parsed_table_name)