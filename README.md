# 1-bit Image Rerendering

1-bit Image Rerendering is a Gradio app for interactive monochrome image stylization. The app UI is named ReShader, and it supports image upload, dithering algorithm selection, dot spacing, contrast and brightness controls, edge overlays, two-color output, dual-region dithering, output resizing, and file export.

## Installation

```bash
conda activate reshader
pip install -r requirements.txt
```

Recommended environment: Python 3.11.

## Run

```bash
python app.py
```

By default, the app listens on `0.0.0.0:7860`. Open it locally at:

```text
http://localhost:7860
```

## Features

| Feature | Description |
| --- | --- |
| Dithering algorithms | Floyd-Steinberg, Atkinson, Jarvis, Stucki, Burkes, Sierra, Bayer, Blue Noise, Halftone, Threshold |
| Dot spacing | Downsamples before dithering and upscales with nearest-neighbor sampling for larger pixel blocks |
| Preprocessing | Adjusts grayscale contrast and brightness before dithering |
| Edge overlay | Uses Canny or Sobel detection and burns edges into the result as black lines |
| Color output | Replaces foreground and background pixels with custom colors |
| Dual-region dithering | Splits foreground and background by brightness or edge density, then applies separate algorithms |
| Style presets | Includes high-contrast manga, ditherpunk, copier zine, e-ink, and halftone presets |
| Color presets | Provides muted foreground and background color pairs that can be combined with any style preset |
| Output size | Exports to a target width and height with center cropping when aspect ratios differ |
| Language switch | Switches the UI between English and Chinese while keeping stable internal preset values |
| Export | Supports png, jpg, bmp, and tiff |

## Project Layout

```text
app.py              Gradio application entry point
dither/             Dithering algorithm registry and implementations
postprocess/        Preprocessing, edge handling, coloring, segmentation, and dual-region composition
test/               Manual validation images
```

## Dependencies

| Package | Purpose |
| --- | --- |
| Pillow | Image loading, conversion, resizing, and export |
| numpy | Array operations |
| scikit-image | Edge detection and morphology |
| gradio | Web UI |
