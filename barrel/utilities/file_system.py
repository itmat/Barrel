import aws_cdk.aws_efs as efs


def set_availability_zone(file_system: efs.FileSystem, availability_zone: str):
    file_system: efs.CfnFileSystem = file_system.node.default_child
    file_system.availability_zone_name = availability_zone
