import os
import shutil
import tempfile
from gsmodutils import GSMProject, load_model
from gsmodutils.utils.io import load_medium
import cobra

_IAF_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'iAF1260.json')
_CORE_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'e_coli_core.json')

scrumpy_model_path = os.path.join(os.path.dirname(__file__), 'scrumpy', 'MetaSal.spy')
scrumpy_biomass_path = os.path.join(os.path.dirname(__file__), 'scrumpy', 'biomass_comp.json')
scrumpy_media_path = os.path.join(os.path.dirname(__file__), 'scrumpy', 'media.json')

METACYC_DB_PATH = os.path.join(os.path.dirname(__file__), 'metacyc_db')


class CleanUpFile(object):
    """
    Context utility for ensuring that a given file is always removed after a test is run
    """
    def __init__(self, fpath):
        self._fpath = fpath

    def __enter__(self):
        pass

    def __exit__(self, *args):
        if os.path.exists(self._fpath):
            os.remove(self._fpath)


class CleanUpDir(object):
    """
    Context utility for ensuring that a given temp directory
    """
    def __init__(self, path=None):
        self.path = path

    def __enter__(self):
        if self.path is None:
            # Create a tempdir
            self.path = tempfile.mkdtemp()

        return self

    def __exit__(self, *args):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)


class FakeProjectContext(object):
    
    def __init__(self, model=None, path=None, use_second_model=False):
        """
        Assumes projectConfig class works correctly
        """
        self.path = path
        if self.path is None:
            self.path = tempfile.mkdtemp()

        self.mdl_path = tempfile.mkstemp()
        self.model = model
        if self.model is None:
            self.model = load_model(_IAF_MODEL_PATH)

        self.second_model = None
        if use_second_model:
            self.second_model = load_model(_CORE_MODEL_PATH)

    def __enter__(self):
        """
        Create a temporary gsmodutils project folder
        """
        add_models = [self.model]

        if self.second_model is not None:
            add_models += [self.second_model]

        self.project = GSMProject.create_project(add_models, 'TEST PROJECT ONLY', 'test', '123@abc.com', self.path)
        return self
    
    def __exit__(self, *args):
        """
        Delete directory and model
        """
        os.remove(self.mdl_path[1])
        shutil.rmtree(self.path)

    def add_fake_conditions(self):
        """ Add some fake conditions to the project"""
        conditions = dict(
            EX_xyl__D_e=-8.0,
            EX_ca2_e=-99999.0,
            EX_cbl1_e=-0.01,
            EX_cl_e=-99999.0,
            EX_co2_e=-99999.0,
            EX_cobalt2_e=-99999.0,
            EX_cu2_e=-99999.0,
            EX_fe2_e=-99999.0,
            EX_fe3_e=-99999.0,
            EX_h2o_e=-99999.0,
            EX_h_e=-99999.0,
            EX_k_e=-99999.0,
            EX_mg2_e=-99999.0,
            EX_mn2_e=-99999.0,
            EX_mobd_e=-99999.0,
            EX_na1_e=-99999.0,
            EX_nh4_e=-99999.0,
            EX_o2_e=-18.5,
            EX_pi_e=-99999.0,
            EX_so4_e=-99999.0,
            EX_tungs_e=-99999.0,
            EX_zn2_e=-99999.0
        )
        mdl = self.project.model
        load_medium(mdl, conditions)
        self.project.save_conditions(mdl, "xyl_src", apply_to=self.project.config.default_model)

    def add_fake_designs(self):
        """ Add a fake design with a parent design """
        model = self.project.model
        project = self.project

        # Phosphoribulokinase reaction
        stoich = dict(
            atp_c=-1.0,
            ru5p__D_c=-1.0,
            adp_c=1.0,
            h_c=1.0,
            rb15bp_c=1.0,
        )

        rb15bp = cobra.Metabolite(id='rb15bp_c', name='D-Ribulose 1,5-bisphosphate', formula='C5H8O11P2', charge=0)
        model.add_metabolites(rb15bp)

        pruk = cobra.Reaction(id="PRUK", name="Phosphoribulokinase reaction", lower_bound=-1000, upper_bound=1000)
        model.add_reactions([pruk])
        pruk.add_metabolites(stoich)

        # Rubisco reaction (Ribulose-bisphosphate carboxylase)
        stoich = {
            "3pg_c": 2.0,
            "rb15bp_c": -1.0,
            "co2_c": -1.0,
            "h2o_c": -1.0,
            "h_c": 2.0
        }

        rubisco = cobra.Reaction(id="RBPC", lower_bound=0, upper_bound=1000.0, name="Ribulose-bisphosphate carboxylase")

        model.add_reactions([rubisco])
        rubisco.add_metabolites(stoich)

        model.genes.get_by_id("b3916").knock_out()
        model.genes.get_by_id("b1723").knock_out()
        model.genes.get_by_id("b1852").knock_out()

        model.reactions.EX_glc__D_e.lower_bound = -10.0
        model.reactions.EX_nh4_e.lower_bound = -1000.0

        project.save_design(model, 'cbb_cycle', 'calvin cycle',
                            description='Reactions necissary for the calvin cycle in ecoli', overwrite=True)

        # Create a child of this design
        model = project.load_design('cbb_cycle')
        reaction = cobra.Reaction(id="HMGCOASi", name="Hydroxymethylglutaryl CoA synthase")

        aacoa = cobra.Metabolite(id="aacoa_c", charge=-4, formula="C25H36N7O18P3S", name="Acetoacetyl-CoA")
        hmgcoa = cobra.Metabolite(id="hmgcoa_c", charge=-5, formula="C27H40N7O20P3S", name="Hydroxymethylglutaryl CoA")

        model.add_metabolites([aacoa, hmgcoa])

        stoich = dict(
            aacoa_c=-1.0,
            accoa_c=-1.0,
            coa_c=1.0,
            h_c=1.0,
            h2o_c=-1.0,
            hmgcoa_c=1.0,
        )

        model.add_reactions([reaction])
        reaction.add_metabolites(stoich)
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

        mev__r = cobra.Metabolite(id="mev__R_c", name="R Mevalonate", charge=-1, formula="C6H11O4")
        model.add_metabolites([mev__r])

        reaction = cobra.Reaction(id="HMGCOAR", name="Hydroxymethylglutaryl CoA reductase")
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

        stoich = dict(
            coa_c=-1.0,
            h_c=2.0,
            nadp_c=-2.0,
            nadph_c=2.0,
            hmgcoa_c=1.0,
            mev__R_c=-1.0
        )

        model.add_reactions([reaction])

        reaction.add_metabolites(stoich)

        model.add_boundary(mev__r, type='sink')  # add somewhere for mevalonate to go

        project.save_design(model, 'mevalonate_cbb', 'mevalonate production', parent='cbb_cycle',
                            description='Reactions for the production of mevalonate', overwrite=True)

        py_design = """
def gsmdesign_testpy(model, project):
    reaction = model.reactions.get_by_id("ATPM")
    reaction.bounds = (-999, 999)
    return model

gsmdesign_testpy.parent = "mevalonate_cbb"
        """
        ndpath = os.path.join(project.design_path, 'design_fake.py')
        with open(ndpath, 'w+') as desf:
            desf.write(py_design)

    def add_fake_tests(self):
        code_str = """
# Look our tests are python 2 compatible!
# p.s. if you're reading this you're such a nerd
from __future__ import print_function 
from gsmodutils.test.utils import ModelTestSelector

@ModelTestSelector(models=["not_there"], conditions=["xyl_src", "bad", "not_there"], designs=["not_there"])
def test_func(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")


# For code coverage
@ModelTestSelector()
def test_func_cove(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")


def test_model(model, project, log):
    solution = model.solver.optimize()
    print('This is the end')
    log.warning(True, "this is a warning")
    log.assertion(True, "Model grows", "Model does not grow")
    log.assertion(False, "Model grows", "Model does not grow")


def test_exception(model, project, log):
    raise Exception('This is exceptional')
            """

        test_path = os.path.join(self.path, "tests", "test_code.py")
        with open(test_path, "w+") as tf:
            tf.write(code_str)
