import aws_cdk.aws_efs as efs

from pathlib import Path

from barrel.configuration import Analysis, Infrastructure, User

infrastructure = Infrastructure(
    file_system_type=efs.FileSystem,
    file_system_mount_point=Path("/mnt/fs"),
    users=[User(id=1000, name="ec2-user")],
)

analyses = {
    "analysis": Analysis(
        infrastructure=infrastructure,
    )
}
