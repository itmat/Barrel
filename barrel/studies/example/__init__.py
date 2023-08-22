import aws_cdk.aws_efs as efs
import aws_cdk.aws_fsx as fsx

from barrel.configuration import (
    Analysis,
    Bucket,
    FileSystem,
    Infrastructure,
    Link,
    User,
)

infrastructure = Infrastructure(
    bucket=Bucket(name="itmat-bioinformatics-test-data", prefix="example"),
    file_system=FileSystem(type=efs.FileSystem),
    users=[User(id=1000, name="ec2-user")],
)

# infrastructure = Infrastructure(
#     bucket=Bucket(name="itmat-bioinformatics-test-data", prefix="example"),
#     file_system=FileSystem(
#         type=fsx.LustreFileSystem,
#         links=[Link(file_system_path="/data", bucket_prefix="example")],
#     ),
#     users=[User(id=1000, name="ec2-user")],
# )

analyses = {
    "analysis": Analysis(
        infrastructure=infrastructure,
        pipeline="pipeline.py",
    )
}
