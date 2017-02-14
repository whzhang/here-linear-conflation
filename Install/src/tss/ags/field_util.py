import arcpy

def transform_dataset_keep_fields(dataset, keep_fields):
    """
    Transform the input dataset to only keep fields where the field name exists in the input "keep_fields" list
    :param dataset:
    :param keep_fields:
    """
    for field in arcpy.ListFields(dataset):
        if field.required:
            continue
        if field.type in ["OID", "Geometry"]:
            continue
        if field.name.lower() not in [kfld.lower() for kfld in keep_fields]:
            arcpy.DeleteField_management(dataset, field.name)

def alter_field_name(data, old_field_name, new_field_name, is_sde=True):
    """
    Alter the field name. If the input data is in the enterprise geodatabase, then use the old-school way to
    create-copy-delete fields because an existing issue has been identified that the arcpy.AlterField_management won't
    take effect for sde data until the process ends.  Else try alterField_management first, if not working then use the
    old-school way.
    :param data:
    :param old_field_name:
    :param new_field_name:
    :param is_sde: default to True
    :return:
    """
    if old_field_name == new_field_name:
        return
    if is_sde:
        old_field = [field for field in arcpy.ListFields(data) if field.name == old_field_name][0]
        arcpy.AddField_management(data, new_field_name, old_field.type, old_field.precision,
                                  old_field.scale, old_field.length, old_field.aliasName, old_field.isNullable, old_field.required)
        arcpy.CalculateField_management(data, new_field_name, "!%s!" % old_field_name, "PYTHON")
        arcpy.DeleteField_management(data, old_field_name)
    else:
        try:
            arcpy.AlterField_management(data, old_field_name, new_field_name, new_field_name)
        except Exception as e:
            arcpy.AddMessage(e)
            old_field = [field for field in arcpy.ListFields(data) if field.name == old_field_name][0]
            arcpy.AddField_management(data, new_field_name, old_field.type, old_field.precision,
                                      old_field.scale, old_field.length, old_field.aliasName, old_field.isNullable, old_field.required)
            arcpy.CalculateField_management(data, new_field_name, "!%s!" % old_field_name, "PYTHON")
            arcpy.DeleteField_management(data, old_field_name)

def get_field_details(data, field_name):
    # Default field type and field length
    field_type = 'TEXT'
    field_length = 255

    for field in arcpy.ListFields(data):
        if field.name == field_name:
            field_type = field.type
            field_length = field.length
            break

    if field_type == 'Double':
        field_type = 'DOUBLE'
    elif field_type == 'Single':
        field_type = 'FLOAT'
    elif field_type == 'Integer':
        field_type = 'LONG'
    elif field_type == 'SmallInteger':
        field_type = 'SHORT'
    elif field_type == 'Date':
        field_type = 'DATE'
    else:
        field_type = 'TEXT'

    return {'field_type': field_type, 'field_length': field_length}
