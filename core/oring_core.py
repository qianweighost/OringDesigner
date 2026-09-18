# -*- coding: utf-8 -*-
"""
O 形橡胶密封圈设计计算内核
=====================================================================
覆盖范围
  · 径向密封 —— 活塞密封（O 圈装于活塞，密封缸孔）
  · 径向密封 —— 活塞杆密封（O 圈装于缸头沟槽，密封活塞杆）
  · 轴向密封 —— 端面/法兰静密封
计算内容
  密封圈内径 d1 / 外径 d0 / 线径 d2 / 压缩量 c / 压缩率 ε / 拉伸率 δ
  沟槽槽深 h / 槽宽 b / 槽底径 / 沟槽内外径 / 填充率 / 允许挤出间隙
  材料选型 / 邵氏硬度选型 / 挡圈判定

标准参考
  GB/T 3452.1  液压气动用 O 形橡胶密封圈 第 1 部分：尺寸系列及公差
  GB/T 3452.3  液压气动用 O 形橡胶密封圈 第 2 部分：沟槽尺寸
  GB/T 531.1   橡胶袖珍硬度计压入硬度试验方法（邵氏 A）
  ISO 3601 / SAE AS568  国际与美制系列
  Parker O-Ring Handbook / 机械设计手册（材料相容性、挤出间隙）

⚠ 本内核给出的是工程通用设计值。量产前请以最新版标准原文与供应商
  实测数据复核，尤其是有特殊介质、特殊温度或安全强制要求的场合。
"""

from __future__ import annotations

import math

# =====================================================================
# 一、标准数据表
# =====================================================================

# ---- 线径 d2 系列 (mm) ----
# 公制    GB/T 3452.1 优先数系
# 英制    AS568 / ISO 3601-1 折算
# 通用    市场上常见的其他商用品径（非优先数系，按需选用）
D2_SPECS = [
    (1.00, "通用"), (1.50, "通用"), (1.60, "通用"),
    (1.78, "英制"), (1.80, "公制"),
    (2.00, "通用"), (2.40, "通用"), (2.50, "通用"),
    (2.62, "英制"), (2.65, "公制"),
    (3.00, "通用"), (3.10, "通用"), (3.53, "英制"), (3.55, "公制"),
    (4.00, "通用"), (4.50, "通用"), (5.00, "通用"),
    (5.30, "公制"), (5.33, "英制"),
    (6.00, "通用"), (6.99, "英制"), (7.00, "公制"),
    (8.00, "通用"), (8.40, "通用"), (9.53, "英制"),
    (10.00, "通用"), (12.00, "通用"),
]

D2_ALL = [x for x, _ in D2_SPECS]
D2_TAG = {x: t for x, t in D2_SPECS}
# 公制优先数系（GB/T 3452.1 标准线径）
D2_METRIC = [x for x, t in D2_SPECS if t == "公制"]
# 英制系列 AS568 / ISO 3601-1（折算为 mm）
D2_INCH = [x for x, t in D2_SPECS if t == "英制"]

# 线径极限偏差 ±(mm)，按 GB/T 3452.1 / ISO 3601-1 分档
D2_TOL_BANDS = [
    (1.80, 0.08), (2.20, 0.08), (2.70, 0.09), (3.60, 0.10), (4.50, 0.10),
    (5.60, 0.12), (6.80, 0.13), (8.00, 0.14), (1e9, 0.15),
]
# 最小 / 最大可用线径（手工输入时校验）
D2_MIN, D2_MAX = 0.80, 15.00

# ---- 内径 d1 优先数系 (mm) ----
# GB/T 3452.1 系列 A 常用规格（节选覆盖 φ3.55 ~ φ500）
D1_SERIES = [
    3.55, 4.87, 5.15, 5.30, 5.60, 6.00, 6.30, 6.70, 7.10, 7.50,
    8.00, 8.50, 9.00, 9.50, 10.00, 10.60, 11.20, 11.80, 12.50, 13.20,
    14.00, 15.00, 16.00, 17.00, 18.00, 19.00, 20.00, 21.20, 22.40, 23.60,
    25.00, 26.50, 28.00, 29.50, 31.50, 33.50, 34.50, 35.50, 36.50, 37.50,
    38.70, 40.00, 41.20, 42.50, 43.70, 45.00, 46.20, 47.50, 48.70, 50.00,
    51.50, 53.00, 54.50, 56.00, 58.00, 60.00, 61.50, 63.00, 65.00, 67.00,
    69.00, 71.00, 73.00, 75.00, 77.50, 80.00, 82.50, 85.00, 87.50, 90.00,
    92.50, 95.00, 97.50, 100.00, 103.00, 106.00, 109.00, 112.00, 115.00,
    118.00, 122.00, 125.00, 128.00, 132.00, 136.00, 140.00, 145.00, 150.00,
    155.00, 160.00, 165.00, 170.00, 175.00, 180.00, 185.00, 190.00, 195.00,
    200.00, 206.00, 212.00, 218.00, 224.00, 230.00, 236.00, 243.00, 250.00,
    258.00, 265.00, 272.00, 280.00, 290.00, 300.00, 307.00, 315.00, 325.00,
    335.00, 345.00, 355.00, 365.00, 375.00, 387.00, 400.00, 412.00, 425.00,
    437.00, 450.00, 462.00, 475.00, 487.00, 500.00,
]

# 内径公差 ±(mm)，按内径分段（GB/T 3452.1 简化）
D1_TOL_BANDS = [
    (10.0, 0.10), (16.0, 0.13), (25.0, 0.15), (40.0, 0.20),
    (63.0, 0.25), (100.0, 0.35), (160.0, 0.50), (250.0, 0.70),
    (400.0, 1.00), (1e9, 1.30),
]


DESIGN_DOC = """标准依据
  GB/T 3452.1  液压气动用 O 形橡胶密封圈  第 1 部分：尺寸系列及公差
  GB/T 3452.3  液压气动用 O 形橡胶密封圈  第 2 部分：沟槽尺寸
  GB/T 531.1   橡胶袖珍硬度计压入硬度试验方法（邵氏 A）
  ISO 3601 / SAE AS568  国际与美制尺寸系列
  Parker O-Ring Handbook / 机械设计手册  材料相容性与挤出间隙

免责声明
  本报告由程序按上述标准的通用工程取值自动生成，用于方案比选与初步设计。
  正式投产前请以最新版标准原文、供应商实测数据以及实际工况验证结果复核，
  尤其是涉及高压、高温、强腐蚀介质或安全强制要求的场合。"""


def d1_tolerance(d1: float) -> float:
    for hi, tol in D1_TOL_BANDS:
        if d1 <= hi:
            return tol
    return 1.30


def d2_tolerance(d2: float) -> float:
    """线径极限偏差 ±(mm)，按 GB/T 3452.1 / ISO 3601-1 分档取值。"""
    for hi, tol in D2_TOL_BANDS:
        if d2 <= hi + 1e-9:
            return tol
    return 0.15


def d2_family(d2: float) -> tuple[float | None, str]:
    """返回 (最接近的标准线径 or None, 系列标签)。

    与标准值相差 ≤ 0.02 mm 视为该标准规格；否则为自定义线径。
    """
    best = min(D2_ALL, key=lambda x: abs(x - d2))
    if abs(best - d2) <= 0.02:
        return best, D2_TAG[best]
    return None, "自定义"


# ---- 沟槽标准尺寸 (槽深 h, 槽宽 b) ----
# 键：线径 d2 → {"static": (h, b), "dynamic": (h, b), "axial": (h, b)}
# static  = 径向静密封（液压/气动通用）
# dynamic = 径向往复动密封
# axial   = 轴向端面静密封
GROOVE_STD = {
    1.80: {"static": (1.42, 2.40), "dynamic": (1.52, 2.60), "axial": (1.25, 2.40)},
    2.65: {"static": (2.10, 3.60), "dynamic": (2.22, 3.80), "axial": (1.90, 3.60)},
    3.55: {"static": (2.80, 4.80), "dynamic": (3.00, 5.00), "axial": (2.60, 4.80)},
    5.30: {"static": (4.20, 7.10), "dynamic": (4.50, 7.50), "axial": (3.80, 7.10)},
    7.00: {"static": (5.60, 9.50), "dynamic": (5.95, 9.90), "axial": (5.10, 9.50)},
}

# 沟槽尺寸锚点表 (d2, h/t, b)，逐值取自 GB/T 3452.3-2005 表1 / 表2 / 表3。
#   static 表2 静密封    hyd 表2 液压动密封    pneu 表2 气动动密封    axial 表3 轴向密封
# 非锚点线径在相邻锚点间按线径线性插值；超出两端时按末段斜率外推。
# 校验：由这些槽深反算的压缩率，全部落在附录 A 的允许区间内（两张表自洽）。
_GROOVE_ANCHORS = {
    "static": [(1.80, 1.32, 2.40), (2.65, 2.00, 3.60), (3.55, 2.90, 4.80),
               (5.30, 4.31, 7.10), (7.00, 5.85, 9.50)],
    "hyd": [(1.80, 1.35, 2.40), (2.65, 2.10, 3.60), (3.55, 2.85, 4.80),
            (5.30, 4.35, 7.10), (7.00, 5.85, 9.50)],
    "pneu": [(1.80, 1.40, 2.20), (2.65, 2.15, 3.40), (3.55, 2.95, 4.60),
             (5.30, 4.50, 6.90), (7.00, 6.10, 9.30)],
    "axial": [(1.80, 1.28, 2.60), (2.65, 1.97, 3.80), (3.55, 2.75, 5.00),
              (5.30, 4.24, 7.30), (7.00, 5.72, 9.70)],
}

# 旧版类别名兼容：dynamic 视同液压动密封
_GROOVE_ALIAS = {"dynamic": "hyd"}

# ---- 沟槽圆角与导入倒角（GB/T 3452.3-2005 表1 / 表2 / 表3）----
# 槽底圆角 r1 按线径分档（标准只给了 3 档，按邻近原则选取）
_R1_BANDS = [("<=2.65", 0.20, 0.40), ("3.55~5.30", 0.40, 0.80), (">=7.00", 0.80, 1.20)]
# 槽口（棱）圆角 r2：标准全档统一
_R2_RANGE = (0.10, 0.30)
# 导入倒角角度：标准未给角度，行业通行 15°~30°（推荐 20°）
_LEAD_ANGLE_RANGE = (15.0, 30.0)
_LEAD_ANGLE_REC = 20.0
# 最小导角长度 Zmin（标准表1 明列，按线径取值，mm）
_LEAD_ZMIN = {1.80: 1.10, 2.65: 1.50, 3.55: 1.80, 5.30: 2.70, 7.00: 3.60}

# ---- 挡圈厚度占用（单侧一个挡圈的额外槽宽，mm）----
# 由标准表1 的 b → b1 → b2 差值得到：b1-b = b2-b1 = 该值，是标准给出的挡圈占位。
_BACKUP_ALLOWANCE = {1.80: 1.40, 2.65: 1.40, 3.55: 1.40, 5.30: 1.90, 7.00: 2.80}


def backup_width_allowance(d2: float) -> float:
    """单侧一个挡圈占用的额外槽宽（mm），取自标准表1 的 b1/b2 差值。"""
    xs = sorted(_BACKUP_ALLOWANCE)
    if d2 <= xs[0]:
        return _BACKUP_ALLOWANCE[xs[0]]
    if d2 >= xs[-1]:
        return _BACKUP_ALLOWANCE[xs[-1]]
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        if x1 <= d2 <= x2:
            k = (d2 - x1) / (x2 - x1)
            return round(_BACKUP_ALLOWANCE[x1]
                         + (_BACKUP_ALLOWANCE[x2] - _BACKUP_ALLOWANCE[x1]) * k, 2)
    return _BACKUP_ALLOWANCE[xs[-1]]


def edge_fillet_lead(d2: float) -> dict:
    """沟槽圆角与导入倒角推荐值（GB/T 3452.3-2005）。

    返回 dict：r1 槽底圆角、r2 槽口圆角、lead_angle 导入倒角角度、
    lead_zmin 最小导角长度、以及是否落在标准表内的标记。
    """
    if d2 <= 2.65:
        r1 = (0.20, 0.40)
    elif d2 <= 5.30:
        r1 = (0.40, 0.80)
    else:
        r1 = (0.80, 1.20)

    zs = sorted(_LEAD_ZMIN)
    if d2 <= zs[0]:
        zmin, zsrc = _LEAD_ZMIN[zs[0]], f"按最小档 d₂ {zs[0]:.2f} 取值"
    elif d2 >= zs[-1]:
        zmin, zsrc = _LEAD_ZMIN[zs[-1]], f"按最大档 d₂ {zs[-1]:.2f} 取值"
    else:
        zmin = None
        for i in range(len(zs) - 1):
            x1, x2 = zs[i], zs[i + 1]
            if x1 <= d2 <= x2:
                k = (d2 - x1) / (x2 - x1)
                zmin = round(_LEAD_ZMIN[x1] + (_LEAD_ZMIN[x2] - _LEAD_ZMIN[x1]) * k, 2)
                break
        zsrc = "插值"

    return {
        "r1": r1, "r2": _R2_RANGE,
        "lead_angle": _LEAD_ANGLE_RANGE, "lead_angle_rec": _LEAD_ANGLE_REC,
        "lead_zmin": zmin, "lead_zmin_src": zsrc,
        "in_table": 1.80 <= d2 <= 7.00,
    }

# 由标准表反算出的线径比例系数（参考值，用于结果说明）
_K_STATIC = 1.348   # b = K · d2
_K_DYNAMIC = 1.423
_K_AXIAL = 1.348
_E_STATIC = 0.2075  # 压缩率典型值
_E_DYNAMIC = 0.1547
_E_AXIAL = 0.2821


def groove_std_pair(d2: float, kind: str) -> tuple[float, float, str]:
    """按线径求标准槽深 / 槽宽。

    kind: 'static' 径向静密封 | 'hyd' 液压动密封 | 'pneu' 气动动密封 | 'axial' 轴向密封
          （旧名 'dynamic' 视同 'hyd'）
    返回 (h, b, 来源说明)
    """
    kind = _GROOVE_ALIAS.get(kind, kind)
    pts = _GROOVE_ANCHORS.get(kind) or _GROOVE_ANCHORS["static"]
    # 命中锚点
    for x, h, b in pts:
        if abs(x - d2) <= 1e-9:
            return h, b, "标准表值"
    # 两端外推
    if d2 < pts[0][0]:
        (x1, h1, b1), (x2, h2, b2) = pts[0], pts[1]
        src = "按线径外推"
    elif d2 > pts[-1][0]:
        (x1, h1, b1), (x2, h2, b2) = pts[-2], pts[-1]
        src = "按线径外推"
    else:
        src = "按线径插值"
        for i in range(len(pts) - 1):
            if pts[i][0] <= d2 <= pts[i + 1][0]:
                (x1, h1, b1), (x2, h2, b2) = pts[i], pts[i + 1]
                break
    k = (d2 - x1) / (x2 - x1)
    return h1 + (h2 - h1) * k, b1 + (b2 - b1) * k, src


def backup_ring_count(motion: str, is_axial: bool) -> int:
    """推荐挡圈数量。

    往复 / 回转密封为双作用，两侧各需一个挡圈；静密封按单侧受压取一个。
    """
    if is_axial:
        return 1
    if motion in ("往复", "回转"):
        return 2
    return 1


# ---- 允许挤出间隙（单侧，mm）----
# 行：邵氏 A 硬度；列：工作压力 MPa
_GAP_PRESSURES = [3.5, 7.0, 10.5, 14.0, 21.0, 35.0]
GAP_TABLE = {
    60: [0.20, 0.10, 0.05, None, None, None],
    70: [0.25, 0.15, 0.10, 0.05, None, None],
    80: [0.30, 0.20, 0.15, 0.10, 0.08, None],
    90: [0.40, 0.30, 0.20, 0.15, 0.10, 0.08],
    95: [0.50, 0.40, 0.30, 0.20, 0.15, 0.10],
}


def allowed_extrusion_gap(hardness: float, pressure: float) -> float | None:
    """按硬度与压力查允许的单侧挤出间隙。超出表范围返回 None。"""
    hs = sorted(GAP_TABLE)
    hs_lo = max([h for h in hs if h <= hardness], default=hs[0])
    hs_hi = min([h for h in hs if h >= hardness], default=hs[-1])
    n = len(_GAP_PRESSURES)
    idx = 0
    for i, p in enumerate(_GAP_PRESSURES):
        if pressure <= p:
            idx = i
            break
    else:
        return None  # 压力超表

    v_lo = GAP_TABLE[hs_lo][idx]
    v_hi = GAP_TABLE[hs_hi][idx]
    if v_lo is None and v_hi is None:
        return None
    if v_lo is None:
        return v_hi
    if v_hi is None:
        return v_lo
    if hs_hi == hs_lo:
        return v_lo
    r = (hardness - hs_lo) / (hs_hi - hs_lo)
    return round(v_lo + (v_hi - v_lo) * r, 3)


# =====================================================================
# 二、材料数据库
# =====================================================================

MEDIA_LIST = [
    "液压油（矿物基）", "气动 / 空气", "水 / 水-乙二醇", "蒸汽", "制动液 DOT3/DOT4",
    "汽油 / 燃油", "柴油 / 生物柴油", "磷酸酯液压油", "制冷剂 / HFC", "热水 / 饮用水",
    "强酸 / 强碱", "有机溶剂 / 酮 / 酯", "食品 / 医药级", "硅油 / 硅脂",
    "臭氧 / 户外老化", "真空", "氢气 / 天然气", "导热油 / 热油",
]


# =====================================================================
# 一·B、常用工况压力预设
# =====================================================================

_G = 9.80665          # 重力加速度 m/s²
RHO_WATER = 1000.0    # 水的密度 kg/m³


def water_depth_pressure(depth_m: float) -> float:
    """静水压力 MPa = ρgh。1 m 水深 ≈ 0.0098 MPa。"""
    return round(RHO_WATER * _G * depth_m / 1e6, 4)


def _depth_preset(m: float, motion: str | None = None,
                  medium: str = "水 / 水-乙二醇",
                  temp: tuple[int, int] = (5, 40)) -> dict:
    p = water_depth_pressure(m)
    return {
        "key": f"depth{m:g}",
        "group": "水深（静水压）",
        "label": f"水深 {m:g} m（≈ {p:.3f} MPa）",
        "p": p,
        "medium": medium,
        "motion": motion,
        "t": temp,
        "note": (f"按静水压 p = ρgh 计算（ρ=1000 kg/m³）：{m:g} m 水柱 ≈ {p:.3f} MPa。"
                 f"水深只决定压力，不决定运动方式——水下执行机构选「往复」，"
                 f"浸水壳体选「静态」，请按实际工况选择（见下方 IPX 预设）。"),
    }


def _ipx_preset(grade: str, m: float, desc: str) -> dict:
    """防水等级（IEC 60529 / GB/T 4208）对应的浸水静密封工况。"""
    p = water_depth_pressure(m)
    return {
        "key": f"ipx_{grade.lower()}_{m:g}",
        "group": "水下浸水（静密封）",
        "label": f"{grade}  {desc}（≈ {p:.3f} MPa）",
        "p": p,
        "medium": "水 / 水-乙二醇",
        "motion": "静态",
        "t": (5, 40),
        "note": (f"{grade} 按 IEC 60529 / GB/T 4208 定义，{m:g} m 水柱 ≈ {p:.3f} MPa。"
                 f"浸水防护属静密封工况，压缩率按 GB/T 3452.3 图A.3 静密封允许区间取值；"
                 f"深水或长期浸泡建议取区间上部，并加装挡圈抑制挤出。"),
    }


# 预设工况：一键带入压力（必要时同步介质 / 运动方式 / 温度）。
# 压力为表压；"通用公称压力" 取自 GB/T 2346 液压气动公称压力系列。
PRESSURE_PRESETS = [
    {
        "key": "manual", "group": "", "label": "手动输入（自定义工况）",
        "p": None, "medium": None, "motion": None, "t": None,
        "note": "直接在下面填写工作压力",
    },
    # ---------- 真空 / 微压 ----------
    {
        "key": "vacuum", "group": "真空微压", "label": "真空密封（表压 0 MPa）",
        "p": 0.0, "medium": "真空", "motion": "静态", "t": (20, 80),
        "note": "真空系统取表压 0 MPa，完全依靠预压缩量密封，推荐较低硬度胶料",
    },
    {
        "key": "air_low", "group": "真空微压", "label": "气体微压 0.1 MPa",
        "p": 0.1, "medium": "气动 / 空气", "motion": "静态", "t": (5, 60),
        "note": "仪表气、低压气路、密封腔体外壳",
    },
    # ---------- 气动 ----------
    {
        "key": "air_04", "group": "气动", "label": "气动系统 0.4 MPa",
        "p": 0.4, "medium": "气动 / 空气", "motion": "往复", "t": (5, 60),
        "note": "小型气缸 / 真空发生器常用压力",
    },
    {
        "key": "air_063", "group": "气动", "label": "气动系统 0.63 MPa",
        "p": 0.63, "medium": "气动 / 空气", "motion": "往复", "t": (5, 60),
        "note": "气动系统常用工作压力 0.5 ~ 0.7 MPa",
    },
    {
        "key": "air_10", "group": "气动", "label": "气动系统 1.0 MPa",
        "p": 1.0, "medium": "气动 / 空气", "motion": "往复", "t": (5, 60),
        "note": "高压气动 / 空压机排气口",
    },
    # ---------- 水深（只带入压力与介质，运动方式交给用户）----------
    _depth_preset(3),
    _depth_preset(5),
    _depth_preset(10),
    _depth_preset(20),
    _depth_preset(30),
    _depth_preset(50),
    _depth_preset(100),
    _depth_preset(300),
    # ---------- 水下浸水（IPX 防护等级，静密封）----------
    _ipx_preset("IPX7", 1.0, "短时浸水 1 m"),
    _ipx_preset("IPX8", 10.0, "持续浸水 10 m"),
    _ipx_preset("IPX8", 30.0, "持续浸水 30 m"),
    # ---------- 液压 ----------
    {
        "key": "hd_16", "group": "液压", "label": "液压 1.6 MPa（低压）",
        "p": 1.6, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 80),
        "note": "机床辅助回路、低压夹紧系统",
    },
    {
        "key": "hd_25", "group": "液压", "label": "液压 2.5 MPa",
        "p": 2.5, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 80),
        "note": "GB/T 2346 公称压力系列值",
    },
    {
        "key": "hd_63", "group": "液压", "label": "液压 6.3 MPa",
        "p": 6.3, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 80),
        "note": "中低压液压系统",
    },
    {
        "key": "hd_10", "group": "液压", "label": "液压 10 MPa",
        "p": 10.0, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 80),
        "note": "中压液压系统",
    },
    {
        "key": "hd_16m", "group": "液压", "label": "液压 16 MPa（工程机械常用）",
        "p": 16.0, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 80),
        "note": "挖掘机 / 装载机等中高压主油路",
    },
    {
        "key": "hd_25m", "group": "液压", "label": "液压 25 MPa",
        "p": 25.0, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 90),
        "note": "高压液压系统，必须配挡圈",
    },
    {
        "key": "hd_315", "group": "液压", "label": "液压 31.5 MPa（高压）",
        "p": 31.5, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 90),
        "note": "高压液压系统，需挡圈 + 高硬度胶料",
    },
    {
        "key": "hd_40", "group": "液压", "label": "液压 40 MPa（超高压）",
        "p": 40.0, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 90),
        "note": "超高压，建议组合密封或聚氨酯材质",
    },
    {
        "key": "hd_63m", "group": "液压", "label": "液压 63 MPa（超高压）",
        "p": 63.0, "medium": "液压油（矿物基）", "motion": "往复", "t": (20, 90),
        "note": "超高压，常规 O 圈已不适用，应选组合密封",
    },
    # ---------- 民用 ----------
    {
        "key": "tap", "group": "民用管路", "label": "自来水 / 给水管路 0.35 MPa",
        "p": 0.35, "medium": "热水 / 饮用水", "motion": "静态", "t": (5, 60),
        "note": "市政供水常规压力 0.2 ~ 0.4 MPa",
    },
    {
        "key": "hotwater", "group": "民用管路", "label": "热水 / 供暖循环 0.6 MPa",
        "p": 0.6, "medium": "热水 / 饮用水", "motion": "静态", "t": (20, 95),
        "note": "供暖与生活热水系统",
    },
    {
        "key": "brake", "group": "民用管路", "label": "液压制动系统 8 MPa",
        "p": 8.0, "medium": "制动液 DOT3/DOT4", "motion": "往复", "t": (-30, 120),
        "note": "汽车制动主缸 / 轮缸，必须使用 EPDM 胶料",
    },
]


def preset_by_key(key: str) -> dict | None:
    for it in PRESSURE_PRESETS:
        if it["key"] == key:
            return it
    return None


class Material:
    """一种密封橡胶材料。score: 0 不可用 → 5 优异。"""

    def __init__(self, code, name, tmin, tmax, hard_range, cost, media,
                 pros, cons, usage):
        self.code = code
        self.name = name
        self.tmin = tmin            # 长期最低工作温度 ℃
        self.tmax = tmax            # 长期最高工作温度 ℃
        self.hard_range = hard_range  # (min, max) 邵氏 A
        self.cost = cost            # 1 最便宜 → 5 最贵
        self.media = media          # dict: 介质 → 0..5
        self.pros = pros
        self.cons = cons
        self.usage = usage

    def __repr__(self):
        return f"<{self.code}>"


MATERIALS = [
    Material(
        "NBR", "丁腈橡胶", -40, 120, (50, 95), 1,
        {"液压油（矿物基）": 5, "气动 / 空气": 4, "水 / 水-乙二醇": 4, "蒸汽": 1,
         "制动液 DOT3/DOT4": 1, "汽油 / 燃油": 4, "柴油 / 生物柴油": 5,
         "磷酸酯液压油": 0, "制冷剂 / HFC": 3, "热水 / 饮用水": 3,
         "强酸 / 强碱": 2, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 2,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 1, "真空": 4,
         "氢气 / 天然气": 3, "导热油 / 热油": 4},
        "性价比最高；耐矿物油、液压油、动植物油、脂肪烃极佳；耐磨性好",
        "不耐酮、酯、磷酸酯液压油、强酸；耐臭氧与耐候性差，不宜户外长期使用",
        "液压系统、气动元件、油泵油缸、通用工业密封——绝大多数场合的首选",
    ),
    Material(
        "HNBR", "氢化丁腈橡胶", -40, 150, (60, 95), 3,
        {"液压油（矿物基）": 5, "气动 / 空气": 4, "水 / 水-乙二醇": 4, "蒸汽": 2,
         "制动液 DOT3/DOT4": 1, "汽油 / 燃油": 4, "柴油 / 生物柴油": 5,
         "磷酸酯液压油": 0, "制冷剂 / HFC": 4, "热水 / 饮用水": 4,
         "强酸 / 强碱": 2, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 2,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 4, "真空": 4,
         "氢气 / 天然气": 4, "导热油 / 热油": 4},
        "NBR 的强化版；耐温上限提高约 30 ℃，耐臭氧、耐老化、耐磨、抗挤出显著提升",
        "价格约为 NBR 的 2~3 倍；仍不耐磷酸酯与强极性溶剂",
        "汽车发动机舱、高压液压、油田钻具、需要长寿命或高温的场合",
    ),
    Material(
        "FKM", "氟橡胶 (Viton)", -20, 200, (60, 95), 4,
        {"液压油（矿物基）": 5, "气动 / 空气": 5, "水 / 水-乙二醇": 4, "蒸汽": 2,
         "制动液 DOT3/DOT4": 2, "汽油 / 燃油": 5, "柴油 / 生物柴油": 5,
         "磷酸酯液压油": 0, "制冷剂 / HFC": 4, "热水 / 饮用水": 3,
         "强酸 / 强碱": 4, "有机溶剂 / 酮 / 酯": 3, "食品 / 医药级": 4,
         "硅油 / 硅脂": 5, "臭氧 / 户外老化": 5, "真空": 5,
         "氢气 / 天然气": 4, "导热油 / 热油": 5},
        "耐高温与耐化学介质能力突出；耐燃油、芳香烃、氯化烃、强氧化剂；耐候极佳",
        "低温性能差（一般不低于 -20 ℃）；不耐酮、酯、氨与低分子有机酸；价格高",
        "汽车燃油系统、高温液压、化工设备、半导体、航天",
    ),
    Material(
        "FFKM", "全氟醚橡胶", -10, 320, (70, 95), 5,
        {"液压油（矿物基）": 5, "气动 / 空气": 5, "水 / 水-乙二醇": 5, "蒸汽": 4,
         "制动液 DOT3/DOT4": 5, "汽油 / 燃油": 5, "柴油 / 生物柴油": 5,
         "磷酸酯液压油": 4, "制冷剂 / HFC": 5, "热水 / 饮用水": 5,
         "强酸 / 强碱": 5, "有机溶剂 / 酮 / 酯": 5, "食品 / 医药级": 5,
         "硅油 / 硅脂": 5, "臭氧 / 户外老化": 5, "真空": 5,
         "氢气 / 天然气": 5, "导热油 / 热油": 5},
        "几乎耐受所有已知介质，耐温范围最宽；气体渗透率极低",
        "价格极其昂贵（普通 FKM 的 10~20 倍）；低温弹性一般",
        "半导体刻蚀设备、强腐蚀化工、航空航天、超高温超高压极端工况",
    ),
    Material(
        "EPDM", "三元乙丙橡胶", -50, 150, (50, 90), 2,
        {"液压油（矿物基）": 1, "气动 / 空气": 4, "水 / 水-乙二醇": 5, "蒸汽": 4,
         "制动液 DOT3/DOT4": 5, "汽油 / 燃油": 0, "柴油 / 生物柴油": 0,
         "磷酸酯液压油": 3, "制冷剂 / HFC": 4, "热水 / 饮用水": 5,
         "强酸 / 强碱": 5, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 4,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 5, "真空": 4,
         "氢气 / 天然气": 2, "导热油 / 热油": 0},
        "耐水、耐蒸汽、耐制动液、耐酮醇类极性溶剂极佳；耐候耐臭氧最好；价格低",
        "完全不耐矿物油、燃油、液压油与烃类溶剂——选错即为致命失效",
        "汽车制动系统、蒸汽阀门、热水管路、户外建筑密封、洗涤设备",
    ),
    Material(
        "VMQ", "硅橡胶", -60, 200, (40, 80), 2,
        {"液压油（矿物基）": 2, "气动 / 空气": 5, "水 / 水-乙二醇": 4, "蒸汽": 3,
         "制动液 DOT3/DOT4": 3, "汽油 / 燃油": 1, "柴油 / 生物柴油": 1,
         "磷酸酯液压油": 2, "制冷剂 / HFC": 4, "热水 / 饮用水": 3,
         "强酸 / 强碱": 3, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 5,
         "硅油 / 硅脂": 5, "臭氧 / 户外老化": 5, "真空": 5,
         "氢气 / 天然气": 2, "导热油 / 热油": 2},
        "使用温域最宽（-60~200 ℃）；耐候、耐臭氧、绝缘性好；无毒无味，食品级适用",
        "机械强度与耐磨性差；不耐油、不耐烃类溶剂；气体渗透率高",
        "低温环境、食品医药、家电、电子电气、医疗器械",
    ),
    Material(
        "FVMQ", "氟硅橡胶", -60, 175, (50, 85), 4,
        {"液压油（矿物基）": 4, "气动 / 空气": 5, "水 / 水-乙二醇": 4, "蒸汽": 2,
         "制动液 DOT3/DOT4": 3, "汽油 / 燃油": 4, "柴油 / 生物柴油": 4,
         "磷酸酯液压油": 1, "制冷剂 / HFC": 5, "热水 / 饮用水": 3,
         "强酸 / 强碱": 3, "有机溶剂 / 酮 / 酯": 2, "食品 / 医药级": 4,
         "硅油 / 硅脂": 5, "臭氧 / 户外老化": 5, "真空": 5,
         "氢气 / 天然气": 3, "导热油 / 热油": 4},
        "兼顾硅橡胶的宽温域与氟橡胶的耐油性；低温可达 -60 ℃",
        "耐温上限低于 FKM；机械强度一般；价格高",
        "航空燃油系统、低温液压、高低温交变的油介质密封",
    ),
    Material(
        "CR", "氯丁橡胶", -40, 120, (50, 90), 1,
        {"液压油（矿物基）": 3, "气动 / 空气": 4, "水 / 水-乙二醇": 4, "蒸汽": 2,
         "制动液 DOT3/DOT4": 2, "汽油 / 燃油": 2, "柴油 / 生物柴油": 3,
         "磷酸酯液压油": 1, "制冷剂 / HFC": 5, "热水 / 饮用水": 4,
         "强酸 / 强碱": 3, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 2,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 5, "真空": 3,
         "氢气 / 天然气": 3, "导热油 / 热油": 2},
        "耐候、耐臭氧、耐制冷剂（R22/R12）良好；阻燃；价格低",
        "耐油性中等，耐温不高；不耐芳香烃与酮酯",
        "制冷压缩机、冷冻设备、户外密封、阻燃要求场合",
    ),
    Material(
        "IIR", "丁基橡胶", -50, 110, (40, 80), 2,
        {"液压油（矿物基）": 2, "气动 / 空气": 5, "水 / 水-乙二醇": 4, "蒸汽": 3,
         "制动液 DOT3/DOT4": 3, "汽油 / 燃油": 1, "柴油 / 生物柴油": 2,
         "磷酸酯液压油": 0, "制冷剂 / HFC": 4, "热水 / 饮用水": 4,
         "强酸 / 强碱": 3, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 3,
         "硅油 / 硅脂": 2, "臭氧 / 户外老化": 4, "真空": 5,
         "氢气 / 天然气": 4, "导热油 / 热油": 1},
        "气密性在橡胶中最好，气体与蒸汽渗透率极低；耐真空、耐老化",
        "弹性与耐磨性差；不耐矿物油与芳香烃；回弹性低",
        "真空系统、气体密封、轮胎内胎、阻尼减震",
    ),
    Material(
        "PU", "聚氨酯橡胶", -30, 80, (70, 95), 3,
        {"液压油（矿物基）": 5, "气动 / 空气": 4, "水 / 水-乙二醇": 3, "蒸汽": 1,
         "制动液 DOT3/DOT4": 1, "汽油 / 燃油": 3, "柴油 / 生物柴油": 4,
         "磷酸酯液压油": 0, "制冷剂 / HFC": 3, "热水 / 饮用水": 1,
         "强酸 / 强碱": 3, "有机溶剂 / 酮 / 酯": 2, "食品 / 医药级": 3,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 4, "真空": 4,
         "氢气 / 天然气": 3, "导热油 / 热油": 3},
        "耐磨性与抗撕裂性在橡胶中最优；耐高压挤出能力强，动密封寿命长",
        "耐水解性差，不宜长期接触热水与蒸汽；耐温上限低（约 80 ℃）",
        "高压液压缸动密封、工程机械、气动执行元件、耐磨场合",
    ),
    Material(
        "ACM", "丙烯酸酯橡胶", -20, 150, (60, 90), 2,
        {"液压油（矿物基）": 5, "气动 / 空气": 4, "水 / 水-乙二醇": 1, "蒸汽": 1,
         "制动液 DOT3/DOT4": 1, "汽油 / 燃油": 3, "柴油 / 生物柴油": 4,
         "磷酸酯液压油": 3, "制冷剂 / HFC": 4, "热水 / 饮用水": 1,
         "强酸 / 强碱": 1, "有机溶剂 / 酮 / 酯": 1, "食品 / 医药级": 1,
         "硅油 / 硅脂": 3, "臭氧 / 户外老化": 4, "真空": 3,
         "氢气 / 天然气": 2, "导热油 / 热油": 5},
        "耐热油、耐齿轮油、耐极压添加剂性能好；耐高温老化；价格适中",
        "耐水性极差，遇水易水解；低温性能一般",
        "汽车变速箱、差速器、高温油封（不得接触水）",
    ),
    Material(
        "PTFE", "聚四氟乙烯", -60, 260, (55, 70), 4,
        {m: 5 for m in MEDIA_LIST},
        "化学惰性最强，几乎耐所有介质；摩擦系数极低；使用温域宽",
        "弹性差，需较大的初始压缩量或配弹簧；冷流性明显；加工成本高",
        "强腐蚀化学泵阀、极端介质、低摩擦要求场合（多为夹套或组合密封）",
    ),
]

MATERIAL_BY_CODE = {m.code: m for m in MATERIALS}


def recommend_materials(t_low: float, t_high: float, medium: str,
                        motion: str = "静态") -> list[dict]:
    """按温度区间与介质给出材料排序建议。

    返回按得分降序的列表，每项含 material / score / temp_ok / reason。
    """
    out = []
    for m in MATERIALS:
        temp_ok = (m.tmin <= t_low) and (m.tmax >= t_high)
        # 温度扣分
        if temp_ok:
            temp_pen = 0.0
        else:
            over = 0.0
            if t_low < m.tmin:
                over += (m.tmin - t_low) / 25.0
            if t_high > m.tmax:
                over += (t_high - m.tmax) / 25.0
            temp_pen = over

        med = m.media.get(medium, 2)
        score = med * 2.0 - temp_pen * 3.0 - (m.cost - 1) * 0.45

        # 动密封优先选耐磨材料
        if motion != "静态":
            if m.code in ("PU", "HNBR", "NBR", "FKM", "PTFE"):
                score += 0.6
            if m.code in ("VMQ", "IIR", "EPDM"):
                score -= 0.6
        if motion == "回转" and m.code == "PTFE":
            score += 0.3

        # PTFE 不是弹性体，作为普通 O 形圈使用必须借助弹簧或夹套结构，
        # 若用户未指定则不应该被排到前列
        if m.code == "PTFE":
            score -= 1.8

        reason = []
        reason.append(f"介质相容性 {'★' * med}{'☆' * (5 - med)}")
        if temp_ok:
            reason.append(f"温度 {m.tmin}~{m.tmax} ℃ 覆盖工况")
        else:
            reason.append(f"⚠ 温度超出 {m.tmin}~{m.tmax} ℃ 范围")

        out.append({
            "code": m.code,
            "name": m.name,
            "score": round(score, 2),
            "temp_ok": temp_ok,
            "temp_range": (m.tmin, m.tmax),
            "media_score": med,
            "cost": m.cost,
            "hard_range": m.hard_range,
            "reason": "；".join(reason),
            "pros": m.pros,
            "cons": m.cons,
            "usage": m.usage,
        })
    out.sort(key=lambda x: -x["score"])
    return out


# =====================================================================
# 二·五、壳体（沟槽）材料
# =====================================================================
# 壳体材料从三条途径影响 O 圈设计：
#   1. 线膨胀系数 α —— 温度变化时沟槽与 O 圈截面各自胀缩，压缩率随之漂移。
#      漂移量 Δε ≈ ΔT·(α_橡胶 − α_壳体)，橡胶 α 远大于金属/塑料，故通常为正值
#      （升温后压缩率变大）；α_壳体 越大，该漂移越小。塑料 α 大，温变时压缩率
#      反而比金属壳体更稳定，但塑料另有蠕变问题（见第 3 条）。
#   2. 弹性模量 E —— 塑料壳体刚度低，受压后沟槽变形张开间隙，挤出风险上升，
#      因此塑料壳体需要更严格的挤出间隙校核。
#   3. 蠕变 / 应力松弛 —— 塑料长期受压会失去部分压缩量，需提高初始压缩率补偿。
HOUSING_MATERIALS = [
    {"code": "steel", "name": "碳钢 / 合金钢", "group": "金属", "alpha": 11.7,
     "E": 206000, "ra": 1.6, "p_max": None,
     "note": "刚性好、沟槽尺寸稳定；需注意防锈与表面处理"},
    {"code": "ss", "name": "不锈钢 304 / 316", "group": "金属", "alpha": 17.3,
     "E": 193000, "ra": 1.6, "p_max": None,
     "note": "耐蚀；α 比碳钢大，温变大时压缩率漂移略小"},
    {"code": "al", "name": "铝合金 6061 / 7075", "group": "金属", "alpha": 23.6,
     "E": 69000, "ra": 1.6, "p_max": None,
     "note": "轻量、导热好；α 较大，阳极氧化面注意封孔"},
    {"code": "brass", "name": "黄铜 / 青铜", "group": "金属", "alpha": 19.0,
     "E": 100000, "ra": 1.6, "p_max": None,
     "note": "管接头、阀体常用；注意脱锌腐蚀"},
    {"code": "cast", "name": "铸铁", "group": "金属", "alpha": 10.5,
     "E": 120000, "ra": 3.2, "p_max": None,
     "note": "泵壳、阀体常用；表面较粗糙，沟槽需精加工"},
    {"code": "abs", "name": "ABS", "group": "塑料", "alpha": 85.0,
     "E": 2300, "ra": 1.6, "p_max": 2.5,
     "note": "易成型、成本低；强度与耐温一般"},
    {"code": "pc", "name": "PC（聚碳酸酯）", "group": "塑料", "alpha": 68.0,
     "E": 2400, "ra": 1.6, "p_max": 3.0,
     "note": "透明、抗冲击；长期浸水需注意水解老化"},
    {"code": "pom", "name": "POM（聚甲醛）", "group": "塑料", "alpha": 110.0,
     "E": 3000, "ra": 1.6, "p_max": 3.5,
     "note": "刚性好、耐磨；α 最大，温变时压缩率漂移最小"},
    {"code": "pa", "name": "PA66（尼龙）", "group": "塑料", "alpha": 90.0,
     "E": 2900, "ra": 1.6, "p_max": 3.0,
     "note": "韧性好；吸水性大，长期浸水尺寸会变化"},
    {"code": "pp", "name": "PP（聚丙烯）", "group": "塑料", "alpha": 120.0,
     "E": 1400, "ra": 1.6, "p_max": 2.0,
     "note": "耐化学性好；模量最低，受压变形最明显"},
]

HOUSING_BY_CODE = {m["code"]: m for m in HOUSING_MATERIALS}

# 橡胶线膨胀系数（1e-6/K）。橡胶的体积膨胀远大于线膨胀，工程近似取此值。
RUBBER_ALPHA = {"NBR": 180.0, "HNBR": 180.0, "FKM": 190.0, "FFKM": 190.0,
                "VMQ": 220.0, "EPDM": 200.0, "CR": 190.0, "PU": 180.0,
                "PTFE": 120.0, "AFLAS": 180.0, "IIR": 190.0, "ACM": 180.0}
RUBBER_ALPHA_DEFAULT = 180.0


def housing_effect(code: str, material_code: str,
                   t_high: float | None, pressure: float) -> dict:
    """壳体材料对压缩率与挤出间隙的影响。

    返回 dict：壳体信息、热漂移 Δε(百分点)、塑料补偿量、警告与说明。
    """
    h = HOUSING_BY_CODE.get(code or "")
    if h is None:
        return {"code": None, "group": None, "d_comp_pp": 0.0,
                "creep_pp": 0.0, "warnings": [], "notes": []}

    warnings: list[str] = []
    notes: list[str] = []
    ar = RUBBER_ALPHA.get(material_code, RUBBER_ALPHA_DEFAULT)
    ah = h["alpha"]

    dT = 0.0
    if t_high is not None:
        dT = max(0.0, float(t_high) - 20.0)
    d_comp = dT * (ar - ah) * 1e-6 * 100.0

    creep = 0.0
    if h["group"] == "塑料":
        creep = 1.5
        notes.append(
            f"壳体为塑料（{h['name']}），长期受压会产生蠕变与应力松弛，"
            f"已提出 {creep:.1f} 个百分点的压缩率补偿；该项与静密封、压力等修正"
            f"合并计算，并受「至多占用至允许上限余量的一半」约束，"
            f"实际取值见「压缩率依据」。")
        pmax = h["p_max"]
        if pmax is not None and pressure > pmax:
            warnings.append(
                f"壳体材料 {h['name']} 弹性模量仅 {h['E']} MPa，在 {pressure:.1f} MPa 下"
                f"壳体与沟槽会明显变形（经验建议 ≤ {pmax:.1f} MPa），间隙张开后 O 圈"
                f"挤出风险高：建议改用金属壳体、加装挡圈，或增加壁厚 / 加金属嵌件增强。")
        if pressure > 0.5:
            notes.append(
                "塑料壳体受压时沟槽会弹性变形并张开间隙，请按更严格的挤出间隙校核，"
                "必要时加装挡圈。")
        if t_high is not None and t_high > 120:
            notes.append(
                "塑料壳体的耐温远低于氟 / 硅橡胶，高温下壳体软化可能先于密封圈失效，"
                "请核对壳体材料的连续使用温度。")

    if dT > 0:
        notes.append(
            f"由 20 ℃ 升至 {t_high:.0f} ℃，橡胶与壳体线膨胀系数之差使压缩率漂移约 "
            f"{d_comp:+.2f} 个百分点（橡胶 {ar:.0f}×10⁻⁶/K vs 壳体 {ah:.1f}×10⁻⁶/K）。")

    return {
        "code": h["code"], "name": h["name"], "group": h["group"],
        "alpha": ah, "E": h["E"], "ra": h["ra"], "p_max": h["p_max"],
        "rubber_alpha": ar, "dT": round(dT, 1), "d_comp_pp": round(d_comp, 2),
        "creep_pp": creep, "note": h["note"],
        "warnings": warnings, "notes": notes,
    }


# =====================================================================
# 三、硬度与压缩率推荐
# =====================================================================

def recommend_hardness(pressure: float, motion: str, medium: str,
                       material: str) -> tuple[int, str]:
    """返回 (推荐邵氏 A 硬度, 说明)。"""
    if pressure < 0.0:
        pressure = 0.0

    if pressure <= 1.6:
        base, why = 60, "真空 / 微压工况，软胶贴合性更好"
    elif pressure <= 6.0:
        base, why = 70, "中低压通用工况"
    elif pressure <= 16.0:
        base, why = 80, "中高压，需较强的抗挤出能力"
    elif pressure <= 32.0:
        base, why = 90, "高压，必须配合挡圈使用"
    else:
        base, why = 95, "超高压，必须配合挡圈，必要时选聚氨酯或组合密封"

    if motion == "往复":
        base = max(base, 80)
        why += "；往复动密封提高硬度以抗磨损"
    elif motion == "回转":
        base = max(base, 80)
        why += "；回转动密封提高硬度以抵抗摩擦生热变形"
    elif motion == "静态":
        base = min(base, 90)

    # 介质对硬度的影响
    if medium in ("气动 / 空气", "真空") and pressure <= 1.6:
        base = min(base, 60)

    base = int(max(40, min(95, base)))
    return base, why


# ---- 压缩率允许范围（%）—— GB/T 3452.3-2005 附录 A ----
# 标准按「工况类别 × 线径」给出允许区间，而不是一个与线径无关的固定百分比；
# 静密封整体高于动密封，且线径越大允许区间越低。
#   hyd    图A.1 液压动密封
#   pneu   图A.2 气动动密封
#   static 图A.3 液压、气动静密封
#   axial  图A.4 轴向密封
COMPRESSION_TABLE = {
    "hyd": {
        1.80: (13.0, 28.5), 2.65: (11.5, 24.0), 3.55: (9.5, 23.0),
        5.30: (9.0, 20.5), 7.00: (9.0, 19.5),
    },
    "pneu": {
        1.80: (9.5, 25.5), 2.65: (8.5, 22.0), 3.55: (6.5, 20.0),
        5.30: (5.5, 17.0), 7.00: (5.0, 15.5),
    },
    "static": {
        1.80: (13.5, 30.5), 2.65: (13.0, 28.0), 3.55: (11.5, 27.5),
        5.30: (11.0, 26.0), 7.00: (10.5, 24.0),
    },
    "axial": {
        1.80: (22.5, 34.5), 2.65: (21.0, 30.0), 3.55: (19.0, 26.0),
        5.30: (16.0, 24.0), 7.00: (15.0, 21.0),
    },
}

COMPRESSION_KIND_NAME = {
    "hyd": "图A.1 液压动密封",
    "pneu": "图A.2 气动动密封",
    "static": "图A.3 液压、气动静密封",
    "axial": "图A.4 轴向密封",
}

# 压缩率类别与沟槽锚点表使用同一套键名（static / hyd / pneu / axial），无需映射。


def compression_kind(mode: str, motion: str, medium: str = "") -> str:
    """判定该工况应查 GB/T 3452.3-2005 附录 A 的哪张压缩率表。

    回转密封标准未单列，按动密封里最低的一档（气动动密封）从严取值。
    """
    if mode == "axial":
        return "axial"
    if motion == "静态":
        return "static"
    if any(k in (medium or "") for k in ("气", "真空", "空气")):
        return "pneu"
    return "hyd"


def compression_band(d2: float, kind: str) -> tuple[float, float, str]:
    """按线径返回压缩率允许区间 (min%, max%, 来源说明)。

    标准附录 A 只列出 1.80 / 2.65 / 3.55 / 5.30 / 7.00 五档线径；
    其余线径在相邻两档之间线性插值，超出两端时收敛到最近档（不作外推）。
    """
    tbl = COMPRESSION_TABLE.get(kind) or COMPRESSION_TABLE["static"]
    xs = sorted(tbl)
    nm = COMPRESSION_KIND_NAME.get(kind, kind)
    if d2 <= xs[0]:
        lo, hi = tbl[xs[0]]
        return lo, hi, f"GB/T 3452.3-2005 {nm}（按最小档 d₂ {xs[0]:.2f} 取值）"
    if d2 >= xs[-1]:
        lo, hi = tbl[xs[-1]]
        return lo, hi, f"GB/T 3452.3-2005 {nm}（按最大档 d₂ {xs[-1]:.2f} 取值）"
    for i in range(len(xs) - 1):
        x1, x2 = xs[i], xs[i + 1]
        if x1 <= d2 <= x2:
            k = (d2 - x1) / (x2 - x1)
            lo = tbl[x1][0] + (tbl[x2][0] - tbl[x1][0]) * k
            hi = tbl[x1][1] + (tbl[x2][1] - tbl[x1][1]) * k
            if k <= 1e-9 or k >= 1.0 - 1e-9:
                return round(lo, 2), round(hi, 2), f"GB/T 3452.3-2005 {nm}"
            return round(lo, 2), round(hi, 2), (
                f"GB/T 3452.3-2005 {nm}（按 d₂ {x1:.2f}~{x2:.2f} 插值）")
    lo, hi = tbl[xs[-1]]
    return lo, hi, f"GB/T 3452.3-2005 {nm}"


def recommend_compression(mode: str, motion: str, pressure: float,
                          hardness: int, d2: float = 3.55,
                          medium: str = "",
                          creep_pp: float = 0.0) -> tuple[float, str]:
    """返回 (推荐压缩率 %, 说明)。

    取值逻辑分三步：
      1) 以国标附录 A 的允许区间为边界，以**标准沟槽深度隐含的压缩率**作基准，
         保证推荐值与 GB/T 3452.3 表1/表2/表3 的沟槽尺寸互相自洽；
      2) 按运动方式 / 压力 / 硬度 / 壳体蠕变累加修正量；
      3) 修正量之和受「余量上限」约束 —— **最多占用基准到允许上限之间余量的一半**。
         这一步是必要的：静密封本来就在区间偏上（如 d₂ 1.80 的标准槽深已到 26.7%，
         而允许上限 30.5%），若各路修正无约束地叠加，任何工况都会顶死上限，
         热膨胀、公差与胶料溶胀就没有余量了。

    mode: radial / axial
    creep_pp: 塑料壳体的蠕变 / 应力松弛补偿（百分点），由 housing_effect 给出
    """
    kind = compression_kind(mode, motion, medium)
    lo, hi, src = compression_band(d2, kind)
    half = (hi - lo) / 2.0

    # 基准：标准沟槽深度对应的压缩率
    h_std, _b_std, _s = groove_std_pair(d2, kind)
    e_std = (d2 - h_std) / d2 * 100.0
    base = max(lo, min(hi, e_std))

    why = f"{src} 允许 {lo:.1f}%~{hi:.1f}%"
    why += f"；标准槽深 {h_std:.2f} mm 对应 {e_std:.1f}%，以此为基准"
    if e_std > hi + 0.05 or e_std < lo - 0.05:
        why += "（注意：该档标准槽深与压缩率表略有出入，已按允许区间收口，建议对照标准原文复核）"

    delta = 0.0
    parts: list[str] = []

    if kind in ("static", "axial"):
        delta += 0.10 * half
        parts.append("静密封取中偏上以建立可靠的初始接触应力")
    else:
        delta -= 0.05 * half
        parts.append("动密封取中偏下以减小摩擦与发热")
        if motion == "回转":
            parts.append("回转工况附录 A 未单列，已按动密封从严取值")

    if pressure > 20.0:
        delta += 0.15 * half
        parts.append("高压工况向区间上部靠拢以补偿挤出变形")
    elif pressure < 2.0:
        delta += 0.10 * half
        parts.append("低压 / 浸水工况向区间上部靠拢以保证初始密封")

    if hardness >= 90:
        delta += 0.5
        parts.append("高硬度胶料回弹差，压缩率略增")

    if creep_pp:
        delta += float(creep_pp)
        parts.append(f"塑料壳体蠕变 / 应力松弛补偿 {creep_pp:+.1f} 个百分点")

    # 余量约束：修正量最多占用「基准 → 允许上限」余量的一半
    room = max(0.0, hi - base)
    cap = 0.5 * room
    if delta > cap:
        parts.append(
            f"以上修正合计本为 {delta:+.2f} 个百分点，受「至多占用至允许上限余量的一半」"
            f"约束收口至 {cap:+.2f}，距允许上限仍留 {hi - (base + cap):.2f} 个百分点"
            f"供热膨胀、公差与胶料溶胀使用")
        delta = cap

    base = max(lo, min(hi, base + delta))
    if parts:
        why += "；" + "；".join(parts)

    return round(base, 2), why


# =====================================================================
# 四、线径与标准件选取
# =====================================================================

def recommend_d2(surface_dia: float, pressure: float, mode: str) -> float:
    """按密封面直径与压力推荐线径。"""
    d = abs(surface_dia)
    # 直径分档
    if d <= 20:
        base = 1.80
    elif d <= 50:
        base = 2.65
    elif d <= 120:
        base = 3.55
    elif d <= 250:
        base = 5.30
    else:
        base = 7.00

    # 轴向密封线径的选取与径向略有不同，压力影响更显著
    if mode == "axial":
        if pressure > 10.0 and base < 3.55:
            base = 3.55
        if pressure > 25.0 and base < 5.30:
            base = 5.30
    else:
        if pressure >= 20.0 and base < 3.55:
            base = 3.55
        elif pressure >= 10.0 and base < 2.65:
            base = 2.65
    return base


def d1_range(d2: float) -> tuple[float, float]:
    """给定线径时，标准内径系列的适用范围 (下限, 上限)。"""
    if d2 <= 1.90:
        return 3.0, 130.0
    if d2 <= 2.80:
        return 5.0, 220.0
    if d2 <= 3.70:
        return 7.0, 320.0
    if d2 <= 5.50:
        return 12.0, 520.0
    return 20.0, 900.0


def nearest_d1(target: float, d2: float) -> float:
    """在标准内径系列中选取最接近 target 的规格，并考虑 d2 的适用范围。"""
    lo, hi = d1_range(d2)
    cands = [x for x in D1_SERIES if lo <= x <= hi]
    if not cands:
        cands = D1_SERIES
    return min(cands, key=lambda x: abs(x - target))


def d1_candidates(target: float, d2: float, span: float = 0.0, count: int = 3):
    """返回最接近的若干标准内径（用于让用户自行取舍）。"""
    lo, hi = d1_range(d2)
    cands = sorted([x for x in D1_SERIES if lo <= x <= hi], key=lambda x: abs(x - target))
    return cands[:count]


def select_d1(groove_ref: float, d2: float, e_target: float, e_max: float,
              e_min: float = -0.5) -> tuple[float, float, str | None]:
    """在标准内径系列中挑选最合适的 O 圈内径。

    groove_ref : O 圈需要套装到的直径（活塞/活塞杆密封即槽底径）
    e_target   : 理想内径拉伸率 %
    e_max      : 允许最大拉伸率 %
    e_min      : 允许的最小拉伸率（负值代表内径略大于槽底，属轻微松装）
    返回 (选定内径, 实际拉伸率 %, 提示信息或 None)
    """
    cands = d1_candidates(groove_ref, d2, count=40)
    ok = []
    for c in cands:
        st = (groove_ref - c) / c * 100.0
        if e_min <= st <= e_max:
            ok.append((c, st))
    if ok:
        c, st = min(ok, key=lambda t: abs(t[1] - e_target))
        return c, st, None
    c = min(cands, key=lambda x: abs((groove_ref - x) / x * 100.0))
    st = (groove_ref - c) / c * 100.0
    return c, st, ("标准内径系列中没有任何规格的拉伸率落在 %.1f%% ~ %.1f%% 区间内，"
                   "已选取拉伸率最接近的规格" % (e_min, e_max))


def select_d1_axial(dm: float, d2: float, e_target: float, e_max: float,
                    e_min: float = -1.0) -> tuple[float, float, str | None]:
    """轴向端面密封按「自由中径 = d1 + d2 与沟槽中心直径对齐」选取内径。"""
    cands = d1_candidates(dm - d2, d2, count=40)
    ok = []
    for c in cands:
        mid = c + d2
        st = (dm - mid) / mid * 100.0
        if e_min <= st <= e_max:
            ok.append((c, st))
    if ok:
        c, st = min(ok, key=lambda t: abs(t[1] - e_target))
        return c, st, None
    c = min(cands, key=lambda x: abs((dm - (x + d2)) / (x + d2) * 100.0))
    mid = c + d2
    st = (dm - mid) / mid * 100.0
    return c, st, ("标准内径系列中没有任何规格的中径拉伸率落在 %.1f%% ~ %.1f%% 区间内，"
                   "已选取最接近的规格" % (e_min, e_max))


# =====================================================================
# 五、沟槽尺寸解算
# =====================================================================

def groove_dims(d2: float, mode: str, motion: str,
                compression_pct: float | None = None,
                width: float | None = None,
                t_high: float | None = None,
                backup_n: int = 0,
                medium: str = "") -> dict:
    """解算槽深 h 与槽宽 b。

    mode: 'radial' | 'axial'
    motion: '静态' | '往复' | '回转'
    若 compression_pct 为 None → 采用标准表值；否则按压缩率反算槽深。
    若 width 为 None → 由标准锚点表按线径插值推荐槽宽（含高温与挡圈修正）。

    backup_n: 需要额外占位的挡圈数量（0 = 不加挡圈）
    """
    kind = compression_kind(mode, motion, medium)

    # ---- 标准锚点表按线径插值 ----
    h_std, b_std, b_std_src = groove_std_pair(d2, kind)

    # ---- 槽深 ----
    if compression_pct is None:
        h = h_std
        e_used = (d2 - h) / d2 * 100.0
        h_src = f"标准推荐值（{b_std_src}）"
    else:
        e_used = float(compression_pct)
        h = d2 * (1.0 - e_used / 100.0)
        h_src = "按压缩率反算"

    # ---- 高温修正：橡胶热膨胀需要额外沟槽空间 ----
    k_temp = 1.0
    temp_note = None
    if t_high is not None and t_high > 100.0:
        k_temp = 1.0 + min(0.05, 0.0008 * (t_high - 100.0))
        temp_note = (f"工作温度 {t_high:.0f} ℃ > 100 ℃，槽宽按 {k_temp:.3f} 系数放大"
                     f"以容纳胶料热膨胀")

    # ---- 挡圈占位 ----
    b_backup = 0.0
    if backup_n > 0:
        b_backup = backup_width_allowance(d2) * backup_n

    if width is None:
        b = b_std * k_temp + b_backup
        b_base = b - b_backup
        if backup_n > 0:
            b_src = f"标准推荐值 + {backup_n} 个挡圈占位"
        elif k_temp > 1.0:
            b_src = "标准推荐值（含高温修正）"
        else:
            b_src = f"标准推荐值（{b_std_src}）"
    else:
        b = float(width)
        b_base = b - b_backup
        b_src = "手动指定"
    b_auto = b_std * k_temp + b_backup

    return {
        "h": h, "b": b,
        "h_std": h_std, "b_std": b_std, "b_auto": b_auto,
        "b_base": b_base, "b_backup": b_backup, "backup_n": backup_n,
        "h_src": h_src, "b_src": b_src,
        "compression_used": e_used,
        "temp_factor": k_temp, "temp_note": temp_note,
        "kind": kind,
    }


# =====================================================================
# 六、主解算入口
# =====================================================================

class DesignError(ValueError):
    pass


def design(mode: str,
           surface_dia: float,
           pressure: float,
           t_low: float,
           t_high: float,
           medium: str,
           motion: str = "静态",
           d2: float | None = None,
           compression_pct: float | None = None,
           groove_width: float | None = None,
           hardness: int | None = None,
           material: str | None = None,
           stretch_pct: float | None = None,
           backup_mode: str = "auto",
           clearance: float | None = None,
           housing: str | None = None) -> dict:
    """统一设计解算入口。

    mode:
      'radial_piston' 径向·活塞密封（O 圈装在活塞上，外径密封缸孔）
      'radial_rod'    径向·活塞杆密封（O 圈装在缸头沟槽内，内径密封活塞杆）
      'axial'         轴向·端面静密封

    surface_dia:
      radial_piston → 缸孔直径 D
      radial_rod    → 活塞杆直径 d
      axial         → 沟槽中心直径 dm

    backup_mode:
      'auto'   自动判定是否需要挡圈（默认）
      'none'   不加挡圈
      'single' 单侧挡圈
      'double' 两侧各一个挡圈
    """
    if mode not in ("radial_piston", "radial_rod", "axial"):
        raise DesignError("未知的密封型式")
    if backup_mode not in ("auto", "none", "single", "double"):
        raise DesignError("挡圈配置参数不合法")
    if surface_dia <= 0:
        raise DesignError("密封面直径必须为正数")
    if pressure < 0:
        raise DesignError("工作压力不能为负数")
    if t_high < t_low:
        raise DesignError("最高温度不能低于最低温度")

    is_axial = mode == "axial"
    calc_mode = "axial" if is_axial else "radial"
    warnings: list[str] = []
    notes: list[str] = []

    # ---------- 1. 线径 ----------
    if d2 is None or d2 <= 0:
        d2 = recommend_d2(surface_dia, pressure, calc_mode)
        d2_src = "自动推荐"
    else:
        if not (D2_MIN <= d2 <= D2_MAX):
            raise DesignError(f"线径应在 {D2_MIN:.2f} ~ {D2_MAX:.2f} mm 之间")
        std_d2, tag = d2_family(d2)
        if std_d2 is None:
            d2_src = "手动指定（自定义线径）"
        else:
            d2_src = f"手动指定（{tag}系列）"

    # ---------- 2. 材料 / 硬度 ----------
    mat_rank = recommend_materials(t_low, t_high, medium, motion)
    if material is None:
        material = mat_rank[0]["code"]
    mat_obj = MATERIAL_BY_CODE.get(material)
    if mat_obj is None:
        raise DesignError(f"未知材料代号：{material}")

    if hardness is None:
        hardness, hard_why = recommend_hardness(pressure, motion, medium, material)
        hardness_src = "自动推荐"
    else:
        hardness_src = "手动指定"
        hard_why = "由用户指定"
    hardness = int(max(30, min(98, hardness)))

    if not (mat_obj.hard_range[0] <= hardness <= mat_obj.hard_range[1]):
        warnings.append(
            f"{mat_obj.code} 常规硬度区间为 {mat_obj.hard_range[0]}~"
            f"{mat_obj.hard_range[1]} 邵氏 A，当前选定 {hardness} A 偏离该范围，"
            f"需与供应商确认可行性。"
        )

    # ---------- 3. 壳体（沟槽）材料影响 ----------
    # 必须排在压缩率之前：塑料壳体的蠕变补偿要作为一项修正参与压缩率推荐，
    # 才能被统一的「余量上限」约束一起收口，而不是事后另行上浮顶到区间上限。
    he = housing_effect(housing, material, t_high, pressure)
    if he.get("code"):
        notes.extend(he["notes"])
        warnings.extend(he["warnings"])

    # ---------- 3b. 压缩率 ----------
    comp_kind = compression_kind(calc_mode, motion, medium)
    comp_lo, comp_hi, comp_rule = compression_band(d2, comp_kind)
    if compression_pct is None:
        compression_pct, comp_why = recommend_compression(
            calc_mode, motion, pressure, hardness, d2=d2, medium=medium,
            creep_pp=he.get("creep_pp", 0.0))
        comp_src = "自动推荐"
    else:
        comp_src = "手动指定"
        comp_why = f"由用户指定；{comp_rule} 允许 {comp_lo:.1f}%~{comp_hi:.1f}%"

    # ---------- 4. 挡圈判定（须在沟槽宽度解算之前，挡圈要占用槽宽）----------
    gap_allow = allowed_extrusion_gap(hardness, pressure)
    need_backup = False
    if gap_allow is None and pressure > 0.5:
        warnings.append(
            f"工作压力 {pressure:.1f} MPa 超出所选硬度 {hardness} A 的可靠工作范围，"
            f"必须设置挡圈（Backup Ring）并考虑使用更高硬度胶料或组合密封。"
        )
        need_backup = True
    if clearance is not None and gap_allow is not None and pressure > 0.5:
        if clearance > gap_allow:
            warnings.append(
                f"设计单侧间隙 {clearance:.3f} mm 大于硬度 {hardness} A 在 "
                f"{pressure:.1f} MPa 下的允许挤出间隙 {gap_allow:.3f} mm，"
                f"存在胶料被挤入间隙而咬伤的风险，务必加装挡圈或减小间隙。"
            )
            need_backup = True

    if pressure > 10.0:
        need_backup = True
        notes.append("工作压力 > 10 MPa，建议配置挡圈以抑制 O 圈挤出。")

    auto_n = backup_ring_count(motion, is_axial)
    if backup_mode == "auto":
        backup_n = auto_n if need_backup else 0
        backup_src = f"自动判定（{backup_n} 个）" if need_backup else "自动判定（不需要）"
    elif backup_mode == "none":
        backup_n = 0
        backup_src = "手动指定：不加挡圈"
        if need_backup:
            warnings.append(
                "按压力 / 间隙评估本工况需要挡圈，当前手动设置为不加挡圈，"
                "请确认挤出间隙已足够小或已改用更高硬度胶料。"
            )
    else:
        backup_n = 1 if backup_mode == "single" else max(auto_n, 2)
        backup_src = "手动指定：单侧挡圈" if backup_n == 1 else "手动指定：两侧各一挡圈"
        if not need_backup and pressure <= 6.0:
            notes.append(
                f"工作压力较低（{pressure:.1f} MPa），加装 {backup_n} 个挡圈会占用槽宽，"
                f"若仅按标准低压工况设计可不加挡圈。"
            )

    # ---------- 5. 沟槽 ----------
    gv = groove_dims(d2, calc_mode, motion,
                     compression_pct=compression_pct,
                     width=groove_width, t_high=t_high,
                     backup_n=backup_n, medium=medium)
    h = gv["h"]
    b = gv["b"]
    if gv["temp_note"]:
        notes.append(gv["temp_note"])
    if backup_n > 0 and groove_width is None:
        notes.append(
            f"槽宽已按标准值计入 {backup_n} 个挡圈的占位宽度 "
            f"{gv['b_backup']:.2f} mm（挡圈厚度按线径估算），"
            f"实际订货槽宽请以挡圈供应商样本复核。"
        )

    if h >= d2:
        raise DesignError("槽深不得大于线径，请检查压缩率")
    if b <= 0:
        raise DesignError("槽宽必须为正数")

    comp_mm = d2 - h
    comp_pct = comp_mm / d2 * 100.0

    # ---------- 6. 按型式解算几何 ----------
    # 内径拉伸率的目标值 / 允许上限
    if motion == "静态":
        e_target, e_max = 2.0, 5.0
    elif motion == "往复":
        e_target, e_max = 2.5, 4.0
    else:
        e_target, e_max = 1.5, 3.0

    select_note = None
    if stretch_pct is None:
        st_src = "自动推荐"
        manual_stretch = False
    else:
        st_src = "手动指定"
        manual_stretch = True

    if mode == "radial_piston":
        # 缸孔 D，沟槽开在活塞外圆上；O 圈套在槽底径上向外密封
        bore = surface_dia
        if h * 2 >= bore:
            raise DesignError("槽深过大，缸孔直径不足以容下沟槽")
        groove_bottom = bore - 2 * h           # 槽底直径 d3
        groove_outer = bore                    # 沟槽外缘 = 缸孔

        if manual_stretch:
            want = groove_bottom / (1 + stretch_pct / 100.0)
            d1_std = nearest_d1(want, d2)
        else:
            d1_std, _st, select_note = select_d1(groove_bottom, d2, e_target, e_max)
        actual_stretch = (groove_bottom - d1_std) / d1_std * 100.0
        # 装配后（O 圈撑在槽底径上）外径理论值，及拉伸导致的截面减薄修正
        installed_od = groove_bottom + 2 * d2
        thin = 1 / math.sqrt(1 + max(actual_stretch, 0) / 100.0)
        installed_od_corr = groove_bottom + 2 * d2 * thin
        interference = (installed_od - bore) / 2.0
        geom = {
            "surface_label": "缸孔直径 D", "surface": bore,
            "groove_bottom": groove_bottom,
            "groove_bottom_label": "槽底直径 d3",
            "groove_outer": groove_outer,
            "groove_outer_label": "沟槽外缘（缸孔）",
        }
        fit = {
            "kind": "外径密封",
            "installed_label": "装配后外径",
            "installed": installed_od,
            "installed_corr": installed_od_corr,
            "seal_surface_label": "缸孔内壁",
            "seal_surface": bore,
            "interference": interference,
            "thin_factor": thin,
        }

    elif mode == "radial_rod":
        # 活塞杆 d，沟槽开在缸头/端盖内孔上；O 圈被压向杆面实现内径密封
        rod = surface_dia
        groove_bottom = rod + 2 * h            # 沟槽底径 D3
        groove_outer = rod                     # 沟槽内缘 = 杆孔

        if manual_stretch:
            want = groove_bottom / (1 + stretch_pct / 100.0)
            d1_std = nearest_d1(want, d2)
        else:
            d1_std, _st, select_note = select_d1(groove_bottom, d2, e_target, e_max)
        actual_stretch = (groove_bottom - d1_std) / d1_std * 100.0
        installed_id = groove_bottom - 2 * d2
        thin = 1 / math.sqrt(1 + max(actual_stretch, 0) / 100.0)
        installed_id_corr = groove_bottom - 2 * d2 * thin
        interference = (rod - installed_id) / 2.0
        geom = {
            "surface_label": "活塞杆直径 d", "surface": rod,
            "groove_bottom": groove_bottom,
            "groove_bottom_label": "沟槽底径 D3",
            "groove_outer": groove_outer,
            "groove_outer_label": "沟槽内缘（杆孔）",
        }
        fit = {
            "kind": "内径密封",
            "installed_label": "装配后内径",
            "installed": installed_id,
            "installed_corr": installed_id_corr,
            "seal_surface_label": "活塞杆外圆",
            "seal_surface": rod,
            "interference": interference,
            "thin_factor": thin,
        }

    else:
        # 轴向端面密封：以沟槽中心直径 dm 为输入
        dm = surface_dia
        if b * 2 >= dm:
            raise DesignError("槽宽过大，沟槽中心直径不足以容下沟槽")
        groove_inner = dm - b                  # 沟槽内径 d4
        groove_outer = dm + b                  # 沟槽外径 d5

        if manual_stretch:
            mid_want = dm / (1 + stretch_pct / 100.0)
            d1_std = nearest_d1(mid_want - d2, d2)
        else:
            d1_std, _st, select_note = select_d1_axial(dm, d2, 1.5, 3.0)
        free_mid = d1_std + d2
        actual_stretch = (dm - free_mid) / free_mid * 100.0
        geom = {
            "surface_label": "沟槽中心直径 dm", "surface": dm,
            "groove_bottom": groove_inner,
            "groove_bottom_label": "沟槽内径 d4",
            "groove_outer": groove_outer,
            "groove_outer_label": "沟槽外径 d5",
        }
        fit = {
            "kind": "端面密封",
            "installed_label": "装配后截面高度",
            "installed": h,
            "installed_corr": h,
            "seal_surface_label": "法兰压紧面",
            "seal_surface": dm,
            "interference": d2 - h,
            "thin_factor": 1.0,
        }

    if select_note:
        warnings.append(select_note)
    d0_std = d1_std + 2 * d2
    # 理想内径：径向密封为槽底径（O 圈套在其上）；轴向为「中心径 − 线径」
    d1_ideal = geom["groove_bottom"] if not is_axial else geom["surface"] - d2

    # ---------- 6b. 拉伸量 / 截面减薄 / 实际（减薄后）压缩量 ----------
    # 橡胶近似体积不可压：内径被撑大 ε 后，线径按 1/√(1+ε) 减薄、截面变小，
    # 于是「装配时真正压进去的量」比名义值 (d2 − h) 小。这一层以前只用于修正
    # 装配后外径，没有进指标卡，容易被误读成压缩率偏大。
    thin = 1.0 / math.sqrt(1.0 + max(actual_stretch, 0.0) / 100.0)
    cord_loaded = d2 * thin                      # 拉伸后的实际线径
    comp_mm_corr = cord_loaded - h               # 拉伸减薄后的实际压缩量
    comp_pct_corr = comp_mm_corr / cord_loaded * 100.0
    if is_axial:
        stretch_ref, stretch_ref_label = geom["surface"], "沟槽中心直径 dm"
        stretch_mm = geom["surface"] - (d1_std + d2)      # 自由中径的增量
    else:
        stretch_ref, stretch_ref_label = geom["groove_bottom"], "槽底直径"
        stretch_mm = geom["groove_bottom"] - d1_std       # 内径的增量
    if thin < 0.999:
        notes.append(
            f"O 圈内径 φ{d1_std:.2f} 套装到 {stretch_ref_label} φ{stretch_ref:.2f} mm，"
            f"拉伸 {actual_stretch:.2f}%（{stretch_mm:+.2f} mm）；胶料近似体积不可压，"
            f"线径相应由 {d2:.2f} mm 减薄至 {cord_loaded:.3f} mm（×{thin:.3f}），"
            f"因此装配后实际压缩量为 {comp_mm_corr:.3f} mm、实际压缩率 "
            f"{comp_pct_corr:.2f}% —— 指标卡上的 {comp_pct:.2f}% 按自由线径定义，"
            f"属名义值，两者差 {(comp_pct - comp_pct_corr):.2f} 个百分点。"
        )

    # ---------- 7. 填充率 ----------
    a_oring = math.pi * (d2 / 2.0) ** 2
    a_groove = h * b
    fill = a_oring / a_groove * 100.0
    use_backup = backup_n > 0

    # ---------- 8. 加工公差建议 ----------
    if d2 <= 2.0:
        h_tol = 0.03
    elif d2 <= 3.7:
        h_tol = 0.05
    else:
        h_tol = 0.08
    # ---- 圆角 / 导入倒角（GB/T 3452.3-2005）----
    ef = edge_fillet_lead(d2)
    is_dyn = comp_kind in ("hyd", "pneu")
    ra_static, ra_dyn = 0.8, 0.4
    machining = {
        "h_tol": h_tol,
        "b_tol_plus": 0.10,
        "bottom_tol": "h9",
        "outer_tol": "H9",
        "fillet_r": ef["r2"][1],
        "lead_angle": f"{ef['lead_angle'][0]:.0f}° ~ {ef['lead_angle'][1]:.0f}°",
        "ra_static": ra_static,
        "ra_dyn": ra_dyn,
        "note": f"槽底与槽侧表面粗糙度 Ra ≤ {ra_static} μm"
                + (f"；动密封 Ra ≤ {ra_dyn} μm" if is_dyn else "")
                + "；所有 O 圈经过的棱边必须去毛刺、去飞边。",
    }
    assembly = {
        "r1": ef["r1"], "r2": ef["r2"],
        "lead_angle": ef["lead_angle"], "lead_angle_rec": ef["lead_angle_rec"],
        "lead_zmin": ef["lead_zmin"], "lead_zmin_src": ef["lead_zmin_src"],
        "in_table": ef["in_table"],
        "note": f"导入倒角 {ef['lead_angle'][0]:.0f}°~{ef['lead_angle'][1]:.0f}°"
                f"（推荐 {ef['lead_angle_rec']:.0f}°），最小导角长度 Zmin ≥ "
                f"{ef['lead_zmin']:.2f} mm；槽底圆角 r₁ "
                f"{ef['r1'][0]:.2f}~{ef['r1'][1]:.2f} mm，槽口圆角 r₂ "
                f"{ef['r2'][0]:.2f}~{ef['r2'][1]:.2f} mm。装配前在 O 圈与导入角涂抹"
                f"与介质相容的润滑剂，可显著降低安装时的划伤与扭曲。",
    }
    if not ef["in_table"]:
        notes.append(
            f"线径 {d2:.2f} mm 超出 GB/T 3452.3 表1 的 1.80~7.00 mm 范围，"
            f"圆角与导角长度按最接近的档位取值，量产前请按标准原文复核。")

    # ---------- 9. 校核 ----------
    # 压缩率：区间与推荐同源，取自 GB/T 3452.3-2005 附录 A
    e_lo, e_hi = comp_lo, comp_hi
    if not (e_lo <= comp_pct <= e_hi):
        warnings.append(
            f"压缩率 {comp_pct:.2f}% 超出 {comp_rule} 的允许区间 "
            f"{e_lo:.1f}%~{e_hi:.1f}%，回弹补偿与密封可靠性可能不足或装配困难。"
        )

    # 高温工况下壳体热膨胀导致的压缩率漂移
    if he.get("code") and abs(he["d_comp_pp"]) > 0.05:
        e_hot = comp_pct + he["d_comp_pp"]
        if not (e_lo <= e_hot <= e_hi):
            warnings.append(
                f"升至 {t_high:.0f} ℃ 时压缩率估算为 {e_hot:.2f}%"
                f"（常温 {comp_pct:.2f}% 叠加热漂移 {he['d_comp_pp']:+.2f} 个百分点），"
                f"已超出允许区间 {e_lo:.1f}%~{e_hi:.1f}%，请复核高温工况下的密封可靠性。")

    # 拉伸率
    st_lo, st_hi = (0.0, 5.0) if not is_axial else (0.0, 3.0)
    if not (st_lo <= actual_stretch <= st_hi):
        if actual_stretch < st_lo:
            warnings.append(
                f"拉伸率 {actual_stretch:.2f}% 偏小（< {st_lo:.0f}%），"
                f"O 圈可能无法紧贴沟槽，装配时易脱落。"
            )
        else:
            warnings.append(
                f"拉伸率 {actual_stretch:.2f}% 超出推荐上限 {st_hi:.0f}%，"
                f"长期使用会加速老化与截面收缩，导致泄漏。"
            )

    # 填充率
    f_lo, f_hi = 60.0, 88.0
    if use_backup:
        # 挡圈占据槽宽空间，填充率天然偏低，且挡圈已限制 O 圈翻滚
        f_lo = 45.0
    if fill > f_hi:
        warnings.append(
            f"沟槽填充率 {fill:.1f}% 偏高（建议 ≤ {f_hi:.0f}%），"
            f"高温或介质溶胀时胶料无膨胀余地，可能导致密封失效。"
        )
    elif fill < f_lo:
        warnings.append(
            f"沟槽填充率 {fill:.1f}% 偏低（建议 ≥ {f_lo:.0f}%），"
            f"沟槽空腔过大，O 圈可能在压力下翻滚或扭曲。"
        )

    # 温度 vs 材料
    if not (mat_obj.tmin <= t_low and mat_obj.tmax >= t_high):
        warnings.append(
            f"{mat_obj.code} 的长期工作温度范围为 {mat_obj.tmin}~{mat_obj.tmax} ℃，"
            f"当前工况 {t_low:.0f}~{t_high:.0f} ℃ 超出该范围。"
        )

    # 介质不相容
    med_score = mat_obj.media.get(medium, 2)
    if med_score <= 1:
        warnings.append(
            f"{mat_obj.code} 对介质「{medium}」的相容性很差（评分 {med_score}/5），"
            f"请改用推荐列表中排序更靠前的材料。"
        )

    # ---------- 9. 结果 ----------
    best = mat_rank[0]
    return {
        "mode": mode,
        "geometry": geom,
        "oring": {
            "d1": d1_std,
            "d1_ideal": d1_ideal,
            "d1_tol": d1_tolerance(d1_std),
            "d2": d2,
            "d2_tol": d2_tolerance(d2),
            "d0": d0_std,
            "d2_src": d2_src,
        },
        "groove": {
            "h": h, "h_std": gv["h_std"], "h_src": gv["h_src"],
            "b": b, "b_std": gv["b_std"], "b_auto": gv["b_auto"],
            "b_src": gv["b_src"],
            "b_base": gv["b_base"], "b_backup": gv["b_backup"],
            "temp_factor": gv["temp_factor"],
            "bottom": geom["groove_bottom"],
            "bottom_label": geom["groove_bottom_label"],
            "outer": geom["groove_outer"],
            "outer_label": geom["groove_outer_label"],
            "area": a_groove,
        },
        "metrics": {
            "compression_mm": comp_mm,
            "compression_pct": comp_pct,
            "compression_range": (e_lo, e_hi),
            "stretch_pct": actual_stretch,
            "stretch_range": (st_lo, st_hi),
            "stretch_mm": stretch_mm,
            "stretch_ref": stretch_ref,
            "stretch_ref_label": stretch_ref_label,
            "thin_factor": thin,
            "cord_free": d2,
            "cord_loaded": cord_loaded,
            "compression_mm_corr": comp_mm_corr,
            "compression_pct_corr": comp_pct_corr,
            "fill_pct": fill,
            "fill_range": (f_lo, f_hi),
            "oring_area": a_oring,
            "gap_allow": gap_allow,
            "clearance": clearance,
            "backup_ring": use_backup,
            "backup_n": backup_n,
            "backup_src": backup_src,
        },
        "fit": fit,
        "machining": machining,
        "assembly": assembly,
        "housing": he,
        "material": {
            "code": mat_obj.code,
            "name": mat_obj.name,
            "t_range": (mat_obj.tmin, mat_obj.tmax),
            "hard_range": mat_obj.hard_range,
            "cost": mat_obj.cost,
            "pros": mat_obj.pros,
            "cons": mat_obj.cons,
            "usage": mat_obj.usage,
            "media_score": med_score,
            "ranking": mat_rank,
        },
        "hardness": {
            "value": hardness, "src": hardness_src, "why": hard_why,
        },
        "compression_src": {"src": comp_src, "why": comp_why,
                            "rule": comp_rule, "kind": comp_kind},
        "stretch_src": {"src": st_src},
        "input": {
            "mode": mode, "surface_dia": surface_dia, "pressure": pressure,
            "t_low": t_low, "t_high": t_high, "medium": medium, "motion": motion,
            "backup_mode": backup_mode,
        },
        "warnings": warnings,
        "notes": notes,
        "best_material": best,
    }


# =====================================================================
# 七、便捷封装：按标准 O 圈反算
# =====================================================================

def verify_with_standard_oring(mode: str, d1: float, d2: float, surface_dia: float,
                               pressure: float, t_low: float, t_high: float,
                               medium: str, motion: str = "静态") -> dict:
    """已知标准 O 圈（d1×d2）与密封面尺寸，校核压缩率与拉伸率。"""
    is_axial = mode == "axial"
    kind = "axial" if is_axial else ("dynamic" if motion != "静态" else "static")
    h_std, b_std, _src = groove_std_pair(d2, kind)

    res = design(mode, surface_dia, pressure, t_low, t_high, medium, motion,
                 d2=d2, compression_pct=(d2 - h_std) / d2 * 100.0)
    res["oring"]["d1"] = d1
    res["oring"]["d0"] = d1 + 2 * d2

    if mode == "radial_piston":
        bottom = surface_dia - 2 * h_std
        st = (bottom - d1) / d1 * 100.0
    elif mode == "radial_rod":
        bottom = surface_dia + 2 * h_std
        st = (bottom - d1) / d1 * 100.0
    else:
        free_mid = d1 + d2
        st = (surface_dia - free_mid) / free_mid * 100.0
    res["metrics"]["stretch_pct"] = st
    return res


# =====================================================================
# 八、自检
# =====================================================================

if __name__ == "__main__":
    tests = [
        ("活塞密封 φ40 缸孔 / 16 MPa 液压油", dict(
            mode="radial_piston", surface_dia=40.0, pressure=16.0,
            t_low=20.0, t_high=80.0, medium="液压油（矿物基）", motion="往复")),
        ("活塞杆密封 φ25 杆 / 10 MPa", dict(
            mode="radial_rod", surface_dia=25.0, pressure=10.0,
            t_low=20.0, t_high=70.0, medium="液压油（矿物基）", motion="往复")),
        ("轴向法兰密封 φ80 / 1.6 MPa 水", dict(
            mode="axial", surface_dia=80.0, pressure=1.6,
            t_low=5.0, t_high=90.0, medium="水 / 水-乙二醇", motion="静态")),
        ("制动系统 φ30 / 8 MPa 制动液", dict(
            mode="radial_piston", surface_dia=30.0, pressure=8.0,
            t_low=-30.0, t_high=120.0, medium="制动液 DOT3/DOT4", motion="往复")),
        # —— 新增能力：水深工况 / 手工线径 / 手动槽宽 / 不加挡圈 ——
        ("水下设备 φ50 缸孔 / 30 m 水深（往复）", dict(
            mode="radial_piston", surface_dia=50.0,
            pressure=water_depth_pressure(30.0),
            t_low=5.0, t_high=40.0, medium="水 / 水-乙二醇", motion="往复")),
        ("手工线径 3.00 mm / φ20 杆 / 2 MPa", dict(
            mode="radial_rod", surface_dia=20.0, pressure=2.0,
            t_low=20.0, t_high=60.0, medium="气动 / 空气", motion="往复",
            d2=3.00)),
        ("手工槽宽 6.0 mm 覆盖自动推荐 / φ32 缸孔", dict(
            mode="radial_piston", surface_dia=32.0, pressure=6.3,
            t_low=20.0, t_high=80.0, medium="液压油（矿物基）", motion="往复",
            groove_width=6.0)),
        ("高压 25 MPa 且手动不加挡圈", dict(
            mode="radial_piston", surface_dia=63.0, pressure=25.0,
            t_low=20.0, t_high=90.0, medium="液压油（矿物基）", motion="往复",
            backup_mode="none")),
        ("低压 0.35 MPa 且手动加双侧挡圈", dict(
            mode="axial", surface_dia=80.0, pressure=0.35,
            t_low=5.0, t_high=60.0, medium="热水 / 饮用水", motion="静态",
            backup_mode="double")),
    ]
    for title, kw in tests:
        r = design(**kw)
        print("=" * 68)
        print(title)
        o, g, m = r["oring"], r["groove"], r["metrics"]
        print(f"  O 圈     : d1={o['d1']:.2f}±{o['d1_tol']:.2f}  "
              f"d2={o['d2']:.2f}±{o['d2_tol']:.2f}  d0={o['d0']:.2f}"
              f"   [{o['d2_src']}]")
        print(f"  沟槽     : 槽深 h={g['h']:.2f}（{g['h_src']}）  "
              f"槽宽 b={g['b']:.2f}（{g['b_src']}）")
        if g["b_backup"] > 0:
            print(f"             其中 O 圈腔 {g['b_base']:.2f} + "
                  f"挡圈占位 {g['b_backup']:.2f}")
        print(f"             {g['bottom_label']}={g['bottom']:.2f}")
        f = r["fit"]
        print(f"  装配     : {f['installed_label']}={f['installed']:.2f} mm   "
              f"与{f['seal_surface_label']}单侧干涉={f['interference']:.3f} mm")
        print(f"  指标     : 压缩量={m['compression_mm']:.3f} mm "
              f"({m['compression_pct']:.1f}%)  拉伸率={m['stretch_pct']:.2f}%  "
              f"填充率={m['fill_pct']:.1f}%（校核下限 {m['fill_range'][0]:.0f}%）")
        print(f"  材料     : {r['material']['code']} {r['material']['name']}"
              f"  {r['hardness']['value']} Shore A")
        if m["gap_allow"] is not None:
            print(f"  允许间隙 : {m['gap_allow']:.2f} mm（单侧）"
                  f"   挡圈：{m['backup_src']}")
        for w in r["warnings"]:
            print(f"  ⚠ {w}")
        if not r["warnings"]:
            print("  ✓ 各项校核通过")
