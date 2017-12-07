import cobra
import os
from gsmodutils.utils.scrumpy import load_scrumpy_model


def load_model(path, file_format=None):
    """
    Model loading that accepts multiple formats. Implemented to move away from dependency on cameo.load_model which,
    while good for users, created problems in testing.
    :str path: path to model
    :str or None file_format: format model is imported in if None, attemps to guess
    :return: cobra_model
    """
    if not os.path.exists(path):
        raise IOError('File {} not found'.format(path))

    if file_format is None:
        # Guess the file_format from extension
        file_format = os.path.splitext(path)[1][1:].strip().lower()

    if file_format == "json":
        cobra_model = cobra.io.load_json_model(path)
    elif file_format == "yaml":
        cobra_model = cobra.io.load_yaml_model(path)
    elif file_format in ["sbml", "xml"]:
        cobra_model = cobra.io.read_sbml_model(path)
    elif file_format in ["mat", "m", "matlab"]:
        cobra_model = cobra.io.load_matlab_model(path)
    elif file_format in ['spy', 'scrumpy']:
        cobra_model = load_scrumpy_model(path)
    else:
        raise TypeError('Cannot load file format {}'.format(file_format))

    return cobra_model
