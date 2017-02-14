import os
import os.path
import uuid

def get_parent_directory(path, level=1):
    """
    Return the path of upper directory
    @param path: input path
    @param level: the upper level
    @return: @raise ValueError:
    """
    if level <= 0:
        raise ValueError("Level cannot be < 1")
    parent_path = path
    while level > 0:
        parent_path = os.path.dirname(parent_path)
        level -= 1
    return parent_path


def get_user_directory():
    """
    @return: the home directory
    """
    return os.path.expanduser("~")


def get_scratch_folder(path):
    """
    Create a scratch folder (named by uuid) under path directory
    :param path:
    :return:
    """
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    folder_path = os.path.join(path, str(uuid.uuid4()))
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path