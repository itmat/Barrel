import os
import worker

from pathlib import Path
# Set the main directory for the analysis

analysis_directory = Path(
    f"{os.environ['FILE_SYSTEM_MOUNT_POINT']}/{os.environ['STUDY_NAME']}/{os.environ['ANALYSIS_NAME']}"
)

worker.logs_directory = analysis_directory / "logs"
