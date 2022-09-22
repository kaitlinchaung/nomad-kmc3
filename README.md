
# Introduction

The pipeline is built using [Nextflow](https://www.nextflow.io), a workflow tool to run tasks across multiple compute infrastructures in a very portable manner. It uses Docker/Singularity containers making installation trivial and results highly reproducible. The [Nextflow DSL2](https://www.nextflow.io/docs/latest/dsl2.html) implementation of this pipeline uses one container per process which makes it much easier to maintain and update software dependencies. Where possible, these processes have been submitted to and installed from [nf-core/modules](https://github.com/nf-core/modules) in order to make them available to all nf-core pipelines, and to everyone within the Nextflow community!

# Prerequisites

1. Install Java.
2. Install [`nextflow`](https://nf-co.re/usage/installation).
3. Depending on your use case, install [`docker`](https://www.docker.com/), or [`singularity`](https://sylabs.io/guides/3.5/user-guide/introduction.html). By using the `docker` or `singularity` nextflow profile, the pipeline can be run within the NOMAD docker container (also available on [dockerhub](https://hub.docker.com/repository/docker/kaitlinchaung/nomad), which contains all the required dependencies.

# Try the pipeline
To test this pipeine, use the command below. The `test` profile will launch a pipeline run with a small dataset hosted on this repo (located in `test_data/`). The inputs for this profile are defined in `conf/test.config`.

How to run with singularity:
```bash
nextflow run kaitlinchaung/nomad-kmc3 \
    -profile test,singularity \
    -r main \
    -latest
```

How to run with docker:
```bash
nextflow run kaitlinchaung/nomad-kmc3 \
    -profile test,docker \
    -r main \
    -latest
```
# Outputs
For each step, all output files are published in enumerated sub-directories. Here is the output file tree:
```
results/
├── module_1_10X_preprocessing
│   ├── step_1_umitools
│   ├── step_2_extract_cbc_umi
│   ├── step_3_concat_fastqs
│   └── step_4_dedup_cbc_umi
├── module_2_nomad_preprocessing
│   ├── step_1_fetch_anchors
│   ├── step_2_count_anchors
│   ├── step_3_stratify_anchors
│   └── step_4_get_abundant_anchors
├── module_3_nomad_statistics
│   └── step_1_compute_pvals
│       ├── Muscle_Endothelial_capillary_endothelial_cell
│       ├── Muscle_Endothelial_endothelial_cell_of_artery
│       ├── Muscle_Endothelial_endothelial_cell_of_lymphatic_vessel
│       ├── Muscle_Endothelial_endothelial_cell_of_vascular_tree
│       ├── Muscle_Immune_cd4_positive__alpha_beta_t_cell
│       ├── Muscle_Immune_erythrocyte
│       ├── Muscle_Immune_macrophage
│       ├── Muscle_Immune_mast_cell
│       ├── Muscle_Immune_mature_nk_t_cell
│       ├── Muscle_Immune_t_cell
│       ├── Muscle_Stromal_fast_muscle_cell
│       ├── Muscle_Stromal_mesenchymal_cell
│       ├── Muscle_Stromal_mesenchymal_stem_cell
│       ├── Muscle_Stromal_pericyte_cell
│       ├── Muscle_Stromal_skeletal_muscle_satellite_stem_cell
│       ├── Muscle_Stromal_slow_muscle_cell
│       └── Muscle_Stromal_tendon_cell
└── pipeline_info
```

# Citations

This pipeline uses code and infrastructure developed and maintained by the [nf-core](https://nf-co.re) initative, and reused here under the [MIT license](https://github.com/nf-core/tools/blob/master/LICENSE).

> The nf-core framework for community-curated bioinformatics pipelines.
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> Nat Biotechnol. 2020 Feb 13. doi: 10.1038/s41587-020-0439-x.
>

