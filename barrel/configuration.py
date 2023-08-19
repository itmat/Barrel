import os

import aws_cdk.aws_efs as efs

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class User:
    id: int
    name: str


@dataclass
class Infrastructure:
    file_system_type: type[efs.FileSystem]
    file_system_mount_point: Path
    users: list[User] = field(default_factory=list)
    account: str = os.getenv("CDK_DEFAULT_ACCOUNT")
    region: str = os.getenv("CDK_DEFAULT_REGION")


@dataclass
class Analysis:
    infrastructure: Infrastructure


@dataclass
class Configuration(Infrastructure):
    study: str = None
    analysis: str = None
