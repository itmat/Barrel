import argparse
import boto3
import os
import worker

from contextlib import suppress
from pathlib import Path
from urllib.parse import urlparse


def transfer(source: str, destination: Path):
    return worker.execute(
        f"if [ ! -f '{destination}' ]; then transfer --source={source} --destination={destination}; fi",
        job_name="FILE_TRANSFER",
        job_queue=os.environ["JOB_QUEUE_ARN"],
        memory=4096,
        retry_attempts=2,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--destination")
    transfer = parser.parse_args()

    Path(transfer.destination).parent.mkdir(parents=True, exist_ok=True)

    source = urlparse(transfer.source)

    if source.scheme == "s3":
        bucket = source.netloc
        key = source.path[1:]

        s3 = boto3.resource("s3")

        configuration = boto3.s3.transfer.TransferConfig(
            use_threads=False, max_bandwidth=4_000_000
        )
        s3.Bucket(bucket).download_file(key, transfer.destination, Config=configuration)
    elif source.scheme == "file":
        with suppress(FileExistsError):
            os.symlink(source.path, transfer.destination)
    else:
        raise NotImplementedError
