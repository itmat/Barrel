import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs

import aws_cdk.aws_batch_alpha as batch
import aws_cdk.aws_efs as efs

import barrel.utilities as utilities

from constructs import Construct

from barrel.configuration import Configuration
from barrel.workstation import Workstation


class BarrelStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        configuration: Configuration,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Subnet", subnet_type=ec2.SubnetType.PUBLIC
                ),
            ],
        )

        availability_zone, *_ = vpc.availability_zones
        subnet, *_ = vpc.public_subnets

        # File system

        file_system_type = configuration.file_system_type
        file_system_mount_point = configuration.file_system_mount_point

        if file_system_type is efs.FileSystem:
            file_system = efs.FileSystem(
                self,
                "ElasticFileSystem",
                vpc=vpc,
                performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
                lifecycle_policy=efs.LifecyclePolicy.AFTER_1_DAY,
                out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )

            utilities.set_availability_zone(file_system, availability_zone)

        # Computation system

        compute_environment = batch.ManagedEc2EcsComputeEnvironment(
            self,
            "ComputeEnvironment",
            vpc=vpc,
            instance_classes=[
                ec2.InstanceClass.C6A,
                ec2.InstanceClass.M6A,
                ec2.InstanceClass.R6A,
            ],
            maxv_cpus=768,
        )

        file_system.connections.allow_default_port_from(compute_environment)

        job_queue = batch.JobQueue(
            self,
            "JobQueue",
            compute_environments=[
                batch.OrderedComputeEnvironment(
                    compute_environment=compute_environment, order=1
                ),
            ],
        )

        # Worker job definition

        worker = batch.EcsJobDefinition(
            self,
            "Worker",
            container=batch.EcsEc2ContainerDefinition(
                self,
                "WorkerContainer",
                image=ecs.ContainerImage.from_registry(
                    "python:latest",
                ),
                cpu=1,
                memory=cdk.Size.mebibytes(512),
            ),
        )

        if file_system_type is efs.FileSystem:
            worker.container.add_volume(
                batch.EfsVolume(
                    name="Volume",
                    file_system=file_system,
                    container_path=str(file_system_mount_point),
                    readonly=False,
                    enable_transit_encryption=True,
                )
            )

        # Workstation

        workstation = Workstation(
            self,
            "Workstation",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.SMALL
            ),
            block_device_volume_size=128,
            file_system=file_system,
            file_system_mount_point=file_system_mount_point,
        )

        cdk.CfnOutput(
            self,
            "SubmitJobCommand",
            value=f"aws batch submit-job --job-name barrel --job-queue {job_queue.job_queue_arn} --job-definition {worker.job_definition_arn}",
        )
