import pandas
import json
import cobra
from gsmodutils.exceptions import DesignError


class StrainDesign(object):

    def __init__(self, id, name, description, project=None, parent=None, base_model=None):
        """
        Class for handling strain designs created by the project

        Mainly the useful functionality of this over dicts is validation, relationship to projects, creating the models
        as well as displaying the contents as a pandas dataframe

        :param project: Where project is None, the model will not be able to
        """
        self._as_model = None

        self.project = project
        self.base_model = base_model

        self.id = id
        self.name = name
        self.description = description

        self.reactions = []
        self.metabolites = []
        self.genes = []

        if type(parent) in [unicode, str]:
            parent = project.load_design(parent)

        self.parent = parent

    def to_dataframe(self):
        """
        Return the design as a datframe containing the necissary information on reactions and metabolites
        :return:
        """
        df = pandas.DataFrame()
        return df

    def reaction_dataframe(selfs):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        pass

    def metabolite_dataframe(selfs):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        pass

    def gene_dataframe(selfs):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        pass

    @property
    def __info__(self):
        info = dict(
            name=self.name,
            id=self.id,
            description=self.description,
            reactions=len(self.reactions),
            genes=len(self.genes),
            metabolites=len(self.metabolites),
            parent=self.parent,
        )
        return info

    def __repr_html__(self):
        info_str = "<table>"
        for k, v in self.__info__.iteritems():
            info_str += "<tr> <td> <strong> {0} </strong> </td> <td> {1} </td> </tr>".format(k, v)
        info_str += "</table>"
        return info_str

    def to_dict(self):
        pass

    @classmethod
    def from_json(cls, project, file_path):
        """
        Load from a json file
        :param file_path:
        :return:
        """
        with open(file_path) as fp:
            # Make sure fields are validated
            design = json.load(fp)
        return cls.from_dict(design)

    @classmethod
    def from_dict(cls, design):
        cls.validate_dict(design)
        this = cls(
            id=design['id'],
            name=design['name'],
            description=design['description'],
            parent=design['parent'],
            reactions=design['reactions'],
            metabolites=design['metabolies'],
            genes=design['genes'],
            base_model=design['base_model']
        )

        return this

    def to_json(self, file_path, overwrite=False):
        """ Write to a given file """
        if not overwrite and os.path.exists(file_path):
            raise IOError("Existing file exists in design path and overwrite flag is False")

        with open(file_path, "w+") as jsn_f:
            json.dump(self.to_dict(), jsn_f, indent=4)

    def load_model(self, model=None):
        """
        Returns a cobra model containing the parent model with the design applied
        :return:
        """
        if self.project is None and model is None:
            raise DesignError("No specified project or model.")

        if model is None:
            model = self.project.load_model(self.base_model)

        model.merge(self.as_model())
        return model

    def as_model(self):
        """
        Loads a cobra model with just the reactions present in this design
        Can be useful for the cobra.Model methods
        :return: mdl instance of cobra.Model
        """

        mdl = cobra.Model()

        for reaction in self.reactions:
            pass

        for metabolite in self.metabolites:
            pass

        return mdl

    @staticmethod
    def validate_dict(design_dict, throw_exceptions=True):
        """
        Check required fields are present
        :param design_dict:
        :param throw_exceptions:
        :return:
        """
        required_fields = ["id", "name", "description", "metabolites", "reactions", "genes"]
        for field in required_fields:
            if field not in design_dict:
                if not throw_exceptions:
                    return False
                raise DesignError("Required field {} missing from design".format(field))

        # TODO: test if reactions are valid
        # TODO: test if metabolites are valid
        # TODO: test genes are valid

        return True

    def __repr__(self):
        repr_s = "< StraignDesign {id} with {reactions} reactions, {genes} genes and {metabolites} metabolites>".format(
            dict(
                id=self.id,
                reactions=len(self.reactions),
                genes=len(self.genes),
                metabolites=len(self.metabolites)
            )
        )
        return repr_s
