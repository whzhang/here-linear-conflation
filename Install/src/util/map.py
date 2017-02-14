import arcpy
import logging
import os

logger = logging.getLogger(__name__)

def zoom_to_selected_features(layer_name, where_clause):
    """
    Look for a layer in TOC by name. Make a selection based on passing in where clause and zoom to selection features.
    """

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame
    layers = arcpy.mapping.ListLayers(mxd,"",df)

    layer = None
    for lyr in layers:
        if lyr.name == layer_name or lyr.datasetName == layer_name:
            layer = lyr
            break

    if layer:
        arcpy.SelectLayerByAttribute_management(layer, "NEW_SELECTION", where_clause)
    else:
        raise Exception("Layer '%s' does not exist." %layer_name)

    df.extent = layer.getSelectedExtent()

    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()

    return

def clear_table_of_content():
    """
    Clear the table of content.
    """
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame # For now, just clear the active data frame
    layers = arcpy.mapping.ListLayers(mxd, "", df)
    table_views = arcpy.mapping.ListTableViews(mxd, "", df)

    for layer in layers:
        arcpy.mapping.RemoveLayer(df, layer)
    for table_view in table_views:
        arcpy.mapping.RemoveTableView(df, table_view)


def update_table_of_content(layers_to_remove=None,
                            table_views_to_remove=None,
                            feature_classes_to_remove=None,
                            tables_to_remove=None,
                            feature_classes_to_add=None,
                            tables_to_add=None):

    """
    Update table of content. TODO: overhaul this
    :param layers_to_remove: use layer.name to find the layer to be removed
    :param table_views_to_remove: same as above
    :param feature_classes_to_remove: use table view's dataset name to find table views to be removed
    :param tables_to_remove: same as aboves
    :param feature_classes_to_add:
    :param tables_to_add:
    """
    logger.info("update table of content")

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame # For now, only work on active data frame
    layers = [layer for layer in arcpy.mapping.ListLayers(mxd, "", df) if layer.isFeatureLayer]
    table_views = arcpy.mapping.ListTableViews(mxd, "", df)

    if layers_to_remove is not None:
        if layers_to_remove == "*":
            for layer in layers:
                arcpy.mapping.RemoveLayer(df, layer)
        else:
            for layer in layers:
                if layer.name in layers_to_remove:
                    arcpy.mapping.RemoveLayer(df, layer)

    if table_views_to_remove is not None:
        if table_views_to_remove == "*":
            for table_view in table_views:
                arcpy.mapping.RemoveTableView(df, table_view)
        else:
            for table_view in table_views:
                if table_view.name in table_views_to_remove:
                    arcpy.mapping.RemoveTableView(df, table_view)

    if feature_classes_to_remove is not None:
        if feature_classes_to_remove == "*":
            for layer in layers:
                arcpy.mapping.RemoveLayer(df, layer)
        else:
            for layer in layers:
                if layer.datasetName in [os.path.basename(fc) for fc in feature_classes_to_remove]:
                    arcpy.mapping.RemoveLayer(df, layer)

    if tables_to_remove is not None:
        if tables_to_remove == "*":
            for table_view in table_views:
                arcpy.mapping.RemoveTableView(df, table_view)
        else:
            table_names_to_remove = [os.path.basename(tab) for tab in tables_to_remove]
            for table_view in table_views:
                if table_view.datasetName in table_names_to_remove:
                    arcpy.mapping.RemoveTableView(df, table_view)

    if feature_classes_to_add is not None:
        for feature_class in feature_classes_to_add:
            if arcpy.Exists(feature_class):
                logger.info("Adding {0} to TOC.".format(feature_class))
                feature_class_name = os.path.basename(feature_class)
                arcpy.MakeFeatureLayer_management(feature_class, feature_class_name)
                layer = arcpy.mapping.Layer(feature_class_name)
                arcpy.mapping.AddLayer(df, layer, "BOTTOM")
                df.extent = layer.getSelectedExtent()

    if tables_to_add is not None:
        for table in tables_to_add:
            if arcpy.Exists(table):
                logger.info("Adding {0} to TOC".format(table))
                table_name = os.path.basename(table)
                arcpy.MakeTableView_management(table,table_name)
                table_view = arcpy.mapping.TableView(table_name)
                arcpy.mapping.AddTableView(df, table_view)

    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()
