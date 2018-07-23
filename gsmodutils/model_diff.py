from __future__ import print_function
from cobra import Model
from gsmodutils.utils import check_obj_sim, convert_stoich, equal_stoich


class ModelDiff(dict):

    def __init__(self, model_a=None, model_b=None, *args, **kwargs):
        """
        A subclass of dict that has a nice, friendly html representation for use with jupyter
        :param cobra.Model model_a: left model (base model)
        :param cobra.Model model_b: right model (new model)
        """
        self.model_a = model_a
        self.model_b = model_b

        self.update(*args, **kwargs)

        required_attr = ["metabolites", "reactions", "genes",
                         "removed_reactions", "removed_metabolites", "removed_genes"]

        for k in required_attr:
            self.setdefault(k, [])

        if self.model_b is not None and self.model_a is not None:
            self._diff_models(self.model_a, self.model_b)

        super(ModelDiff, self).__init__(*args, **kwargs)

    def _table_header(self):

        title = ""
        if self.model_b is not None and self.model_a is not None:
            title = "Model diff between {} {}".format(self.model_a.id, self.model_b.id)

        info_str = """
               {}
                <table>
                    <tr>
                        <td> Removed reactions: </td>
                        <td> {} </td>
                    </tr>
                    <tr>
                        <td> Removed metabolites: </td>
                        <td> {} </td>
                    </tr>
                    <tr>
                        <td> Removed genes: </td>
                        <td> {} </td>
                    </tr>

                    <tr>
                        <td> Added or removed reactions: </td>
                        <td> {} </td>
                    </tr>
                    <tr>
                        <td> Added or removed  metabolites: </td>
                        <td> {} </td>
                    </tr>
                    <tr>
                        <td> Added or removed  genes: </td>
                        <td> {} </td>
                    </tr>
                """.format(
            title,
            len(self["removed_reactions"]),
            len(self["removed_metabolites"]),
            len(self["removed_genes"]),
            len(self["reactions"]),
            len(self["metabolites"]),
            len(self["genes"]),
        )
        return info_str

    def _reaction_table(self):
        info_str = ""
        if len(self["reactions"]):
            info_str += "<strong> Added/Changed reactions: </strong>"
            for reaction in self["reactions"]:
                info_str += """
                <table>
                <th> Reaction id</th>
                <th>name</th>
                <th>gene_reaction_rule</th>
                <th>subsystem</th>
                <th>upper_bound</th>
                <th>lower_bound</th>
                <th>objective_coefficient</th>
                <tr>
                    <td>{id}</td>
                    <td>{name}</td>
                    <td>{gene_reaction_rule}</td>
                    <td>{subsystem}</td>
                    <td>{upper_bound}</td>
                    <td>{lower_bound}</td>
                    <td>{objective_coefficient}</td>
                </tr>
                <tr> <td colspan=7 > {rstr} </td> </tr>
                <tr> <td colspan=7> {rstr_names} </td> </tr>
                """.format(**reaction)

            info_str += "</table>"
        return info_str

    def _metabolite_table(self):
        """
        :return:
        """
        info_str = ""
        if len(self["metabolites"]):
            info_str += """
            <strong> Added/Changed Metabolites </strong>
            <table>
                <th> Metabolite id </th>
                <th> name </th>
                <th> compartment </th>
                <th> charge </th>
                <th> notes </th>
                <th> annotation </th>   
            """
            for mb in self["metabolites"]:
                info_str += """
                    <tr>
                        <td>{id}</td>
                        <td>{name}</td>
                        <td>{compartment}</td>
                        <td>{charge}</td>
                        <td>{notes}</td>
                        <td>{annotation}</td>
                    </tr>
                """.format(**mb)

            info_str += "</table>"

        return info_str

    def _genes_table(self):
        """
        :return:
        """
        info_str = ""
        if len(self["genes"]):
            info_str += """
            <strong> Added/Changed Metabolites </strong>
            <table>
                <th> Gene id </th>
                <th> Gene name </th>
                <th> notes </th>
                <th> functional </th>
                <th> annotation </th>
            """
            for gene in self["genes"]:
                info_str += """
                <tr>
                    <td>{id}</td>
                    <td>{name}</td>
                    <td>{notes}</td>
                    <td>{functional}</td>
                    <td>{annotation}</td>
                </tr>
                """.format(**gene)
        info_str += "</table>"
        return info_str

    def _repr_html_(self):
        """Method intended for jupyter notebooks"""
        info_str = self._table_header()

        def _rem_tpl(attr, title):
            istr = ""
            if len(self.get(attr)):
                istr = """
                <table>
                    <th> {0} </th>
                """.format(title)
                for remid in self.get(attr):
                    istr += """
                    <tr> 
                        <td> {} </td>
                    </tr>
                    """.format(remid)

                istr += "</table>"
            return istr

        info_str += _rem_tpl("removed_metabolites", "Removed Metabolite")
        info_str += "<br />"
        info_str += _rem_tpl("removed_reactions", "Removed Reactions")
        info_str += "<br />"
        info_str += _rem_tpl("removed_genes", "Removed genes")
        info_str += "<br />"

        info_str += self._reaction_table()
        info_str += "<br />"
        info_str += self._metabolite_table()
        info_str += "<br />"
        info_str += self._genes_table()
        info_str += "<br />"
        return info_str

    @staticmethod
    def model_diff(model_a, model_b):
        """
        Returns a dictionary that contains all of the changed reactions between model a and model b
        This includes any reactions or metabolites removed, or any reactions or metabolites added/changed
        This does not say HOW a model has changed if reactions or metabolites are changed they are just included
        with their new values

        Diff assumes l -> r (i.e. model_a is the base model)
        :param cobra.Model model_a:
        :param cobra.Model model_b:
        :return:
        """
        if not (isinstance(model_a, Model) and isinstance(model_b, Model)):
            raise TypeError('Can only compare cobra models')

        return ModelDiff(model_a, model_b)

    def _diff_models(self, model_a, model_b):
        """

        :param cobra.Model model_a:
        :param cobra.Model model_b:
        :return:
        """
        metfields = ['formula', 'charge', 'compartment', 'name']
        for ma in model_a.metabolites:
            # Find removed metabolites
            try:
                model_b.metabolites.get_by_id(ma.id)
            except KeyError:
                self['removed_metabolites'].append(ma.id)

        def parse_compartment(compartment):
            if compartment == "":
                return None
            return compartment

        for mb in model_b.metabolites:
            # find added metabolites
            # find if metabolite has changed at all
            try:
                ma = model_a.metabolites.get_by_id(mb.id)
                ma.compartment = parse_compartment(ma.compartment)
            except KeyError:
                ma = None

            if ma is None or not check_obj_sim(ma, mb, metfields):
                self['metabolites'].append(
                    dict(
                       id=mb.id,
                       notes=mb.notes,
                       compartment=parse_compartment(mb.compartment),
                       formula=mb.formula,
                       name=mb.name,
                       charge=mb.charge,
                       annotation=mb.annotation,
                    )
                )

        reacfields = [
            'lower_bound', 'upper_bound',
            'gene_reaction_rule', 'subsystem', 'name',
            'variable_kind',
        ]
        for ra in model_a.reactions:
            # reaction has been removed
            try:
                model_b.reactions.get_by_id(ra.id)
            except KeyError:
                self['removed_reactions'].append(ra.id)

        for rb in model_b.reactions:
            # reaction is new
            try:
                ra = model_a.reactions.get_by_id(rb.id)
            except KeyError:
                ra = None

            # reaction has changed or is new
            if ra is None or not check_obj_sim(ra, rb, reacfields) or not equal_stoich(ra, rb):
                self['reactions'].append(
                    dict(
                        id=rb.id,
                        lower_bound=rb.lower_bound,
                        upper_bound=rb.upper_bound,
                        gene_reaction_rule=rb.gene_reaction_rule,
                        subsystem=rb.subsystem,
                        objective_coefficient=rb.objective_coefficient,
                        name=rb.name,
                        variable_kind=rb.variable_kind,
                        metabolites=dict(convert_stoich(rb.metabolites)),
                        rstr=rb.build_reaction_string(use_metabolite_names=False),
                        rstr_names=rb.build_reaction_string(use_metabolite_names=True)
                    )
                )
        # Gene reaction rules are stored in reactions, however models also contains metadata for genes
        genefields = ["name", "annotation", "notes"]

        for ga in model_a.genes:
            try:
                model_b.genes.get_by_id(ga.id)
            except KeyError:
                self['removed_genes'].append(ga.id)

        for gb in model_b.genes:
            try:
                ga = model_a.genes.get_by_id(gb.id)
            except KeyError:
                ga = None
                # reaction has changed or is new
            if ga is None or not check_obj_sim(ga, gb, genefields):
                self['genes'].append(
                    dict(
                        id=gb.id,
                        name=gb.name,
                        annotation=gb.annotation,
                        notes=gb.notes,
                        functional=gb.functional,
                    )
                )


def model_diff(model_a, model_b):
    """
    @depricated - use ModelDiff.model_diff(model_a, model_b)
    Returns a ModelDiff dictionary that contains all of the changed reactions between model a and model b
    This includes any reactions or metabolites removed, or any reactions or metabolites added/changed
    This does not say HOW a model has changed if reactions or metabolites are changed they are just included with their
    new values
    Diff assumes l -> r (i.e. model_a is the base model)
    """
    return ModelDiff.model_diff(model_a, model_b)
