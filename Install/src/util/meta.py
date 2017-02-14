import os
import arcpy
from src.tss.ags import get_full_table_name

import logging
logger = logging.getLogger(__name__)

# Variables
intersection_manager_inf = "Intersection_Manager_Metadata"

def write_im_meta_data(outputGdb, component, create_date=None, update_date=None):
    meta_data_table = os.path.join(outputGdb, intersection_manager_inf)

    if not arcpy.Exists(meta_data_table):
        arcpy.CreateTable_management(outputGdb, intersection_manager_inf)
        arcpy.AddField_management(meta_data_table, "Component", "TEXT", field_length=50)
        arcpy.AddField_management(meta_data_table, "create_date", "DATE")
        arcpy.AddField_management(meta_data_table, "last_update_date", "DATE")

    if create_date is not None:
        with arcpy.da.UpdateCursor(meta_data_table, ["Component", "create_date"]) as uCur:
            for uRow in uCur:
                if uRow[0] == component:
                    uRow[1] = create_date
                    uCur.updateRow(uRow)
                    return

        iCur = arcpy.da.InsertCursor(meta_data_table, ["Component", "create_date"])
        iCur.insertRow([component, create_date])

    if update_date is not None:
        with arcpy.da.UpdateCursor(meta_data_table, ["Component", "last_update_date"]) as uCur:
            for uRow in uCur:
                if uRow[0] == component:
                    uRow[1] = update_date
                    uCur.updateRow(uRow)

def read_im_meta_data(outputGdb, component):
    logger.info("read intersection manager meta data")
    meta_data_table = get_full_table_name(intersection_manager_inf, outputGdb)
    create_update_date_dict = {"create_date": None, "last_update_date": None}
    if not arcpy.Exists(meta_data_table):
        logger.info("intersection meta table not found")
        return create_update_date_dict
    with arcpy.da.SearchCursor(meta_data_table, ["component", "create_date", "last_update_date"]) as sCursor:
        for sRow in sCursor:
            if sRow[0] == component:
                create_update_date_dict = {"Component": component, "create_date": sRow[1], "last_update_date": sRow[2]}
    logger.info("create update date dict" + str(create_update_date_dict))
    return create_update_date_dict