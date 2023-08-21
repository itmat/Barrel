from dataclasses import dataclass
from transfer import transfer
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class Read:
    source: str
    location: Path

    def __post_init__(self):
        self.location = Path(self.location)
        self.origin = urlparse(self.source).scheme

        if self.origin in ["s3", "file"]:
            self.download = transfer(source=self.source, destination=self.location)
        elif self.origin == "job":
            self.download = self.source.removeprefix("job://")
        else:
            raise NotImplementedError


@dataclass
class Sample:
    id: str
    reads: list[Read]
    alignment: Path = None
