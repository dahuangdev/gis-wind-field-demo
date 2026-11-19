# gis-wind-field-demo

GIS 风场 pack/unpack 精度回归的最小可复现 demo。

风速分量 (u, v) 打包进纹理（每分量 16-bit = 高低字节）再解包，
回归脚本验证解包误差是否过门禁。弱风是卡点：8-bit 量化步长
约 0.47 m/s，而弱风信号本身才 0~2 m/s，相对误差直接失控，
所以弱风必须走 16-bit——门禁就是为卡这一点设计的。

## 文件

- `regression.py` — 精度回归脚本，只用 Python 标准库
- `tests.yaml` — 用例与门禁阈值（PyYAML 没装时用内置解析器）
- `sample.geojson` — 12 个 GRIB2 采样点（u/v 分量）
- `shaders/wind_pack.glsl` — pack/unpack 的 GLSL 实现（与脚本同一套数学）
- `shaders/wind_render.glsl` — 风场粒子渲染参考着色器
- `regression.log` — 本机跑出来的原始回归日志

## 一键复现

```bash
python3 regression.py
```

## 实测结果（regression.log）

- 16-bit：4 个用例全部 PASS，max_abs 误差 0.0009 m/s（门禁 0.01），
  12 个 GeoJSON 采样点 PASS
- 8-bit（仅作对照）：弱风 max_abs 0.2353 m/s，撞上弱风门禁 0.05，
  强风 max_rel 0.0219~0.0737，撞上相对误差门禁 0.02

结论：生产档位 16-bit 全过，8-bit 在弱风下不可用。
