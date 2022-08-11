from pathlib import Path
from shutil import copy, rmtree

import pytest
from juju.application import Application
from pytest_operator.plugin import OpsTest

itest_root = Path(__file__)
root = itest_root.parent.parent.parent


@pytest.fixture(autouse=True)
def libs():
    lib = root / 'signals.py'
    tester_libs = []
    for tester in ('echo-tester', 'ping-tester'):
        tgt_lib_path = itest_root / tester / 'lib'
        tester_libs.append(tgt_lib_path)
        tgt_path = tgt_lib_path / 'charms' / 'signals' / 'v0' / 'signals.py'
        copy(lib.absolute(), tgt_path.absolute())

    yield

    for tgt_lib_path in tester_libs:
        rmtree(tgt_lib_path)


@pytest.fixture
@pytest.mark.abort_on_fail
async def ping_charm(ops_test: OpsTest):
    return await ops_test.build_charm(itest_root / 'ping-tester')


@pytest.fixture
@pytest.mark.abort_on_fail
async def echo_charm(ops_test: OpsTest):
    return await ops_test.build_charm(itest_root / 'echo-tester')


@pytest.fixture(autouse=True)
async def deployment(ops_test: OpsTest, echo_charm, ping_charm):
    await ops_test.model.deploy(echo_charm, application_name='echo')
    await ops_test.model.deploy(ping_charm, application_name='ping')
    await ops_test.model.wait_for_idle(['echo', 'ping'], status='active')

    yield

    await ops_test.model.applications['echo'].remove()
    await ops_test.model.applications['ping'].remove()


async def test_ping(ops_test: OpsTest):
    ping_app: Application = await ops_test.model.applications['ping']
    await ping_app.run('ping')
    await ops_test.model.wait_for_idle(['echo', 'ping'], status='active')
