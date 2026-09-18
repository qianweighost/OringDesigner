# -*- coding: utf-8 -*-
"""离屏自检：跑一遍典型工况，并把每个页签截图，便于回归检查界面。

用法：
    python tools/selftest.py                 # 使用真实字体引擎，窗口不弹出
    ORING_PLATFORM=offscreen python tools/selftest.py
产出：
    tools/out/selftest.txt      自检报告
    tools/out/shot_*.png        各页签截图
    tools/out/sample_report.*   示例设计报告
"""
import os
import sys
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

if os.environ.get("ORING_PLATFORM"):
    os.environ["QT_QPA_PLATFORM"] = os.environ["ORING_PLATFORM"]

OUT = os.path.join(_ROOT, "tools", "out")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from app import GITHUB_URL, SITE_URL, MainWindow  # noqa: E402
from core.oring_core import (COMPRESSION_TABLE, PRESSURE_PRESETS, compression_band,
                             design, edge_fillet_lead, groove_std_pair,
                             recommend_compression, water_depth_pressure)  # noqa: E402
from ui import theme  # noqa: E402


def _d2_items(rad):
    """下拉框里所有标准线径数值。"""
    cb = rad.in_d2.combo
    return [float(cb.itemData(i)) for i in range(cb.count())
            if cb.itemData(i) is not None]


def _idx_of(rad, val):
    """找到最接近给定线径的选项下标。"""
    cb = rad.in_d2.combo
    best, bi = None, 0
    for i in range(cb.count()):
        d = cb.itemData(i)
        if d is None:
            continue
        if best is None or abs(float(d) - val) < abs(best - val):
            best, bi = float(d), i
    return bi


CASES = [
    # (缸孔/杆径, 压力 MPa, 介质, 运动, 低温, 高温, 型式)
    (40.0, 16.0, "液压油（矿物基）", "往复", 20, 80, "radial_piston"),
    (25.0, 10.0, "液压油（矿物基）", "往复", 20, 70, "radial_rod"),
    (63.0, 25.0, "液压油（矿物基）", "静态", 30, 100, "radial_piston"),
    (10.0, 1.0, "气动 / 空气", "静态", 5, 60, "radial_piston"),
    (125.0, 2.5, "水 / 水-乙二醇", "往复", 5, 90, "radial_rod"),
    (30.0, 8.0, "制动液 DOT3/DOT4", "往复", -30, 120, "radial_piston"),
]

log = []
try:
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.stylesheet())
    win = MainWindow()
    win.resize(1400, 900)
    win.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    win.show()
    if win.layout():
        win.layout().activate()
    for _ in range(6):
        app.processEvents()

    # ---- 窗口 / 任务栏图标 ----
    from ui import icons
    app.setWindowIcon(icons.app_icon())      # 与 main() 中一致
    ic = app.windowIcon()
    log.append(f"✓ 应用窗口图标：{'已设置' if not ic.isNull() else '缺失！'}"
               f"（档位 {len(ic.availableSizes())} 个，含 "
               f"{max(s.width() for s in ic.availableSizes())}px）")
    log.append(f"✓ 主窗口自身图标：{'已设置' if not win.windowIcon().isNull() else '缺失！'}")

    # ---- 页眉链接 ----
    links = [b for b in win.findChildren(QPushButton)
             if b.objectName() == "LinkBtn"]
    for b in links:
        log.append(f"✓ 页眉链接：『{b.text() or '纯图标'}』-> {b.url}"
                   f"（图标 {b.iconSize().width()}px，"
                   f"悬停图标 {'有' if not b._hover.isNull() else '无'}）")
    if len(links) != 2:
        log.append(f"✗ 页眉链接数量异常：{len(links)}")
    if not any(b.url == GITHUB_URL for b in links):
        log.append("✗ 未找到 GitHub 链接")
    if not any(b.url == SITE_URL for b in links):
        log.append("✗ 未找到个人网站链接")

    names = ["径向密封", "轴向密封", "材料选型库", "标准尺寸库", "使用说明"]
    for i in range(win.tabs.count()):
        win.tabs.setCurrentIndex(i)
        for _ in range(8):
            app.processEvents()
        win.grab().save(os.path.join(OUT, f"shot_{i}.png"))
        log.append(f"截图 {i} -> {names[i]}")

    # ---- 常用工况预设 ----
    rad = win.tabs.widget(0)
    n_preset = rad.in_preset.combo.count()
    log.append(f"✓ 工况预设共 {n_preset} 项："
               + "、".join(it["label"] for it in PRESSURE_PRESETS[1:6]) + " …")
    log.append(f"✓ 水深换算：1 m -> {water_depth_pressure(1):.4f} MPa，"
               f"10 m -> {water_depth_pressure(10):.3f} MPa，"
               f"100 m -> {water_depth_pressure(100):.3f} MPa")

    # 用预设跑一发（30 m 水深 + 往复）
    rad.in_preset.combo.setCurrentIndex(
        [it["key"] for it in PRESSURE_PRESETS].index("depth30"))
    rad.in_dia.set_value(50.0)
    rad.recalc()
    r = rad._res
    log.append(f"✓ 预设「30 m 水深」→ 压力 {r['input']['pressure']:.3f} MPa，"
               f"介质 {r['input']['medium']}，运动 {r['input']['motion']}，"
               f"d1={r['oring']['d1']:.2f} d2={r['oring']['d2']:.2f} "
               f"b={r['groove']['b']:.2f}")
    log.append(f"  提示行：{rad.lbl_preset.text()}")

    # 手动改压力 -> 预设应退回「手动输入」
    rad.in_press.set_value(1.25)
    log.append(f"✓ 手动改压力后预设回到："
               f"『{rad.in_preset.combo.currentText()}』")

    # ---- 径向典型工况 ----
    for (dia, pr, med, mo, lo, hi, mode) in CASES:
        rad.mode = mode
        rad.in_preset.combo.setCurrentIndex(0)
        rad.in_dia.set_value(dia)
        rad.in_press.set_value(pr)
        rad.in_medium.combo.setCurrentText(med)
        rad.in_motion.combo.setCurrentText(mo)
        rad.in_tlow.set_value(lo)
        rad.in_thigh.set_value(hi)
        rad.in_d2.combo.setCurrentIndex(0)
        rad.in_width.clear()
        rad.in_backup.combo.setCurrentIndex(0)
        rad.recalc()
        r = rad._res
        if r is None:
            log.append(f"✗ {mode} D={dia} 未获得结果")
            continue
        g, m = r["groove"], r["metrics"]
        log.append(
            f"✓ {mode:14s} D={dia:6.1f} P={pr:5.1f} {med:<16s} -> "
            f"d1={r['oring']['d1']:7.2f} d2={r['oring']['d2']:.2f} "
            f"h={g['h']:5.2f} b={g['b']:5.2f}（{g['b_src']}）"
            f"ε={m['compression_pct']:5.1f}% "
            f"δ={m['stretch_pct']:5.2f}% "
            f"K={m['fill_pct']:5.1f}% "
            f"挡圈={m['backup_n']} "
            f"{r['material']['code']:5s} {r['hardness']['value']}A "
            f"警告={len(r['warnings'])}")

    # ---- 线径：扩充列表 + 手工输入 ----
    rad.mode = "radial_piston"
    log.append(f"✓ 线径下拉共 {rad.in_d2.combo.count()} 项（含「自动推荐」），"
               f"最小 {min(x for x in _d2_items(rad)):.2f}、"
               f"最大 {max(x for x in _d2_items(rad)):.2f} mm")

    # 选一个标准线径
    idx = _idx_of(rad, 5.30)
    rad.in_d2.combo.setCurrentIndex(idx)
    rad.in_dia.set_value(63.0)
    rad.in_press.set_value(16.0)
    rad.recalc()
    r = rad._res
    log.append(f"✓ 下拉选 φ5.30 → d2={r['oring']['d2']:.2f}"
               f"（{r['oring']['d2_src']}）  提示：{rad.lbl_d2.text()}")

    # 手工输入一个非标准线径
    rad.in_d2.combo.setEditText("3.20")
    rad.recalc()
    r = rad._res
    log.append(f"✓ 手工输入 3.20 → d2={r['oring']['d2']:.2f}"
               f"（{r['oring']['d2_src']}）  h={r['groove']['h']:.2f} "
               f"b={r['groove']['b']:.2f}（{r['groove']['b_src']}）")
    log.append(f"  提示：{rad.lbl_d2.text()}")

    # 越界值应被拦截
    rad.in_d2.combo.setEditText("99")
    rad.recalc(force=True)
    if rad._res is None:
        cell = rad.row_oring.grid.itemAtPosition(0, 1)
        msg = cell.widget().text() if (cell and cell.widget()) else "?"
        log.append(f"✓ 越界线径 99 已拦截：{msg}")
    else:
        log.append("✗ 越界线径 99 未被拦截")
        rad.in_d2.combo.setCurrentIndex(0)

    # ---- 槽宽：自动推荐 / 手动覆盖 ----
    rad.in_d2.combo.setCurrentIndex(0)
    rad.in_width.clear()
    rad.recalc()
    auto_b = rad._res["groove"]["b"]
    log.append(f"✓ 槽宽自动推荐：b={auto_b:.2f} mm（{rad._res['groove']['b_src']}）"
               f"  提示：{rad.lbl_b.text()}")
    rad.in_width.set_value(6.5)
    rad.recalc()
    r = rad._res
    log.append(f"✓ 槽宽手动覆盖 6.5 → b={r['groove']['b']:.2f}"
               f"（{r['groove']['b_src']}）  提示：{rad.lbl_b.text()}")
    rad.in_width.clear()

    # ---- 挡圈：自动 / 不加 / 单侧 / 双侧 ----
    rad.in_dia.set_value(63.0)
    rad.in_press.set_value(25.0)
    rad.in_motion.combo.setCurrentText("往复")
    for name in ("自动判定", "不加挡圈", "单侧挡圈", "两侧各一个"):
        rad.in_backup.combo.setCurrentText(name)
        rad.recalc()
        r = rad._res
        g, m = r["groove"], r["metrics"]
        log.append(f"✓ 挡圈[{name}] -> n={m['backup_n']} "
                   f"槽宽 {g['b']:.2f} = 腔 {g['b_base']:.2f} + 占位 {g['b_backup']:.2f}"
                   f"  K={m['fill_pct']:.1f}%（下限 {m['fill_range'][0]:.0f}%）"
                   f"  警告={len(r['warnings'])}")
    rad.in_backup.combo.setCurrentIndex(0)

    # ---- 轴向 ----
    ax = win.tabs.widget(1)
    ax.in_dia.set_value(80.0)
    ax.in_press.set_value(1.6)
    ax.in_medium.combo.setCurrentText("蒸汽")
    ax.in_tlow.set_value(20)
    ax.in_thigh.set_value(150)
    ax.recalc()
    ra = ax._res
    log.append(f"✓ axial          dm=80.0 -> d1={ra['oring']['d1']:.2f} "
               f"h={ra['groove']['h']:.2f} b={ra['groove']['b']:.2f}"
               f"（{ra['groove']['b_src']}）"
               f"ε={ra['metrics']['compression_pct']:.1f}% "
               f"{ra['material']['code']} {ra['hardness']['value']}A")

    # ---- GB/T 3452.3-2005 附录A：压缩率表逐值核对与单调性 ----
    bad = []
    for k, tbl in COMPRESSION_TABLE.items():
        for d2, (lo, hi) in tbl.items():
            gl, gh, _s = compression_band(d2, k)
            if abs(gl - lo) > 1e-6 or abs(gh - hi) > 1e-6:
                bad.append((k, d2, gl, gh))
    log.append(f"{'✓' if not bad else '✗'} 附录A 四类压缩率表逐值核对："
               f"{'全部一致' if not bad else f'偏差 {bad[:3]}'}")

    d2s = (1.80, 2.65, 3.55, 5.30, 7.00)
    hi_ser = [compression_band(x, "static")[1] for x in d2s]
    mono = all(hi_ser[i] >= hi_ser[i + 1] for i in range(len(hi_ser) - 1))
    log.append(f"{'✓' if mono else '✗'} 静密封允许上限随线径单调下降：{hi_ser}")

    higher = all(compression_band(x, "static")[1] > compression_band(x, "pneu")[1]
                 for x in d2s)
    log.append(f"{'✓' if higher else '✗'} 静密封区间整体高于动密封：{higher}")

    # ---- 水深预设不得覆盖运动方式（水深只是压力来源）----
    cb = rad.in_preset.combo
    rad.in_motion.combo.setCurrentText("静态")
    di = next((i for i in range(cb.count()) if "水深 20 m" in cb.itemText(i)), None)
    if di is not None:
        cb.setCurrentIndex(di)
        kept = rad.in_motion.current()
        log.append(f"{'✓' if kept == '静态' else '✗'} 水深预设不改运动方式："
                   f"仍为「{kept}」")

    # ---- IPX 预设应为静密封，且压缩率落在静密封表区间内 ----
    ii = next((i for i in range(cb.count()) if "IPX8" in cb.itemText(i)), None)
    if ii is not None:
        cb.setCurrentIndex(ii)
        rad.recalc()
        r = rad._res
        mm = r["metrics"]
        inb = mm["compression_range"][0] <= mm["compression_pct"] <= mm["compression_range"][1]
        log.append(f"{'✓' if (rad.in_motion.current() == '静态' and inb) else '✗'} "
                   f"IPX8 预设：运动「{rad.in_motion.current()}」"
                   f" p={r['input']['pressure']:.3f} MPa"
                   f" ε={mm['compression_pct']:.2f}%"
                   f" 区间={mm['compression_range'][0]:.1f}~{mm['compression_range'][1]:.1f}%")
    cb.setCurrentIndex(0)

    # ---- 壳体材料：热漂移 + 塑料蠕变补偿 ----
    for code in (None, "al", "pom"):
        idx = 0
        if code:
            for i in range(rad.in_housing.combo.count()):
                if rad.in_housing.combo.itemText(i).startswith(code):
                    idx = i
                    break
        rad.in_housing.combo.setCurrentIndex(idx)
        rad.recalc()
        r = rad._res
        ho = r.get("housing") or {}
        log.append(f"✓ 壳体[{code or '未指定'}] ε={r['metrics']['compression_pct']:.2f}%"
                   f" 热漂移={ho.get('d_comp_pp', 0):+.2f}pp"
                   f" 蠕变补偿={ho.get('creep_pp', 0):.1f}pp"
                   f" α={ho.get('alpha', 0):.1f} 警告={len(r['warnings'])}")
    rad.in_housing.combo.setCurrentIndex(0)

    # ---- 安装圆角 / 导入倒角 ----
    rad.recalc()
    asm = rad._res["assembly"]
    log.append(f"✓ 圆角/倒角：r₁ {asm['r1'][0]:.2f}~{asm['r1'][1]:.2f}"
               f"  r₂ {asm['r2'][0]:.2f}~{asm['r2'][1]:.2f}"
               f"  导入角 {asm['lead_angle'][0]:.0f}°~{asm['lead_angle'][1]:.0f}°"
               f"  Zmin={asm['lead_zmin']:.2f} mm")
    for d2v in (1.80, 3.55, 7.00, 12.00):
        e = edge_fillet_lead(d2v)
        log.append(f"   d₂={d2v:.2f} -> r₁ {e['r1'][0]:.2f}~{e['r1'][1]:.2f}"
                   f"  Zmin={e['lead_zmin']:.2f}（{e['lead_zmin_src']}）"
                   f"  标准表内={'是' if e['in_table'] else '否'}")

    # ---- 压缩率「余量上限」约束：各工况修正不得把值顶到区间上限 ----
    import math as _math
    _viol = []
    _cases = [("hyd", "往复", "", "radial"), ("pneu", "往复", "气动 / 空气", "radial"),
              ("static", "静态", "", "radial"), ("axial", "静态", "", "axial")]
    for kind, motion, med, md in _cases:
        for d2v in (1.80, 2.65, 3.55, 5.30, 7.00):
            lo, hi, _s = compression_band(d2v, kind)
            h_std, _b, _t = groove_std_pair(d2v, kind)
            base0 = max(lo, min(hi, (d2v - h_std) / d2v * 100.0))
            cap = 0.5 * max(0.0, hi - base0)
            for p in (0.0, 1.0, 16.0, 32.0):
                for hd in (60, 70, 90):
                    for cr in (0.0, 1.5):
                        e, _w = recommend_compression(md, motion, p, hd,
                                                      d2=d2v, medium=med, creep_pp=cr)
                        # 推荐值对外保留 2 位小数，判据同样按 2 位收口，避免四舍五入残差
                        if e > round(base0 + cap, 2) + 1e-9:
                            _viol.append((kind, d2v, p, hd, cr, e, base0 + cap))
    log.append(f"{'✓' if not _viol else '✗'} 压缩率余量约束"
               f"（修正合计 ≤ 至区间上限余量的一半）："
               f"{'全部满足' if not _viol else f'{len(_viol)} 例越界 {_viol[:2]}'}")

    # ---- 拉伸 → 截面减薄 → 实际压缩量 链路自洽 ----
    _bad2 = []
    for md, dia in (("radial_piston", 16.30), ("radial_rod", 25.0), ("axial", 63.0)):
        r = design(md, dia, 1.0, 5, 40, "水 / 水-乙二醇",
                   motion="静态", d2=1.80 if md != "axial" else 3.55)
        mm = r["metrics"]
        thin_exp = 1.0 / _math.sqrt(1.0 + max(mm["stretch_pct"], 0.0) / 100.0)
        checks = {
            "thin": abs(mm["thin_factor"] - thin_exp) < 1e-9,
            "cord": abs(mm["cord_loaded"] - mm["cord_free"] * thin_exp) < 1e-9,
            "comp": abs(mm["compression_mm_corr"]
                        - (mm["cord_loaded"] - r["groove"]["h"])) < 1e-9,
            "stretch_mm": abs(mm["stretch_mm"]
                              - (mm["stretch_ref"] - (r["oring"]["d1"]
                                 if md != "axial"
                                 else r["oring"]["d1"] + mm["cord_free"]))) < 1e-9,
            "corr_le_nom": mm["compression_pct_corr"] <= mm["compression_pct"] + 1e-9,
        }
        if not all(checks.values()):
            _bad2.append((md, [k for k, v in checks.items() if not v]))
        log.append(f"   拉伸链[{md}]：δ={mm['stretch_pct']:.2f}%"
                   f" 拉伸量={mm['stretch_mm']:+.2f} mm"
                   f" 线径 {mm['cord_free']:.2f}→{mm['cord_loaded']:.3f}"
                   f"（×{mm['thin_factor']:.3f}）"
                   f" 压缩量 {mm['compression_mm']:.3f}→{mm['compression_mm_corr']:.3f} mm"
                   f"（{mm['compression_pct']:.2f}%→{mm['compression_pct_corr']:.2f}%）"
                   f" {'✓' if all(checks.values()) else '✗'}")
    log.append(f"{'✓' if not _bad2 else '✗'} 拉伸/减薄/实际压缩量链路自洽："
               f"{'全部通过' if not _bad2 else f'{_bad2}'}")

    # ---- 导出报告链路 ----
    txt = rad._report_text()
    html = rad._report_html()
    with open(os.path.join(OUT, "sample_report.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    with open(os.path.join(OUT, "sample_report.html"), "w", encoding="utf-8") as f:
        f.write(html)
    log.append(f"✓ 报告导出：TXT {len(txt)} 字符 / HTML {len(html)} 字符"
               f"（含压力来源行：{'是' if '压力来源' in txt else '否'}）")

    # ---- 其它页签 ----
    mp = win.tabs.widget(2)
    mp.cb_med.setCurrentText("制动液 DOT3/DOT4")
    mp.ed_hi.setText("120")
    mp._rank()
    log.append("材料库筛选：" + mp.lbl_res.text())

    sp = win.tabs.widget(3)
    sp.search.setText("25")
    log.append("标准库筛选：" + sp.lbl_count.text())
    sp.search.clear()
    sp.cb_tag.setCurrentText("英制")
    log.append("标准库按系列筛选（英制）：" + sp.lbl_count.text())
    sp.cb_tag.setCurrentIndex(0)

except Exception:  # noqa: BLE001
    log.append("异常：\n" + traceback.format_exc())

out_file = os.path.join(OUT, "selftest.txt")
with open(out_file, "w", encoding="utf-8") as f:
    f.write("\n".join(log))
print("\n".join(log))
print("\n报告：", out_file)
