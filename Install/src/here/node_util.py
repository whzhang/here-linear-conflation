import arcpy
import logging
logger = logging.getLogger(__name__)

# intermediate data ----------------------------------------------------------------------------------------------------
here_links_endpoints_start = 'here_links_endpoints_start'
here_links_endpoints_end = 'here_links_endpoints_end'
here_ref_nodes = 'here_ref_nodes'
here_links_endpoints_join = 'here_links_endpoints_join'
here_links_endpoints_missnodes_w_duplicates = 'here_links_endpoints_missnodes_w_duplicates'
here_links_endpoints_missnodes = 'here_links_endpoints_missnodes'

locate_nodes_along_network_w_duplicates = 'LOCATE_NODES_ALONG_NETWORK_w_duplicates'
locate_nodes_along_network_frequency = 'LOCATE_NODES_ALONG_NETWORK_FREQUENCY'
# ----------------------------------------------------------------------------------------------------------------------

class Node:
    def __init__(self, **kwargs):
        self.link = kwargs.get('link', None)
        self.link_id_field = kwargs.get('link_id_field', None)
        self.ref_node_id_field = kwargs.get('ref_node_id_field', None)
        self.non_ref_node_id_field = kwargs.get('non_ref_node_id_field', None)

        self.node = kwargs.get('node', None)
        self.node_id_field = kwargs.get('node_id_field', None)

        self.network = kwargs.get('network', None)
        self.network_route_id_field = kwargs.get('network_route_id_field', None)

        self.candidate_table = kwargs.get('candidate_table', None)

        self.search_radius = kwargs.get('search_radius', None)

    def identify_node(self):
        # NOTE: node = all reference nodes + partial non-reference nodes(missing node)
        logger.info("Identifying HERE Link Nodes...")

        # identify endpoints of links
        arcpy.FeatureVerticesToPoints_management(self.link, here_links_endpoints_start, "START")
        arcpy.FeatureVerticesToPoints_management(self.link, here_links_endpoints_end, "END")

        # remove duplicates in reference nodes
        arcpy.Dissolve_management(here_links_endpoints_start,here_ref_nodes, [self.ref_node_id_field], multi_part='SINGLE_PART')
        arcpy.SpatialJoin_analysis(here_links_endpoints_end, here_ref_nodes, here_links_endpoints_join,\
                                   'JOIN_ONE_TO_MANY', 'KEEP_ALL', '', 'INTERSECT')

        # get missing nodes
        arcpy.Select_analysis(here_links_endpoints_join,here_links_endpoints_missnodes_w_duplicates, where_clause='JOIN_FID = -1')

        # remove duplicates in missing nodes
        arcpy.Dissolve_management(here_links_endpoints_missnodes_w_duplicates,here_links_endpoints_missnodes, [self.non_ref_node_id_field], multi_part='SINGLE_PART')

        # populate node id for reference node
        arcpy.AddField_management(here_ref_nodes,self.node_id_field,'LONG')
        arcpy.CalculateField_management(here_ref_nodes,self.node_id_field,'[{0}]'.format(self.ref_node_id_field))

        fields = arcpy.ListFields(here_ref_nodes)
        delete_fields = []
        for field in fields:
            if not (field.name == 'OBJECTID' or field.name == 'Shape' or field.name == self.node_id_field):
                delete_fields.append(field.name)
        arcpy.DeleteField_management(here_ref_nodes,delete_fields)

        # populate node id for missing node
        arcpy.AddField_management(here_links_endpoints_missnodes, self.node_id_field, 'LONG')
        arcpy.CalculateField_management(here_links_endpoints_missnodes, self.node_id_field, '[{0}]'.format(self.non_ref_node_id_field))
        arcpy.DeleteField_management(here_links_endpoints_missnodes, [self.non_ref_node_id_field])

        # merge reference node and missing node
        arcpy.Merge_management([here_ref_nodes,here_links_endpoints_missnodes],self.node)

        # delete intermediate outputs
        # arcpy.Delete_management(here_links_endpoints_start)
        # arcpy.Delete_management(here_links_endpoints_end)
        # arcpy.Delete_management(here_ref_nodes)
        # arcpy.Delete_management(here_links_endpoints_join)
        # arcpy.Delete_management(here_links_endpoints_missnodes_w_duplicates)
        # arcpy.Delete_management(here_links_endpoints_missnodes)

        return self.node


    def locate_node_along_route(self):
        # locate node along target route.
        logger.info("Locating nodes along target routes...")

        # locate nodes to DOT LRS
        arcpy.LocateFeaturesAlongRoutes_lr(self.node,self.network, self.network_route_id_field, self.search_radius,
                                       locate_nodes_along_network_w_duplicates, 'RID POINT MEAS', 'ALL', 'DISTANCE', 'NO_ZERO', 'FIELDS')

        # deal with cases that one node is located on the same route more than once
        # TODO: we simply assign the mean measure values to nodes in these cases. Validate this.
        arcpy.Frequency_analysis(locate_nodes_along_network_w_duplicates, locate_nodes_along_network_frequency,['RID',self.node_id_field])

        arcpy.Copy_management(locate_nodes_along_network_w_duplicates,self.candidate_table)

        with arcpy.da.SearchCursor(locate_nodes_along_network_frequency, ['FREQUENCY','RID',self.node_id_field], where_clause='FREQUENCY >1') as sCur:
            # test whether cursor is empty
            try:
                sCur.next()
                flg = True
            except:
                flg = False

            if flg:
                sCur.reset()
                for row in sCur:
                    frequency = row[0]
                    rid = row[1]
                    node_id = row[2]

                    where_clause = "RID = '{0}' AND {2} = {1}".format(rid, node_id, self.node_id_field)

                    with arcpy.da.UpdateCursor(self.candidate_table, ['RID','MEAS',self.node_id_field], where_clause=where_clause) as uCur:
                        meas_sum = 0.0
                        meas_average = 0.0
                        for record in uCur:
                            meas = record[1]
                            meas_sum += meas
                        meas_average = meas_sum / frequency

                        uCur.reset()
                        for record in uCur:
                            record[1] = meas_average
                            uCur.updateRow(record)

                        uCur.reset()
                        for i in range(1,frequency):
                            uCur.next()
                            uCur.deleteRow()

        # delete intermediate outputs
        # arcpy.Delete_management(locate_nodes_along_network_w_duplicates)
        # arcpy.Delete_management(locate_nodes_along_network_frequency)

        return self.candidate_table

