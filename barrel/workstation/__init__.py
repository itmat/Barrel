import json
import os
import requests

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_efs as efs
import aws_cdk.aws_fsx as fsx

from pathlib import Path

from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct

from barrel.configuration import User
from barrel.utilities.file_system import mount

SSH_PORT = 2222


class Workstation(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        users: list[User],
        vpc: ec2.Vpc,
        instance_type: ec2.InstanceType,
        block_device_volume_size: int,
        file_system: efs.FileSystem | fsx.LustreFileSystem,
        file_system_mount_point: Path,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.instance = ec2.Instance(
            self,
            "Instance",
            vpc=vpc,
            instance_type=instance_type,
            machine_image=ec2.MachineImage.latest_amazon_linux2(cached_in_context=True),
            user_data_causes_replacement=True,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=block_device_volume_size,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        encrypted=True,
                    ),
                )
            ],
        )

        # SSH connection

        aws_ip_ranges = json.loads(
            requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json").text
        )

        for entry in aws_ip_ranges["prefixes"]:
            if (
                entry["service"] == "EC2_INSTANCE_CONNECT"
                and entry["region"] == scope.region
            ):
                ec2_instance_connect_service_ip = entry["ip_prefix"]

        self.instance.connections.allow_from(
            ec2.Peer.ipv4(ec2_instance_connect_service_ip),
            ec2.Port.tcp(22),
        )

        self.instance.add_user_data("yum install -y ec2-instance-connect")

        # File system

        file_system.connections.allow_default_port_from(self.instance)
        mount(file_system, self.instance, file_system_mount_point)

        # Container

        self.instance.add_user_data(
            "yum install -y docker", "systemctl start docker", "groupadd docker"
        )

        image = DockerImageAsset(
            self,
            "Image",
            directory="barrel/workstation/container",
            build_args={
                "USERS": json.dumps(
                    [
                        {
                            "id": user.id,
                            "name": user.name,
                            "key": user.key.public.read_text(),
                        }
                        for user in users
                    ]
                )
            },
        )

        image.repository.grant_pull(self.instance)

        run_container_command = f"""
            aws ecr get-login-password --region {scope.region} |                                                        \
            docker login --username AWS --password-stdin {scope.account}.dkr.ecr.{scope.region}.{scope.url_suffix}

            docker run --detach --init                                                                                  \
                --mount source={file_system_mount_point},target={file_system_mount_point},type=bind                     \
                --publish {SSH_PORT}:22                                                                                 \
                --env TZ={os.environ["TZ"]}                                                                             \
                {image.image_uri}
        """

        self.instance.add_user_data(run_container_command)

        security_group = ec2.SecurityGroup(self, "SecurityGroup", vpc=vpc)

        for user in users:
            for cidr_block in user.cidr_blocks:
                security_group.add_ingress_rule(
                    ec2.Peer.ipv4(cidr_block), ec2.Port.tcp(SSH_PORT)
                )

        self.instance.add_security_group(security_group)
        self.instance.add_user_data("usermod --append --groups docker ec2-user")
