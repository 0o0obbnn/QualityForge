#!/usr/bin/env python3
"""QualityForge 重设计 · 蓝紫禁色取色验证脚本

扫描指定目录下所有 HTML/CSS 文件中的颜色定义 (hex / rgb / hsl),
计算 HSL 色相, 判定是否落入蓝紫禁带 (hue 190-320°),
并排除"文本说明中的色值"场景 (如禁令对照表中以 code 形式列出的旧色值)。

用法:
  python3 tools/verify_palette.py <目标目录> [--old <旧目录>] [--json]

退出码: 0 = 通过 (无蓝紫), 1 = 发现蓝紫色
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

# 蓝紫禁带 (含青 190 起, 到品红前 320 止; 用户禁止蓝/紫/蓝紫渐变)
BAN_LO, BAN_HI = 190.0, 320.0


def hex_to_hsl(hexc: str):
    h = hexc.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2 / 255
    if mx == mn:
        return (0.0, 0.0, l)
    d = mx - mn
    # 0-1 空间标准饱和度公式, 避免除零
    s = d / (mx + mn) if l <= 0.5 else d / (2 - mx - mn)
    if mx == r:
        hue = ((g - b) / d) % 6
    elif mx == g:
        hue = (b - r) / d + 2
    else:
        hue = (r - g) / d + 4
    return (hue * 60, s, l)


def parse_color(text: str):
    """从文本提取 (value, hue) 列表。"""
    out = []
    # hex
    for m in re.finditer(r'#[0-9a-fA-F]{6}\b', text):
        hsl = hex_to_hsl(m.group(0))
        if hsl:
            out.append((m.group(0), hsl))
    # rgb / rgba
    for m in re.finditer(r'rgba?\(([^)]+)\)', text):
        parts = [p.strip() for p in m.group(1).split(',')]
        try:
            if parts[0].startswith('var'):  # 跳过变量引用
                continue
            r, g, b = (float(parts[i]) for i in range(3))
            mx, mn = max(r, g, b), min(r, g, b)
            l = (mx + mn) / 2 / 255
            if mx == mn:
                hue = 0.0
            else:
                d = mx - mn
                if mx == r:
                    hue = ((g - b) / d) % 6
                elif mx == g:
                    hue = (b - r) / d + 2
                else:
                    hue = (r - g) / d + 4
                hue *= 60
            out.append((m.group(0), (hue, 0.0, l)))
        except (ValueError, IndexError):
            continue
    return out


def in_ban(hsl) -> bool:
    """色相在禁带内; 完全无彩 (s=0) 不算。"""
    hue, sat, _ = hsl
    if sat < 0.02:
        return False
    return BAN_LO <= hue <= BAN_HI


def scan_dir(root: Path, skip_prefixes=()):
    """返回 {file: [(color, hue, sat, context_line)]} 违例表。

    豁免场景 (不参与渲染的颜色):
    - HTML 中 <code>…</code> 内的色值 (如禁令对照表的文本引用)
    - CSS 注释 /* … */ 内的色值
    """
    violations = {}
    for dirpath, _, files in os.walk(root):
        if any(str(Path(dirpath)).startswith(str(root / p)) for p in skip_prefixes):
            continue
        for fn in files:
            if not (fn.endswith('.html') or fn.endswith('.css')):
                continue
            p = Path(dirpath) / fn
            text = p.read_text(encoding='utf-8', errors='ignore')
            # 豁免 code 标签内容
            text = re.sub(r'<code>.*?</code>', '', text, flags=re.S)
            # 豁免 CSS 注释
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
            file_viol = []
            for line_no, line in enumerate(text.splitlines(), 1):
                for color, hsl in parse_color(line):
                    if in_ban(hsl):
                        file_viol.append({
                            'line': line_no,
                            'color': color,
                            'hue': round(hsl[0], 1),
                            'sat': round(hsl[1], 2),
                            'context': line.strip()[:120],
                        })
            if file_viol:
                violations[str(p)] = file_viol
    return violations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    root = Path(args.target)
    viol = scan_dir(root)

    if args.json:
        print(json.dumps(viol, ensure_ascii=False, indent=2))
    else:
        if not viol:
            print(f"✅ 通过: {root} 下未发现蓝紫色相 (hue {BAN_LO:.0f}-{BAN_HI:.0f}°) 的颜色")
        else:
            for f, items in viol.items():
                print(f"\n❌ {f}: {len(items)} 处")
                for it in items[:20]:
                    print(f"  L{it['line']}: {it['color']}  hue={it['hue']}°  {it['context']}")

    sys.exit(1 if viol else 0)


if __name__ == '__main__':
    main()
