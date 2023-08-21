import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3

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

        if configuration.bucket.name:
            bucket = s3.Bucket.from_bucket_name(
                self, "Bucket", configuration.bucket.name
            )
        else:
            bucket = s3.Bucket(self, "Bucket", **configuration.bucket.properties)

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

        file_system_type = configuration.file_system.type
        file_system_mount_point = configuration.file_system.mount_point

        if file_system_type is efs.FileSystem:
            file_system = efs.FileSystem(
                self,
                "ElasticFileSystem",
                vpc=vpc,
                **configuration.file_system.properties,
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

        worker_job_definition_name = f"{cdk.Names.unique_id(self)}WorkerDefinition"

        worker = batch.EcsJobDefinition(
            self,
            "Worker",
            container=batch.EcsEc2ContainerDefinition(
                self,
                "WorkerContainer",
                image=ecs.ContainerImage.from_asset(
                    directory="barrel",
                    file="worker/Dockerfile",
                    build_args={"STUDY_NAME": configuration.study},
                ),
                environment={
                    "STUDY_NAME": configuration.study,
                    "ANALYSIS_NAME": configuration.analysis,
                    "AWS_DEFAULT_REGION": self.region,
                    "JOB_QUEUE_ARN": job_queue.job_queue_arn,
                    "WORKER_JOB_DEFINITION_NAME": worker_job_definition_name,
                    "BUCKET_NAME": bucket.bucket_name,
                    "FILE_SYSTEM_MOUNT_POINT": str(file_system_mount_point),
                },
                job_role=iam.Role(
                    self,
                    "WorkerRole",
                    assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                ),
                cpu=1,
                memory=cdk.Size.mebibytes(512),
            ),
            job_definition_name=worker_job_definition_name,
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

        bucket.grant_read(worker.container.job_role)

        grant_submit_job = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["batch:SubmitJob"],
            resources=[
                job_queue.job_queue_arn,
                self.format_arn(
                    service="batch",
                    resource="job-definition",
                    resource_name=worker_job_definition_name,
                ),
            ],
        )

        grant_list_jobs = iam.PolicyStatement(
            effect=iam.Effect.ALLOW, actions=["batch:ListJobs"], resources=["*"]
        )

        worker.container.job_role.add_to_principal_policy(grant_submit_job)
        worker.container.job_role.add_to_principal_policy(grant_list_jobs)

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
            users=configuration.users,
        )

        cdk.CfnOutput(
            self,
            "StartPipelineCommand",
            value=f"""
                aws batch submit-job                                                                                \
                    --job-name PIPELINE                                                                             \
                    --job-queue {job_queue.job_queue_arn}                                                           \
                    --job-definition {worker_job_definition_name}                                                   \
                    --container-override command='["python3", "{configuration.study}/{configuration.pipeline}"]'
            """,
        )
