import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_efs as efs
import aws_cdk.aws_fsx as fsx
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3

import aws_cdk.custom_resources as cr

from pathlib import Path

from barrel.configuration import Link
from barrel.utilities import get_region


def set_availability_zone(file_system: efs.FileSystem, availability_zone: str):
    file_system: efs.CfnFileSystem = file_system.node.default_child
    file_system.availability_zone_name = availability_zone


def set_version(file_system: fsx.LustreFileSystem, version: str = "2.12"):
    file_system: fsx.CfnFileSystem = file_system.node.default_child
    file_system.file_system_type_version = version


def mount_command(
    file_system: efs.FileSystem | fsx.LustreFileSystem, mount_point: Path
):
    if isinstance(file_system, efs.FileSystem):
        return f"""
            yum install -y amazon-efs-utils
            mkdir -p {mount_point}
            mount -t efs -o tls {file_system.file_system_id} {mount_point}
            echo {file_system.file_system_id}:/ {mount_point} efs _netdev,noresvport,tls,iam 0 0 >> /etc/fstab
        """

    if isinstance(file_system, fsx.LustreFileSystem):
        return f"""
            amazon-linux-extras install -y lustre
            mkdir -p {mount_point}
            mount -t lustre -o relatime,flock {file_system.dns_name}@tcp:/{file_system.mount_name} {mount_point}
            echo {file_system.dns_name}@tcp:/{file_system.mount_name} {mount_point}                                     \
                lustre defaults,relatime,flock,_netdev,x-systemd.automount,x-systemd.requires=network.service 0 0       \
                >> /etc/fstab
        """

    raise NotImplementedError


def mount_template(
    file_system: efs.FileSystem | fsx.LustreFileSystem, mount_point: Path
):
    if isinstance(file_system, fsx.LustreFileSystem):
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(mount_command(file_system, mount_point))

        multipart_user_data = ec2.MultipartUserData()
        multipart_user_data.add_part(
            ec2.MultipartBody.from_user_data(user_data=user_data)
        )

        return ec2.LaunchTemplate(
            file_system.stack, "FileSystemMountTemplate", user_data=multipart_user_data
        )

    if isinstance(file_system, efs.FileSystem):
        return None


def mount(
    file_system: efs.FileSystem | fsx.LustreFileSystem,
    instance: ec2.Instance,
    mount_point: Path,
):
    instance.add_user_data(mount_command(file_system, mount_point))


def establish(link: Link, file_system: fsx.LustreFileSystem, bucket: s3.IBucket):
    stack = file_system.stack

    if not stack.region == get_region(bucket):
        raise ValueError(
            "Linking of file system with a bucket requires both resources to exist in the same region."
        )

    bucket_arn = bucket.bucket_arn
    bucket_name = bucket.bucket_name

    if link.bucket_prefix:
        bucket_prefix = link.bucket_prefix.strip("/")
    else:
        bucket_prefix = None

    if not bucket_prefix:
        data_repository_arn = bucket_arn
        data_repository_path = f"s3://{bucket_name}"
    else:
        data_repository_arn = f"{bucket_arn}/{bucket_prefix}"
        data_repository_path = f"s3://{bucket_name}/{bucket_prefix}"

    if link.read_only:
        data_repository_permissions = ["s3:Get*", "s3:List*"]
        data_repository_configuration = {
            "AutoImportPolicy": {"Events": ["NEW", "CHANGED", "DELETED"]},
        }
    else:
        data_repository_permissions = ["s3:Get*", "s3:List*", "s3:PutObject"]
        data_repository_configuration = {
            "AutoImportPolicy": {"Events": ["NEW", "CHANGED", "DELETED"]},
            "AutoExportPolicy": {"Events": ["NEW", "CHANGED", "DELETED"]},
        }

    cr.AwsCustomResource(
        stack,
        "CreateDataRepositoryAssociation",
        policy=cr.AwsCustomResourcePolicy.from_statements(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "fsx:CreateDataRepositoryAssociation",
                        "fsx:DeleteDataRepositoryAssociation",
                    ],
                    resources=[
                        stack.format_arn(
                            service="fsx",
                            resource="file-system",
                            resource_name=file_system.file_system_id,
                        ),
                        stack.format_arn(
                            service="fsx",
                            resource="association",
                            resource_name=f"{file_system.file_system_id}/*",
                        ),
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=data_repository_permissions,
                    resources=[bucket_arn, f"{data_repository_arn}/*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "iam:CreateServiceLinkedRole",
                        "iam:AttachRolePolicy",
                        "iam:PutRolePolicy",
                    ],
                    resources=[
                        f"arn:{stack.partition}:iam::{stack.account}:role/aws-service-role/s3.data-source.lustre.fsx.{stack.url_suffix}/*"
                    ],
                ),
            ]
        ),
        on_create=cr.AwsSdkCall(
            service="FSx",
            action="createDataRepositoryAssociation",
            parameters={
                "FileSystemId": file_system.file_system_id,
                "FileSystemPath": link.file_system_path,
                "DataRepositoryPath": data_repository_path,
                "BatchImportMetaDataOnCreate": True,
                "S3": data_repository_configuration,
            },
            physical_resource_id=cr.PhysicalResourceId.from_response(
                "Association.AssociationId"
            ),
        ),
        on_delete=cr.AwsSdkCall(
            service="FSx",
            action="deleteDataRepositoryAssociation",
            parameters={
                "AssociationId": cr.PhysicalResourceIdReference(),
                "DeleteDataInFileSystem": False,
            },
        ),
    )
