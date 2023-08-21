import worker

from abc import ABC, abstractproperty
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Program(ABC):
    version: str
    location: Path

    @abstractproperty
    def install_command(self) -> str:
        pass

    @abstractproperty
    def executable(self) -> Path:
        pass

    def __post_init__(self):
        self.installation = self.install()

    def install(self) -> str:
        command = f"""
            if [ -d "{self.location}" ]; then exit 0; fi
            
            mkdir -p {self.location}

            export TEMPORARY_DIRECTORY=$(mktemp -d)
            cd $TEMPORARY_DIRECTORY

            {self.install_command}

            rm -r $TEMPORARY_DIRECTORY
        """

        name = type(self).__name__
        return worker.execute(command, job_name=f"INSTALL_{name}", vcpu=8, memory=16000)

