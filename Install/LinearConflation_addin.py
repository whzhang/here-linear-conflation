import pythonaddins
import os
import sys

sys.path.append(os.path.dirname(__file__))
from src.util.helper import toolDialog

local_path = os.path.dirname(__file__)
linear_conflation_tbx = os.path.join(local_path, 'LinearConflation.tbx')

class LinearConflationExt(object):
    """Implementation for LinearConflation_addin.extension (Extension)"""
    def __init__(self):
        # For performance considerations, please remove all unused methods in this class.
        self._wxApp = None

    def startup(self):
        """On startup of ArcGIS, initiate the logger"""
        try:
            from wx import PySimpleApp
            self._wxApp = PySimpleApp()
            self._wxApp.MainLoop()

            # setup logger
            from src.tss import setup_logger
            setup_logger('HERELinearConflation')

        except Exception:
            pythonaddins.MessageBox("Error starting the HERE Linear Conflation Extension", "Extension Error", 0)

    # @property
    # def enabled(self):
    #     if self._enabled == False:
    #         generateMatchCandidateButton.enabled = False
    #         verifyMatchCandidateButton.enabled = False
    #     else:
    #         generateMatchCandidateButton.enabled = True
    #         verifyMatchCandidateButton.enabled = True
    #     return self._enabled
    #
    # @enabled.setter
    # def enabled(self, value):
    #     """Set the enabled property of this extension when the extension is turned on or off in the Extension Dlalog of ArcMap."""
    #     self._enabled = value

class GenerateMatchCandidate(object):
    """Implementation for LinearConflation_addin.configurationButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            toolDialog(linear_conflation_tbx,'generateMatchCandidate')
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Generate Match Candidate' tool. %s" % e, "Error", "0")

class VerifyMatchCandidate(object):
    """Implementation for LinearConflation_addin.setRouteIDMatchingRuleButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

        self._dlg = None

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            if self._dlg is None:
                from VerifyMatchCandidateDialog import VerifyMatchCandidateDialog
                self._dlg = VerifyMatchCandidateDialog()
            self._dlg.Show(True)
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Verify Match Candidate Table' tool. %s" % e, "Error", "0")

class GenerateHereRoute(object):
    """Implementation for LinearConflation_addin.configurationButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            toolDialog(linear_conflation_tbx,'generateHereRoute')
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Generate HERE Route' tool. %s" % e, "Error", "0")

class GenerateXrefTable(object):
    """Implementation for LinearConflation_addin.configurationButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            toolDialog(linear_conflation_tbx,'generateXrefTable')
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Generate XREF Table' tool. %s" % e, "Error", "0")

class TransferHereEventAttributeToDOT(object):
    """Implementation for LinearConflation_addin.configurationButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            toolDialog(linear_conflation_tbx,'transferHereEventAttributeToDot')
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Transfer HERE Event Attribute To DOT' tool. %s" % e, "Error", "0")

class TransferDOTEventAttributeToHERE(object):
    """Implementation for LinearConflation_addin.configurationButton (Button)"""
    def __init__(self):
        # self._enabled = True
        self.checked = False

    @property
    def enabled(self):
        try:
            # return self._enabled and extension.enabled
            return linearConflationExtension.enabled
        except:
            return False

    def onClick(self):
        try:
            toolDialog(linear_conflation_tbx,'transferDotEventAttributeToHere')
        except Exception as e:
            pythonaddins.MessageBox("Can't Open the 'Transfer DOT Event Attribute To HERE' tool. %s" % e, "Error", "0")