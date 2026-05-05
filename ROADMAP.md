# Stylization Roadmap

This roadmap summarizes improvements inspired by technical analyses of Return of the Obra Dinn. The main direction is to move from plain dithering to a layered pipeline with edge detection, dithering, and postprocessing.

## Rendering Notes

### Creator Perspective

- The visual target was inspired by the 512x342 1-bit display of the 1987 Macintosh Plus.
- Readability matters more than texture density. The two central tools are geometry outlines and restrained dithering.
- Low-resolution output stretched to full screen makes pixels large enough that the eye no longer blends dither patterns back into gray tones.
- The final approach aligned the 3D camera with the 2D dither pattern to reduce shimmer, and raised the internal resolution from 640x360 to 800x450.

### Technical Breakdown

The Obra Dinn style can be separated into three techniques:

1. Dithering: a blue-noise variant that holds up better than Bayer under screen scaling and video compression.
2. Temporal consistency: mapping dither patterns onto spherical coordinates, which is not required for static image processing.
3. Edge postprocessing: crisp line work that preserves readability.

### Implementation Notes

- Render smooth lighting first, then use a postprocess noise texture for thresholding.
- Use blue noise for broad environment regions and Bayer patterns for characters or important objects to create visual layering.
- Overlay edges after dithering so silhouettes and object boundaries stay readable.
- Floyd-Steinberg is non-local and harder to parallelize in shaders. Ordered dithering is easier to run efficiently.

### Project Implications

```text
source image -> grayscale -> edge detection -> edge overlay -> selective dithering -> 1-bit output
```

1. Edge overlays are important for readable 1-bit output.
2. Dithering should be restrained in high-contrast regions and stronger in low-contrast regions.
3. Dual-region dithering can create hierarchy by using Bayer in foreground areas and blue noise in background areas.

## Improvement Areas

### 1. Edge Overlay

Purpose: preserve object silhouettes and improve readability.

Implementation:

- Generate an edge mask with Sobel or Canny.
- Overlay edges as pure black on top of the dithered result.
- Use `--edge-width N` to control line thickness through morphological dilation.
- Use `--edge-strength` to control edge sensitivity.

Blend strategies:

- Dither first, then overlay edges for consistently sharp lines.
- Keep edge pixels black and dither only the remaining regions.

### 2. Dual-Region Dithering

Purpose: use different dithering algorithms for foreground and background regions.

Implementation:

- Segment foreground and background by brightness threshold or edge density.
- Use Bayer for foreground regions and blue noise for background regions.
- Expose a `--dual-dither` option with separate foreground and background algorithms.

### 3. Contrast and Brightness Preprocessing

Purpose: improve source image separation before dithering.

Implementation:

- Use `--contrast FACTOR` to scale contrast.
- Use `--brightness OFFSET` to shift brightness.
- Apply the adjustment after grayscale conversion and before dithering.

### 4. Foreground Color

Purpose: support arbitrary two-color output together with the existing background color control.

Implementation:

- Use `--fg-color HEX` to replace black pixels.
- Combine `--fg-color` and `--bg-color` for custom palettes.

### 5. Pipeline Mode

Purpose: run a complete stylization workflow with one command or preset.

Implementation:

- Add a `--stylize` option that enables a recommended edge and dither configuration.
- Add pipeline configuration for advanced users who want to combine steps manually.

## References

- Lucas Pope creator notes, PlayStation Blog: https://blog.playstation.com/archive/2019/10/17/lucas-pope-on-return-of-the-obra-dinns-art-style/
- Lucas Pope development log, TIGSource: https://dukope.com/devlogs/obra-dinn/tig-32/
- Shader Showcase: Obra Dinn, Alan Zucconi: https://www.alanzucconi.com/2018/10/24/shader-showcase-saturday-11/
- Ultra Effects: Obra Dithering, Daniel Ilett: https://danielilett.com/2020-02-26-tut3-9-obra-dithering/
- Ditherpunk: https://surma.dev/things/ditherpunk/
- Bilibili video on dither types and implementation by Nobody_AVIS: https://www.bilibili.com/video/BV1mbHpz7ERz/
