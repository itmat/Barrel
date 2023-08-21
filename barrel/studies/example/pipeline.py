import os
import worker

from pathlib import Path

from bioinformatics.data import Read, Sample
from bioinformatics.genome import Genome, Species
from bioinformatics.software import STAR

# Set the main directory for the analysis

analysis_directory = Path(
    f"{os.environ['FILE_SYSTEM_MOUNT_POINT']}/{os.environ['STUDY_NAME']}/{os.environ['ANALYSIS_NAME']}"
)

worker.logs_directory = analysis_directory / "logs"

# Software

software_directory = analysis_directory / "software"

star = STAR("2.7.10b", software_directory / "STAR-2.7.10b")

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

    sample = Sample(id=sample_name, reads=[forward_read, reverse_read])
    samples.append(sample)

# Align

for sample in samples:
    star.align(
        sample, analysis_directory / "alignment" / f"{sample.id}_Aligned.out.sam"
    )

