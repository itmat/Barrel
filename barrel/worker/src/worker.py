import asyncio
import boto3
import os
import sys

from pathlib import Path
from typing import Iterable

analysis_directory = Path(
    f"{os.environ['FILE_SYSTEM_MOUNT_POINT']}/{os.environ['STUDY_NAME']}/{os.environ['ANALYSIS_NAME']}"
)

logs_directory = analysis_directory / "logs"


def execute(
    command: str,
    job_name: str,
    vcpu: int = 1,
    memory: int = 2048,
    depends_on: list[str] = [],
    retry_attempts: int = 1,
    job_queue: str = os.environ["JOB_QUEUE_ARN"],
) -> str:
    batch = boto3.client("batch")

    environment = {
        "STDOUT_LOG": logs_directory / f"{job_name}.out",
        "STDERR_LOG": logs_directory / f"{job_name}.err",
    }

    logs_directory.mkdir(parents=True, exist_ok=True)

    return batch.submit_job(
        jobName=job_name,
        jobQueue=job_queue,
        jobDefinition=os.environ["WORKER_JOB_DEFINITION_NAME"],
        dependsOn=[{"jobId": job_id} for job_id in depends_on],
        retryStrategy={"attempts": retry_attempts},
        containerOverrides={
            "command": ["worker", command],
            "environment": [
                {"name": key, "value": str(value)} for key, value in environment.items()
            ],
            "resourceRequirements": [
                {"type": "MEMORY", "value": str(memory)},
                {"type": "VCPU", "value": str(vcpu)},
            ],
        },
    )["jobId"]


def wait(dependencies: Iterable[str] = []):
    return execute(":", job_name="WAIT", depends_on=list(dependencies))


def every(jobs: Iterable[str]):
    "Shrink the dependency list to a list containing one job – used to go around the limit of 20 dependencies per job"

    jobs_list = list(jobs)

    if len(jobs_list) == 0:
        return [wait()]

    if len(jobs_list) == 1:
        return jobs_list

    reduced_jobs_list = [
        wait(jobs_list[i : i + 20]) for i in range(0, len(jobs_list), 20)
    ]

    return every(reduced_jobs_list)


def main():
    command = sys.argv[1]

    async def duplicate(stream, streams):
        async for line in stream:
            for target in streams:
                target.write(line.decode())

    async def execute(command):
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        with open(os.environ["STDOUT_LOG"], "a") as stdout_log:
            with open(os.environ["STDERR_LOG"], "a") as stderr_log:
                await asyncio.gather(
                    duplicate(process.stdout, (sys.stdout, stdout_log)),
                    duplicate(process.stderr, (sys.stderr, stderr_log)),
                )

        return await process.wait()

    return asyncio.run(execute(command))
