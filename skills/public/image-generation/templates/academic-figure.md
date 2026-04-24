# Academic Figure Template

## When to Use

Use this template when the user requests:
- Research paper figures, journal illustrations
- Model architecture diagrams, system design figures
- Experiment flowcharts, methodology overviews
- Scientific mechanism illustrations
- Comparison diagrams, taxonomy trees

## Prompt Construction Guide

Academic figures need highly structured prompts. Follow this pattern:

### 1. Opening — State the figure type and purpose
```
A clean, professional academic illustration of [SUBJECT], suitable for a [FIELD] research paper published in [TARGET JOURNAL STYLE, e.g. Nature/Science/IEEE].
```

### 2. Layout — Describe spatial arrangement
```
The diagram is organized as [layout type]:
- Left-to-right flow / Top-to-bottom flow / Radial layout / Grid layout
- [N] main components arranged [how]
- Connected by [arrows/lines/dashed lines] indicating [what]
```

### 3. Components — Detail each element
```
Component 1: [Name] — [shape] in [color], containing [sub-elements], labeled "[text]"
Component 2: [Name] — [shape] in [color], ...
...
```

### 4. Visual Style — Enforce academic aesthetics
```
Style requirements:
- Clean white background
- Vector-like rendering with minimal shading
- Consistent [pastel/muted] color palette
- Sans-serif labels (resembling Helvetica or Arial)
- Thin black outlines on all shapes
- Subtle drop shadows for depth (optional)
- No decorative elements or gradients
- Resembling figures in [Nature/Science/IEEE/Cell] journals
```

### 5. Color Coding — Define a consistent palette
```
Color coding:
- [Category A]: light blue (#A8D8EA)
- [Category B]: light orange (#FFD3B6)
- [Category C]: light green (#A8E6CF)
- [Category D]: light purple (#D4A5FF)
- Arrows/connections: dark gray (#333333)
- Labels: black (#000000)
```

## Example Prompts

### System Architecture (CS/AI)
```
A clean, professional academic illustration of a Retrieval-Augmented Generation (RAG) system architecture, suitable for an AI research paper. The diagram flows left to right with three main stages: (1) Document Ingestion on the left — a stack of document icons feeds into a chunking module (light blue rounded rectangle), then into an embedding model (light green rounded rectangle), which stores vectors in a Vector Database (cylinder icon in light purple). (2) Query Processing in the center — a user query enters an embedding model (same light green), performs similarity search against the vector database (dashed arrow), and retrieves top-k relevant chunks. (3) Answer Generation on the right — retrieved chunks and the original query feed into a large language model (light orange rounded rectangle), which produces the final answer. All components are labeled with clean sans-serif text. Arrows are dark gray with directional heads. White background, vector style, consistent pastel color palette, Nature journal figure aesthetic.
```

Size: `1536x1024` (landscape)

### Biological Pathway
```
A detailed scientific illustration of the mTOR signaling pathway, suitable for a Cell or Nature Reviews journal figure. The diagram shows a cell membrane at the top with receptor tyrosine kinases (RTKs) embedded in it. Growth factor ligands bind to RTKs, activating PI3K (light blue circle) which converts PIP2 to PIP3. PIP3 recruits AKT (light green circle) to the membrane, where it is phosphorylated. Activated AKT inhibits TSC1/TSC2 complex (red X mark), releasing Rheb-GTP which activates mTORC1 (large orange oval). mTORC1 has two main downstream branches: (a) phosphorylation of S6K1 leading to protein synthesis (rightward arrow to ribosome icon), (b) phosphorylation of 4E-BP1 releasing eIF4E for cap-dependent translation. A negative feedback loop from S6K1 back to IRS1 is shown as a dashed red inhibitory arrow. AMPK (purple circle) is shown as a separate input that activates TSC1/TSC2 under energy stress. All proteins are labeled, activating arrows are green, inhibitory arrows are red with flat heads. White background, consistent color coding, clean vector style.
```

Size: `1024x1536` (portrait)

### Experiment Methodology
```
A professional academic flowchart showing a machine learning experiment methodology, suitable for an IEEE conference paper. The flow goes top to bottom with four phases separated by horizontal dashed lines labeled Phase 1-4. Phase 1 "Data Collection": three data source icons (clinical records in blue, imaging data in green, genomic data in purple) converge into a central "Data Integration" box. Phase 2 "Preprocessing": sequential boxes for "Missing Value Imputation", "Feature Normalization", "Train/Val/Test Split (70/15/15)". Phase 3 "Model Development": three parallel branches for "Random Forest", "XGBoost", "Deep Neural Network", each with a small icon, converging into an "Ensemble" box. Phase 4 "Evaluation": a box containing "5-Fold Cross Validation" with output arrows to metric boxes: "AUC-ROC", "Sensitivity", "Specificity", "F1-Score". A side panel shows "Statistical Analysis: DeLong test, McNemar test". Clean white background, rounded rectangles with subtle shadows, consistent pastel colors per phase, sans-serif labels, vector illustration style.
```

Size: `1024x1536` (portrait)

## Recommended Settings

| Figure Type | Size | Quality |
|-------------|------|---------|
| Architecture diagram (wide) | `1536x1024` | `high` |
| Vertical flowchart | `1024x1536` | `high` |
| Square mechanism diagram | `1024x1024` | `high` |
| Draft / iteration | any | `medium` |

## Aspect Ratio

Use `auto` unless the layout clearly demands landscape or portrait.
