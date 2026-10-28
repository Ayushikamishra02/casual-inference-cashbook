import warnings

import pytest

warnings.filterwarnings("ignore")


@pytest.fixture(scope="session")
def ck():
    from causalbook import data

    return data.card_krueger()


@pytest.fixture(scope="session")
def nsw_obs():
    from causalbook import data

    return data.nsw_observational()


@pytest.fixture(scope="session")
def smoking():
    from causalbook import data

    return data.prop99()
