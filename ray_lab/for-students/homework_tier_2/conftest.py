import os
import sys

import pytest
import ray

sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def ray_session():
    ray.init(ignore_reinit_error=True)
    yield
    ray.shutdown()
