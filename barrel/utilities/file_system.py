import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_efs as efs

from pathlib import Path


def set_availability_zone(file_system: efs.FileSystem, availability_zone: str):
    file_system: efs.CfnFileSystem = file_system.node.default_child
    file_system.availability_zone_name = availability_zone


def mount(file_system: efs.FileSystem, instance: ec2.Instance, mount_point: Path):
    mount_point = str(mount_point)

    mount_command = f"""
        yum install -y amazon-efs-utils
        mkdir -p {mount_point}
        mount -t efs -o tls {file_system.file_system_id} {mount_point}
        echo {file_system.file_system_id}:/ {mount_point} efs _netdev,noresvport,tls,iam 0 0 >> /etc/fstab
    """

    instance.add_user_data(mount_command)
