import aws_cdk.aws_efs as efs

from pathlib import Path

from barrel.configuration import Analysis, Infrastructure


infrastructure = Infrastructure(
    file_system_type=efs.FileSystem, file_system_mount_point=Path("/mnt/fs")
)

analyses = {
    "analysis": Analysis(
        infrastructure=infrastructure,
    )
}
