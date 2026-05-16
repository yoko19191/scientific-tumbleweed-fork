# Environments

You work with an Ubuntu 22.04 sandbox.

The system environment already includes common build tools and runtimes:

- Build tools: `build-essential`, `gcc`, `g++`, `gfortran`, `make`, `cmake`, `ninja`, `autoconf`, `automake`, `pkg-config`
- Basic tools: `bash`, `curl`, `wget`, `git`, `jq`, `rg`, `unzip`, `zip`, `xz`, `file`, `rsync`
- Python runtime: `python3`, `pip`, `uv`
- R runtime: `R`, `Rscript`, `rig`
- Node runtime: `node`, `npm`, `pnpm`, `yarn`

Miniforge3 is installed at `~/miniforge3`.
The conda `base` environment is not auto-activated by default.

## Python

You are given the following Python packages in the system Python environment.
Use `python3` unless you specifically need the conda bioinformatics tools.

Data analysis packages include:

- `numpy`, `scipy`, `pandas`, `polars`, `pyarrow`, `duckdb`, `openpyxl`
- `requests`, `PyYAML`, `beautifulsoup4`

Machine learning packages include:

- `scikit-learn`, `statsmodels`, `xgboost`, `lightgbm`, `catboost`
- `imbalanced-learn`, `category-encoders`, `feature-engine`, `mlxtend`
- `optuna`, `scikit-optimize`, `shap`, `lime`, `yellowbrick`
- `sktime`, `tsfresh`, `pmdarima`, `prophet`

Visualization packages include:

- `matplotlib`, `seaborn`, `plotly`, `altair`, `bokeh`
- `plotnine`, `holoviews`, `hvplot`, `panel`, `dash`, `streamlit`
- `networkx`, `pyvis`, `ipywidgets`

Document and file packages include:

- `Pillow`, `PyMuPDF`, `python-pptx`, `reportlab`, `svglib`, `cairosvg`
- `mammoth`, `markdownify`, `ebooklib`, `nbconvert`, `pyreadstat`, `tabula-py`

Bioinformatics packages include:

- `biopython`, `pysam`, `pyfaidx`, `pybedtools`, `pyBigWig`
- `GEOparse`, `gseapy`, `mygene`, `bioservices`, `goatools`, `gprofiler-official`
- `anndata`, `scanpy`, `scikit-bio`, `bioframe`, `lifelines`
- `gffutils`, `HTSeq`, `cyvcf2`, `pyranges`, `pysradb`, `scikit-allel`, `sgkit`, `rdkit`

## R

You are given R with common CRAN and Bioconductor packages.

Data and reporting packages include:

- `tidyverse`, `data.table`, `dplyr`, `readr`, `readxl`, `writexl`, `openxlsx`
- `DBI`, `RSQLite`, `duckdb`, `janitor`, `skimr`, `broom`
- `knitr`, `rmarkdown`, `kableExtra`, `devtools`, `remotes`

Statistics and machine learning packages include:

- `survival`, `survminer`, `lme4`, `glmnet`
- `xgboost`, `lightgbm`, `tidymodels`, `caret`
- `e1071`, `kernlab`, `rpart`, `nnet`
- `DALEX`, `shapviz`, `pROC`, `forecast`, `rstatix`, `performance`

Visualization packages include:

- `ggplot2`, `ggpubr`, `ggrepel`, `patchwork`, `cowplot`, `plotly`
- `DT`, `pheatmap`, `ComplexHeatmap`, `EnhancedVolcano`
- `VennDiagram`, `UpSetR`, `factoextra`, `ggtree`, `ggraph`, `leaflet`

Bioinformatics packages include:

- `BiocManager`, `BiocGenerics`, `Biostrings`, `GenomicRanges`, `IRanges`, `S4Vectors`
- `SummarizedExperiment`, `SingleCellExperiment`, `MultiAssayExperiment`
- `AnnotationDbi`, `AnnotationHub`, `org.Hs.eg.db`, `org.Mm.eg.db`, `biomaRt`
- `rtracklayer`, `VariantAnnotation`, `Rsamtools`
- `DESeq2`, `edgeR`, `limma`, `tximport`
- `Seurat`, `SeuratObject`, `scran`, `scater`, `scuttle`, `SCnorm`, `muscat`
- `clusterProfiler`, `enrichplot`, `fgsea`, `GSEABase`, `GSVA`, `GEOquery`
- `minfi`, `ChIPseeker`, `DiffBind`, `MotifDb`, `mixOmics`, `MOFA2`
- `phyloseq`, `SNPRelate`

## CLI

Bioinformatics CLI tools are installed in the conda environment named `bioinfo`.

Activate it with:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
mamba activate bioinfo
```

The environment path is:

```bash
~/miniforge3/envs/bioinfo
```

Available workflow and utility tools include:

- `snakemake`, `nextflow`, `nf-core`, `parallel`
- `sra-tools`, `entrez-direct`, `seqkit`, `csvtk`

Available NGS tools include:

- QC and trimming: `fastqc`, `fastp`, `trimmomatic`, `multiqc`, `cutadapt`, `seqtk`
- Alignment and quantification: `bwa-mem2`, `STAR`, `hisat2`, `bowtie2`, `minimap2`, `salmon`, `kallisto`
- BAM and intervals: `samtools`, `picard`, `bedtools`, `deeptools`, `sambamba`, `subread`, `htslib`
- Variant tools: `gatk4`, `bcftools`, `freebayes`, `snpeff`, `vcftools`

Available domain tools include:

- Single-cell: `alevin-fry`, `starsolo`, `bustools`
- Epigenomics: `macs3`, `chromvar`
- Assembly: `spades`, `flye`, `hifiasm`, `quast`
- Phylogeny: `mafft`, `muscle`, `iqtree`, `raxml-ng`, `fasttree`, `mrbayes`
- Metagenomics: `kraken2`, `bracken`, `metaphlan`, `humann`, `kaiju`, `mash`, `fastani`
- GWAS and population genetics: `plink2`, `eigensoft`, `admixture`, `king`
- Genome annotation: `prokka`, `bakta`, `eggnog-mapper`

## Documents And PDFs

The sandbox also includes document tools:

- `pandoc`, `libreoffice`, `wkhtmltopdf`
- `pdftotext`, `qpdf`, `ghostscript`, `mupdf-tools`
- `xelatex`, `lualatex`, `latexmk`, `biber`
- `imagemagick`, `graphicsmagick`, `inkscape`, `rsvg-convert`
- `graphviz`, `plantuml`, `tesseract`, `ocrmypdf`

Use `xelatex` or `latexmk -xelatex` for Chinese PDF documents.

## Configuration

The sandbox uses mirror configuration for faster package installation:

- apt mirror: Tsinghua Ubuntu mirror
- PyPI mirror: Tsinghua PyPI mirror
- npm registry: `https://registry.npmmirror.com`
- CRAN mirror: Tsinghua CRAN mirror
- Bioconductor mirror: Tsinghua Bioconductor mirror
