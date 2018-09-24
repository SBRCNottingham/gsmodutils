from tutils import FakeProjectContext
import pytest
from gsmodutils.utils.io import load_model, load_medium
import tempfile
from gsmodutils.utils.validator import validate_model
import cobra
from gsmodutils.utils import FrozenDict, convert_stoich, equal_stoich, biomass_debug


def test_load_model():
    """ Force exceptions to be thrown """
    with pytest.raises(IOError):
        load_model('/this/path/does/not/exist')

    with pytest.raises(TypeError):
        # Create a fake file, format is not valid
        with tempfile.NamedTemporaryFile() as fp:
            load_model(fp.name, file_format="foo")

    with FakeProjectContext() as ctx:
        model = ctx.project.model

        load_medium(model, {}, copy=True)
        with pytest.raises(TypeError):
            load_medium(model, set())

        with pytest.raises(TypeError):
            load_medium(set(), dict())


def test_validator():
    """ Check models validate properly """
    with FakeProjectContext() as ctx:
        # Valid model
        model = ctx.project.model
        result = validate_model(model)
        assert len(result['errors']) == 0

        # Model that can't grow
        for re in model.exchanges:
            re.lower_bound = 0

        result = validate_model(model)
        assert len(result['errors']) == 1

        # model without constraints
        model = cobra.Model()
        result = validate_model(model)
        # Should issue warning, this assertion makes sure
        assert len(result['warnings']) == 1


def test_forzen_dict():
    """"""
    fd = FrozenDict({'x': 'moo'})
    hash(fd)

    with pytest.raises(AttributeError):
        fd.popitem()

    with pytest.raises(AttributeError):
        fd.pop('x')

    with pytest.raises(AttributeError):
        fd['x'] = 'f'

    with pytest.raises(AttributeError):
        del fd['x']

    with pytest.raises(AttributeError):
        fd.setdefault('gg')

    with pytest.raises(AttributeError):
        fd.update()


def test_stoich_st():

    convert_stoich({"a":-1, "b":-1, "c":1})

    with pytest.raises(TypeError):
        equal_stoich({}, {})

    with FakeProjectContext() as ctx:
        model = ctx.project.model
        assert equal_stoich(model.reactions[20], model.reactions[20])
        assert not equal_stoich(model.reactions[20], model.reactions[30])


def test_biomass_debug():
    with pytest.raises(TypeError):
        biomass_debug(None, 'foo')

    with FakeProjectContext() as ctx:
        # Valid model
        model = ctx.project.model
        # Remove way of producing
        non_products = biomass_debug(model, model.reactions.BIOMASS_Ec_iAF1260_core_59p81M)
        assert len(non_products) == 0

