from __future__ import print_function

from cobra import Model

from gsmodutils.utils import check_obj_sim, convert_stoich, equal_stoich


class ModelDiff(dict):
    """
    A subclass of dict that has a nice, friendly html representation for use with jupyter
    """
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

        required_attr = ["metabolites", "reactions","genes",
                         "removed_reactions", "removed_metabolites", "removed_genes"]

        for k in required_attr:
            self.setdefault(k, [])

    def _table_header(self):
        info_str = """
                Model diff with
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
            for reaction in self["reactions"]:
                info_str += """
                Added or changed reactions:
                <table>
                <tr>
                    <td>{id}</td>
                    <td>{name}</td>
                    <td>{gene_reaction_rule}</td>
                    <td>{subsystem}</td>
                    <td>{upper_bound}</td>
                    <td>{lower_bound}</td>
                    <td>{objective_coefficient}</td>
                    <td>{rstr}</td>
                    <td>
                        <table>
                            <th> Metabolite </th>
                            <th> Coef </th>
                """.format(**reaction)

                for s, v in reaction["metabolites"]:
                    info_str += "<tr> <td> {} </td> <td> {} </td> </tr>".format(s, v)
                info_str += "</table></td> </tr>"

            info_str += "</table>"
        return info_str

    def _metabolite_table(self):
        """
        :return:
        """
        info_str = ""
        if len(self["metabolites"]):
            info_str += """
            """

        return info_str

    def _genes_table(self):
        """
        :return:
        """
        info_str = ""
        if len(self["genes"]):
            info_str += """
            """

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
                for id in self.get(attr):
                    istr += """
                    <tr> 
                        <td> {} </td>
                    </tr>
                    """.format(id)

                istr += "</table>"
            return istr

        info_str += _rem_tpl("removed_metabolites", "Removed Metabolite")
        info_str += _rem_tpl("removed_reactions", "Removed Reactions")
        info_str += _rem_tpl("removed_genes", "Removed genes")

        info_str += self._reaction_table()
        info_str += self._metabolite_table()
        info_str += self._genes_table()
        return info_str


def model_diff(model_a, model_b):
    """
    Returns a dictionary that contains all of the changed reactions between model a and model b
    This includes any reactions or metabolites removed, or any reactions or metabolites added/changed
    This does not say HOW a model has changed if reactions or metabolites are changed they are just included with their
    new values
    Diff assumes l -> r (i.e. model_a is the base model)
    """

    if not (isinstance(model_a, Model) and isinstance(model_b, Model)):
        raise TypeError('Can only compare cobra models')

    metfields = ['formula', 'charge', 'compartment', 'name']
    
    diff = ModelDiff(
        removed_metabolites=[],
        removed_reactions=[],
        reactions=[],
        metabolites=[]
    )
    
    for ma in model_a.metabolites:
        # Find removed metabolites
        try:
            model_b.metabolites.get_by_id(ma.id)
        except KeyError:
            diff['removed_metabolites'].append(ma.id)

    for mb in model_b.metabolites:
        # find added metabolites
        # find if metabolite has changed at all
        try:
            ma = model_a.metabolites.get_by_id(mb.id)
        except KeyError:
            ma = None
            
        if ma is None or not check_obj_sim(ma, mb, metfields):
                diff['metabolites'].append(
                    dict(
                       id=mb.id,
                       notes=mb.notes,
                       compartment=mb.compartment,
                       formula=mb.formula,
                       name=mb.name,
                       charge=mb.charge,
                       annotation=mb.annotation,
                    )
                )
    
    reacfields = [
        'lower_bound', 'upper_bound', 
        'gene_reaction_rule', 'subsystem', 'name', 
        'variable_kind' 
    ]
    for ra in model_a.reactions:
        # reaction has been removed
        try:
            model_b.reactions.get_by_id(ra.id)
        except KeyError:
            diff['removed_reactions'].append(ra.id)
    
    for rb in model_b.reactions:
        # reaction is new
        try:
            ra = model_a.reactions.get_by_id(rb.id)
        except KeyError:
            ra = None
            
        # reaction has changed or is new
        if ra is None or not check_obj_sim(ra, rb, reacfields) or not equal_stoich(ra, rb):
            diff['reactions'].append(
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
                    rstr=repr(rb),
                )
            )
    # Gene reaction rules are stored in reactions, however models also contains metadata for genes
    genefields = ["name", "annotation", "notes"]

    for ga in model_a.genes:
        try:
            model_b.genes.get_by_id(ga.id)
        except KeyError:
            diff['removed_genes'].append(ga.id)

    for gb in model_b.genes:
        try:
            ga = model_a.genes.get_by_id(gb.id)
        except KeyError:
            ga = None
            # reaction has changed or is new
        if ga is None or not check_obj_sim(ga, gb, genefields):
            diff['genes'].append(
                dict(
                    id=gb.id,
                    name=gb.name,
                    annotation=gb.annotation,
                    notes=gb.notes,
                    functional=gb.functional,
                )
            )
    return diff
