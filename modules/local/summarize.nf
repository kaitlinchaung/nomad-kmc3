
process SUMMARIZE {

    label 'process_high_memory'
    conda (params.enable_conda ? "conda-forge::python=3.9.5 pandas=1.4.1 numpy=1.22.3 bioconda::blast=2.12.2 bioconda::biopython=1.70" : null)

    input:
    path anchor_scores
    path anchor_targets_counts
    path annotated_anchors
    path annotated_targets

    output:
    path outfile                , emit: tsv

    script:
    outfile                     = "summary.tsv"
    """
    summarize.py \\
        --anchor_scores ${anchor_scores} \\
        --anchor_targets_counts ${anchor_targets_counts} \\
        --annotated_anchors ${annotated_anchors} \\
        --annotated_targets ${annotated_targets} \\
        --outfile ${outfile}
    """
}
