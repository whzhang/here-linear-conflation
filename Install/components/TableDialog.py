import os
import wx
import datetime
import copy

from TableGroup import TableGroup

import logging
logger = logging.getLogger(__name__)


class TableDialog(wx.Frame):
    """
    This is a 'TableDialog' object for HERE Linear Conflation
    """
    def __init__(self, **kwargs):
        """Initialize the Frame and add wx widgets."""
        parent = kwargs.get('parent', None)
        title = kwargs.get('title', None)
        data = kwargs.get('data', None)
        rowLabels = kwargs.get('rowLabels', None)
        colLabels = kwargs.get('colLabels', None)
        menuOptions = kwargs.get('menuOptions', None)
        self.otherOptions = kwargs.get('otherOptions', {})

        self.targetTable = self.otherOptions['targetTable'] if 'targetTable' in self.otherOptions.keys() else None
        self.saveEditFunction = self.otherOptions['saveEditFunction'] if 'saveEditFunction' in self.otherOptions.keys() else None

        wx.Frame.__init__(self, parent, wx.ID_ANY, title=title,
                          style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP)
        self.SetIcon(wx.Icon(os.path.join(os.path.dirname(__file__), "img", "Tlogo.ico"), wx.BITMAP_TYPE_ICO))
        self.MinSize = 450, 300
        self.MaxSize = 1050, 700
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Table Section
        self.table = TableGroup(
            parent=self,
            data=data,
            colLabels=colLabels,
            menuOptions=menuOptions
        )

        # Button panel
        # TODO: Rewrite button panel to make it configurable from outside like popUpMenu
        btnPanel = wx.Panel(self, -1)
        applyBtn = wx.Button(btnPanel,wx.ID_OK, 'Save Edits')
        clearBtn = wx.Button(btnPanel,wx.ID_ANY, 'Clear Edits')
        closeBtn = wx.Button(btnPanel,wx.ID_CANCEL, 'Cancel')
        self.Bind(wx.EVT_BUTTON, self.SaveEdits, applyBtn)
        self.Bind(wx.EVT_BUTTON, self.ClearEdits, clearBtn)
        self.Bind(wx.EVT_BUTTON, self.OnClose, closeBtn)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(applyBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        btnSizer.Add(clearBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        btnSizer.Add(closeBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 5)
        btnPanel.SetSizer(btnSizer)
        btnPanel.Fit()
        # End of Button Toolbar

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.table, 1, flag=wx.EXPAND)
        mainSizer.Add(btnPanel, flag=wx.EXPAND)
        self.SetSizer(mainSizer)
        self.Fit()
        self.CenterOnScreen()

        # initiate output data as None
        self.updated_data = None

        # # Uncomment line below when testing as a standalone application.
        # self.Show(True)

    # End __init__ built-in

    def ClearEdits(self, event):
        self.table.ClearEdits()

    def SaveEdits(self, event):
        import pythonaddins

        self.Show(False)

        if self.targetTable is None or self.saveEditFunction is None:
            pythonaddins.MessageBox("This function has not been implemented.", 'ERROR', 0)
            return

        with pythonaddins.ProgressDialog as progress_bar:
            progress_bar.animation = 'Spiral'
            progress_bar.title = 'Verify Match Candidate'
            progress_bar.canCancel = False

            self.updated_data = self.GetUpdatedData()

        if self.updated_data is None or len(self.updated_data) == 0:
            pythonaddins.MessageBox("No change detected.", 'INFO', 0)
            return

        # This is a validator for updated data. Check if 'verified_match' and 'false_match' are true at the same time.
        # Todo: figure out if there is a way to do it at 'front end'.
        with pythonaddins.ProgressDialog as progress_bar:
            progress_bar.animation = 'Spiral'
            progress_bar.title = 'Verify Match Candidate'
            progress_bar.canCancel = False
            validator = []
            for row in self.updated_data:
                oid = row[0]
                verified_match = row[8]
                false_match = row[9]

                if verified_match == false_match == '1':
                    validator.append("Invalid input! Match Candidate (OBJECTID: '{0}') cannot be a verified match "
                                     "and a false match at the same time!".format(oid))
                    break

        if len(validator) > 0:
            msg = '\n'.join(validator)
            pythonaddins.MessageBox(msg, 'WARNING', 0)
            logger.warning(msg)
            self.updated_data = None
            self.Show(True)
        self.saveEditFunction(target_table=self.targetTable, updated_data=self.updated_data)

        # Get remaining data to be view, refresh the table, and open the table back
        remain_data = [row for row in self.table.data if row not in self.updated_data]
        self.PopulateTable(remain_data)
        self.Show(True)

    def ClearTable(self):
        self.table.ClearTable()

    def PopulateTable(self,data):
        self.table.PopulateTable(data)

    def GetUpdatedData(self):
        updated_data = self.table.GetUpdatedData()
        return updated_data

    def OnClose(self, event):
        """Close the frame. Destroy/Close are not supported in ArcMap."""
        self.Show(False)

        # End OnClose event method



# def zoom_to_selected_feature(**kwargs):
#     self = kwargs.get('self', None)
#     event = kwargs.get('event', None)
#     options = kwargs.get('options', None)
#
#     selectedRow = self.myGrid.GetSelectedRows()
#     oid = self.myGrid.GetCellValue(selectedRow[0], 0)
#
#     layer_name = options['layer_name'] if options is not None and 'layer_name' in options else None
#
#     if layer_name is not None:
#         where_clause = "OBJECTID = {0}".format(oid)
#         # zoom_to_selected_features(layer_name, where_clause)

# Uncomment following code when testing in stand alone mode
# data = [["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""]\
#     ,["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],["1","11",""],\
#     ["1","11",""],["1","11",""],["1","11",""],["1","11",""]]

# data2 = [["1","11",""],["2","22",""],["3","33",""],["4","44",""],["5","55",""],["6","66",""],["7","77",""]]

# data3 = [["1","Low","1", ""],["2","Medium","", "0"],["3","High","", ""]]
#
# col_names = ["Object Id","Confidence Level","Verify Match", "False Match"]
#
# popup_menu = {}
# popup_menu['Zoom to HERE Link'] = {'function': zoom_to_selected_feature,
#                                    'options': {'layer_name': os.path.basename('a')}}
# popup_menu['Zoom to DOT Route'] = {'function': zoom_to_selected_feature,
#                                    'options': {'layer_name': os.path.basename('b')}}
#
#
# app = wx.App(False)
#
# table = TableDialog(
#     title="Verify Match Candidates",
#     data=[],
#     colLabels=col_names,
#     menuOptions=popup_menu
# )
#
# table.PopulateTable(data3)
# table.Show(True)
#
# app.MainLoop()
