import wx
import wx.grid as gridlib
import copy

class TableGroup(wx.Panel):
    """
    This is a 'TableGroup' object customized for HERE Linear Conflation
    @:parameters
    data: data array, example: [[value1,value2,value3...],[value_x,value_y,value_z...],[...]]
    rowLabels: array, example: [name1,name2,name3...]
    colLabels: array, example: [name1,name2,name3...]
    menuOptions: dictionary, example: {'MenuName1': {'function': func, 'option': {}}}
    """
    def __init__(self, **kwargs):
        parent = kwargs.get('parent', None)
        data = kwargs.get('data', None)
        rowLabels = kwargs.get('rowLabels', None)
        colLabels = kwargs.get('colLabels', None)
        menuOptions = kwargs.get('menuOptions', None)

        wx.Panel.__init__(self, parent, wx.ID_ANY)

        # UI
        self.data = data
        self.source_data = copy.deepcopy(self.data)
        self.menuOptions = menuOptions
        self.sortColumnAscending = True

        self.myGrid = gridlib.Grid(self, wx.ID_ANY)
        self.myGrid.EnableDragGridSize()
        self.myGrid.SetRowLabelSize(0)
        self.myGrid.SetLabelFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.BOLD))

        # set table base
        self.tableBase = TableBase(
            data=self.data,
            colLabels=colLabels
        )
        self.myGrid.SetTable(self.tableBase,selmode=gridlib.Grid.SelectRows)

        # set first two columns ready-only
        # TODO: verify if column attr has to be set after "SetTable", otherwise, it will throw error
        col_attr = gridlib.GridCellAttr()
        col_attr.SetReadOnly(True)
        self.myGrid.SetColAttr(0,col_attr) # set object id field to read-only
        self.myGrid.SetColAttr(2,col_attr) # set HERE link id field to read-only
        self.myGrid.SetColAttr(7,col_attr) # set confidence level field to read-only

        # set grid cell as checkbox
        attr = gridlib.GridCellAttr()
        attr.SetEditor(gridlib.GridCellBoolEditor())
        attr.SetRenderer(gridlib.GridCellBoolRenderer())
        self.myGrid.SetColAttr(8, attr)
        self.myGrid.SetColAttr(9, attr)

        # set grid cell background color
        for i in range(0, self.myGrid.GetNumberRows()):
            rowAttr = gridlib.GridCellAttr()
            rowAttr.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            rowAttr.SetBackgroundColour("#FFFFFF")  # "#FFFFFF": RGB white
            if i % 2 == 1: # even number rows
                rowAttr.SetBackgroundColour("#E0E0E0")  # "#E0E0E0": RGB light grey
            self.myGrid.SetRowAttr(i, rowAttr)

        self.myGrid.AutoSize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.myGrid, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Fit()

        # Event binding
        self.myGrid.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self.ShowPopupMenu)
        self.myGrid.Bind(gridlib.EVT_GRID_LABEL_LEFT_DCLICK, self.OnSortColumn)

    @property
    def value(self):
        return self.data

    def ClearEdits(self):
        self.PopulateTable(self.source_data)

    def ClearTable(self):
        self.tableBase.ClearTable()
        self.data = self.tableBase.data
        self.myGrid.ForceRefresh()

    def PopulateTable(self, data):
        # make a copy of source data
        self.source_data = copy.deepcopy(data)

        self.tableBase.PopulateTable(data)
        self.data = self.tableBase.data
        self.myGrid.ForceRefresh()

    def ShowPopupMenu(self, event):
        """
        Create and display a popup menu on right-click event
        """
        row = event.GetRow()
        self.myGrid.SelectRow(row, False)
        self.myGrid.Refresh()

        if self.menuOptions is None:
            return

        menu = wx.Menu()

        # Add item(s) to the menu
        for popUpItemName, popUpItemOptions in self.menuOptions.items():
            menuItem = wx.MenuItem(menu, wx.ID_ANY, popUpItemName)
            self.Bind(wx.EVT_MENU, self.OnPopupItemSelected, menuItem)
            menu.AppendItem(menuItem)

        # Popup the menu.  If an item is selected then its handler will be called before PopupMenu returns.
        self.PopupMenu(menu)
        menu.Destroy()

    def OnPopupItemSelected(self, event):
        """
        Prototype 'OnPopupItemSelected' handler
        """
        itemId = event.GetId()
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(itemId)
        menuItemLabel = menuItem.GetLabel()

        function = self.menuOptions[menuItemLabel]['function'] if 'function' in self.menuOptions[
            menuItemLabel] else None
        options = self.menuOptions[menuItemLabel]['options'] if 'options' in self.menuOptions[menuItemLabel] else None
        function(self=self, event=event, options=options)

    def GetUpdatedData(self):
        updated_data = []
        row_num = self.myGrid.GetNumberRows()
        col_num = self.myGrid.GetNumberCols()

        for r in range(0, row_num):
            src_row_values = self.source_data[r]
            new_row_values = []
            for c in range(0, col_num):
                cellValue = int(self.myGrid.GetCellValue(r, c)) if c == 0 else self.myGrid.GetCellValue(r, c) #OBJECTID field is integer type
                new_row_values.append(cellValue)

            if src_row_values != new_row_values and new_row_values not in updated_data:
                updated_data.append(new_row_values)

        return updated_data

    def OnSortColumn(self, event):
        self.sortColumnAscending = False if self.sortColumnAscending else True
        sorted_data = sorted(self.data, key=lambda row: row[event.Col], reverse=self.sortColumnAscending)
        self.PopulateTable(sorted_data)


class TableBase(wx.grid.PyGridTableBase):
    def __init__(self, **kwargs):
        data = kwargs.get('data', None)
        rowLabels = kwargs.get('rowLabels', None)
        colLabels = kwargs.get('colLabels', None)

        gridlib.PyGridTableBase.__init__(self)

        self.data = data
        self.rowLabels = rowLabels
        self.colLabels = colLabels

        # Grid cell attribute settings
        # Note: these attribute settings will not take effect without the GetAttr() function
        # Note: these attribute settings could be overwritten by col/row attribute settings applied in its 'parent', e.g 'TableGroup'
        # self.odd=gridlib.GridCellAttr()
        # self.odd.SetBackgroundColour("#FFFFFF") #"#FFFFFF": RGB white
        # self.odd.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        # self.even=gridlib.GridCellAttr()
        # self.even.SetBackgroundColour("#E0E0E0") #"#E0E0E0": RGB light grey
        # self.even.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

    def GetNumberRows(self):
        return len(self.data)

    def GetNumberCols(self):
        return len(self.colLabels)

    def GetRowLabelValue(self, row):
        if self.rowLabels:
            return self.rowLabels[row]

    def GetColLabelValue(self, col):
        if self.colLabels:
            return self.colLabels[col]

    def IsEmptyCell(self, row, col):
        return self.data[row][col] is not None

    def GetValue(self, row, col):
        return self.data[row][col]

    def SetValue(self, row, col, value):
        if value is not None:
            self.data[row][col] = value
        else:
            self.data[row][col] = ""

    # Uncommented GetAttr() function to apply attribute settings to table base.
    # def GetAttr(self, row, col, kind):
    #     attr = [self.odd, self.even][row % 2]
    #     attr.IncRef()
    #     return attr

    def ClearTable(self):
        # Begin clearing the whole table
        self.GetView().BeginBatch()

        # Delete all rows. Run it only to keep column headers.
        msg = gridlib.GridTableMessage(self,gridlib.GRIDTABLE_NOTIFY_ROWS_DELETED,0,self.GetNumberRows())
        self.GetView().ProcessTableMessage(msg)

        # Delete all cols. Run it to delete all rows and column headers.
        # msg = gridlib.GridTableMessage(self,gridlib.GRIDTABLE_NOTIFY_COLS_DELETED,0,self.GetNumberCols())
        # self.GetView().ProcessTableMessage(msg)

        self.GetView().EndBatch()
        # End clearing process

        # Update table view
        self.data = []

        msg = gridlib.GridTableMessage(self, gridlib.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)

    def PopulateTable(self, data):
        self.ClearTable()
        self.data = data

        self.GetView().BeginBatch()
        msg = gridlib.GridTableMessage(self,gridlib.GRIDTABLE_NOTIFY_ROWS_APPENDED,self.GetNumberRows())
        self.GetView().ProcessTableMessage(msg)
        self.GetView().EndBatch()

        msg = gridlib.GridTableMessage(self, gridlib.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().ProcessTableMessage(msg)