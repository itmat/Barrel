import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs

import aws_cdk.aws_batch_alpha as batch

from constructs import Construct


class BarrelStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
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

        job_queue = batch.JobQueue(
            self,
            "JobQueue",
            compute_environments=[
                batch.OrderedComputeEnvironment(
                    compute_environment=compute_environment, order=1
                ),
            ],
        )

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

        cdk.CfnOutput(
            self,
            "SubmitJobCommand",
            value=f"aws batch submit-job --job-name barrel --job-queue {job_queue.job_queue_arn} --job-definition {worker.job_definition_arn}",
        )
