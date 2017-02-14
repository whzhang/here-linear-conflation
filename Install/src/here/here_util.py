import arcpy
import os
import logging

from src.util.helper import get_default_parameters

logger = logging.getLogger(__name__)

SECTION = 'Default'
Config = get_default_parameters()

def matching_route_by_id(candidate_table):
    arcpy.AddMessage("Matching routes by ID...")

    here_route_id_delimiter = Config.get(SECTION,'here_route_id_delimiter')
    here_route_type_pos = Config.get(SECTION,'here_route_type_pos')
    here_route_number_pos = Config.get(SECTION,'here_route_number_pos')
    here_route_direction_pos = Config.get(SECTION,'here_route_direction_pos')
    target_route_id_delimiter = Config.get(SECTION,'target_route_id_delimiter')
    target_route_type_start_pos = Config.get(SECTION,'target_route_type_start_pos')
    target_route_type_end_pos = Config.get(SECTION,'target_route_type_end_pos')
    target_route_number_start_pos = Config.get(SECTION,'target_route_number_start_pos')
    target_route_number_end_pos = Config.get(SECTION,'target_route_number_end_pos')
    route_type_naming_convention = Config.get(SECTION,'route_type_naming_convention')

    rules = [here_route_id_delimiter,here_route_type_pos,here_route_number_pos,here_route_direction_pos,\
             target_route_id_delimiter,target_route_type_start_pos,target_route_type_end_pos,\
             target_route_number_start_pos,target_route_number_end_pos,route_type_naming_convention]

    with arcpy.da.UpdateCursor(candidate_table, ['TargetRoute','SourceRoute','IsRouteIdMatching']) as uCur_candidate:
        for candidate in uCur_candidate:
            target_route = candidate[0]
            source_route = candidate[1]

            # arcpy.AddMessage(target_route+"-"+source_route)
            if compare_route_id(rules,source_route,target_route):
                candidate[2] = "YES"
                uCur_candidate.updateRow(candidate)
            else:
                candidate[2] = "NO"
                uCur_candidate.updateRow(candidate)

    return True


def compare_route_id(rules,source_rid,target_rid):
    # ToDo: needs to be rewrite to handle different name structure. Current algorithm only fits for state routes

    import re

    here_route_id_delimiter = rules[0]
    here_route_type_pos = rules[1]
    here_route_number_pos = rules[2]
    here_route_direction_pos = rules[3]
    target_route_id_delimiter = rules[4]
    target_route_type_start_pos = rules[5]
    target_route_type_end_pos = rules[6]
    target_route_number_start_pos = rules[7]
    target_route_number_end_pos = rules[8]
    route_type_naming_convention = rules[9]

    src_route_delimiter = re.split(";",here_route_id_delimiter.replace("space"," "))
    delimiters = "|".join(src_route_delimiter)

    source_rid_list = re.split(delimiters,source_rid)

    target_rid_type = target_rid[(target_route_type_start_pos-1):target_route_type_end_pos]
    target_rid_number = str(int(target_rid[(target_route_number_start_pos-1):target_route_number_end_pos]))
    target_rid_parsed = target_rid_type+"-"+target_rid_number

    # Additional criterion.(Converntion: [HERE,DOT])
    route_type_naming_convention_list = []
    for item in re.split(";",route_type_naming_convention):
        route_type_naming_convention_list.append(re.split(" ",item))

    flg = False
    isConstructID = False

    for criterion in route_type_naming_convention_list:
        if source_rid_list[here_route_type_pos-1] == criterion[0]:
            source_rid_list[here_route_type_pos-1] = criterion[1]
            isConstructID = True

    # reconstruct source route name ignoring route direction
    if isConstructID:
        src_rid_parsed = source_rid_list[here_route_type_pos-1]+"-"+source_rid_list[here_route_number_pos-1]
    else:
        src_rid_parsed = source_rid

    # arcpy.AddMessage(target_rid+"-"+source_rid)
    # arcpy.AddMessage(target_rid_parsed+"-"+src_rid_parsed)

    if src_rid_parsed == target_rid_parsed:
        flg = True

    return flg


def calculate_confidence_level(candidate_table):
    logger.info("Calculating Confidence Level...")

    with arcpy.da.UpdateCursor(candidate_table,["NumMatchingIntersection","IsRouteIdMatching","ConfidenceLevel"]) as uCur_candidate:
        for candidate in uCur_candidate:
            numMatchingIntersection = candidate[0]
            isRouteIDMatching = candidate[1]

            if numMatchingIntersection >= 2:
                if isRouteIDMatching == "YES":
                    candidate[2] = "HIGH"
                else:
                    candidate[2] = "MEDIUM"
            elif numMatchingIntersection > 0:
                if isRouteIDMatching == "YES":
                    candidate[2] = "MEDIUM"
                else:
                    candidate[2] = "LOW"
            else:
                candidate[2] = "LOW"

            uCur_candidate.updateRow(candidate)


def matching_intersections_func(source_intersections,target_intersections,search_radius,source_intersections_LUT,target_intersections_LUT,candidate_table):
    logger.info("Matching intersections...")

    # Intermediate Data
    near_table = "NEAR_Table"

    # generate near table
    arcpy.GenerateNearTable_analysis(source_intersections, target_intersections, near_table, search_radius,\
                                     'NO_LOCATION', 'NO_ANGLE', 'ALL', '0', 'PLANAR')

    # add 'IN_INTERSECTIONID' and "NEAR_INTERSECTIONID" to the near tbale
    arcpy.AddField_management(near_table,"IN_INTERSECTION_ID","LONG")
    arcpy.AddField_management(near_table,"NEAR_INTERSECTION_ID","LONG")

    # arcpy.AddMessage("Updating near table...")

    with arcpy.da.UpdateCursor(near_table,["IN_FID","NEAR_FID","IN_INTERSECTION_ID","NEAR_INTERSECTION_ID"]) as uCur_near:
        for row in uCur_near:
            in_id = row[0]
            near_id = row[1]

            with arcpy.da.SearchCursor(source_intersections,["OBJECTID","INTERSECTION_ID"],where_clause = "OBJECTID = "+str(in_id)) as sCur_src_intersection:
                for src_intersection in sCur_src_intersection:
                    row[2] = src_intersection[1]

            with arcpy.da.SearchCursor(target_intersections,["OBJECTID","INTERSECTION_ID"],where_clause = "OBJECTID = "+str(near_id)) as sCur_tgt_intersection:
                for tgt_intersection in sCur_tgt_intersection:
                    row[3] = tgt_intersection[1]

            uCur_near.updateRow(row)

    # matching intersections
    # arcpy.AddMessage("Start matching intersections...")
    with arcpy.da.UpdateCursor(candidate_table,["TargetRoute","SourceRoute","NumMatchingIntersection"]) as uCursor:
        for candidate in uCursor:
            target_route = candidate[0]
            source_route = candidate[1]
            # arcpy.AddMessage(target_route+"-"+source_route)
            sCur_sourceLUT = arcpy.da.SearchCursor(source_intersections_LUT,["INTERSECTION_ID","ON_ROUTE_ID"],where_clause = "ON_ROUTE_ID = '"+source_route+"'")
            # check if source route has intersections. Add intersection ids to list if yes. Update candidate table and go to next candidate pair if no
            try:
                sCur_sourceLUT.reset()
                sCur_sourceLUT.next()
                sCur_sourceLUT.reset()
                intersections_source_route = []
                for intersection in sCur_sourceLUT:
                    intersections_source_route.append(intersection[0])
            except:
                candidate[2] = 0
                uCursor.updateRow(candidate)
                continue

            sCur_targetLUT = arcpy.da.SearchCursor(target_intersections_LUT,["INTERSECTION_ID","ON_ROUTE_ID"],where_clause = "ON_ROUTE_ID = '"+target_route+"'")

            # check if target route has intersections. Add intersection ids to list if yes. Update candidate table and go to next candidate pair if no
            try:
                sCur_targetLUT.reset()
                sCur_targetLUT.next()
                sCur_targetLUT.reset()
                intersections_target_route = []
                for intersection in sCur_targetLUT:
                    intersections_target_route.append(intersection[0])
            except:
                candidate[2] = 0
                uCursor.updateRow(candidate)
                continue

            count = 0
            for intersection_id in intersections_source_route:
                with arcpy.da.SearchCursor(near_table,["IN_INTERSECTIONID","NEAR_INTERSECTIONID"],where_clause = "IN_INTERSECTIONID = "+str(intersection_id)) as sCur_near:
                    try:
                        sCur_near.reset()
                        sCur_near.next()
                        sCur_near.reset()

                        for matchingIntersections in sCur_near:
                            near_fid = matchingIntersections[1]
                            if near_fid in intersections_target_route:
                                count+=1
                    except:
                        continue

            candidate[2] = count
            uCursor.updateRow(candidate)

    arcpy.Delete_management(near_table)

    return True