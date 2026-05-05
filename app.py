#!/usr/bin/env python3
"""Gradio UI for interactive 1-bit image rerendering."""

from __future__ import annotations

import gradio as gr
import numpy as np
from PIL import Image

from dither import get_algorithm, list_algorithms
from postprocess import (
    adjust_contrast_brightness, apply_colors, apply_dual_dither,
    detect_edges, overlay_edges, segment_by_brightness, segment_by_edges,
)

# Keep last render result for download in different formats
_last_result: Image.Image | None = None

CSS = """
:root {
    --app-title-height: 52px;
}

html, body {
    height: 100%;
    overflow: hidden;
}

/* Title: fixed at top, never moves */
#title {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--background-fill-primary);
    padding: 8px 16px !important;
    margin: 0 !important;
}

/* Desktop layout: image columns stay still; parameter column scrolls. */
.gradio-container {
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
}

#main-row {
    display: flex !important;
    flex-wrap: nowrap !important;
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
    padding-top: var(--app-title-height) !important;
    margin-top: 0 !important;
    align-items: flex-start !important;
}

#col-left, #col-middle, #col-right {
    height: calc(100vh - var(--app-title-height)) !important;
    max-height: calc(100vh - var(--app-title-height)) !important;
    align-self: flex-start !important;
    box-sizing: border-box;
    min-height: 0 !important;
    min-width: 0 !important;
}

#col-left, #col-middle {
    overflow: hidden !important;
}

#col-right {
    display: block !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    overscroll-behavior: contain;
    touch-action: pan-y;
    padding-right: 10px;
    padding-bottom: 16px;
    scrollbar-width: none;
    -ms-overflow-style: none;
}

#col-right::-webkit-scrollbar {
    display: none;
    width: 0;
    height: 0;
}

#col-right > * {
    flex: none !important;
    flex-shrink: 0 !important;
}

#col-right > * + * {
    margin-top: 14px !important;
}

#col-right * {
    box-sizing: border-box;
    max-width: 100%;
}

@media (max-width: 899px) {
    body {
        overflow: auto;
    }

    .gradio-container {
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
    }

    #main-row {
        display: flex !important;
        flex-wrap: wrap !important;
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
    }

    #col-left, #col-middle, #col-right {
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
    }
}

/* Full-screen overlay for the rendered image */
.fullscreen-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.92);
    z-index: 9999;
    cursor: zoom-out;
    justify-content: center;
    align-items: center;
}
.fullscreen-overlay.active { display: flex; }
.fullscreen-overlay img {
    max-width: 95vw;
    max-height: 95vh;
    object-fit: contain;
}
#fullscreen-btn {
    min-width: auto !important;
    padding: 6px 12px !important;
}
"""

# Inject JS on load: sync layout dimensions with the rendered title height
# and set up the fullscreen overlay.
JS_INIT = """
() => {
    // Sync fixed app layout with actual title height.
    const title = document.getElementById('title');
    const row = document.getElementById('main-row');
    if (title && row) {
        const h = title.offsetHeight;
        const mainHeight = `calc(100vh - ${h}px)`;
        document.documentElement.style.setProperty('--app-title-height', h + 'px');
        row.style.display = 'flex';
        row.style.flexWrap = 'nowrap';
        row.style.overflow = 'hidden';
        row.style.paddingTop = h + 'px';
        row.style.marginTop = '0';
        row.style.height = '100vh';
        row.style.maxHeight = '100vh';
        for (const id of ['col-left', 'col-middle', 'col-right']) {
            const col = document.getElementById(id);
            if (col) {
                col.style.height = mainHeight;
                col.style.maxHeight = mainHeight;
                col.style.minWidth = '0';
                col.style.minHeight = '0';
            }
        }
        const left = document.getElementById('col-left');
        const middle = document.getElementById('col-middle');
        const right = document.getElementById('col-right');
        if (left) left.style.overflow = 'hidden';
        if (middle) middle.style.overflow = 'hidden';
        if (right) {
            right.style.display = 'block';
            right.style.overflowX = 'hidden';
            right.style.overflowY = 'auto';
            right.style.overscrollBehavior = 'contain';
            right.style.touchAction = 'pan-y';
        }
    }

    // Set up fullscreen overlay
    if (!document.getElementById('fs-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'fs-overlay';
        overlay.className = 'fullscreen-overlay';
        overlay.innerHTML = '<img id="fs-img" src="" />';
        overlay.onclick = () => overlay.classList.remove('active');
        document.body.appendChild(overlay);
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') overlay.classList.remove('active');
        });
    }
}
"""

JS_OPEN_FULLSCREEN = """
() => {
    const overlay = document.getElementById('fs-overlay');
    // Find the rendered output image inside the middle column
    const col = document.getElementById('col-middle');
    const img = col && col.querySelector('img');
    if (overlay && img && img.src) {
        document.getElementById('fs-img').src = img.src;
        overlay.classList.add('active');
    }
}
"""

STYLE_PRESET_FIELDS = [
    "algorithm",
    "spacing",
    "contrast",
    "brightness",
    "edge_enabled",
    "edge_method",
    "edge_strength",
    "edge_width",
    "threshold_val",
    "dot_size",
    "dual_enabled",
    "dual_seg_method",
    "dual_seg_threshold",
    "dual_fg_algo",
    "dual_bg_algo",
    "dual_fg_spacing",
    "dual_bg_spacing",
]

COLOR_FIELDS = ["fg_color", "bg_color", "use_fg", "use_bg"]
LANG_EN = "English"
LANG_ZH = "中文"
DEFAULT_STYLE_PRESET = "Basic Atkinson"
DEFAULT_COLOR_PRESET = "Warm Gray Paper"

PRESETS = {
    "Basic Atkinson": {
        "algorithm": "atkinson",
        "spacing": 1,
        "contrast": 1.0,
        "brightness": 0,
        "edge_enabled": False,
        "edge_method": "canny",
        "edge_strength": 1.0,
        "edge_width": 1,
        "fg_color": "#000000",
        "bg_color": "#F5E6D0",
        "use_fg": False,
        "use_bg": False,
        "threshold_val": 128,
        "dot_size": 8,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
    "Horror Manga High Contrast": {
        "algorithm": "threshold",
        "spacing": 2,
        "contrast": 1.85,
        "brightness": -10,
        "edge_enabled": True,
        "edge_method": "sobel",
        "edge_strength": 1.65,
        "edge_width": 1,
        "fg_color": "#080706",
        "bg_color": "#F0E6D2",
        "use_fg": True,
        "use_bg": True,
        "threshold_val": 116,
        "dot_size": 8,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
    "Cabin Investigation Ditherpunk": {
        "algorithm": "atkinson",
        "spacing": 1,
        "contrast": 1.3,
        "brightness": -2,
        "edge_enabled": True,
        "edge_method": "canny",
        "edge_strength": 1.4,
        "edge_width": 1,
        "fg_color": "#14110E",
        "bg_color": "#D8C7A3",
        "use_fg": True,
        "use_bg": True,
        "threshold_val": 128,
        "dot_size": 8,
        "dual_enabled": True,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 134,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 2,
    },
    "Copier Zine": {
        "algorithm": "bayer2x2",
        "spacing": 3,
        "contrast": 1.9,
        "brightness": 12,
        "edge_enabled": True,
        "edge_method": "sobel",
        "edge_strength": 1.4,
        "edge_width": 2,
        "fg_color": "#111111",
        "bg_color": "#F4EAD8",
        "use_fg": True,
        "use_bg": True,
        "threshold_val": 120,
        "dot_size": 8,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
    "Soft E-Ink Grain": {
        "algorithm": "bluenoise",
        "spacing": 1,
        "contrast": 1.08,
        "brightness": 6,
        "edge_enabled": False,
        "edge_method": "canny",
        "edge_strength": 1.0,
        "edge_width": 1,
        "fg_color": "#202020",
        "bg_color": "#F7F7F2",
        "use_fg": True,
        "use_bg": True,
        "threshold_val": 128,
        "dot_size": 8,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
    "Midnight Newspaper Halftone": {
        "algorithm": "halftone",
        "spacing": 1,
        "contrast": 1.45,
        "brightness": -4,
        "edge_enabled": True,
        "edge_method": "canny",
        "edge_strength": 1.15,
        "edge_width": 1,
        "fg_color": "#1A1715",
        "bg_color": "#E9DDC4",
        "use_fg": True,
        "use_bg": True,
        "threshold_val": 128,
        "dot_size": 7,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
    "Minimal Silhouette": {
        "algorithm": "threshold",
        "spacing": 4,
        "contrast": 2.15,
        "brightness": -18,
        "edge_enabled": False,
        "edge_method": "sobel",
        "edge_strength": 1.0,
        "edge_width": 1,
        "fg_color": "#000000",
        "bg_color": "#FFFFFF",
        "use_fg": False,
        "use_bg": False,
        "threshold_val": 110,
        "dot_size": 8,
        "dual_enabled": False,
        "dual_seg_method": "brightness",
        "dual_seg_threshold": 128,
        "dual_fg_algo": "bayer4x4",
        "dual_bg_algo": "bluenoise",
        "dual_fg_spacing": 1,
        "dual_bg_spacing": 1,
    },
}

COLOR_PRESETS = {
    "Default Black and White": ("#000000", "#FFFFFF", False, False),
    "Warm Gray Paper": ("#2F2A27", "#E8DED1", True, True),
    "Mist Blue Limewash": ("#2D3A3F", "#D7D8D2", True, True),
    "Sage Paper": ("#3B4038", "#D9D7C7", True, True),
    "Terracotta Dust": ("#4A3632", "#DDD0C6", True, True),
    "Deep Green Ivory": ("#26352F", "#E7E0D0", True, True),
    "Charcoal Old Book": ("#221F1D", "#D6C8B5", True, True),
    "Night Blue Matte": ("#252E3A", "#D3D1C7", True, True),
}

STYLE_PRESET_LABELS_ZH = {
    "Basic Atkinson": "基础 Atkinson",
    "Horror Manga High Contrast": "恐怖漫画高反差",
    "Cabin Investigation Ditherpunk": "船舱调查 Ditherpunk",
    "Copier Zine": "复印机 Zine",
    "Soft E-Ink Grain": "电子墨水柔颗粒",
    "Midnight Newspaper Halftone": "午夜报纸网点",
    "Minimal Silhouette": "极简剪影",
}

COLOR_PRESET_LABELS_ZH = {
    "Default Black and White": "默认黑白",
    "Warm Gray Paper": "暖灰纸张",
    "Mist Blue Limewash": "雾蓝石灰",
    "Sage Paper": "鼠尾草纸",
    "Terracotta Dust": "陶土灰粉",
    "Deep Green Ivory": "墨绿米白",
    "Charcoal Old Book": "炭黑旧书",
    "Night Blue Matte": "夜蓝雾面",
}

UI_TEXT = {
    "en": {
        "title": "# 1-bit Image Rerendering",
        "language": "Language",
        "upload_image": "Upload Image",
        "render": "Render",
        "rendered_output": "Rendered Output",
        "fullscreen": "Fullscreen",
        "presets": "Presets",
        "style_preset": "Style Preset",
        "color_preset": "Color Preset",
        "output_size": "Output Size",
        "output_note": "Set to 0 to keep the source image dimension.",
        "output_width": "Output Width (px)",
        "output_height": "Output Height (px)",
        "algorithm": "Dithering Algorithm",
        "spacing": "Dot Spacing",
        "preprocessing": "Preprocessing",
        "contrast": "Contrast",
        "brightness": "Brightness",
        "edge_detection": "Edge Detection",
        "enable_edge": "Enable Edge Overlay",
        "edge_method": "Detection Method",
        "edge_strength": "Sensitivity",
        "edge_width": "Line Width",
        "colors": "Colors",
        "custom_foreground": "Custom Foreground",
        "foreground_color": "Foreground Color",
        "custom_background": "Custom Background",
        "background_color": "Background Color",
        "dual_region": "Dual-Region Dithering",
        "enable_dual": "Enable Dual-Region Dithering",
        "segmentation_method": "Segmentation Method",
        "brightness_threshold": "Brightness Threshold",
        "foreground_algorithm": "Foreground Algorithm",
        "background_algorithm": "Background Algorithm",
        "foreground_spacing": "Foreground Spacing",
        "background_spacing": "Background Spacing",
        "algorithm_params": "Algorithm Parameters",
        "threshold_value": "Threshold Value",
        "halftone_dot_size": "Halftone Dot Size",
        "export": "Export",
        "export_format": "Export Format",
        "export_file": "Export File",
        "download": "Download",
        "seg_brightness": "Brightness",
        "seg_edges": "Edges",
    },
    "zh": {
        "title": "# 1-bit Image Rerendering",
        "language": "语言",
        "upload_image": "上传图片",
        "render": "渲染",
        "rendered_output": "渲染结果",
        "fullscreen": "全屏查看",
        "presets": "预设参数",
        "style_preset": "风格预设",
        "color_preset": "双色预设",
        "output_size": "输出尺寸",
        "output_note": "设为 0 则使用原图对应维度。",
        "output_width": "输出宽度 (px)",
        "output_height": "输出高度 (px)",
        "algorithm": "抖动算法",
        "spacing": "点阵稀疏度",
        "preprocessing": "预处理",
        "contrast": "对比度",
        "brightness": "亮度",
        "edge_detection": "边缘检测",
        "enable_edge": "启用描边",
        "edge_method": "检测方法",
        "edge_strength": "灵敏度",
        "edge_width": "线宽",
        "colors": "颜色",
        "custom_foreground": "自定义前景色",
        "foreground_color": "前景色",
        "custom_background": "自定义背景色",
        "background_color": "背景色",
        "dual_region": "双区域抖动",
        "enable_dual": "启用双区域抖动",
        "segmentation_method": "分割方式",
        "brightness_threshold": "亮度分割阈值",
        "foreground_algorithm": "前景算法",
        "background_algorithm": "背景算法",
        "foreground_spacing": "前景稀疏度",
        "background_spacing": "背景稀疏度",
        "algorithm_params": "算法特定参数",
        "threshold_value": "Threshold 阈值",
        "halftone_dot_size": "Halftone 网点大小",
        "export": "导出",
        "export_format": "导出格式",
        "export_file": "导出文件",
        "download": "下载",
        "seg_brightness": "亮度",
        "seg_edges": "边缘",
    },
}


def _language_key(language: str) -> str:
    return "zh" if language == LANG_ZH else "en"


def _style_preset_key(value: str | None) -> str:
    if value in PRESETS:
        return value
    for key, label in STYLE_PRESET_LABELS_ZH.items():
        if value == label:
            return key
    return DEFAULT_STYLE_PRESET


def _color_preset_key(value: str | None) -> str:
    if value in COLOR_PRESETS:
        return value
    for key, label in COLOR_PRESET_LABELS_ZH.items():
        if value == label:
            return key
    return DEFAULT_COLOR_PRESET


def _style_preset_choices(language: str) -> list[tuple[str, str]]:
    if _language_key(language) == "zh":
        return [(STYLE_PRESET_LABELS_ZH[key], key) for key in PRESETS]
    return [(key, key) for key in PRESETS]


def _color_preset_choices(language: str) -> list[tuple[str, str]]:
    if _language_key(language) == "zh":
        return [(COLOR_PRESET_LABELS_ZH[key], key) for key in COLOR_PRESETS]
    return [(key, key) for key in COLOR_PRESETS]


def _segmentation_choices(language: str) -> list[tuple[str, str]]:
    text = UI_TEXT[_language_key(language)]
    return [
        (text["seg_brightness"], "brightness"),
        (text["seg_edges"], "edges"),
    ]


def _resize_center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize to cover target dimensions, then center crop.

    Uses NEAREST resampling to preserve dither patterns.
    """
    src_w, src_h = img.size
    if (src_w, src_h) == (target_w, target_h):
        return img

    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if abs(src_ratio - target_ratio) < 0.01:
        # Aspect ratio essentially unchanged — direct resize
        return img.resize((target_w, target_h), Image.Resampling.NEAREST)

    # Scale to *cover* the target area (use the larger scale factor)
    if src_ratio > target_ratio:
        # Source is wider relative to target → match height, crop width
        new_h = target_h
        new_w = round(src_w * target_h / src_h)
    else:
        # Source is taller relative to target → match width, crop height
        new_w = target_w
        new_h = round(src_h * target_w / src_w)

    img = img.resize((new_w, new_h), Image.Resampling.NEAREST)

    # Center crop to exact target
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _to_grayscale(image: Image.Image) -> Image.Image:
    if image.mode == "RGBA":
        bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        return bg.convert("L")
    return image.convert("L")


def render(
    input_image: np.ndarray | None,
    algorithm: str,
    spacing: int,
    contrast: float,
    brightness: int,
    edge_enabled: bool,
    edge_method: str,
    edge_strength: float,
    edge_width: int,
    fg_color: str,
    bg_color: str,
    use_fg: bool,
    use_bg: bool,
    threshold_val: int,
    dot_size: int,
    dual_enabled: bool,
    dual_seg_method: str,
    dual_seg_threshold: int,
    dual_fg_algo: str,
    dual_bg_algo: str,
    dual_fg_spacing: int,
    dual_bg_spacing: int,
    output_w: int,
    output_h: int,
) -> Image.Image | None:
    global _last_result

    if input_image is None:
        _last_result = None
        return None

    image = Image.fromarray(input_image)
    gray = _to_grayscale(image)
    original_size = gray.size

    # --- Pre-processing ---
    gray = adjust_contrast_brightness(gray, contrast=contrast, brightness=brightness)

    # --- Edge detection (before spacing downscale, on full-res) ---
    edges = None
    if edge_enabled:
        edges = detect_edges(gray, method=edge_method, strength=edge_strength, width=edge_width)

    # --- Dithering ---
    if dual_enabled:
        # Dual-region: segmentation on full-res, spacing handled per-region
        if dual_seg_method == "brightness":
            fg_mask = segment_by_brightness(gray, threshold=dual_seg_threshold)
        else:
            fg_mask = segment_by_edges(gray)
        fg_algo = get_algorithm(dual_fg_algo)
        bg_algo = get_algorithm(dual_bg_algo)
        result = apply_dual_dither(
            gray, fg_mask, fg_algo, bg_algo,
            fg_spacing=dual_fg_spacing, bg_spacing=dual_bg_spacing,
        )
    else:
        # Single algorithm: global spacing
        work = gray
        if spacing > 1:
            new_w = max(1, original_size[0] // spacing)
            new_h = max(1, original_size[1] // spacing)
            work = work.resize((new_w, new_h), Image.Resampling.LANCZOS)

        kwargs: dict = {}
        if algorithm == "threshold":
            kwargs["threshold"] = threshold_val
        elif algorithm == "halftone":
            kwargs["dot_size"] = dot_size
        algo = get_algorithm(algorithm, **kwargs)
        result = algo.apply(work)

        if spacing > 1:
            result = result.convert("L").resize(original_size, Image.Resampling.NEAREST)

    # --- Overlay edges ---
    if edges is not None:
        result = overlay_edges(result, edges)

    # --- Colorize ---
    fc = fg_color.strip() if use_fg and fg_color.strip() else None
    bc = bg_color.strip() if use_bg and bg_color.strip() else None
    result = apply_colors(result, fg_color=fc, bg_color=bc)

    # Ensure result is RGB PIL Image (avoids Gradio numpy dtype issues)
    if not isinstance(result, Image.Image):
        result = Image.fromarray(np.array(result))
    result = result.convert("RGB")

    # --- Output resize (center crop if aspect ratio changes) ---
    target_w = int(output_w) if output_w and int(output_w) > 0 else original_size[0]
    target_h = int(output_h) if output_h and int(output_h) > 0 else original_size[1]
    if result.size != (target_w, target_h):
        result = _resize_center_crop(result, target_w, target_h)

    _last_result = result
    return result


def download(fmt: str) -> str | None:
    """Save last render result to a temp file in the chosen format."""
    if _last_result is None:
        return None

    ext = fmt.lower()
    path = f"/tmp/1bit_image_rerendering_output.{ext}"
    if ext == "jpg":
        img = _last_result.convert("RGB") if _last_result.mode != "RGB" else _last_result
        img.save(path, quality=95)
    else:
        _last_result.save(path)
    return path


def apply_preset(name: str) -> tuple:
    preset = PRESETS.get(_style_preset_key(name), PRESETS[DEFAULT_STYLE_PRESET])
    return tuple(preset[field] for field in STYLE_PRESET_FIELDS)


def apply_color_preset(name: str) -> tuple[str, str, bool, bool]:
    return COLOR_PRESETS.get(_color_preset_key(name), COLOR_PRESETS[DEFAULT_COLOR_PRESET])


def set_language(
    language: str,
    style_preset: str | None,
    color_preset: str | None,
) -> tuple:
    text = UI_TEXT[_language_key(language)]
    style_key = _style_preset_key(style_preset)
    color_key = _color_preset_key(color_preset)

    return (
        gr.update(label=text["language"]),
        gr.update(value=text["title"]),
        gr.update(label=text["upload_image"]),
        gr.update(value=text["render"]),
        gr.update(label=text["rendered_output"]),
        gr.update(value=text["fullscreen"]),
        gr.update(label=text["presets"]),
        gr.update(
            label=text["style_preset"],
            choices=_style_preset_choices(language),
            value=style_key,
        ),
        gr.update(
            label=text["color_preset"],
            choices=_color_preset_choices(language),
            value=color_key,
        ),
        gr.update(label=text["output_size"]),
        gr.update(value=text["output_note"]),
        gr.update(label=text["output_width"]),
        gr.update(label=text["output_height"]),
        gr.update(label=text["algorithm"]),
        gr.update(label=text["spacing"]),
        gr.update(label=text["preprocessing"]),
        gr.update(label=text["contrast"]),
        gr.update(label=text["brightness"]),
        gr.update(label=text["edge_detection"]),
        gr.update(label=text["enable_edge"]),
        gr.update(label=text["edge_method"]),
        gr.update(label=text["edge_strength"]),
        gr.update(label=text["edge_width"]),
        gr.update(label=text["colors"]),
        gr.update(label=text["custom_foreground"]),
        gr.update(label=text["foreground_color"]),
        gr.update(label=text["custom_background"]),
        gr.update(label=text["background_color"]),
        gr.update(label=text["dual_region"]),
        gr.update(label=text["enable_dual"]),
        gr.update(label=text["segmentation_method"], choices=_segmentation_choices(language)),
        gr.update(label=text["brightness_threshold"]),
        gr.update(label=text["foreground_algorithm"]),
        gr.update(label=text["background_algorithm"]),
        gr.update(label=text["foreground_spacing"]),
        gr.update(label=text["background_spacing"]),
        gr.update(label=text["algorithm_params"]),
        gr.update(label=text["threshold_value"]),
        gr.update(label=text["halftone_dot_size"]),
        gr.update(label=text["export"]),
        gr.update(label=text["export_format"]),
        gr.update(value=text["export_file"]),
        gr.update(label=text["download"]),
    )


def build_ui() -> gr.Blocks:
    algo_names = list(list_algorithms().keys())
    text = UI_TEXT["en"]

    with gr.Blocks(title="1-bit Image Rerendering", fill_width=True) as app:
        title = gr.Markdown(text["title"], elem_id="title")

        with gr.Row(elem_id="main-row", equal_height=False):
            # === Left: Upload + Render button ===
            with gr.Column(scale=1, min_width=200, elem_id="col-left"):
                input_image = gr.Image(label=text["upload_image"], type="numpy", height=780)
                render_btn = gr.Button(text["render"], variant="primary", size="lg")

            # === Middle: Result ===
            with gr.Column(scale=3, min_width=400, elem_id="col-middle"):
                output_image = gr.Image(
                    label=text["rendered_output"],
                    type="pil",
                    height=780,
                    interactive=False,
                    format="png",
                    buttons=["download"],
                )
                fullscreen_btn = gr.Button(text["fullscreen"], size="sm", elem_id="fullscreen-btn")

            # === Right: Parameters (independently scrollable) ===
            with gr.Column(scale=1, min_width=260, elem_id="col-right"):
                language = gr.Radio(
                    choices=[LANG_EN, LANG_ZH],
                    value=LANG_EN,
                    label=text["language"],
                )

                with gr.Accordion(text["presets"], open=True) as presets_acc:
                    preset_name = gr.Dropdown(
                        choices=_style_preset_choices(LANG_EN),
                        value=DEFAULT_STYLE_PRESET,
                        label=text["style_preset"],
                    )
                    color_preset_name = gr.Dropdown(
                        choices=_color_preset_choices(LANG_EN),
                        value=DEFAULT_COLOR_PRESET,
                        label=text["color_preset"],
                    )

                with gr.Accordion(text["output_size"], open=True) as output_size_acc:
                    output_size_note = gr.Markdown(text["output_note"])
                    output_w = gr.Number(
                        value=0, label=text["output_width"], precision=0, minimum=0,
                    )
                    output_h = gr.Number(
                        value=0, label=text["output_height"], precision=0, minimum=0,
                    )

                algorithm = gr.Dropdown(
                    choices=algo_names, value="atkinson", label=text["algorithm"],
                )
                spacing = gr.Slider(1, 8, value=1, step=1, label=text["spacing"])

                with gr.Accordion(text["preprocessing"], open=False) as preprocessing_acc:
                    contrast = gr.Slider(
                        0.2, 3.0, value=1.0, step=0.1, label=text["contrast"],
                    )
                    brightness = gr.Slider(
                        -128, 128, value=0, step=1, label=text["brightness"],
                    )

                with gr.Accordion(text["edge_detection"], open=True) as edge_acc:
                    edge_enabled = gr.Checkbox(value=False, label=text["enable_edge"])
                    edge_method = gr.Dropdown(
                        choices=["canny", "sobel"], value="canny", label=text["edge_method"],
                    )
                    edge_strength = gr.Slider(
                        0.1, 3.0, value=1.0, step=0.1, label=text["edge_strength"],
                    )
                    edge_width = gr.Slider(1, 5, value=1, step=1, label=text["edge_width"])

                with gr.Accordion(text["colors"], open=False) as colors_acc:
                    use_fg = gr.Checkbox(value=False, label=text["custom_foreground"])
                    fg_color = gr.ColorPicker(value="#000000", label=text["foreground_color"])
                    use_bg = gr.Checkbox(value=False, label=text["custom_background"])
                    bg_color = gr.ColorPicker(value="#F5E6D0", label=text["background_color"])

                with gr.Accordion(text["dual_region"], open=False) as dual_acc:
                    dual_enabled = gr.Checkbox(value=False, label=text["enable_dual"])
                    dual_seg_method = gr.Dropdown(
                        choices=_segmentation_choices(LANG_EN), value="brightness",
                        label=text["segmentation_method"],
                    )
                    dual_seg_threshold = gr.Slider(
                        0, 255, value=128, step=1, label=text["brightness_threshold"],
                    )
                    dual_fg_algo = gr.Dropdown(
                        choices=algo_names, value="bayer4x4",
                        label=text["foreground_algorithm"],
                    )
                    dual_bg_algo = gr.Dropdown(
                        choices=algo_names, value="bluenoise",
                        label=text["background_algorithm"],
                    )
                    dual_fg_spacing = gr.Slider(
                        1, 8, value=1, step=1, label=text["foreground_spacing"],
                    )
                    dual_bg_spacing = gr.Slider(
                        1, 8, value=1, step=1, label=text["background_spacing"],
                    )

                with gr.Accordion(text["algorithm_params"], open=False) as algorithm_params_acc:
                    threshold_val = gr.Slider(
                        0, 255, value=128, step=1, label=text["threshold_value"],
                    )
                    dot_size = gr.Slider(
                        2, 20, value=8, step=1, label=text["halftone_dot_size"],
                    )

                with gr.Accordion(text["export"], open=False) as export_acc:
                    dl_format = gr.Dropdown(
                        choices=["png", "jpg", "bmp", "tiff"],
                        value="png",
                        label=text["export_format"],
                    )
                    dl_btn = gr.Button(text["export_file"])
                    dl_file = gr.File(label=text["download"], interactive=False)

        # --- Events ---
        all_inputs = [
            input_image, algorithm, spacing, contrast, brightness,
            edge_enabled, edge_method, edge_strength, edge_width,
            fg_color, bg_color, use_fg, use_bg,
            threshold_val, dot_size,
            dual_enabled, dual_seg_method, dual_seg_threshold,
            dual_fg_algo, dual_bg_algo,
            dual_fg_spacing, dual_bg_spacing,
            output_w, output_h,
        ]
        preset_outputs = [
            algorithm, spacing, contrast, brightness,
            edge_enabled, edge_method, edge_strength, edge_width,
            threshold_val, dot_size,
            dual_enabled, dual_seg_method, dual_seg_threshold,
            dual_fg_algo, dual_bg_algo,
            dual_fg_spacing, dual_bg_spacing,
        ]
        language_outputs = [
            language,
            title,
            input_image,
            render_btn,
            output_image,
            fullscreen_btn,
            presets_acc,
            preset_name,
            color_preset_name,
            output_size_acc,
            output_size_note,
            output_w,
            output_h,
            algorithm,
            spacing,
            preprocessing_acc,
            contrast,
            brightness,
            edge_acc,
            edge_enabled,
            edge_method,
            edge_strength,
            edge_width,
            colors_acc,
            use_fg,
            fg_color,
            use_bg,
            bg_color,
            dual_acc,
            dual_enabled,
            dual_seg_method,
            dual_seg_threshold,
            dual_fg_algo,
            dual_bg_algo,
            dual_fg_spacing,
            dual_bg_spacing,
            algorithm_params_acc,
            threshold_val,
            dot_size,
            export_acc,
            dl_format,
            dl_btn,
            dl_file,
        ]
        language.change(
            fn=set_language,
            inputs=[language, preset_name, color_preset_name],
            outputs=language_outputs,
        )
        preset_name.change(fn=apply_preset, inputs=preset_name, outputs=preset_outputs)
        color_preset_name.change(
            fn=apply_color_preset,
            inputs=color_preset_name,
            outputs=[fg_color, bg_color, use_fg, use_bg],
        )
        render_btn.click(fn=render, inputs=all_inputs, outputs=output_image)
        dl_btn.click(fn=download, inputs=dl_format, outputs=dl_file)

        # Init JS (fix overflow + fullscreen overlay)
        app.load(fn=None, js=JS_INIT)
        fullscreen_btn.click(fn=None, js=JS_OPEN_FULLSCREEN)

    return app


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="0.0.0.0", server_port=7860, theme=gr.themes.Soft(), css=CSS)
