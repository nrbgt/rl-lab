""" automation scripts for building gt-coar-lab

Roughly, the intent is:
- on a contributor's machine
  - derive conda-lock files from yml files
  - derive constructor files from lock file
  - update CI configuration from constructs
- in CI, or a contributor's machine
  - validate well-formedness of the source files
  - build any novel conda packages
  - build an installer
  - test the installer
  - gather test reports
  - combine test reports
  - generate documentation
  - build a release candidate
"""

# Copyright (c) 2020 University System of Georgia and GTCOARLab Contributors
# Distributed under the terms of the BSD-3-Clause License
import os
from pathlib import Path

from doit.tools import CmdAction, create_folder
from ruamel_yaml import safe_load

# see additional environment variable hacks at the end
DOIT_CONFIG = {
    "backend": "sqlite3",
    "verbosity": 2,
    "par_type": "thread",
    "default_tasks": ["ALL"],
}

# patch environment for all child tasks
os.environ.update(PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", MAMBA_NO_BANNER="1")


def task_setup():
    """handle non-conda setup tasks"""
    yield dict(
        name="yarn",
        doc="install npm dependencies with yarn",
        file_dep=[P.YARN_LOCK, P.PACKAGE_JSON, P.YARNRC],
        actions=[U.script(C.YARN)],
        targets=[P.YARN_INTEGRITY],
    )


def task_lint():
    """ensure all files match expected style"""
    yield dict(
        name="prettier",
        doc="format YAML, markdown, JSON, etc.",
        file_dep=[*P.ALL_PRETTIER, P.YARN_INTEGRITY, P.PRETTIERRC],
        actions=[
            U.script(
                [
                    *C.YARN,
                    "prettier",
                    "--config",
                    P.PRETTIERRC,
                    "--list-different",
                    "--write",
                    *P.ALL_PRETTIER,
                ]
            )
        ],
    )

    yield dict(
        name="black",
        doc="format python source",
        file_dep=[*P.ALL_PY, P.PYPROJECT],
        actions=[
            U.script(["isort", *P.ALL_PY]),
            U.script(["black", "--quiet", *P.ALL_PY]),
        ],
    )

    yield dict(
        name="yamllint",
        doc="check yaml format",
        task_dep=["lint:prettier"],
        file_dep=[*P.ALL_YAML],
        actions=[U.script(["yamllint", *P.ALL_YAML])],
    )


def task_lock():
    """generate conda locks for all envs"""
    for variant in C.VARIANTS:
        for subdir in C.SUBDIRS:
            variant_spec = P.SPECS / f"{variant}-{subdir}.yml"
            if not variant_spec.exists():
                continue
            args = ["conda-lock", "--mamba", "--platform", subdir]
            lockfile = P.LOCKS / f"{variant}-{subdir}.conda.lock"
            specs = [*P.CORE_SPECS, P.SPECS / f"{subdir}.yml", variant_spec]
            args += sum([["--file", spec] for spec in specs], [])
            args += ["--filename-template", variant + "-{platform}.conda.lock"]

            yield dict(
                name=f"{variant}:{subdir}",
                file_dep=specs,
                actions=[
                    (create_folder, [P.LOCKS]),
                    U.cmd(args, cwd=str(P.LOCKS)),
                ],
                targets=[lockfile],
            )


# some namespaces for project-level stuff
class C:
    """constants"""

    ENC = dict(encoding="utf-8")
    YARN = ["yarn", "--silent"]
    VARIANTS = ["cpu", "gpu"]
    SUBDIRS = ["linux-64", "osx-64", "win-64"]


class P:
    """paths"""

    DODO = Path(__file__)
    ROOT = DODO.parent
    SCRIPTS = ROOT / "_scripts"
    CI = ROOT / ".github"

    # checked in
    CONDARC = CI / ".condarc"
    PACKAGE_JSON = SCRIPTS / "package.json"
    YARNRC = SCRIPTS / ".yarnrc"
    PYPROJECT = SCRIPTS / "pyproject.toml"
    TEMPLATES = ROOT / "templates"
    SPECS = ROOT / "specs"

    # generated, but checked in
    YARN_LOCK = SCRIPTS / "yarn.lock"
    WORKFLOW = CI / "workflows/ci.yml"
    LOCKS = ROOT / "locks"

    # stuff we don't check in
    BUILD = ROOT / "build"
    DIST = ROOT / "dist"
    NODE_MODULES = SCRIPTS / "node_modules"
    YARN_INTEGRITY = NODE_MODULES / ".yarn-integrity"

    # config cruft
    PRETTIERRC = SCRIPTS / ".prettierrc"

    # collections of things
    CORE_SPECS = [SPECS / "_base.yml", SPECS / "core.yml"]
    ALL_PY = [DODO]
    ALL_YAML = [
        *SPECS.glob("*.yml"),
        *CI.rglob("*.yml"),
    ]
    ALL_MD = [*ROOT.glob("*.md")]
    ALL_PRETTIER = [
        *ALL_YAML,
        *ALL_MD,
        *SCRIPTS.glob("*.json"),
        *CI.glob("*.yml"),
        CONDARC,
        PYPROJECT,
    ]


class D:
    """data"""

    WORKFLOW = safe_load(P.WORKFLOW.read_text(**C.ENC))


class U:
    """utilities"""

    cmd = lambda *args, **kwargs: CmdAction(*args, **kwargs, shell=False)
    script = lambda *args, **kwargs: U.cmd(*args, **kwargs, cwd=str(P.SCRIPTS))


# late environment patches
os.environ.update(CONDARC=str(P.CONDARC))
