"""
Tests for metacyc integration

Requires the use of fake database as real metacyc databases require a license
"""
from tutils import METACYC_DB_PATH, FakeProjectContext
from gsmodutils.utils import metacyc
import os


def test_db():

    with FakeProjectContext() as ctx:
        cache_location = os.path.join(ctx.path, '.gsmod_metacyc_db.json')
        db = metacyc.parse_db(METACYC_DB_PATH)
        db = metacyc.parse_db(METACYC_DB_PATH)
        _ = metacyc.build_universal_model(METACYC_DB_PATH, use_cache=True, cache_location=cache_location)
        _ = metacyc.build_universal_model(METACYC_DB_PATH, use_cache=True, cache_location=cache_location)
        _ = metacyc.build_universal_model(METACYC_DB_PATH, use_cache=False)
        model = ctx.model
        metacyc.add_pathway(model, reaction_ids=["ALCOHOL-DEHYDROG-RXN"], db_path=METACYC_DB_PATH)
        model = ctx.model
        metacyc.add_pathway(model, enzyme_ids=["EC-1.1.1.1"], db_path=METACYC_DB_PATH)
