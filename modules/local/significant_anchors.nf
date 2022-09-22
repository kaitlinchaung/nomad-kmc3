
process SIGNIFICANT_ANCHORS {

    tag "${samplesheet_id}"
    label "process_high"
    publishDir(
        path: {"${params.outdir}/module_3_nomad_statistics/step_2_significant_anchors/${samplesheet_id}"},
        mode: "copy",
        pattern: "*.tsv")
    publishDir(
        path: {"${params.outdir}/module_3_nomad_statistics/step_2_significant_anchors/${samplesheet_id}"},
        mode: "copy",
        pattern: "*.csv")
    conda (params.enable_conda ? "conda-forge::python=3.9.5 pandas=1.4.1 anaconda::statsmodels" : null)

    input:
    tuple val(samplesheet_id), path(samplesheet), path(anchors)
    val fdr_threshold

    output:
    tuple val(samplesheet_id), path(samplesheet), path(outfile_scores), emit: scores
    path "all*tsv"              , emit: all_scores  , optional: true
    path "anchors_Cjs*"         , emit: cjs         , optional: true

    script:
    outfile_scores              = "significant_anchors_pvals.tsv"
    outfile_all_anchors_pvals   = "all_anchors_pvals.tsv"
    outfile_Cjs                 = "anchors_Cjs_random_opt.tsv"
    """
    significant_anchors.py \\
        --fdr_threshold ${fdr_threshold} \\
        --samplesheet ${samplesheet} \\
        --outfile_scores ${outfile_scores} \\
        --outfile_all_anchors_pvals ${outfile_all_anchors_pvals} \\
        --outfile_Cjs ${outfile_Cjs}
    """
}
