from __future__ import print_function, absolute_import, division
from jsonschema import ValidationError


class ProjectNotFound(Exception):
    """ Used if no project can be found in a given directory path """
    pass


class ProjectConfigurationError(Exception):
    """ Used if project configuration is erroneous """
    pass


class DesignError(Exception):
    """ Design error occurs when their is an issue with a given design file """
    pass


class MediumError(Exception):
    """ Model medium incorrect. Model likely misses reaction """
    pass


class DesignNotFoundError(Exception):
    """ Designs not found in project """
    pass


class DesignOrphanError(Exception):
    """ Error for orphan designs """
    pass

