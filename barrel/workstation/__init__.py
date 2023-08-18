import json
import requests

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_efs as efs

from pathlib import Path

from constructs import Construct

from ..utilities.file_system import mount


class Workstation(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        instance_type: ec2.InstanceType,
        block_device_volume_size: int,
        file_system: efs.FileSystem,
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

        # Connect the file system

        file_system.connections.allow_default_port_from(self.instance)
        mount(file_system, self.instance, file_system_mount_point)
