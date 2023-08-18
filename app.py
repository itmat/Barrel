#!/usr/bin/env python3
import string

import aws_cdk as cdk

from importlib import import_module

from barrel.barrel_stack import BarrelStack
from barrel.configuration import Configuration

app = cdk.App()

study_name = app.node.try_get_context("study")
analysis_name = app.node.try_get_context("analysis")

study = import_module(f"barrel.studies.{study_name}")
analysis = study.analyses[analysis_name]

configuration = Configuration(
    study=study_name,
    analysis=analysis_name,
    file_system_type=analysis.infrastructure.file_system_type,
    file_system_mount_point=analysis.infrastructure.file_system_mount_point,
)


def to_pascal_case(identifier):
    return string.capwords(identifier, sep="_").replace("_", "")


stage = cdk.Stage(app, to_pascal_case(configuration.study))
BarrelStack(stage, "BarrelStack", configuration=configuration)

app.synth()
