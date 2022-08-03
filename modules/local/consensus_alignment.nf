
process CONSENSUS_ALIGNMENT {

    label 'process_high_memory'
    label 'error_retry'
    conda (params.enable_conda ? 'bioconda::star=2.7.9a' : null)
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/star:2.7.5a--0' :
        'quay.io/biocontainers/star:2.7.5a--0' }"

    input:
    path fasta
    path star_index
    path gtf

    output:
    path "*.bam"    , emit: bam
    path "*.mate1"  , emit: unmapped_fasta

    script:
    fasta_name  = fasta.baseName
    """
    STAR \\
        --runThreadN ${task.cpus} \\
        --genomeDir ${star_index} \\
        --readFilesIn ${fasta} \\
        --twopassMode Basic \\
        --alignIntronMax 1000000 \\
        --outFileNamePrefix ${fasta_name}_ \\
        --outSAMtype BAM Unsorted \\
        --outSAMattributes All \\
        --chimOutType WithinBAM SoftClip Junctions \\
        --chimJunctionOverhangMin 10 \\
        --chimSegmentReadGapMax 0 \\
        --chimOutJunctionFormat 1 \\
        --chimSegmentMin 12 \\
        --chimScoreJunctionNonGTAG -4 \\
        --chimNonchimScoreDropMin 10 \\
        --quantMode GeneCounts \\
        --sjdbGTFfile ${gtf} \\
        --outReadsUnmapped Fastx

    """
}
