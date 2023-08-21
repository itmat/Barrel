import os
import worker

from abc import ABC, abstractproperty
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from worker import every, wait

from bioinformatics.data import Read, Sample
from bioinformatics.genome import Genome, Species


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


class FASTQC(Program):
    @property
    def install_command(self):
        return f"""
            wget https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v{self.version}.zip
            unzip fastqc_v{self.version}.zip -d {self.location}
            mv {self.location}/FastQC/* {self.location}; rmdir {self.location}/FastQC
            chmod a+x {self.location}/fastqc
        """

    @property
    def executable(self):
        return Path(f"{self.location}/fastqc")

    def analyze(self, read: Read, output_directory: Path):
        if not Path(
            f"{output_directory}/{read.location.name.removesuffix(''.join(read.location.suffixes))}_fastqc.zip"
        ).exists():
            worker.execute(
                f"mkdir -p {output_directory}; {self.executable} -o {output_directory} {read.location}",
                job_name="QUALITY_ANALYSIS",
                depends_on=[self.installation, read.download],
            )


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


class SAMTOOLS(Program):
    @property
    def install_command(self):
        return f"""
            wget https://github.com/samtools/samtools/releases/download/{self.version}/samtools-{self.version}.tar.bz2
            tar -xf samtools-{self.version}.tar.bz2

            cd samtools-{self.version}
            autoreconf
            ./configure --prefix={self.location}
            make
            make install
        """

    @property
    def executable(self):
        return Path(f"{self.location}/bin/samtools")


class SAM2COV(Program):
    @property
    def install_command(self):
        return f"""
            wget https://github.com/khayer/sam2cov/archive/v{self.version}.tar.gz
            tar -xzf v{self.version}.tar.gz --strip-components 1 --directory {self.location}

            cd {self.location}
            make
        """

    @property
    def executable(self):
        return Path(f"{self.location}/sam2cov")


class PORT(Program):
    @property
    def install_command(self):
        return f"""
            wget https://github.com/itmat/Normalization/archive/v{self.version}.tar.gz
            tar -xzf v{self.version}.tar.gz --strip-components 1 --directory {self.location}
        """

    @property
    def executable(self):
        return Path(f"{self.location}/norm_scripts/run_normalization")

    def normalize(
        self,
        samples: list[Sample],
        genome: Genome,
        location: Path,
        sam2cov: SAM2COV,
        samtools: SAMTOOLS,
        second_part: bool = False,
        resume: bool = False,
        cutoff: int = None,
        samples_list: str = "sample_directories.txt",
        unaligned_files_list: str = "unaligned_files.loc",
        configuration_file_name: str = "PORT.cfg",
    ) -> str:
        location.mkdir(exist_ok=True)

        # create list of samples
        with open(f"{location}/{samples_list}", "w") as samples_file:
            for sample in samples:
                print(sample.id, file=samples_file)

        # create links to aligned and FASTQ files as well as the list of unaligned files
        with open(f"{location}/{unaligned_files_list}", "w") as unaligned_file:
            for sample in samples:
                link_directory = f"{location}/reads/{sample.id}"

                os.makedirs(link_directory, exist_ok=True)

                with suppress(FileExistsError):
                    os.symlink(sample.alignment, f"{link_directory}/Aligned.out.sam")

                for read in sample.reads:
                    print(f"{link_directory}/{read.location.name}", file=unaligned_file)
                    with suppress(FileExistsError):
                        os.symlink(
                            read.location, f"{link_directory}/{read.location.name}"
                        )

        # create index for genome FASTA file
        genome_fasta_file_index_creation = worker.execute(
            f"""
                if [ -f {genome.fasta_file}.fai ]; then exit 0; fi
                {samtools.executable} faidx -o {genome.fasta_file}.fai {genome.fasta_file};
            """,
            job_name="CREATE_GENOME_FASTA_FILE_INDEX",
            memory=10000,
            depends_on=[samtools.installation, genome.files_download],
        )

        # create genome info file
        genome_info_file = f"{genome.location}/{genome.species}.{genome.version}.{genome.release}.annotation.txt"
        genome_info_file_creation = worker.execute(
            f"""
                if [ -f {genome_info_file} ]; then exit 0; fi
                perl {self.location}/norm_scripts/convert_gtf_to_PORT_geneinfo.transcripts.pl {genome.gtf_file} {genome_info_file}
            """,
            job_name="CREATE_GENOME_INFO_FILE",
            depends_on=[self.installation, genome.files_download],
        )

        ribosomal_rna_fasta_file = {
            Species.HOMO_SAPIENS: "rRNA_mm9.fa",
            Species.MUS_MUSCULUS: "rRNA_mm9.fa",
            Species.DROSOPHILA_MELANOGASTER: "rRNA_dm.fa",
            Species.DANIO_RERIO: "rRNA_danRer.fa",
            Species.CAENORHABDITIS_ELEGANS: "rRNA_c.elegans.fa",
        }[genome.species]

        # Make configuration file
        configuration = {
            "GENOME_FA": genome.fasta_file,
            "GENOME_FAI": f"{genome.fasta_file}.fai",
            "GENE_INFO_FILE": genome_info_file,
            "rRNA_FA": f"{self.location}/norm_scripts/{ribosomal_rna_fasta_file}",
            "SAMTOOLS": samtools.executable,
            "SAM2COV_LOC": sam2cov.executable,
            "CHRM": genome.mitochondrial_chromosome,
        }

        port_configuration = open(f"{os.environ['STUDY_NAME']}/port.cfg").read()

        for key, value in configuration.items():
            port_configuration = port_configuration.replace(
                f"{{{key} = VALUE}}", f"{key} = {value}"
            )

        with open(f"{location}/{configuration_file_name}", "w") as configuration_file:
            configuration_file.write(port_configuration)

        # start the normalization
        command = f"""                                          \
            {self.executable}                                   \
            --sample_dirs {location}/{samples_list}             \
            --loc {location}/reads                              \
            --unaligned {location}/{unaligned_files_list}       \
            --alignedfilename Aligned.out.sam                   \
            --cfg {location}/{configuration_file_name}          \
        """

        if resume:
            command += f" -resume"

        if cutoff:
            command += f" -cutoff_highexp {cutoff}"

        if second_part:
            command += f" -part2"

        return worker.execute(
            command,
            job_name="NORMALIZE",
            depends_on=[
                self.installation,
                samtools.installation,
                sam2cov.installation,
                genome.files_download,
                genome_fasta_file_index_creation,
                genome_info_file_creation,
            ]
            + every(sample.aligning for sample in samples),
        )
