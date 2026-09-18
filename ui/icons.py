# -*- coding: utf-8 -*-
"""矢量图标：把内联 SVG 渲染成 QPixmap（带缓存）。

图标直接以 SVG 源码内联，不依赖外部图片文件，打包成单文件 exe 后依然可用。
优先使用 QtSvg 渲染；若运行环境缺少 QtSvg 模块，则退回 QPainter 手绘形式，
保证界面不会因为一个图标而报错。
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QImage, QLinearGradient,
                           QPainter, QPen, QPixmap)

try:  # QtSvg 属于 PySide6-Essentials，正常安装一定有
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:  # pragma: no cover
    QSvgRenderer = None  # type: ignore[assignment]
    _HAS_SVG = False

# 超采样倍数：渲染后交给 Qt 按逻辑尺寸缩放，高 DPI 屏同样清晰
_SS = 4
_CACHE: dict = {}

# GitHub 官方 octicon mark-github（16×16，MIT License）
_GITHUB_PATH = (
    "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13"
    "-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66"
    ".07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15"
    "-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 "
    "2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 "
    "2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 "
    "2.2 0 .21.15.46.55.38A8.012 8.012 0 0 0 16 8c0-4.42-3.58-8-8-8z"
)


def _svg(body: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" '
            f'width="16" height="16">{body}</svg>')


def svg_pixmap(svg: str, size: int) -> QPixmap:
    """把 SVG 源码渲染成逻辑尺寸为 size 的 QPixmap（内部超采样）。"""
    key = (svg, size)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    pm = QPixmap(size * _SS, size * _SS)
    pm.fill(Qt.GlobalColor.transparent)
    if _HAS_SVG:
        r = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        p = QPainter(pm)
        r.render(p)
        p.end()
    pm.setDevicePixelRatio(float(_SS))
    _CACHE[key] = pm
    return pm


def github_pixmap(size: int = 18, color: str = "#4A5A6A") -> QPixmap:
    """GitHub 图标（实心填充）。"""
    svg = _svg(f'<path d="{_GITHUB_PATH}" fill="{color}"/>')
    pm = svg_pixmap(svg, size)
    if not _HAS_SVG:  # 退路：画一个圆角方块占位
        pm = QPixmap(size * _SS, size * _SS)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(color), 1.6 * _SS))
        p.drawRoundedRect(1.5 * _SS, 1.5 * _SS, 13 * _SS, 13 * _SS, 3 * _SS, 3 * _SS)
        p.end()
        pm.setDevicePixelRatio(float(_SS))
    return pm


def globe_pixmap(size: int = 18, color: str = "#4A5A6A") -> QPixmap:
    """个人网站图标：线圈地球（经线 + 两条纬线）。"""
    # 圆半径 6.6，纬线 y=5.6 / 10.4 处弦半宽 = sqrt(6.6² − 2.4²) ≈ 6.15
    body = (
        f'<circle cx="8" cy="8" r="6.6" fill="none" stroke="{color}" '
        f'stroke-width="1.5"/>'
        f'<ellipse cx="8" cy="8" rx="3.05" ry="6.6" fill="none" '
        f'stroke="{color}" stroke-width="1.2"/>'
        f'<path d="M1.9 5.6h12.2M1.9 10.4h12.2" fill="none" stroke="{color}" '
        f'stroke-width="1.2" stroke-linecap="round"/>'
    )
    return svg_pixmap(_svg(body), size)


# =====================================================================
# 程序主图标
# =====================================================================

# 任务栏 / 标题栏需要多档尺寸，Windows 会按 DPI 自己挑
APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def app_icon_image(size: int) -> QImage:
    """画一枚程序图标：蓝色圆角底 + 白色 O 圈 + 沟槽示意线。

    与打包进 exe 的 app.ico 使用同一套画法（tools/make_icon.py 调用本函数）。
    """
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    m = size * 0.055
    rect = QRectF(m, m, size - 2 * m, size - 2 * m)
    grad = QLinearGradient(0, m, 0, size - m)
    grad.setColorAt(0.0, QColor("#4C88FF"))
    grad.setColorAt(1.0, QColor("#1B49B8"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(rect, size * 0.225, size * 0.225)

    pen = QPen(QColor("#FFFFFF"), max(1.0, size * 0.108))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    d = size * 0.468
    p.drawEllipse(QRectF((size - d) / 2, (size - d) / 2, d, d))

    p.setPen(QPen(QColor(255, 255, 255, 90), max(1.0, size * 0.032)))
    y = size * 0.795
    p.drawLine(QRectF(size * 0.235, y, size * 0.53, 0).topLeft(),
               QRectF(size * 0.235, y, size * 0.53, 0).topRight())
    p.end()
    return img


def app_icon() -> QIcon:
    """程序图标（多尺寸）。注意：必须在 QGuiApplication 之后调用。"""
    ic = QIcon()
    for s in APP_ICON_SIZES:
        ic.addPixmap(QPixmap.fromImage(app_icon_image(s)))
    return ic
