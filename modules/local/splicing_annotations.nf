
process SPLICING_ANNOTATIONS {

    label 'process_medium'
    conda (params.enable_conda ? "bioconda::bedtools=2.30.0" : null)

    input:
    path bam
    path unmapped_fasta
    path gene_bed
    path ann_AS_gtf
    path fasta
    path genome_annotations_anchors

    output:
    path "*tsv"                 , emit: tsv
    path "called_exons.bed"     , emit: bed
    path fasta                  , emit: fasta
    path "consensus_genes.txt"  , emit: consenus_genes

    script:
    outfile_unmapped            = "unmapped_consensus_sequences.tsv"
    outfile_annotations         = "consensus_called_exons.tsv"
    """
    ## get reported alignments
    samtools view ${bam} \\
        | cut -f1,10 \\
        >> reported_alignments.txt

    ## get called exons
    bedtools bamtobed -split -i ${bam} \\
        | sed '/^chr/!d' \\
        | sort -k1,1 -k2,2n \\
        > called_exons.bed

    ## get called exons start and end positions
    awk -v OFS='\\t' '{print \$1,\$2-1,\$2+1,\$4,"called_exon_start",\$6"\\n"\$1,\$3-1,\$3+1,\$4,"called_exon_end",\$6}' called_exons.bed \\
        | sort -k1,1 -k2,2n \\
        | awk -v OFS='\\t' '{if (\$2 < 0) print \$1,0,\$3,\$4,\$5,\$6; else print \$1,\$2,\$3,\$4,\$5,\$6}' \\
        > positions_called_exons.bed

    ## annotate called exon start and ends
    bedtools intersect -a positions_called_exons.bed -b ${ann_AS_gtf} -loj -wb \\
        | cut -f1-5,10-13 \\
        | bedtools groupby -g 1,2,3,4,5, -c 6,7,8,9 -o distinct,distinct,distinct,distinct \\
        > annotated_positions_called_exons.bed

    ## get consensus genes
    bedtools intersect -a called_exons.bed -b ${gene_bed} -wb -loj \\
        | cut -f 4,10 \\
        | bedtools groupby -g 1 -c 2 -o distinct \\
        > consensus_genes.txt

    ## add consensus and anchor gene columns
    splicing_annotations.py \\
        --unmapped_fasta ${unmapped_fasta} \\
        --ann_called_exons annotated_positions_called_exons.bed \\
        --fasta ${fasta} \\
        --genome_annotations_anchors ${genome_annotations_anchors} \\
        --consensus_genes consensus_genes.txt \\
        --reported_alignments reported_alignments.txt \\
        --outfile_unmapped ${outfile_unmapped} \\
        --outfile_annotations ${outfile_annotations}
    """
}
