# -*- coding: utf-8 -*-
"""密封沟槽剖面示意图组件（QPainter 实时绘制）。

径向密封绘制下半剖视（局部放大），轴向密封绘制法兰端面剖视。
横纵比例按视图自适应，纵向可放大以便看清细小特征，图下方标注放大倍数。
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QPainter,
                           QPainterPath, QPen, QPolygonF)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .theme import (ACCENT, BORDER, DIM, METAL, OK, RUBBER, TEXT, TEXT_DIM,
                    WARN)


class _View:
    """把毫米坐标映射到像素坐标（y 轴向上）。"""

    def __init__(self, x0, x1, y0, y1, w, h, pad_l=54, pad_r=26, pad_t=30, pad_b=42):
        self.xc = (x0 + x1) / 2.0
        self.yc = (y0 + y1) / 2.0
        iw = max(20.0, w - pad_l - pad_r)
        ih = max(20.0, h - pad_t - pad_b)
        sx = iw / max(1e-6, (x1 - x0))
        sy = ih / max(1e-6, (y1 - y0))
        # 限制纵向放大倍数，避免剖面严重失真
        ratio = sy / sx if sx > 0 else 1.0
        if ratio > 3.0:
            sy = sx * 3.0
        elif ratio < 1.0 / 3.0:
            sy = sx / 3.0
        self.sx, self.sy = sx, sy
        self.cx = pad_l + iw / 2.0
        self.cy = pad_t + ih / 2.0

    @property
    def ratio(self) -> float:
        return self.sy / self.sx if self.sx else 1.0

    def X(self, x):
        return self.cx + (x - self.xc) * self.sx

    def Y(self, y):
        return self.cy - (y - self.yc) * self.sy

    def P(self, x, y) -> QPointF:
        return QPointF(self.X(x), self.Y(y))


def _hatch(p: QPainter, poly: QPolygonF, color: str, spacing: int = 6):
    """给多边形填充 45° 剖面线。"""
    path = QPainterPath()
    path.addPolygon(poly)
    path.closeSubpath()
    p.save()
    p.setClipPath(path)
    rect = poly.boundingRect()
    pen = QPen(QColor(color), 1)
    p.setPen(pen)
    x = rect.left() - rect.height()
    while x < rect.right() + rect.height():
        p.drawLine(QPointF(x, rect.bottom()), QPointF(x + rect.height(), rect.top()))
        x += spacing
    p.restore()
    p.setPen(QPen(QColor(color), 1.2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolygon(poly)


def _arrow(p: QPainter, tip: QPointF, ang: float, size: float = 5.5):
    """在 tip 处画一个指向 ang（弧度）的实心箭头。"""
    a1, a2 = ang + math.radians(155), ang - math.radians(155)
    p1 = QPointF(tip.x() + size * math.cos(a1), tip.y() + size * math.sin(a1))
    p2 = QPointF(tip.x() + size * math.cos(a2), tip.y() + size * math.sin(a2))
    p.setBrush(QBrush(QColor(DIM)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF([tip, p1, p2]))


def _text(p: QPainter, x: float, y: float, s: str, color=TEXT, size=9.0,
          bold=False, anchor="mm", box=False):
    f = QFont()
    f.setPointSizeF(size)
    f.setBold(bold)
    p.setFont(f)
    fm = QFontMetricsF(f)
    lines = s.split("\n")
    w = max(fm.horizontalAdvance(ln) for ln in lines) + (10 if box else 0)
    h = fm.height() * len(lines) + (7 if box else 0)
    if anchor[0] == "l":
        rx = x
    elif anchor[0] == "r":
        rx = x - w
    else:
        rx = x - w / 2.0
    if anchor[1] == "t":
        ry = y
    elif anchor[1] == "b":
        ry = y - h
    else:
        ry = y - h / 2.0
    rect = QRectF(rx, ry, w, h)
    if box:
        p.setBrush(QBrush(QColor("#FFFFFFE6")))
        p.setPen(QPen(QColor(BORDER), 1))
        p.drawRoundedRect(rect, 4, 4)
    p.setPen(QPen(QColor(color), 1))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, s)


class SealDiagram(QWidget):
    """根据解算结果绘制密封沟槽剖面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._res = None
        self.setMinimumSize(360, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_result(self, res):
        self._res = res
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 8, 8)

        if self._res is None:
            _text(p, self.width() / 2, self.height() / 2,
                  "输入参数后点击「开始计算」", TEXT_DIM, 11)
            return

        if self._res["mode"] == "axial":
            self._paint_axial(p)
        else:
            self._paint_radial(p)

    # ------------------------------------------------------------------
    def _paint_radial(self, p: QPainter):
        r = self._res
        geom, g, m, fit = r["geometry"], r["groove"], r["metrics"], r["fit"]
        o = r["oring"]
        h, b, d2 = g["h"], g["b"], o["d2"]
        piston = r["mode"] == "radial_piston"
        surf = geom["surface"]

        gap = 0.10                      # 示意用单侧挤出间隙
        if piston:
            bore_r = surf / 2.0
            land_r = bore_r - gap
            gb_r = land_r - h
        else:
            rod_r = surf / 2.0
            land_r = rod_r + gap
            gb_r = land_r + h

        body = max(d2 * 1.7, h * 1.9)
        wall = max(d2 * 1.05, 2.4)
        x_lim = b * 2.4

        if piston:
            y_lo = gb_r - body * 0.55
            y_hi = bore_r + wall
        else:
            y_lo = land_r - wall
            y_hi = gb_r + body * 0.55

        v = _View(-x_lim, x_lim, y_lo, y_hi, self.width(), self.height())

        # ---- 金属基体（下端）----
        if piston:
            body_poly = QPolygonF([
                v.P(-x_lim, gb_r - body), v.P(-x_lim, land_r),
                v.P(-b / 2, land_r), v.P(-b / 2, gb_r),
                v.P(b / 2, gb_r), v.P(b / 2, land_r),
                v.P(x_lim, land_r), v.P(x_lim, gb_r - body),
            ])
            _hatch(p, body_poly, METAL)
            _text(p, v.X(-x_lim) + 8, v.Y(gb_r - body * 0.45), "活塞体", TEXT_DIM, 8.5,
                  anchor="lm")
            # 缸壁
            wall_poly = QPolygonF([
                v.P(-x_lim, bore_r), v.P(x_lim, bore_r),
                v.P(x_lim, bore_r + wall), v.P(-x_lim, bore_r + wall),
            ])
            _hatch(p, wall_poly, METAL)
            _text(p, v.X(x_lim) - 8, v.Y(bore_r + wall * 0.5), "缸体", TEXT_DIM, 8.5,
                  anchor="rm")
        else:
            body_poly = QPolygonF([
                v.P(-x_lim, gb_r + body), v.P(-x_lim, land_r),
                v.P(-b / 2, land_r), v.P(-b / 2, gb_r),
                v.P(b / 2, gb_r), v.P(b / 2, land_r),
                v.P(x_lim, land_r), v.P(x_lim, gb_r + body),
            ])
            _hatch(p, body_poly, METAL)
            _text(p, v.X(-x_lim) + 8, v.Y(gb_r + body * 0.5), "缸头/端盖", TEXT_DIM, 8.5,
                  anchor="lm")
            wall_poly = QPolygonF([
                v.P(-x_lim, land_r), v.P(x_lim, land_r),
                v.P(x_lim, land_r - wall), v.P(-x_lim, land_r - wall),
            ])
            _hatch(p, wall_poly, METAL)
            _text(p, v.X(x_lim) - 8, v.Y(land_r - wall * 0.5), "活塞杆", TEXT_DIM, 8.5,
                  anchor="rm")

        # ---- 沟槽空腔底纹 ----
        cav = QPolygonF([v.P(-b / 2, gb_r), v.P(b / 2, gb_r),
                         v.P(b / 2, land_r), v.P(-b / 2, land_r)])
        p.setBrush(QBrush(QColor("#F7F9FC")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(cav)

        # ---- O 圈（压缩后的截面：近似圆角矩形的鼓形）----
        w_eq = m["oring_area"] / h if h > 0 else d2
        cx = 0.0
        cy = (gb_r + land_r) / 2.0
        p.setBrush(QBrush(QColor(RUBBER)))
        p.setPen(QPen(QColor("#222A33"), 1.2))
        rect = QRectF(v.X(cx - w_eq / 2), v.Y(cy + h / 2),
                      w_eq * v.sx, h * v.sy)
        rad = max(3.0, min(rect.width(), rect.height()) * 0.34)
        p.drawRoundedRect(rect, rad, rad)
        _text(p, v.X(cx), v.Y(cy), "O 圈", "#FFFFFF", 8.5, bold=True)

        # ---- 尺寸标注 ----
        # 槽宽 b
        yb = gb_r - body * 0.30 if piston else gb_r + body * 0.30
        self._dim_h(p, v, -b / 2, b / 2, yb, f"b = {b:.2f}", feature_y=gb_r)
        # 槽深 h
        xh = b / 2 + b * 0.34
        self._dim_v(p, v, gb_r, land_r, xh, f"h = {h:.2f}", feature_x=0.0)
        # 密封面直径
        if piston:
            _text(p, v.X(0), v.Y(bore_r) - 4,
                  f"缸孔 φ{surf:.2f}", TEXT, 9.0, bold=True, anchor="mb")
        else:
            _text(p, v.X(0), v.Y(land_r) + 4,
                  f"活塞杆 φ{surf:.2f}", TEXT, 9.0, bold=True, anchor="mt")
        # 槽底径引线
        gb_lab = geom["groove_bottom_label"]
        tx = -b / 2 - b * 0.30
        _text(p, v.X(tx), v.Y(gb_r) + (14 if piston else -14),
              f"{gb_lab} φ{geom['groove_bottom']:.2f}", DIM, 8.5,
              anchor="mm" if piston else "mm", box=True)
        p.setPen(QPen(QColor(DIM), 1, Qt.PenStyle.DashLine))
        p.drawLine(v.P(tx, gb_r), v.P(0, gb_r))

        # 干涉量
        comp = m["compression_mm"]
        _text(p, v.X(b * 0.72), v.Y(cy),
              f"单侧压缩\n{comp:.3f} mm", ACCENT, 8.5, anchor="lm", box=True)

        # 装配后尺寸
        meas = fit["installed_label"]
        _text(p, v.X(-x_lim) + 8, 20, f"{meas} {fit['installed']:.2f} mm  ·  "
              f"与{fit['seal_surface_label']}单侧干涉 {fit['interference']:.3f} mm",
              OK, 8.5, anchor="lm")
        self._foot(p, v, "径向密封沟槽剖面（下半剖视 · 局部放大）")

    # ------------------------------------------------------------------
    def _paint_axial(self, p: QPainter):
        r = self._res
        geom, g, m = r["geometry"], r["groove"], r["metrics"]
        h, b, d2 = g["h"], g["b"], r["oring"]["d2"]
        dm = geom["surface"]

        slab = max(d2 * 1.25, h * 1.3)
        x_lim = b * 2.9
        v = _View(-x_lim, x_lim, -h - slab, slab, self.width(), self.height())

        # ---- 下法兰（开槽侧）----
        low = QPolygonF([
            v.P(-x_lim, 0), v.P(-b / 2, 0), v.P(-b / 2, -h),
            v.P(b / 2, -h), v.P(b / 2, 0), v.P(x_lim, 0),
            v.P(x_lim, -h - slab), v.P(-x_lim, -h - slab),
        ])
        _hatch(p, low, METAL)
        _text(p, v.X(-x_lim) + 8, v.Y(-h - slab * 0.5), "法兰 A（开槽）",
              TEXT_DIM, 8.5, anchor="lm")

        # ---- 上法兰（压紧侧）----
        up = QPolygonF([
            v.P(-x_lim, 0), v.P(x_lim, 0),
            v.P(x_lim, slab), v.P(-x_lim, slab),
        ])
        _hatch(p, up, METAL)
        _text(p, v.X(-x_lim) + 8, v.Y(slab * 0.5), "法兰 B（压紧）",
              TEXT_DIM, 8.5, anchor="lm")

        # ---- O 圈（压缩后的截面）----
        w_eq = m["oring_area"] / h if h > 0 else d2
        p.setBrush(QBrush(QColor(RUBBER)))
        p.setPen(QPen(QColor("#222A33"), 1.2))
        rect = QRectF(v.X(-w_eq / 2), v.Y(0), w_eq * v.sx, h * v.sy)
        rad = max(3.0, min(rect.width(), rect.height()) * 0.34)
        p.drawRoundedRect(rect, rad, rad)
        _text(p, v.X(0), v.Y(-h / 2), "O 圈", "#FFFFFF", 8.5, bold=True)

        # ---- 标注 ----
        self._dim_h(p, v, -b / 2, b / 2, -h - slab * 0.55, f"槽宽 b = {b:.2f}",
                    feature_y=-h)
        self._dim_v(p, v, -h, 0, b / 2 + b * 0.30, f"槽深 h = {h:.2f}",
                    feature_x=0.0)
        _text(p, v.X(x_lim) - 6, v.Y(slab) + 4,
              f"沟槽内径 d4 = {geom['groove_bottom']:.2f}\n"
              f"沟槽外径 d5 = {geom['groove_outer']:.2f}\n"
              f"中心径 dm = {dm:.2f}",
              DIM, 8.2, anchor="rt", box=True)
        _text(p, v.X(-b / 2 - b * 0.22), v.Y(-h / 2),
              f"轴向压缩 {m['compression_mm']:.3f} mm", ACCENT, 8.2,
              anchor="rm", box=True)
        self._foot(p, v, "轴向端面密封沟槽剖面 · 两法兰端面贴合压紧")

    # ------------------------------------------------------------------
    def _foot(self, p: QPainter, v: _View, caption: str):
        r = self._res
        txt = f"{caption}"
        if abs(v.ratio - 1.0) > 0.05:
            txt += f"　纵向比例已放大 {v.ratio:.1f}×"
        _text(p, self.width() / 2, self.height() - 12, txt, TEXT_DIM, 8.5, anchor="mb")

    def _dim_h(self, p: QPainter, v: _View, x1, x2, y, label, feature_y=None):
        yp = v.Y(y)
        if feature_y is not None:
            p.setPen(QPen(QColor(DIM), 1, Qt.PenStyle.DashLine))
            for xx in (x1, x2):
                p.drawLine(QPointF(v.X(xx), yp + (4 if y > feature_y else -4)),
                           QPointF(v.X(xx), v.Y(feature_y)))
        p.setPen(QPen(QColor(DIM), 1.2))
        p.drawLine(QPointF(v.X(x1), yp), QPointF(v.X(x2), yp))
        for xx, ang in ((x1, 0.0), (x2, math.pi)):
            _arrow(p, QPointF(v.X(xx), yp), ang)
        _text(p, (v.X(x1) + v.X(x2)) / 2, yp - 9, label, DIM, 8.5,
              anchor="mb", box=True)

    def _dim_v(self, p: QPainter, v: _View, y1, y2, x, label, feature_x=None):
        xp = v.X(x)
        if feature_x is not None:
            p.setPen(QPen(QColor(DIM), 1, Qt.PenStyle.DashLine))
            for yy in (y1, y2):
                p.drawLine(QPointF(xp + (4 if x > feature_x else -4), v.Y(yy)),
                           QPointF(v.X(feature_x), v.Y(yy)))
        p.setPen(QPen(QColor(DIM), 1.2))
        p.drawLine(QPointF(xp, v.Y(y1)), QPointF(xp, v.Y(y2)))
        for yy, ang in ((y1, -math.pi / 2), (y2, math.pi / 2)):
            _arrow(p, QPointF(xp, v.Y(yy)), ang)
        _text(p, xp + 7, (v.Y(y1) + v.Y(y2)) / 2, label, DIM, 8.5,
              anchor="lm", box=True)
