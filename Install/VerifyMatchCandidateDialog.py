import arcpy
import os
import wx
import traceback
import datetime
import pythonaddins

from components.TableDialog import TableDialog
from components.DataInputPanel import DataInputPanel
from components.DropDownPanel import DropDownPanel
from src.config.schema import default_schemas
from src.util.map import update_table_of_content, zoom_to_selected_features
from src.util.helper import get_scratch_gdb
from src.tss.ags import build_numeric_in_sql_expression

import logging
logger = logging.getLogger(__name__)

# Load schema and config settings --------------------------------------------------------------------------------------
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

candidate_table_fields = ['OBJECTID', candidate_table_dot_rid_field, candidate_table_here_lid_field,
                          candidate_table_dot_rt_name_field, candidate_table_dot_cnty_id_field,
                          candidate_table_here_st_name_field, candidate_table_here_cnty_id_field,
                          candidate_table_conf_lvl_field, candidate_table_verified_match_field,
                          candidate_table_false_match_field]

choices = ['All', 'No Match', 'Low', 'Medium', 'High', 'User Confirmed']
# ----------------------------------------------------------------------------------------------------------------------


class VerifyMatchCandidateDialog(wx.Frame):
    def __init__(self):
        """Initialize the Frame and add wx widgets."""
        wx.Frame.__init__(self, None, wx.ID_ANY, title="Verify Match Candidate", style=wx.DEFAULT_FRAME_STYLE)

        self.SetIcon(wx.Icon(os.path.join(os.path.dirname(__file__), "components/img", "Tlogo.ico"), wx.BITMAP_TYPE_ICO))
        self.MinSize = 600, 530
        self.MaxSize = 600, 530
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.table = None

        # Context Section
        contextPanel = wx.Panel(self, wx.ID_ANY)
        contextSizer = wx.BoxSizer(wx.VERTICAL)

        # Input Components
        self.candidateTable = DataInputPanel(parent=contextPanel, label='Match Candidate Table')

        self.hereLinkIdField = DropDownPanel(parent=contextPanel, label='HERE Link Id Field', choices=[])
        self.hereLink = DataInputPanel(parent=contextPanel, label='HERE Link Feature', field=self.hereLinkIdField)

        self.dotRouteIdField = DropDownPanel(parent=contextPanel, label='DOT Route Id Field', choices=[])
        self.dotRoute = DataInputPanel(parent=contextPanel, label='DOT Route Feature', field=self.dotRouteIdField)

        self.confLvlThld = DropDownPanel(parent=contextPanel, label='Confidence Level Threshold', choices=choices)
        self.confLvlThld.value = 'All'

        contextSizer.Add(self.candidateTable, 0, wx.ALL | wx.EXPAND, 10)
        contextSizer.Add(self.hereLink, 0, wx.ALL | wx.EXPAND, 10)
        contextSizer.Add(self.hereLinkIdField, 0, wx.ALL | wx.EXPAND, 10)
        contextSizer.Add(self.dotRoute, 0, wx.ALL | wx.EXPAND, 10)
        contextSizer.Add(self.dotRouteIdField, 0, wx.ALL | wx.EXPAND, 10)
        contextSizer.Add(self.confLvlThld, 0, wx.ALL | wx.EXPAND, 10)

        # Button Components
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)

        yesBtn = wx.Button(contextPanel, wx.ID_YES, 'Ok')
        noBtn = wx.Button(contextPanel, wx.ID_NO, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.OnOK, yesBtn)
        self.Bind(wx.EVT_BUTTON, self.OnClose, noBtn)

        btnSizer.Add(yesBtn, 0, wx.ALL, 0)
        btnSizer.Add(noBtn, 0, wx.LEFT, 5)

        contextSizer.Add((-1, 40))
        contextSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT|wx.ALL, 10)

        contextPanel.SetSizer(contextSizer)
        contextPanel.Fit()

        self.CenterOnScreen()

        # # Uncomment line below when testing as a standalone application.
        # self.Show(True)

    def OnClose(self, event):
        """Close the frame. Destroy/Close are not supported in ArcMap."""
        self.Show(False)

    def OnOK(self, event):
        try:
            logger.info("Start verifying match candidates...")

            self.Show(False)

            scratch_folder = os.path.join(os.path.expanduser("~"), ".HERELinearConflation")
            scratch_gdb = get_scratch_gdb(scratch_folder)

            arcpy.env.workspace = scratch_gdb
            arcpy.env.overwriteOutput = True
            arcpy.env.addOutputsToMap = False

            candidate_table = self.candidateTable.data
            here_link = self.hereLink.data
            here_link_id_field = self.hereLinkIdField.value
            dot_network = self.dotRoute.data
            dot_network_rid_field = self.dotRouteIdField.value
            conf_lvl_thld = self.confLvlThld.value

            # Input validator ------------------------------------------------------------------------------------------
            input_validator = []
            with pythonaddins.ProgressDialog(title='Verify Match Candidate') as progress_bar:
                progress_bar.animation = 'Spiral'
                progress_bar.title = 'Verify Match Candidate'
                progress_bar.canCancel = False

                if candidate_table is None:
                    input_validator.append("Match Candidate Table has not been specified!")

                if here_link is None:
                    input_validator.append("HERE Link feature has not been specified!")

                if here_link_id_field is None:
                    input_validator.append("HERE Link Id Field has not been specified!")

                if dot_network is None:
                    input_validator.append("DOT Network feature has not been specified!")

                if dot_network_rid_field is None:
                    input_validator.append("DOT Network Route Id Field has not been specified!")

            if len(input_validator):
                msg = '\n'.join(input_validator)
                # wx.MessageBox(msg, 'Warning', wx.OK | wx.ICON_WARNING)
                pythonaddins.MessageBox(msg, 'WARNING', 0)
                logger.warning(msg)
                self.Show(True)
                return

            input_validator = []
            with pythonaddins.ProgressDialog(title='Verify Match Candidate') as progress_bar:
                progress_bar.animation = 'Spiral'
                progress_bar.title = 'Verify Match Candidate'
                progress_bar.canCancel = False

                if not arcpy.Exists(candidate_table):
                    input_validator.append("'{0}' does not exist!".format(candidate_table))

                if not arcpy.Exists(here_link):
                    input_validator.append("'{0}' does not exist!".format(here_link))

                if not arcpy.Exists(dot_network):
                    input_validator.append("'{0}' does not exist!".format(dot_network))

                if len(input_validator):
                    msg = '\n'.join(input_validator)
                    pythonaddins.MessageBox(msg, 'WARNING', 0)
                    logger.warning(msg)
                    self.Show(True)
                    return
            # ----------------------------------------------------------------------------------------------------------

            with pythonaddins.ProgressDialog as progress_bar:
                progress_bar.animation = 'Spiral'
                progress_bar.title = 'Verify Match Candidate'
                progress_bar.canCancel = False

                data_tbv = []

                # Use conf_lvl_thld as the maximum threshold
                conf_lvl_tbv = ["'{0}'".format(conf_lvl) for conf_lvl in choices[1:choices.index(conf_lvl_thld)+1]]

                where_clause = "{0} IN ({1})".format(candidate_table_conf_lvl_field, ','.join(conf_lvl_tbv)) \
                    if conf_lvl_thld != 'All' and len(conf_lvl_tbv) > 0 else "1=1"
                with arcpy.da.SearchCursor(candidate_table, candidate_table_fields, where_clause=where_clause) as sCur:
                    for row in sCur:
                        # Convert NoneType value into empty string to nicely display it in the table
                        row = ['' if value is None else value for value in row]
                        data_tbv.append(row)

                del sCur

            if len(data_tbv) == 0:
                pythonaddins.MessageBox("No match candidate found for confidence level: '{0}'.".format(conf_lvl_thld), 'INFO', 0)
                return

            with pythonaddins.ProgressDialog as progress_bar:
                progress_bar.animation = 'Spiral'
                progress_bar.title = 'Verify Match Candidate'
                progress_bar.canCancel = False

                update_table_of_content(feature_classes_to_remove=[here_link, dot_network],
                                        feature_classes_to_add=[here_link, dot_network])

                col_names = ["Object Id", "DOT Route Id", "HERE Link Id", "DOT Route Name", "DOT County Id",
                             "HERE Street Name", "HERE County Id", "Confidence", "Verified Match", "Rejected Match"]

                menu_options = {}
                menu_options['Zoom to HERE Link'] = {'function': zoom_to_here_link,
                                                     'options': {'layer_name': os.path.basename(here_link),
                                                                 'here_lid_field': here_link_id_field}}
                menu_options['Zoom to DOT Route'] = {'function': zoom_to_dot_route,
                                                     'options': {'layer_name': os.path.basename(dot_network),
                                                                 'dot_rid_field': dot_network_rid_field}}

                other_options = {}
                other_options['targetTable'] = candidate_table
                other_options['saveEditFunction'] = update_match_candidate_table

                self.table = TableDialog(
                    title="Verify Match Candidates",
                    data=[],
                    colLabels=col_names,
                    menuOptions=menu_options,
                    otherOptions=other_options
                )

                self.table.PopulateTable(data_tbv)
                self.table.Show(True)

        except Exception, err:
            logger.error("Error: {0}".format(err.args[0]))
            logger.error(traceback.format_exc())
            pythonaddins.MessageBox("Error: {0}".format(err.args[0]), 'ERROR', 0)


def zoom_to_here_link(**kwargs):
    """
    Function to run when pop-up menu option is selected
    """

    self = kwargs.get('self', None)
    event = kwargs.get('event', None)
    options = kwargs.get('options', None)

    selectedRow = self.myGrid.GetSelectedRows()
    lid = self.myGrid.GetCellValue(selectedRow[0], 2) # '2' is the index of link id field

    layer_name = options['layer_name'] if options is not None and 'layer_name' in options else None
    here_lid_field = options['here_lid_field'] if options is not None and 'here_lid_field' in options else None

    if layer_name is not None:
        try:
            # assuming the lid field is a string type
            where_clause = "{0} = '{1}'".format(here_lid_field, lid)
            # logger.info("layer_name: {0}, where_clause: {1}".format(layer_name, where_clause))
            zoom_to_selected_features(layer_name, where_clause)
        except:
            # assuming the lid field is a number type
            where_clause = "{0} = {1}".format(here_lid_field, lid)
            # logger.info("layer_name: {0}, where_clause: {1}".format(layer_name, where_clause))
            zoom_to_selected_features(layer_name, where_clause)


def zoom_to_dot_route(**kwargs):
    """
    Function to run when pop-up menu option is selected
    """

    self = kwargs.get('self', None)
    event = kwargs.get('event', None)
    options = kwargs.get('options', None)

    selectedRow = self.myGrid.GetSelectedRows()
    rid = self.myGrid.GetCellValue(selectedRow[0], 1) # '2' is the index of route id field

    layer_name = options['layer_name'] if options is not None and 'layer_name' in options else None
    dot_rid_field = options['dot_rid_field'] if options is not None and 'dot_rid_field' in options else None

    if layer_name is not None and dot_rid_field is not None:
        try:
            # assuming the rid field is a string type
            where_clause = "{0} = '{1}'".format(dot_rid_field, rid)
            # logger.info("layer_name: {0}, where_clause: {1}".format(layer_name, where_clause))
            zoom_to_selected_features(layer_name, where_clause)
        except:
            # assuming the rid field is a number type
            where_clause = "{0} = {1}".format(dot_rid_field, rid)
            # logger.info("layer_name: {0}, where_clause: {1}".format(layer_name, where_clause))
            zoom_to_selected_features(layer_name, where_clause)

def update_match_candidate_table(**kwargs):
    try:
        candidate_table = kwargs.get('target_table', None)
        updated_data = kwargs.get('updated_data', [])

        if len(updated_data) == 0 or candidate_table is None or not arcpy.Exists(candidate_table):
            return

        # Convert empty string type value back to NoneType before update the table
        updated_data = [[None if value == '' else value for value in row] for row in updated_data]

        for row in updated_data:
            verified_match = row[8]
            false_match = row[9]

            if verified_match == '1':
                row[7] = 'User Confirmed'

            if false_match == '1':
                row[7] = 'No Match'


        updated_data_dict = {row[0]:row for row in updated_data}

        where_clause = build_numeric_in_sql_expression("OBJECTID", updated_data_dict.keys())

        with arcpy.da.Editor(os.path.dirname(candidate_table)) as editor:
            with arcpy.da.UpdateCursor(candidate_table, candidate_table_fields, where_clause=where_clause) as uCur:
                for row in uCur:
                    oid = row[0]
                    value = updated_data_dict[oid]
                    uCur.updateRow(value)
        del uCur

        pythonaddins.MessageBox("Update Match Candidate Table successfully!", 'Update', 0)

    except Exception, err:
        logger.error("Error: {0}".format(err.args[0]))
        logger.error(traceback.format_exc())
        pythonaddins.MessageBox("Error: {0}".format(err.args[0]), 'ERROR', 0)


# app = wx.App(False)
# frame = VerifyMatchCandidateDialog()
# frame.Show(True)
# app.MainLoop()