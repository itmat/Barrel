import worker

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Species(StrEnum):
    HOMO_SAPIENS = "Homo_sapiens"
    MUS_MUSCULUS = "Mus_musculus"
    DROSOPHILA_MELANOGASTER = "Drosophila_melanogaster"
    DANIO_RERIO = "Danio_rerio"
    CAENORHABDITIS_ELEGANS = "Caenorhabditis_elegans"


@dataclass
class Genome:
    species: Species
    version: str
    release: str
    location: Path

    def __post_init__(self):
        self.location = Path(self.location)

        self.fasta_file = (
            self.location / f"{self.species}.{self.version}.dna.primary_assembly.fa"
        )
        self.gtf_file = (
            self.location / f"{self.species}.{self.version}.{self.release}.chr.gtf"
        )

        if self.species == Species.DROSOPHILA_MELANOGASTER:
            self.mitochondrial_chromosome = "mitochondrion_genome"

        if self.species in (Species.HOMO_SAPIENS, Species.MUS_MUSCULUS):
            self.mitochondrial_chromosome = "MT"

        self.files_download = self.download_genome_files()

    def download_genome_files(self):
        if self.species == Species.DROSOPHILA_MELANOGASTER:
            command = f"""
                if [ ! -f '{self.fasta_file}' ]; then
                    for chromosome in 2L 2R 3L 3R 4 X Y mitochondrion_genome;
                    do
                        wget -O {self.species}.{self.version}.dna.primary_assembly.${{chromosome}}.fa.gz http://ftp.ensembl.org/pub/release-{self.release}/fasta/{self.species.lower()}/dna/{self.species}.{self.version}.dna.primary_assembly.${{chromosome}}.fa.gz
                    done
                    
                    mkdir -p {self.location}
                    zcat {self.species}.{self.version}.dna.primary_assembly.*.fa.gz > {self.fasta_file};
                fi

                if [ ! -f '{self.gtf_file}' ]; then
                    wget -P {self.location} http://ftp.ensembl.org/pub/release-{self.release}/gtf/{self.species.lower()}/{self.gtf_file.name}.gz
                    gunzip {self.gtf_file}.gz;
                fi
            """
        else:
            command = f"""
                if [ ! -f '{self.fasta_file}' ]; then
                    wget -P {self.location} http://ftp.ensembl.org/pub/release-{self.release}/fasta/{self.species.lower()}/dna/{self.fasta_file.name}.gz
                    gunzip {self.fasta_file}.gz;
                fi

                if [ ! -f '{self.gtf_file}' ]; then
                    wget -P {self.location} http://ftp.ensembl.org/pub/release-{self.release}/gtf/{self.species.lower()}/{self.gtf_file.name}.gz
                    gunzip {self.gtf_file}.gz;
                fi
            """

        return worker.execute(command, job_name="DOWNLOAD_GENOME_FILES")
