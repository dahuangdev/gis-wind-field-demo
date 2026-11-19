#!/usr/bin/env python3
"""GIS 风场 pack/unpack 精度回归（最小可复现 demo）.

复现流程：
  1. 读 tests.yaml（用例 + 门禁阈值）
  2. 按 seed 合成风场采样 (u, v)，并读 sample.geojson 的真实采样点
  3. pack -> unpack（16-bit / 8-bit），统计误差
  4. 按门禁判定：弱风（风速 < weak_wind_threshold）只看绝对误差，
     因为弱风下相对误差没有意义；强风同时看绝对误差与相对误差
  5. 生产档位是 16-bit：它必须全过；8-bit 只作对照——弱风下它会
     撞上绝对误差门禁，这正是“弱风误差卡点”的设计依据：
     8-bit 量化步长约 0.47 m/s，弱风信号本身才 0~2 m/s，
     相对误差直接失控，所以弱风必须走 16-bit

只用标准库。tests.yaml 优先用 PyYAML 解析，没装时用内置的
极简解析器（本文件的 yaml 结构很简单，解析器够用）。
"""
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _scalar(s):
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def _mini_yaml(path):
    """只够解析本 demo 的 tests.yaml：顶层 key: value + cases 列表。"""
    cfg = {"cases": []}
    in_cases = False
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line == "cases:":
                in_cases = True
                continue
            if in_cases and line.startswith("- "):
                parts = [p.strip() for p in line[2:].split(",")]
                cfg["cases"].append(parts)
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                cfg[key.strip()] = _scalar(val.strip())
    return cfg


def load_yaml(path):
    try:
        import yaml  # type: ignore
    except ImportError:
        return _mini_yaml(path)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def norm_cases(raw_cases):
    cases = []
    for item in raw_cases:
        if isinstance(item, dict):
            cases.append({
                "name": str(item["name"]),
                "seed": int(item["seed"]),
                "n": int(item["n"]),
                "speed_min": float(item["speed_min"]),
                "speed_max": float(item["speed_max"]),
            })
        else:
            parts = [p.strip() for p in item.split(",")] if isinstance(item, str) else [str(p) for p in item]
            cases.append({
                "name": parts[0],
                "seed": int(parts[1]),
                "n": int(parts[2]),
                "speed_min": float(parts[3]),
                "speed_max": float(parts[4]),
            })
    return cases


def pack(value, vmin, vmax, levels):
    q = round((value - vmin) / (vmax - vmin) * (levels - 1))
    return max(0, min(levels - 1, q))


def unpack(q, vmin, vmax, levels):
    return vmin + q / (levels - 1) * (vmax - vmin)


def sample_wind(rng, speed_min, speed_max, n):
    pts = []
    for _ in range(n):
        speed = rng.uniform(speed_min, speed_max)
        theta = rng.uniform(0.0, 2.0 * math.pi)
        pts.append((speed * math.cos(theta), speed * math.sin(theta)))
    return pts


def evaluate(points, vmin, vmax, levels, weak_threshold):
    abs_errs = []
    weak_abs_errs = []
    rel_errs = []
    for u, v in points:
        for comp in (u, v):
            q = pack(comp, vmin, vmax, levels)
            back = unpack(q, vmin, vmax, levels)
            abs_errs.append(abs(back - comp))
        speed = math.hypot(u, v)
        if speed < weak_threshold:
            for comp in (u, v):
                q = pack(comp, vmin, vmax, levels)
                weak_abs_errs.append(abs(unpack(q, vmin, vmax, levels) - comp))
        elif speed > 0:
            for comp in (u, v):
                q = pack(comp, vmin, vmax, levels)
                rel_errs.append(abs(unpack(q, vmin, vmax, levels) - comp) / speed)
    return {
        "max_abs": max(abs_errs),
        "mean_abs": sum(abs_errs) / len(abs_errs),
        "max_abs_weak": max(weak_abs_errs) if weak_abs_errs else 0.0,
        "max_rel_strong": max(rel_errs) if rel_errs else 0.0,
    }


def main():
    cfg = load_yaml(ROOT / "tests.yaml")
    vmin = float(cfg["pack_min"])
    vmax = float(cfg["pack_max"])
    weak_t = float(cfg["weak_wind_threshold"])
    gate16 = float(cfg["max_abs_error_16bit"])
    gate8 = float(cfg["max_abs_error_8bit"])
    gate_weak = float(cfg["max_abs_error_weak_wind"])
    gate_rel = float(cfg["max_rel_error_strong_wind"])
    cases = norm_cases(cfg["cases"])

    print("GIS wind-field pack/unpack precision regression")
    print("pack range: [%s, %s] m/s, weak-wind threshold: %s m/s" % (vmin, vmax, weak_t))
    print("gates: 16-bit max_abs<=%.3f, 8-bit max_abs<=%.3f, weak max_abs<=%.3f, strong max_rel<=%.3f"
          % (gate16, gate8, gate_weak, gate_rel))
    print("-" * 96)

    verdicts = []
    for case in cases:
        rng = random.Random(case["seed"])
        pts = sample_wind(rng, case["speed_min"], case["speed_max"], case["n"])
        for bits, levels, gate in ((16, 65536, gate16), (8, 256, gate8)):
            m = evaluate(pts, vmin, vmax, levels, weak_t)
            ok_abs = m["max_abs"] <= gate
            ok_weak = m["max_abs_weak"] <= gate_weak
            ok_rel = m["max_rel_strong"] <= gate_rel
            passed = ok_abs and ok_weak and ok_rel
            verdicts.append((case["name"], bits, passed))
            print("case=%-12s n=%-4d bits=%-2d max_abs=%.4f mean_abs=%.4f "
                  "max_abs_weak=%.4f max_rel_strong=%.4f  %s"
                  % (case["name"], case["n"], bits, m["max_abs"], m["mean_abs"],
                     m["max_abs_weak"], m["max_rel_strong"], "PASS" if passed else "FAIL"))

    # sample.geojson 真实采样点：只考核生产档位 16-bit
    with open(ROOT / "sample.geojson", encoding="utf-8") as f:
        gj = json.load(f)
    geo_pts = [(ft["properties"]["u"], ft["properties"]["v"])
               for ft in gj["features"]]
    m = evaluate(geo_pts, vmin, vmax, 65536, weak_t)
    geo_ok = m["max_abs"] <= gate16 and m["max_abs_weak"] <= gate_weak
    print("-" * 96)
    print("geojson: %d sample points, 16-bit max_abs=%.4f max_abs_weak=%.4f  %s"
          % (len(geo_pts), m["max_abs"], m["max_abs_weak"], "PASS" if geo_ok else "FAIL"))

    prod_ok = geo_ok and all(p for _, bits, p in verdicts if bits == 16)
    print("=" * 96)
    print("VERDICT: production packing (16-bit) %s" % ("PASS" if prod_ok else "FAIL"))
    print("note: 8-bit is reference only; it fails the weak-wind gate by design "
          "(step ~0.47 m/s vs weak signal 0-2 m/s)")
    return 0 if prod_ok else 1


if __name__ == "__main__":
    sys.exit(main())
