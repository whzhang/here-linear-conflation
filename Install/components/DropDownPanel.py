import wx

class DropDownPanel(wx.Panel):
    """
    This is wrapper of wx.ComboBox supports dropdown menu
    @parameter
    parent: parent of the data input panel
    label: data input label
    """
    def __init__(self, **kwargs):
        self.parent = kwargs.get('parent', None)
        self.label = kwargs.get('label', None)
        self.choices = kwargs.get('choices', [])

        self._value = None

        wx.Panel.__init__(self, self.parent, wx.ID_ANY)

        # Label Section
        labelPanel = wx.Panel(self, wx.ID_ANY)
        labelSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.labelComponent = wx.StaticText(labelPanel, label=self.label)

        labelSizer.Add(self.labelComponent, 0, wx.ALIGN_LEFT | wx.ALL | wx.EXPAND, 0)
        labelPanel.SetSizer(labelSizer)
        labelPanel.Fit()

        # ComboBox Section
        comboBoxPanel = wx.Panel(self, wx.ID_ANY)
        comboBoxSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.comboBoxComponent = wx.ComboBox(comboBoxPanel, choices = self.choices, style=wx.CB_READONLY)
        self.comboBoxComponent.Bind(wx.EVT_COMBOBOX, self.OnItemSelected)

        comboBoxSizer.Add(self.comboBoxComponent, 1, wx.ALIGN_LEFT | wx.ALL | wx.EXPAND, 0)
        comboBoxPanel.SetSizer(comboBoxSizer)
        comboBoxPanel.Fit()

        # Pipe up all components
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(labelPanel, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(comboBoxPanel, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Fit()

    def OnItemSelected(self, event):
        self._value = self.comboBoxComponent.GetValue()

    def UpdateChoices(self, choices):
        if not isinstance(choices, list):
            return
        self.comboBoxComponent.Clear()
        self.comboBoxComponent.AppendItems(choices)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.comboBoxComponent.SetValue = value
        self.comboBoxComponent.SetSelection(self.choices.index(value))