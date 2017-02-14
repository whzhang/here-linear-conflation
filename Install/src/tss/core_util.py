def extract_number_from_string(input_string):
    """
    @param input_string:
    @return: A list of numeric value
    """
    import re
    return [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", input_string)]


def linear_units_to_mile(linear_unit_string):
    """
    Convert a linear unit length to a numeric in mile as the unit
    :param linear_unit_string:
    """
    # Split the input string with any spaces, maximum occurrence is set to 1
    # to make sure we can handle units such as "Nautical Mile"
    val, unit = linear_unit_string.split(None, 1)
    conversion_dict = {
        "Centimeters": 6.21371e-6,
        "Feet": 0.000189394,
        "Inches": 1.5783e-5,
        "Kilometers": 0.621371,
        "Meters": 0.000621371,
        "Miles": 1,
        "Millimeters": 6.2137e-7,
        "Nautical Miles": 1.15078
    }
    if unit not in conversion_dict:
        raise Exception("unhandled unit {0}".format(unit))
    return float(val) * conversion_dict[unit]