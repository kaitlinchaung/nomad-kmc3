
process ANCHOR_TARGET_COUNTS {

    label 'process_high'
    conda (params.enable_conda ? "conda-forge::python=3.9.5 pandas=1.4.1" : null)

    input:
    path targets_samplesheet

    output:
    path "anchor_targets_counts*.tsv"  , emit: anchor_target_counts

    script:
    outfile_counts_distances_hamming   = "anchor_targets_counts.tsv"
    """
    anchor_target_counts.py \\
        --targets_samplesheet ${targets_samplesheet} \\
        --outfile_counts_distances ${outfile_counts_distances_hamming}
    """
}