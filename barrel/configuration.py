import aws_cdk.aws_efs as efs

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Infrastructure:
    file_system_type: type[efs.FileSystem]
    file_system_mount_point: Path


@dataclass
class Analysis:
    infrastructure: Infrastructure


@dataclass
class Configuration(Infrastructure):
    study: str = None
    analysis: str = None
