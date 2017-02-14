import os
import sys
import uuid

from src.tss import get_parent_directory

def get_default_parameters():
    try:
        import ConfigParser

        Config = ConfigParser.ConfigParser()
        init_cfg = os.path.join(get_parent_directory(__file__, 2), "config/params.ini")
        updated_cfg = os.path.join(get_parent_directory(__file__, 2), "config/params_updated.ini")

        if os.path.exists(updated_cfg):
            Config.read(updated_cfg)
        else:
            Config.read(init_cfg)

        return Config
    except ImportError:
        pass

def set_parameters(SECTION, key_value_dict):
    try:
        import ConfigParser

        Config = ConfigParser.ConfigParser()
        init_cfg = os.path.join(get_parent_directory(__file__, 2), "config/params.ini")
        updated_cfg = os.path.join(get_parent_directory(__file__, 2), "config/params_updated.ini")

        if os.path.exists(updated_cfg):
            Config.read(updated_cfg)
        else:
            Config.read(init_cfg)

        for key, value in key_value_dict.items():
            Config.set(SECTION, key, value)
        with open(updated_cfg, "wb") as cfg:
            Config.write(cfg)

        return Config
    except ImportError:
        pass

def get_scratch_gdb(path):
    if not os.path.isdir(path):
        raise Exception("Not a valid directory: '{0}'!".format(path))
    desc = arcpy.Describe(path)
    if desc.dataType == "Folder":
        gdb_path = os.path.join(path, "scratch.gdb")
        if not arcpy.Exists(gdb_path):
            arcpy.CreateFileGDB_management(os.path.dirname(gdb_path), os.path.basename(gdb_path))
        return gdb_path
    raise Exception("Failed to create a scratch file geodatabase in this directory: '{0}'!".format(path))

def clear_scratch_gdb(scratch_gdb):
    arcpy.env.workspace = scratch_gdb
    for item in arcpy.ListFeatureClasses():
        arcpy.Delete_management(item)
    for item in arcpy.ListTables():
        arcpy.Delete_management(item)

# enable local imports
local_path = os.path.dirname(__file__)
sys.path.insert(0, local_path)

try:
    import arcpy
    import pythonaddins
except:
    """
    The `import config` above thows a warning if ArcPy is unavailable,
    just swallow it here and let this script import, since most of
    these utils don't depend on ArcPy.
    """
    pass

def toolDialog(toolbox, tool):
    """Error-handling wrapper around pythonaddins.GPToolDialog."""
    result = None
    try:
        result = pythonaddins.GPToolDialog(toolbox, tool)
        # FIXME: this is a hack to prevent:
        # TypeError: GPToolDialog() takes at most 1 argument (2 given)
        # print ''
    except TypeError:
        pass
    # don't return anything. this prevents:
    #   TypeError: GPToolDialog() takes at most 1 argument (2 given)
    return result