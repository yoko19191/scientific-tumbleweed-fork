# Sandbox Environment

This sandbox has been prepared as a general scientific, bioinformatics, document-processing, and agent runtime environment.

This document lists only components that were confirmed as available by `0_check.sh`. If an item is not listed here, do not assume it is installed.

## Provisioning Scripts

Run these scripts in order when building or refreshing the sandbox:

- `0_check.sh`: check installed CLI tools, Python/R packages, LaTeX files, fonts, and mirror configuration. Bioinformatics CLI checks start from `~/miniforge3/envs/bioinfo/bin`. This script does not install anything.
- `1_install_base_environment.sh`: install Ubuntu base utilities, compilers, Python runtime and headers, `uv`, `rig`, R, fonts, and native development libraries needed on Ubuntu 22.04 arm64.
- `3_configuration.sh`: configure apt, PyPI, npm, CRAN, and Bioconductor mirrors.
- `4_install_python_packages.sh`: install Python scientific, document-processing, AI client, and bioinformatics packages.
- `5_install_r_packages.sh`: install CRAN and Bioconductor packages.
- `6_install_cli_latex.sh`: install Node package managers, document CLI tools, the mamba `bioinfo` CLI environment, and a practical LaTeX environment.
- `7_cleanup_environment.sh`: clean package-manager caches, temporary files, Python bytecode caches, and build logs.

## Environment Overview

- The default shell runtime includes system Python, Node.js, R, build tools, document tools, and common Unix utilities.
- `~/miniforge3` contains a conda/miniforge installation, but conda is not activated by default.
- The existing `bioinfo` environment is managed by mamba under `~/miniforge3/envs/bioinfo`.
- General scripting should use the default system `python3` and `R` unless a task specifically needs tools from the mamba `bioinfo` environment.
- Apt sources are configured to use a mirror.
- `pip` is configured through `/etc/pip.conf`.
- npm is configured to use `https://registry.npmmirror.com`.
- R is configured to use the Tsinghua CRAN mirror and Tsinghua Bioconductor mirror.

To activate the mamba-managed bioinformatics environment:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate bioinfo
```

The bioinformatics command directory is:

```bash
~/miniforge3/envs/bioinfo/bin
```

## Core Runtime Commands

- Shell and Python: `bash`, `python`, `python3`, `pip`, `uv`
- Node.js package tooling: `node`, `npm`, `pnpm`, `yarn`
- R tooling: `R`, `Rscript`, `rig`
- Conda-compatible package manager: `mamba` at `~/miniforge3/bin/mamba`

## Build And System Commands

- Privilege and build tools: `sudo`, `gcc`, `g++`, `gfortran`, `make`, `cmake`
- Autotools and native build helpers: `autoconf`, `automake`, `pkg-config`
- Network and source control: `curl`, `wget`, `git`
- General utilities: `jq`, `gpg`, `lsb_release`, `locale`, `unzip`, `zip`, `xz`, `file`, `rg`

## Document And LaTeX Commands

- Document conversion and PDF tools: `pandoc`, `gs`
- Font and TeX utilities: `fc-match`, `kpsewhich`
- LaTeX build tools and engines: `latexmk`, `xelatex`, `pdflatex`

## Available Bioinformatics CLI Tools

These tools are installed in the mamba-managed `bioinfo` environment at `~/miniforge3/envs/bioinfo`.

- QC and trimming: `fastqc`, `fastp`, `trimmomatic`, `multiqc`, `cutadapt`
- Alignment and quantification: `bwa-mem2`, `STAR`, `hisat2`, `bowtie2`, `minimap2`, `salmon`, `kallisto`
- BAM and interval operations: `samtools`, `picard`, `bedtools`, `bamCoverage`, `sambamba`, `featureCounts`
- Variant calling and annotation: `gatk`, `bcftools`, `freebayes`, `snpEff`, `vcftools`
- Single-cell RNA-seq: `alevin-fry`
- Multi-omics and epigenomics: `macs3`
- Genome assembly: `spades.py`, `flye`, `hifiasm`
- Phylogeny: `mafft`, `muscle`, `iqtree`, `raxml-ng`, `FastTree`, `mb`
- Data access and workflow utilities: `fasterq-dump`, `esearch`, `seqkit`, `csvtk`, `parallel`, `snakemake`

The corresponding mamba packages confirmed in the `bioinfo` environment include:

- `fastqc`, `fastp`, `trimmomatic`, `multiqc`, `cutadapt`
- `bwa-mem2`, `star`, `hisat2`, `bowtie2`, `minimap2`, `salmon`, `kallisto`
- `samtools`, `picard`, `bedtools`, `deeptools`, `sambamba`, `subread`
- `gatk4`, `bcftools`, `freebayes`, `snpeff`, `vcftools`
- `alevin-fry`, `macs3`
- `spades`, `flye`, `hifiasm`
- `mafft`, `muscle`, `iqtree`, `raxml-ng`, `fasttree`, `mrbayes`
- `sra-tools`, `entrez-direct`, `seqkit`, `csvtk`, `parallel`, `snakemake`

## Available Python Imports

Use `python3` as the default Python interpreter. The following imports were confirmed:

- Core and configuration: `requests`, `yaml`
- Data and analytics: `duckdb`, `pyarrow`, `polars`, `openpyxl`, `pandas`, `numpy`, `scipy`, `sklearn`, `statsmodels`
- Visualization: `matplotlib`, `seaborn`, `plotly`, `altair`, `bokeh`
- Images, PDFs, documents, and file formats: `PIL`, `fitz`, `pptx`, `svglib`, `reportlab`, `cairosvg`, `mammoth`, `markdownify`, `bs4`, `ebooklib`, `nbconvert`, `pyreadstat`, `tabula`
- Web and API clients: `curl_cffi`, `google.genai`, `openai`
- Bioinformatics and life science: `Bio`, `pysam`, `pyfaidx`, `pybedtools`, `gseapy`, `mygene`, `bioservices`, `goatools`, `gprofiler`, `anndata`, `scanpy`, `skbio`, `lifelines`, `bioframe`, `pyBigWig`

## Available R Packages

CRAN and general-purpose packages:

- Data manipulation and I/O: `tidyverse`, `data.table`, `dtplyr`, `readxl`, `writexl`, `openxlsx`, `DBI`, `RSQLite`, `janitor`, `skimr`, `broom`
- Visualization: `ggplot2`, `ggpubr`, `ggrepel`, `patchwork`, `cowplot`, `plotly`, `htmlwidgets`, `DT`, `pheatmap`, `VennDiagram`, `UpSetR`, `igraph`, `vegan`
- Statistics and modeling: `survival`, `survminer`, `lme4`, `glmnet`
- Reporting and development: `knitr`, `rmarkdown`, `kableExtra`, `Rcpp`, `Matrix`, `devtools`, `remotes`
- Optional single-cell packages present in this sandbox: `Seurat`, `SeuratObject`

Bioconductor packages:

- Package management and core data structures: `BiocManager`, `BiocGenerics`, `Biostrings`, `GenomicRanges`, `IRanges`, `S4Vectors`, `GenomicAlignments`, `SummarizedExperiment`, `SingleCellExperiment`, `MultiAssayExperiment`
- Infrastructure: `AnnotationDbi`, `AnnotationHub`, `BiocFileCache`, `BiocParallel`, `DelayedArray`, `MatrixGenerics`
- Annotation resources: `org.Hs.eg.db`, `org.Mm.eg.db`, `TxDb.Hsapiens.UCSC.hg38.knownGene`, `BSgenome.Hsapiens.UCSC.hg38`, `biomaRt`
- Sequencing and genomics: `rtracklayer`, `VariantAnnotation`, `Rsamtools`
- RNA-seq and differential expression: `DESeq2`, `edgeR`, `limma`, `tximport`
- Single-cell analysis: `scran`, `scater`, `scuttle`, `SCnorm`, `muscat`
- Enrichment and pathways: `clusterProfiler`, `enrichplot`, `fgsea`, `GSEABase`
- Epigenomics and multi-omics: `minfi`, `ChIPseeker`, `MotifDb`, `mixOmics`, `MOFA2`
- Visualization and data access: `ComplexHeatmap`, `Gviz`, `karyoploteR`, `EnhancedVolcano`, `GEOquery`

## Available LaTeX Files And Fonts

The sandbox provides a practical LaTeX setup suitable for common scientific writing and Chinese documents.

- LaTeX classes and packages: `article.cls`, `ctex.sty`, `amsmath.sty`, `graphicx.sty`, `booktabs.sty`, `hyperref.sty`, `siunitx.sty`
- Font: `Noto Serif CJK SC`

Use `xelatex` or `latexmk -xelatex` for Chinese documents.
