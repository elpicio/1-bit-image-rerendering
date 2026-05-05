# 风格化改进方向

基于《奥伯拉丁的回归》渲染技术分析，整理以下改进方向。
核心思路：从"纯抖动"升级为"边缘检测 + 抖动 + 后处理"的多层管线。

## Obra Dinn 渲染技术深度分析

### 创作者视角（Lucas Pope 自述）

- 灵感来自 1987 年 Macintosh Plus 的 512×342 1-bit 屏幕
- **可读性优先**，核心两件事：**几何体描边** + **谨慎的抖动**
- 关键教训：低分辨率拉伸到全屏后，像素太大，眼睛无法将抖动图案混合回灰度 → **"使用抖动最重要的是尽可能少用"**
- 最终方案：将 3D 相机与 2D 抖动图案统一，减少闪烁；分辨率从 640×360 提升到 800×450

### 技术拆解（Alan Zucconi 分析）

Obra Dinn 风格由**三个独立技术**组成：
1. **抖动效果** — Blue Noise 变体（比 Bayer 在屏幕缩放和视频压缩下表现更好）
2. **时间一致性** — 抖动映射到球面（静态图处理可跳过）
3. **边缘检测后处理** — 清晰的线条描边，是可读性的关键

### 实现细节（Daniel Ilett 教程）

- 管线流程：正常渲染平滑光照 → 后处理用噪声纹理做阈值化 → 亮度 > 噪声则亮，否则暗
- **环境用 Blue Noise，人物/重要物体用 Bayer**（制造视觉对比层次）
- 描边效果叠加在抖动之上，辅助视觉清晰度
- Floyd-Steinberg 是非局部效果，shader 里难做；Ordered Dithering（Bayer）可以高效并行化

### 对我们项目的核心启示

```
原始图像 → 灰度化 → 边缘检测(描边层) → 叠加描边 → 选择性抖动 → 1-bit 输出
```

1. **边缘检测描边是必须的** — 没有它纯抖动 1-bit 图像可读性差
2. **抖动要克制** — 对比度高的区域少抖动，低的区域多抖动
3. **双抖动模式创造层次** — 前景 Bayer（清晰规则）vs 背景 Blue Noise（有机柔和）

## 改进方向

### 1. 边缘检测描边（优先级最高）

**作用**：保持物体轮廓清晰可辨认，风格化效果质的飞跃

**实现思路**：
- Sobel / Canny 边缘检测，生成边缘掩码
- 边缘以纯黑叠加到抖动结果上（不被抖动打断）
- 参数 `--edge-width N` 控制描边线粗（形态学膨胀）
- 参数 `--edge-strength` 控制边缘检测灵敏度

**两种混合策略**：
- A) 先抖动再叠边缘（边缘永远清晰锐利）
- B) 边缘区域不做抖动直接黑，其余区域正常抖动

### 2. 双区域抖动（视觉层次）

**作用**：前景/背景使用不同抖动算法，模仿 Obra Dinn 的层次感

**实现思路**：
- 用亮度阈值或边缘密度做粗略前景/背景分割
- 前景区域用 Bayer（规则、清晰），背景用 Blue Noise（有机、柔和）
- 参数 `--dual-dither` 启用，可指定前景/背景算法

### 3. 对比度/亮度预处理

**作用**：抖动前增强图像，让结果更有表现力

**实现思路**：
- `--contrast FACTOR` 调整对比度（>1 增强，<1 减弱）
- `--brightness OFFSET` 调整亮度偏移
- 在灰度化之后、抖动之前应用

### 4. 前景色参数

**作用**：配合已有的 `--bg-color`，允许自定义前景（点/线）颜色

**实现思路**：
- `--fg-color HEX` 将黑色像素替换为指定颜色
- 与 `--bg-color` 配合可实现任意双色组合（如深棕+牛皮纸、深蓝+米白等）

### 5. 管线模式（组合以上所有）

**作用**：一条命令完成完整的风格化流程

**实现思路**：
- `--stylize` 一键启用推荐的描边+抖动组合
- 或者提供 pipeline 配置，让用户自由组合各步骤

## 参考资料

- Lucas Pope 创作者自述（PlayStation Blog）: https://blog.playstation.com/archive/2019/10/17/lucas-pope-on-return-of-the-obra-dinns-art-style/
- Lucas Pope 开发日志（TIGSource）: https://dukope.com/devlogs/obra-dinn/tig-32/
- Shader Showcase: Obra Dinn（Alan Zucconi 技术分析）: https://www.alanzucconi.com/2018/10/24/shader-showcase-saturday-11/
- Ultra Effects: Obra Dithering（Daniel Ilett Unity 实现教程）: https://danielilett.com/2020-02-26-tut3-9-obra-dithering/
- Ditherpunk（抖动算法总览）: https://surma.dev/things/ditherpunk/
- B站视频《风格化美学：抖动的类型、原理及实现》by Nobody_AVIS: https://www.bilibili.com/video/BV1mbHpz7ERz/
