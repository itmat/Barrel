import os
import worker

from pathlib import Path

from bioinformatics.data import Read, Sample
from bioinformatics.genome import Genome, Species
from bioinformatics.software import FASTQC, STAR, PORT, SAMTOOLS, SAM2COV

# Set the main directory for the analysis

analysis_directory = Path(
    f"{os.environ['FILE_SYSTEM_MOUNT_POINT']}/{os.environ['STUDY_NAME']}/{os.environ['ANALYSIS_NAME']}"
)

worker.logs_directory = analysis_directory / "logs"

# Software

software_directory = analysis_directory / "software"

fastqc = FASTQC("0.12.1", software_directory / "FastQC-0.12.1")
star = STAR("2.7.10b", software_directory / "STAR-2.7.10b")
port = PORT("0.8.5f-beta_hotfix1", software_directory / "PORT-v0.8.5f-beta_hotfix1")
samtools = SAMTOOLS("1.18", software_directory / "samtools-1.18")
sam2cov = SAM2COV("0.0.5.4-beta", software_directory / "sam2cov-v0.0.5.4-beta")

# Genome

genome = Genome(
    Species.MUS_MUSCULUS, "GRCm38", release="102", location=analysis_directory / "genome"
)

star.create_index(genome)

# Samples

fastq_files_source_directory = (
    f"s3://{os.environ['BUCKET_NAME']}/{os.environ['BUCKET_PREFIX']}/fastq/0.1%"
)

controls = {f"W{i+1}": f"Control{i+1}" for i in range(6)}
treatments = {f"K{i+1}": f"Treatment{i+1}" for i in range(6)}

sample_information = controls | treatments

samples = []

for sample_id, sample_name in sample_information.items():
    forward_read = Read(
        source=f"{fastq_files_source_directory}/{sample_id}_1.fastq.gz",
        location=analysis_directory / "fastq" / f"{sample_name}_1.fastq.gz",
    )

    reverse_read = Read(
        source=f"{fastq_files_source_directory}/{sample_id}_2.fastq.gz",
        location=analysis_directory / "fastq" / f"{sample_name}_2.fastq.gz",
    )

    fastqc.analyze(forward_read, analysis_directory / "qc")
    fastqc.analyze(reverse_read, analysis_directory / "qc")

    sample = Sample(id=sample_name, reads=[forward_read, reverse_read])
    samples.append(sample)

# Align

for sample in samples:
    star.align(
        sample, analysis_directory / "alignment" / f"{sample.id}_Aligned.out.sam"
    )

# Normalize

port.normalize(
    samples,
    genome,
    sam2cov=sam2cov,
    samtools=samtools,
    location=analysis_directory / "normalization",
    # second_part=True,
    # cutoff=3,
    # resume=True
)
