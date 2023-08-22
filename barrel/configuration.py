import atexit
import os
import requests

import aws_cdk as cdk
import aws_cdk.aws_efs as efs
import aws_cdk.aws_s3 as s3

from dataclasses import dataclass, field
from paramiko import RSAKey
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional


@dataclass
class Key:
    public: Path
    private: Optional[Path] = None


@dataclass
class User:
    id: int
    name: str
    key: Key = None
    cidr_blocks: list[str] = None

    def __post_init__(self):
        if not self.key:
            self.key = Key(
                Path.home() / ".ssh" / f"{self.name}.pub",
                Path.home() / ".ssh" / self.name,
            )

            if not self.key.public.exists() and not self.key.private.exists():
                key = RSAKey.generate(4096)
                key.write_private_key_file(self.key.private)
                self.key.public.write_text(f"{key.get_name()} {key.get_base64()}")

            elif not self.key.public.exists() and self.key.private.exists():
                key = RSAKey.from_private_key_file(self.key.private)
                self.key.public = Path(NamedTemporaryFile(suffix=".pub").name)
                self.key.public.write_text(f"{key.get_name()} {key.get_base64()}")

                atexit.register(lambda: self.key.public.unlink())

            elif self.key.public.exists() and not self.key.private.exists():
                self.key.private = None

        if not self.cidr_blocks:
            ip_address = requests.get("https://checkip.amazonaws.com").text.strip()
            self.cidr_blocks = [f"{ip_address}/32"]


@dataclass
class Bucket:
    name: Optional[str] = None
    prefix: str = None
    access_via_ftp_server: bool = False
    properties: Optional[dict] = None

    def __post_init__(self):
        if not self.name and not self.properties:
            self.properties = dict(
                block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                encryption=s3.BucketEncryption.S3_MANAGED,
                auto_delete_objects=True,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )


@dataclass
class FileSystem:
    type: type[efs.FileSystem]
    mount_point: Path = "/mnt/fs"
    properties: Optional[dict] = None

    def __post_init__(self):
        if not self.properties:
            self.properties = dict(
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                lifecycle_policy=efs.LifecyclePolicy.AFTER_1_DAY,
                out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )


@dataclass
class Infrastructure:
    bucket: Bucket
    file_system: FileSystem
    users: list[User] = field(default_factory=list)
    account: str = os.getenv("CDK_DEFAULT_ACCOUNT")
    region: str = os.getenv("CDK_DEFAULT_REGION")


@dataclass
class Analysis:
    infrastructure: Infrastructure
    pipeline: Path


@dataclass
class Configuration(Infrastructure):
    study: str = None
    analysis: str = None
    pipeline: Path = None
