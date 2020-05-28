# Copyright (c) 2020 University System of Georgia and GTCOARLab Contributors
# Distributed under the terms of the BSD-3-Clause License
from scripts import meta as M
from scripts import paths as P
from scripts import utils as U

DOIT_CONFIG = {
    "backend": "sqlite3",
    "verbosity": 2,
    "par_type": "thread",
}


# prepare envs
[globals().update(U.make_prepare_task(env_spec)) for env_spec in M.ENVS_TO_PREPARE]

# linting
[
    globals().update(U.make_lint_task(target, files))
    for target, files in P.LINTERS.items()
]


def task_integrity():
    return dict(
        file_dep=[P.PROJ, U.env_canary("qa"), *P.ALL_PY, *P.ALL_PRETTIER],
        actions=[[*P.APR, "integrity"]],
    )


# building
[
    globals().update(U.make_build_task(target, *files))
    for target, files in M.BUILDERS.items()
]

# binding
def task_binder():
    return dict(
        file_dep=[P.PROJ, U.env_canary("qa")],
        actions=[[*P.APR, "binder"]],
        targets=[P.BINDER_ENV],
    )
