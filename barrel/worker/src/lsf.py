import argparse
import boto3
import fileinput
import os
import time


def bjobs():
    batch = boto3.client("batch")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        help="Displays job information without truncating fields",
        action="store_true",
    )
    parser.parse_args()

    job_queue = os.environ["JOB_QUEUE_ARN"]
    jobs_paginator = batch.get_paginator("list_jobs")

    for status in ("SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING"):
        for page in jobs_paginator.paginate(jobQueue=job_queue, jobStatus=status):
            time.sleep(0.1)
            for job in page["jobSummaryList"]:
                job_name = job["jobName"].replace("-", ".")
                print(job_name, "RUN" if status == "RUNNING" else "PEND")

    time.sleep(1.5)


def bsub():
    batch = boto3.client("batch")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-J", "--job_name", help="Assigns the specified name to the job"
    )
    parser.add_argument(
        "-M",
        "--memory",
        help="Sets a memory limit for all the processes that belong to the job",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        help="Appends the standard output of the job to the specified log",
    )
    parser.add_argument(
        "-e",
        "--error_file",
        help="Appends the standard error output of the job to the specified log",
    )
    args = parser.parse_args()

    job_name = args.job_name.replace(".", "-")
    commands = "".join(fileinput.input(files=("-",)))

    memory = int(args.memory) + 512

    if "filtersam" or "get_novel_exons" in job_name:
        memory += 3072

    environment = {"STDOUT_LOG": args.output_file, "STDERR_LOG": args.error_file}

    batch.submit_job(
        jobName=job_name,
        jobQueue=os.environ["JOB_QUEUE_ARN"],
        jobDefinition=os.environ["WORKER_JOB_DEFINITION_NAME"],
        containerOverrides={
            "command": ["worker", commands],
            "environment": [
                {"name": key, "value": value} for key, value in environment.items()
            ],
            "resourceRequirements": [
                {"type": "MEMORY", "value": str(memory)},
                {"type": "VCPU", "value": "1"},
            ],
        },
    )
