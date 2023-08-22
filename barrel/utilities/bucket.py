import aws_cdk as cdk
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_transfer as transfer

import boto3

from typing import Optional

from barrel.configuration import User


def configure_access_via_ftp(
    bucket: s3.IBucket, users: list[User], prefix: Optional[str] = None
):
    stack = bucket.stack

    ftp_server_access_role = iam.Role(
        stack,
        "FtpServerAccessRole",
        assumed_by=iam.ServicePrincipal("transfer.amazonaws.com"),
    )

    ftp_server_logging_role = iam.Role(
        stack,
        "FtpServerLoggingRole",
        assumed_by=iam.ServicePrincipal("transfer.amazonaws.com"),
    )

    ftp_server_logging_role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSTransferLoggingAccess"
        )
    )

    if not prefix:
        bucket.grant_read_write(ftp_server_access_role)
    else:
        bucket.grant_read_write(ftp_server_access_role, f"{prefix}/*")

    ftp_server = transfer.CfnServer(
        stack,
        "FtpServer",
        domain="S3",
        protocols=["SFTP"],
        identity_provider_type="SERVICE_MANAGED",
        logging_role=ftp_server_logging_role.role_arn,
    )

    home_directory = (
        f"/{bucket.bucket_name}" if not prefix else f"/{bucket.bucket_name}/{prefix}"
    )

    for user in users:
        transfer.CfnUser(
            stack,
            f"{user.name.capitalize()}FtpServerUser",
            server_id=ftp_server.attr_server_id,
            user_name=user.name,
            home_directory=home_directory,
            role=ftp_server_access_role.role_arn,
            ssh_public_keys=[user.key.public.read_text()],
        )

    cdk.CfnOutput(
        stack,
        "FtpServerEndpoint",
        value=f"{ftp_server.attr_server_id}.server.transfer.{stack.region}.{stack.url_suffix}",
    )


def get_region(bucket: s3.IBucket):
    bucket_location = boto3.client("s3").get_bucket_location(Bucket=bucket.bucket_name)
    return bucket_location["LocationConstraint"]
