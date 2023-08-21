import worker

from abc import ABC, abstractproperty
from dataclasses import dataclass
from pathlib import Path
from worker import wait

from bioinformatics.data import Sample
from bioinformatics.genome import Genome


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


class STAR(Program):
    @property
    def install_command(self):
        return f"""
            wget https://github.com/alexdobin/STAR/archive/{self.version}.tar.gz
            tar -xzf {self.version}.tar.gz --strip-components 1 --directory {self.location}
            cd {self.location}/source
            make -j STAR
        """

    @property
    def executable(self):
        return self.location / "source" / "STAR"

    def create_index(self, genome: Genome):
        self.index_location = Path(
            f"{genome.location}/{genome.species}.{genome.version}.{genome.release}.index"
        )

        create_index_command = f"""
            mkdir -p {self.index_location}

            {self.executable}                                   \
                --runMode genomeGenerate                        \
                --runThreadN 16                                 \
                --limitGenomeGenerateRAM {90 * 1024**3}         \
                --genomeDir {self.index_location}               \
                --genomeFastaFiles {genome.fasta_file}          \
                --sjdbGTFfile {genome.gtf_file}                 \
                --sjdbOverhang 99
        """

        dependencies = [self.installation, genome.files_download]

        if self.index_location.exists():
            self.index_creation = wait(dependencies)
        else:
            self.index_creation = worker.execute(
                create_index_command,
                job_name="CREATE_INDEX",
                vcpu=16,
                memory=104448,
                depends_on=dependencies,
            )

    def align(self, sample: Sample, output: Path):
        additional_options = []

        if any(read.location.name.endswith(".gz") for read in sample.reads):
            additional_options.append("--readFilesCommand zcat")

        if output.suffix == ".bam":
            additional_options.append("--outSAMtype BAM Unsorted")

        command = f"""
            mkdir -p {output.parent}

            {self.executable}                                                               \
                --outFileNamePrefix {output}                                                \
                --genomeDir {self.index_location}                                           \
                --runMode alignReads                                                        \
                --runThreadN 6                                                              \
                --outSAMunmapped Within KeepPairs                                           \
                --runRNGseed 42                                                             \
                --outSAMtype SAM                                                            \
                --readFilesIn {" ".join(str(read.location) for read in sample.reads)}       \
                {" ".join(additional_options)}

            mv {output}Aligned.out{output.suffix} {output}
        """

        dependencies = [self.installation, self.index_creation] + [
            read.download for read in sample.reads
        ]

        sample.alignment = output

        if output.exists():
            sample.aligning = wait(dependencies)
        else:
            sample.aligning = worker.execute(
                command,
                job_name="ALIGN",
                vcpu=6,
                memory=40960,
                depends_on=dependencies,
            )

