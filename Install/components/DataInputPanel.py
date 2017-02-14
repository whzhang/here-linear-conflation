import wx
import os
import arcpy
import pythonaddins

class DataInputPanel(wx.Panel):
    """
    This is wx.Panel implementation of ESRI data input
    @parameter
    parent: parent of the data input panel
    label: data input label
    """
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent', None)
        self.label = kwargs.get('label', None)
        self.field = kwargs.get('field', None)

        self.dataInput = None

        wx.Panel.__init__(self, self.parent, wx.ID_ANY)

        # Label Section
        labelPanel = wx.Panel(self, wx.ID_ANY)
        labelSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.labelComponent = wx.StaticText(labelPanel, label=self.label)

        labelSizer.Add(self.labelComponent, 0, wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, 0)
        labelPanel.SetSizer(labelSizer)
        labelPanel.Fit()

        # Data Input Section
        dataInputPanel = wx.Panel(self, wx.ID_ANY)
        dataInputSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.textComponent = wx.TextCtrl(dataInputPanel, wx.ID_ANY)
        bmp = wx.Image(os.path.join(os.path.dirname(__file__), "img", "folder.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.buttonComponent = wx.BitmapButton(dataInputPanel, wx.ID_ANY, bmp, style=0)
        self.buttonComponent.Bind(wx.EVT_BUTTON, self.OnButtonClick)

        dataInputSizer.Add(self.textComponent, 1, wx.ALIGN_LEFT | wx.RIGHT | wx.EXPAND, 5)
        dataInputSizer.Add(self.buttonComponent, 0, wx.ALIGN_RIGHT | wx.ALL | wx.EXPAND, 0)
        dataInputPanel.SetSizer(dataInputSizer)
        dataInputPanel.Fit()

        # Pipe up all components
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(labelPanel, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(dataInputPanel, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Fit()


    def OnButtonClick(self, event):
        self.dataInput = pythonaddins.OpenDialog(title=self.label)

        if self.dataInput is not None:
            self.textComponent.SetLabel(self.dataInput)

        if self.field is not None:
            if arcpy.Exists(self.dataInput):
                fields = [f.name for f in arcpy.ListFields(self.dataInput)]
                self.field.UpdateChoices(fields)

        self.parent.SetFocus()


    @property
    def data(self):
        return self.dataInput