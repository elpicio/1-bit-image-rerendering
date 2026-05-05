# ReShader

ReShader 是一个基于 Gradio 的 1-bit 风格化图像渲染应用。入口是 `app.py`，支持图片上传、抖动算法切换、点阵稀疏度、对比度、亮度、边缘描边、双色输出、双区域抖动和导出。

## 安装

```bash
conda activate reshader
pip install -r requirements.txt
```

推荐环境：Python 3.11。

## 启动

```bash
python app.py
```

默认监听 `0.0.0.0:7860`。本机访问：

```text
http://localhost:7860
```

## 功能

| 功能 | 说明 |
| --- | --- |
| 抖动算法 | Floyd-Steinberg、Atkinson、Jarvis、Stucki、Burkes、Sierra、Bayer、Blue Noise、Halftone、Threshold |
| 点阵稀疏度 | 先降采样再最近邻放大，形成更明显的点阵块 |
| 预处理 | 调整灰度图对比度和亮度 |
| 边缘描边 | Canny 或 Sobel 检测后把边缘压成黑色线条 |
| 颜色 | 自定义前景色和背景色 |
| 双区域抖动 | 按亮度或边缘区域拆分前景和背景，分别使用不同算法 |
| 风格预设 | 提供高反差漫画、Ditherpunk、复印机、电子墨水等参数预设 |
| 双色预设 | 提供低饱和前景/背景色组合，可和任意风格预设叠加 |
| 输出尺寸 | 指定目标宽高，比例不一致时居中裁切 |
| 导出 | 支持 png、jpg、bmp、tiff |

## 项目结构

```text
app.py              Gradio 应用入口
dither/             抖动算法注册与实现
postprocess/        预处理、边缘、颜色、分割和双区域合成
test/               手动验证用图片样例
```

## 依赖

| 库 | 用途 |
| --- | --- |
| Pillow | 图像读写与基础处理 |
| numpy | 数组运算 |
| scikit-image | 边缘检测与形态学操作 |
| gradio | Web UI |
