---
name: image-generation
description: Use this skill when the user requests to generate, create, or visualize images. Specializes in academic figures, scientific illustrations, diagrams, and research visualizations. Also supports general image generation.
---

# Image Generation Skill

## Overview

This skill generates high-quality images using DMXAPI's gpt-image-2 model. It reads a plain-text prompt file and calls the API to produce images. Particularly suited for academic and scientific illustrations.

## Core Capabilities

- Generate academic figures: flowcharts, architecture diagrams, conceptual illustrations
- Create scientific visualizations: experiment setups, data pipeline diagrams, model architectures
- Support general image generation (characters, scenes, products, etc.)
- Configurable resolution, quality, and batch generation

## Workflow

### Step 1: Understand Requirements

When a user requests image generation, identify:

- Subject/content: What should be in the image
- Style: Academic illustration, schematic, photorealistic, etc.
- Resolution needs: square (1024x1024), landscape (1536x1024), or portrait (1024x1536)
- Quality level: high, medium, or low

### Step 2: Create Prompt File

Write a descriptive English prompt to a plain text file in `/mnt/user-data/workspace/` with naming pattern: `{descriptive-name}.txt`

The prompt should be a single, detailed natural language description. gpt-image-2 supports up to 32,000 characters — be as specific and semantic as possible.

**Prompt writing guidelines:**

- Use clear, descriptive English regardless of user's language
- Describe the visual layout, style, colors, and composition explicitly
- For academic figures, specify: diagram type, labels, arrows, color coding, legend
- Mention "clean white background", "vector style", "no text artifacts" when appropriate
- Include style references like "Nature/Science journal figure style" for academic work

### Step 3: Execute Generation

Call the Python script:
```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/prompt.txt \
  --output-file /mnt/user-data/outputs/generated-image.png \
  --size auto \
  --quality high
```

Parameters:

- `--prompt-file`: Path to the prompt text file (required)
- `--output-file`: Path to output image file (required)
- `--size`: Resolution — `auto` (default), `1024x1024`, `1536x1024` (landscape), `1024x1536` (portrait)
- `--quality`: Quality level — `auto` (default), `high`, `medium`, `low`
- `--n`: Number of images to generate, 1-10 (optional, default: 1)

[!NOTE]
Do NOT read the python file, just call it with the parameters.

## Academic Figure Examples

### Example 1: Neural Network Architecture Diagram

User request: "画一个 Transformer 模型的架构图"

Create prompt file: `/mnt/user-data/workspace/transformer-arch.txt`
```
A clean, professional academic illustration of the Transformer model architecture, suitable for a machine learning research paper. The diagram shows two main stacks side by side: the Encoder (left, light blue blocks) and the Decoder (right, light orange blocks). Each encoder layer contains a Multi-Head Self-Attention sublayer and a Feed-Forward Network sublayer, with residual connections (curved arrows) and Layer Normalization after each. The decoder additionally includes a Masked Multi-Head Attention sublayer and an Encoder-Decoder Attention sublayer. At the bottom, Input Embedding and Positional Encoding feed into the encoder; Output Embedding and Positional Encoding feed into the decoder. At the top of the decoder, a Linear layer followed by Softmax produces output probabilities. All components are labeled with clean sans-serif text. Arrows indicate data flow direction. The style is minimal, vector-like, with a white background, consistent color coding, and thin black outlines — resembling figures in Nature or Science journals.
```

Execute:
```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/transformer-arch.txt \
  --output-file /mnt/user-data/outputs/transformer-arch.png \
  --size 1024x1536 \
  --quality high
```

### Example 2: Experiment Pipeline Flowchart

User request: "生成一个数据处理流水线的示意图"

Create prompt file: `/mnt/user-data/workspace/data-pipeline.txt`
```
A professional academic flowchart illustrating a machine learning data processing pipeline, suitable for a computer science research paper. The flow goes left to right with five main stages connected by arrows: (1) Raw Data Collection — icon of a database cylinder in gray, (2) Data Preprocessing — icon of a filter funnel in light blue, with sub-steps "cleaning", "normalization", "augmentation" listed below, (3) Feature Extraction — icon of a magnifying glass in green, (4) Model Training — icon of a neural network graph in orange, with a feedback loop arrow labeled "hyperparameter tuning", (5) Evaluation — icon of a bar chart in purple, with metrics "Accuracy", "F1-Score", "AUC" listed below. Each stage is enclosed in a rounded rectangle with a subtle drop shadow. A dashed arrow from Evaluation loops back to Preprocessing labeled "iterative refinement". Clean white background, consistent pastel color palette, sans-serif labels, vector illustration style.
```

Execute:
```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/data-pipeline.txt \
  --output-file /mnt/user-data/outputs/data-pipeline.png \
  --size 1536x1024 \
  --quality high
```

### Example 3: Biological Mechanism Illustration

User request: "画一个 CRISPR-Cas9 基因编辑的原理示意图"

Create prompt file: `/mnt/user-data/workspace/crispr-mechanism.txt`
```
A detailed scientific illustration of the CRISPR-Cas9 gene editing mechanism, suitable for a molecular biology journal figure. The illustration shows a double-stranded DNA helix (blue and purple strands) being cut by the Cas9 protein (depicted as a large, semi-transparent orange molecular shape with a cleft). A guide RNA strand (red) is shown base-pairing with the target DNA sequence, directing Cas9 to the cut site. The PAM sequence (NGG) is highlighted in yellow on the non-target strand. Two cut marks indicate where Cas9's RuvC and HNH nuclease domains cleave each strand (shown as small scissors icons or lightning bolt symbols). Below the main illustration, three repair pathway outcomes are shown branching out: (a) NHEJ — non-homologous end joining leading to insertions/deletions (gene knockout), (b) HDR — homology-directed repair with a donor template leading to precise gene insertion. Labels use clean sans-serif font. Color coding is consistent: DNA in blue/purple, RNA in red, Cas9 in orange, PAM in yellow. White background, Nature journal figure style, vector-like rendering with subtle shading for depth.
```

Execute:
```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/crispr-mechanism.txt \
  --output-file /mnt/user-data/outputs/crispr-cas9.png \
  --size 1024x1024 \
  --quality high
```

## Common Scenarios

### Academic & Scientific
- Model architecture diagrams (neural networks, system designs)
- Experiment pipeline flowcharts
- Biological/chemical mechanism illustrations
- Conceptual framework diagrams
- Comparison charts and taxonomy trees
- Research methodology overviews

### General Purpose
- Character design and portraits
- Scene and environment generation
- Product visualization
- Creative illustrations

## Specific Templates

Read the following template file only when matching the user request.

- [Doraemon Comic](templates/doraemon.md)
- [Academic Figure](templates/academic-figure.md)

## Output Handling

After generation:

- Images are saved to the specified output path (default: `/mnt/user-data/outputs/`)
- Share generated images with user using present_files tool
- Provide brief description of the generation result
- Offer to iterate if adjustments needed

## Notes

- Always write prompts in English regardless of user's language
- Be as descriptive and specific as possible — the model handles up to 32,000 characters
- For academic figures, explicitly describe layout, labels, color coding, and style
- Specify "white background", "vector style", "clean labels" for publication-quality figures
- Use `--size 1536x1024` for landscape diagrams, `1024x1536` for portrait/vertical flows
- Use `--quality high` for publication figures, `medium` for drafts
