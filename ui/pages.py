# -*- coding: utf-8 -*-
"""界面各页面：设计计算、标准尺寸库、材料选型库、使用说明。"""

from __future__ import annotations

import datetime
import html
import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QComboBox,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from core.oring_core import (D1_SERIES, D2_ALL, D2_MAX, D2_MIN, D2_TAG,
                             DESIGN_DOC, HOUSING_MATERIALS, MATERIALS, MEDIA_LIST,
                             PRESSURE_PRESETS, DesignError, d1_range,
                             d2_family, d2_tolerance, design, groove_std_pair,
                             recommend_d2, recommend_materials)

from .diagram import SealDiagram
from .theme import (ACCENT, BAD, BORDER, CARD, OK, TEXT, TEXT_DIM, TEXT_MID,
                    WARN)


# =====================================================================
# 基础控件
# =====================================================================

class Card(QFrame):
    """带标题的白色卡片容器。"""

    def __init__(self, title: str = "", hint: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(8)
        if title:
            head = QHBoxLayout()
            head.setSpacing(8)
            lab = QLabel(title)
            lab.setObjectName("CardTitle")
            head.addWidget(lab)
            head.addStretch(1)
            if hint:
                h = QLabel(hint)
                h.setObjectName("CardHint")
                head.addWidget(h)
            outer.addLayout(head)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        outer.addLayout(self.body)

    def add(self, w):
        self.body.addWidget(w)
        return w

    def add_layout(self, l):
        self.body.addLayout(l)
        return l


class MetricCard(QFrame):
    """大数字指标卡。"""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Metric")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(1)
        self.name = QLabel(name)
        self.name.setObjectName("MetricName")
        self.value = QLabel("—")
        self.value.setObjectName("MetricValue")
        self.value.setStyleSheet(f"color:{TEXT};")
        self.note = QLabel("")
        self.note.setObjectName("MetricNote")
        lay.addWidget(self.name)
        lay.addWidget(self.value)
        lay.addWidget(self.note)
        self._note = ""

    def set(self, value: str, state: str = "ok", note: str = ""):
        color = {"ok": OK, "warn": WARN, "bad": BAD, "na": TEXT_DIM}[state]
        self.value.setText(value)
        self.value.setStyleSheet(f"color:{color};")
        self.note.setText(note)


class HintLabel(QLabel):
    """输入框下方的浅色说明行（用于显示自动推荐值 / 同步了什么）。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("FieldHint")
        self.setWordWrap(True)
        self.setContentsMargins(112, 0, 0, 0)


class NumberInput(QWidget):
    """一行数值输入：标签 + 输入框 + 单位。"""

    def __init__(self, label: str, unit: str = "", placeholder: str = "",
                 label_w: int = 104, tip: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("FieldLabel")
        self.label.setFixedWidth(label_w)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumWidth(70)
        if tip:
            self.edit.setToolTip(tip)
            self.label.setToolTip(tip)
        self.unit = QLabel(unit)
        self.unit.setObjectName("FieldUnit")
        self.unit.setFixedWidth(30)
        lay.addWidget(self.label)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.unit)

    def set_label(self, text: str):
        self.label.setText(text)

    def value(self):
        s = self.edit.text().strip().replace("，", "").replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"「{self.label.text()}」不是有效数值：{s}")

    def set_value(self, v):
        self.edit.setText("" if v is None else f"{v:g}")

    def set_tip(self, tip: str):
        self.edit.setToolTip(tip)
        self.label.setToolTip(tip)

    def clear(self):
        self.edit.clear()

    def on_change(self, fn):
        self.edit.textChanged.connect(fn)


class ComboInput(QWidget):
    def __init__(self, label: str, items, label_w: int = 104, parent=None,
                 editable: bool = False):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.label = QLabel(label)
        self.label.setObjectName("FieldLabel")
        self.label.setFixedWidth(label_w)
        self.combo = QComboBox()
        self.combo.addItems(items)
        if editable:
            self.combo.setEditable(True)
            self.combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            self.combo.lineEdit().setPlaceholderText("选择或直接输入数值")
        lay.addWidget(self.label)
        lay.addWidget(self.combo, 1)

    def on_change(self, fn):
        self.combo.currentIndexChanged.connect(fn)

    def on_text_change(self, fn):
        self.combo.currentTextChanged.connect(fn)

    def current(self):
        return self.combo.currentText()

    def current_data(self):
        return self.combo.currentData()

    def set_tip(self, tip: str):
        self.combo.setToolTip(tip)
        self.label.setToolTip(tip)


class RowList(QWidget):
    """键值对列表。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(5)
        self.grid.setColumnStretch(0, 0)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnMinimumWidth(0, 92)
        self._row = 0

    def clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._row = 0

    def add(self, key: str, value: str, bold=False, color=None):
        k = QLabel(key)
        k.setObjectName("RowKey")
        k.setFixedWidth(92)
        v = QLabel(value)
        v.setObjectName("RowVal")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setWordWrap(True)
        v.setMinimumWidth(40)
        v.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        if color:
            v.setStyleSheet(f"color:{color};font-size:12px;font-weight:600;")
        elif bold:
            v.setStyleSheet(f"color:{TEXT};font-size:12.5px;font-weight:700;")
        self.grid.addWidget(k, self._row, 0)
        self.grid.addWidget(v, self._row, 1)
        self._row += 1

    def add_sep(self):
        f = QFrame()
        f.setObjectName("Divider")
        self.grid.addWidget(f, self._row, 0, 1, 2)
        self._row += 1


# =====================================================================
# 设计计算页
# =====================================================================

class DesignPage(QWidget):
    KINDS_RADIAL = [("radial_piston", "活塞密封"), ("radial_rod", "活塞杆密封")]
    KINDS_AXIAL = [("axial", "端面密封")]

    def __init__(self, group: str = "radial", parent=None):
        super().__init__(parent)
        self.group = group
        self.kinds = self.KINDS_RADIAL if group == "radial" else self.KINDS_AXIAL
        self.mode = self.kinds[0][0]
        self._res = None

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        root.addWidget(self._build_input(), 0)
        root.addWidget(self._build_results(), 1)

        right = QSplitter(Qt.Orientation.Vertical)
        right.setChildrenCollapsible(False)
        right.addWidget(self._build_diagram())
        right.addWidget(self._build_material())
        right.setSizes([420, 340])
        right.setHandleWidth(10)
        root.addWidget(right, 1)

        self._syncing = False     # 预设联动期间抑制反向同步
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(260)
        self._timer.timeout.connect(self.recalc)
        self._wire()

        self._apply_defaults()
        self.recalc(initial=True)

    def _apply_defaults(self):
        """预填一组典型工况，打开即有完整结果可看。"""
        if self.group == "radial":
            self.in_dia.set_value(40)
            self.in_press.set_value(16)
            self.in_motion.combo.setCurrentText("往复")
        else:
            self.in_dia.set_value(80)
            self.in_press.set_value(1.6)
        self.in_tlow.set_value(20)
        self.in_thigh.set_value(80)
        self.in_medium.combo.setCurrentText("液压油（矿物基）")

    # ---------------- 左：输入 ----------------
    def _build_input(self) -> QWidget:
        box = QWidget()
        box.setFixedWidth(396)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        sc = QVBoxLayout(inner)
        sc.setContentsMargins(0, 0, 6, 0)
        sc.setSpacing(10)

        # 密封型式
        if len(self.kinds) > 1:
            c0 = Card("密封型式")
            seg = QHBoxLayout()
            seg.setSpacing(6)
            self.seg_group = QButtonGroup(self)
            for i, (key, name) in enumerate(self.kinds):
                btn = QPushButton(name)
                btn.setObjectName("Seg")
                btn.setCheckable(True)
                btn.setChecked(i == 0)
                btn.clicked.connect(lambda _c, k=key: self._set_mode(k))
                self.seg_group.addButton(btn, i)
                seg.addWidget(btn, 1)
            c0.body.addLayout(seg)
            sc.addWidget(c0)

        # 工况参数
        c1 = Card("工况参数")
        self.in_preset = ComboInput("常用工况预设",
                                    [it["label"] for it in PRESSURE_PRESETS])
        self.in_preset.set_tip("选择常用场景可一键带入工作压力，"
                               "并同步该场景对应的介质、运动方式与温度")
        self.lbl_preset = HintLabel(
            "选预设可自动带入压力；压力值仍可随时手动修改。")
        c1.add(self.in_preset)
        c1.add(self.lbl_preset)

        self.in_dia = NumberInput("密封面直径", "mm", "必填",
                                  tip="活塞密封填缸孔直径；活塞杆密封填活塞杆直径；端面密封填沟槽中心直径")
        self.in_press = NumberInput("工作压力", "MPa", "0",
                                    tip="最大工作压力（表压）。真空工况可填 0；"
                                        "1 m 水柱 ≈ 0.0098 MPa")
        self.in_medium = ComboInput("工作介质", MEDIA_LIST)
        self.in_medium.combo.setEditable(True)
        self.in_motion = ComboInput("运动方式", ["静态", "往复", "回转"])
        self.in_tlow = NumberInput("最低温度", "℃", "20")
        self.in_thigh = NumberInput("最高温度", "℃", "80")
        c1.add(self.in_dia)
        c1.add(self.in_press)
        c1.add(self.in_medium)
        if self.group == "radial":
            c1.add(self.in_motion)
        else:
            # 端面密封按静密封设计，运动方式无意义，直接固定
            self.in_motion.combo.setCurrentText("静态")
            self.in_dia.set_label("沟槽中心直径")
            self.in_dia.edit.setToolTip("沟槽内外径的平均值，即 (d4 + d5) / 2")
        c1.add(self.in_tlow)
        c1.add(self.in_thigh)
        sc.addWidget(c1)

        # 线径与沟槽（留空自动）
        c2 = Card("线径与沟槽尺寸", "留空即为自动推荐")
        self.in_d2 = ComboInput("线径 d2", [], editable=True)
        self.in_d2.combo.addItem("自动推荐", None)
        for x in D2_ALL:
            self.in_d2.combo.addItem(f"{x:.2f}　{D2_TAG[x]}", x)
        self.in_d2.set_tip("可直接从列表选择标准线径，也可手动输入任意数值"
                           f"（{D2_MIN:g} ~ {D2_MAX:g} mm）")
        self.lbl_d2 = HintLabel("")
        self.in_comp = NumberInput("压缩率", "%", "自动")
        self.in_width = NumberInput("槽宽 b", "mm", "自动推荐")
        self.in_width.set_tip("留空 = 按 GB/T 3452.3 标准值自动推荐（含挡圈占位与高温修正）；"
                              "填写则按填写值取值")
        self.lbl_b = HintLabel("")
        for w in (self.in_d2, self.lbl_d2, self.in_comp,
                  self.in_width, self.lbl_b):
            c2.add(w)
        sc.addWidget(c2)

        # 材料与硬度
        c3 = Card("材料与硬度", "留空即为自动选型")
        mats = ["自动"] + [f"{m.code}　{m.name}" for m in MATERIALS]
        self.in_mat = ComboInput("材料", mats)
        self.in_hard = NumberInput("邵氏硬度", "Shore A", "自动")
        c3.add(self.in_mat)
        c3.add(self.in_hard)
        sc.addWidget(c3)

        # 壳体与装配
        c4 = Card("壳体与装配", "壳体材料影响热膨胀与受压变形")
        hs = ["未指定"] + [f"{m['code']}　{m['name']}（{m['group']}）"
                           for m in HOUSING_MATERIALS]
        self.in_housing = ComboInput("壳体材料", hs)
        self.in_housing.set_tip("金属壳体刚性好但线膨胀系数小；塑料壳体线膨胀系数大、"
                                "易蠕变，会自动上浮压缩率补偿，并提示受压变形风险")
        self.in_backup = ComboInput("挡圈配置", ["自动判定", "不加挡圈",
                                                 "单侧挡圈", "两侧各一个"])
        self.in_backup.set_tip("挡圈会占用槽宽，影响自动推荐的槽宽值。"
                               "往复 / 回转密封为双作用，自动判定取两侧各一个")
        self.in_gap = NumberInput("设计单侧间隙", "mm", "不校核")
        self.in_stretch = NumberInput("内径拉伸率", "%", "自动")
        c4.add(self.in_housing)
        c4.add(self.in_backup)
        c4.add(self.in_gap)
        c4.add(self.in_stretch)
        sc.addWidget(c4)

        sc.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.btn_calc = QPushButton("开始计算")
        self.btn_calc.setObjectName("Primary")
        self.btn_calc.setMinimumHeight(34)
        self.btn_calc.clicked.connect(lambda: self.recalc(force=True))
        self.btn_reset = QPushButton("重置")
        self.btn_reset.setMinimumHeight(34)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_export = QPushButton("导出报告")
        self.btn_export.setMinimumHeight(34)
        self.btn_export.clicked.connect(self._export)
        bar.addWidget(self.btn_calc, 2)
        bar.addWidget(self.btn_reset, 1)
        bar.addWidget(self.btn_export, 1)
        outer.addLayout(bar)
        return box

    # ---------------- 中：结果 ----------------
    def _build_results(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(10)

        mrow = QHBoxLayout()
        mrow.setSpacing(8)
        self.m_comp = MetricCard("压缩率 ε")
        self.m_stretch = MetricCard("拉伸率 δ")
        self.m_fill = MetricCard("填充率 K")
        for m in (self.m_comp, self.m_stretch, self.m_fill):
            mrow.addWidget(m, 1)
        lay.addLayout(mrow)

        c1 = Card("密封圈规格")
        self.row_oring = RowList()
        c1.add(self.row_oring)
        lay.addWidget(c1)

        c2 = Card("沟槽设计参数")
        self.row_groove = RowList()
        c2.add(self.row_groove)
        lay.addWidget(c2)

        c3 = Card("装配校核")
        self.row_fit = RowList()
        c3.add(self.row_fit)
        lay.addWidget(c3)

        c4 = Card("校核结论")
        self.warn_box = QVBoxLayout()
        self.warn_box.setSpacing(6)
        c4.body.addLayout(self.warn_box)
        lay.addWidget(c4)

        lay.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    # ---------------- 右上：示意图 ----------------
    def _build_diagram(self) -> QWidget:
        c = Card("沟槽剖面示意")
        self.diagram = SealDiagram()
        c.add(self.diagram)
        c.setMinimumHeight(300)
        return c

    # ---------------- 右下：材料与硬度 ----------------
    def _build_material(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(10)

        c1 = Card("材料与硬度选型")
        self.row_mat = RowList()
        c1.add(self.row_mat)
        self.lbl_mat_note = QLabel("")
        self.lbl_mat_note.setObjectName("CardHint")
        self.lbl_mat_note.setWordWrap(True)
        c1.add(self.lbl_mat_note)
        lay.addWidget(c1)

        c2 = Card("备选材料排序")
        self.tbl_alt = QTableWidget(0, 4)
        self.tbl_alt.setHorizontalHeaderLabels(["材料", "评分", "耐温", "相容性"])
        self.tbl_alt.verticalHeader().setVisible(False)
        self.tbl_alt.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_alt.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_alt.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for i in (1, 2, 3):
            self.tbl_alt.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_alt.setMinimumHeight(150)
        c2.add(self.tbl_alt)
        lay.addWidget(c2)
        lay.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    # ---------------- 交互 ----------------
    def _wire(self):
        for w in (self.in_dia, self.in_press, self.in_comp, self.in_width,
                  self.in_hard, self.in_gap, self.in_stretch, self.in_tlow,
                  self.in_thigh):
            w.on_change(lambda _t: self._timer.start())
        for w in (self.in_medium, self.in_motion, self.in_mat, self.in_backup,
                  self.in_housing):
            w.on_change(lambda _i: self._timer.start())
        # 线径为可编辑下拉框：既要响应选项切换，也要响应手工输入
        self.in_d2.on_text_change(lambda _t: self._timer.start())
        self.in_preset.on_change(self._apply_preset)
        self.in_press.on_change(self._on_press_edit)

    # ---------------- 常用工况预设 ----------------
    def _apply_preset(self, idx: int):
        """把预设工况带入输入框（压力 + 该场景对应的介质 / 运动 / 温度）。"""
        if idx <= 0 or idx >= len(PRESSURE_PRESETS):
            self.lbl_preset.setText("选预设可自动带入压力；压力值仍可随时手动修改。")
            return
        it = PRESSURE_PRESETS[idx]
        applied = []
        self._syncing = True
        try:
            if it.get("p") is not None:
                self.in_press.set_value(it["p"])
                applied.append(f"压力 {it['p']:g} MPa")
            if it.get("medium"):
                self.in_medium.combo.setCurrentText(it["medium"])
                applied.append(f"介质「{it['medium']}」")
            if it.get("motion") and self.group == "radial":
                self.in_motion.combo.setCurrentText(it["motion"])
                applied.append(f"运动「{it['motion']}」")
            if it.get("t"):
                self.in_tlow.set_value(it["t"][0])
                self.in_thigh.set_value(it["t"][1])
                applied.append(f"温度 {it['t'][0]}~{it['t'][1]} ℃")
        finally:
            self._syncing = False
        note = it.get("note") or ""
        self.lbl_preset.setText(
            f"已带入：{'、'.join(applied)}。{note}")
        self._timer.start()

    def _on_press_edit(self, _text: str):
        """手动改动压力时，把预设退回「手动输入」。"""
        if self._syncing:
            return
        idx = self.in_preset.combo.currentIndex()
        if idx <= 0:
            return
        it = PRESSURE_PRESETS[idx]
        try:
            cur = self.in_press.value()
        except ValueError:
            cur = None
        if cur is None or it.get("p") is None or abs(cur - it["p"]) > 1e-9:
            self.in_preset.combo.setCurrentIndex(0)

    def _set_mode(self, key: str):
        self.mode = key
        self.recalc(force=True)

    def _reset(self):
        for w in (self.in_dia, self.in_press, self.in_comp, self.in_width,
                  self.in_hard, self.in_gap, self.in_stretch):
            w.clear()
        self.in_tlow.set_value(20)
        self.in_thigh.set_value(80)
        self.in_medium.combo.setCurrentIndex(0)
        self.in_motion.combo.setCurrentIndex(0)
        self.in_d2.combo.setCurrentIndex(0)
        self.in_mat.combo.setCurrentIndex(0)
        self.in_backup.combo.setCurrentIndex(0)
        self.in_housing.combo.setCurrentIndex(0)
        self.in_preset.combo.setCurrentIndex(0)
        self.lbl_d2.setText("")
        self.lbl_b.setText("")
        self._apply_defaults()
        self.recalc(force=True)

    # ---------------- 计算 ----------------
    def _d2_value(self):
        """读取线径：下拉选项取携带数据，也支持手工输入任意数值。"""
        cb = self.in_d2.combo
        s = cb.currentText().strip().replace("，", "").replace(",", "")
        head = s.replace("　", " ").split()[0] if s else ""
        if not head or head.startswith("自动"):
            d = cb.currentData()
            return float(d) if d is not None else None
        try:
            v = float(head)
        except ValueError:
            d = cb.currentData()
            if d is not None:
                return float(d)
            raise DesignError(
                f"线径「{s}」不是有效数值，请从列表中选择标准线径，"
                f"或直接输入 {D2_MIN:g} ~ {D2_MAX:g} mm 之间的数值")
        if not (D2_MIN <= v <= D2_MAX):
            raise DesignError(
                f"线径 {v:g} mm 超出常用范围（{D2_MIN:g} ~ {D2_MAX:g} mm），"
                f"请确认输入值")
        return v

    def _collect(self) -> dict:
        dia = self.in_dia.value()
        if dia is None or dia <= 0:
            raise DesignError("请填写有效的密封面直径")

        pressure = self.in_press.value()
        if pressure is None:
            pressure = 0.0
        if pressure < 0:
            raise DesignError("工作压力不能为负数")

        t_low = self.in_tlow.value()
        t_high = self.in_thigh.value()
        if t_low is None:
            t_low = 20.0
        if t_high is None:
            t_high = 80.0
        if t_high <= t_low:
            raise DesignError("最高温度必须高于最低温度")

        d2 = self._d2_value()

        mat = None
        ms = self.in_mat.combo.currentText()
        if ms != "自动":
            mat = ms.split("　")[0].strip()

        hard = self.in_hard.value()
        if hard is not None:
            hard = int(round(hard))

        motion = self.in_motion.current() if self.group == "radial" else "静态"

        backup_mode = {"自动判定": "auto", "不加挡圈": "none",
                       "单侧挡圈": "single", "两侧各一个": "double"}.get(
            self.in_backup.current(), "auto")

        hs = self.in_housing.current().strip()
        housing = None if (not hs or hs.startswith("未指定")) else hs.split("　")[0].strip()

        return dict(
            mode=self.mode,
            surface_dia=dia,
            pressure=pressure,
            t_low=t_low,
            t_high=t_high,
            medium=self.in_medium.current().strip() or "液压油（矿物基）",
            motion=motion,
            d2=d2,
            compression_pct=self.in_comp.value(),
            groove_width=self.in_width.value(),
            hardness=hard,
            material=mat,
            stretch_pct=self.in_stretch.value(),
            backup_mode=backup_mode,
            clearance=self.in_gap.value(),
            housing=housing,
        )

    def recalc(self, initial: bool = False, force: bool = False):
        try:
            params = self._collect()
            res = design(**params)
        except DesignError as e:
            self._show_error(str(e))
            return
        except ValueError as e:
            self._show_error(str(e))
            return
        self._res = res
        self._fill(res)

    def _show_error(self, msg: str):
        self._res = None
        for m in (self.m_comp, self.m_stretch, self.m_fill):
            m.set("—", "na", "")
        self.row_oring.clear()
        self.row_oring.add("提示", msg, color=BAD)
        self.row_groove.clear()
        self.row_fit.clear()
        self._clear_warn()
        self._add_warn(msg, "bad")
        self.diagram.set_result(None)
        self.lbl_d2.setText("")
        self.lbl_b.setText("")

    def _clear_warn(self):
        while self.warn_box.count():
            it = self.warn_box.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _add_warn(self, text: str, kind: str = "warn"):
        f = QFrame()
        f.setObjectName("OkItem" if kind == "ok" else "WarnItem")
        lay = QHBoxLayout(f)
        lay.setContentsMargins(10, 7, 10, 7)
        ico = QLabel("✓" if kind == "ok" else ("✕" if kind == "bad" else "!"))
        ico.setFixedWidth(16)
        ico.setStyleSheet(
            f"color:{OK if kind == 'ok' else BAD if kind == 'bad' else WARN};"
            "font-weight:700;font-size:13px;")
        t = QLabel(text)
        t.setObjectName("OkText" if kind == "ok" else "WarnText")
        t.setWordWrap(True)
        lay.addWidget(ico, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(t, 1)
        self.warn_box.addWidget(f)

    @staticmethod
    def _state(val, rng):
        lo, hi = rng
        if lo <= val <= hi:
            return "ok"
        span = max(hi - lo, 1e-6)
        if val < lo * 0.7 or val > hi + span:
            return "bad"
        return "warn"

    def _fill(self, r):
        o, g, m, mat, hd = r["oring"], r["groove"], r["metrics"], r["material"], r["hardness"]
        fit = r["fit"]

        # 指标卡
        st = self._state(m["compression_pct"], m["compression_range"])
        self.m_comp.set(f"{m['compression_pct']:.1f}%", st,
                        f"推荐 {m['compression_range'][0]:.0f}~{m['compression_range'][1]:.0f}%")
        st = self._state(m["stretch_pct"], m["stretch_range"])
        self.m_stretch.set(f"{m['stretch_pct']:.2f}%", st,
                           f"推荐 {m['stretch_range'][0]:.0f}~{m['stretch_range'][1]:.0f}%")
        st = self._state(m["fill_pct"], m["fill_range"])
        self.m_fill.set(f"{m['fill_pct']:.1f}%", st,
                        f"推荐 {m['fill_range'][0]:.0f}~{m['fill_range'][1]:.0f}%")

        # 密封圈规格
        rw = self.row_oring
        rw.clear()
        rw.add("密封型式", self._mode_name())
        rw.add("内径 d1", f"φ{o['d1']:.2f} ± {o['d1_tol']:.2f} mm", bold=True)
        rw.add("线径 d2", f"{o['d2']:.2f} ± {o['d2_tol']:.2f} mm", bold=True)
        rw.add("外径 d0（自由）", f"φ{o['d0']:.2f} mm", bold=True)
        rw.add("截面积", f"{math.pi * (o['d2'] / 2) ** 2:.2f} mm²")
        rw.add("线径来源", o["d2_src"], color=TEXT_DIM)
        rw.add_sep()
        rw.add(fit["installed_label"], f"φ{fit['installed']:.2f} mm", bold=True)
        rw.add(f"与{fit['seal_surface_label']}单侧干涉",
               f"{fit['interference']:.3f} mm", color=ACCENT, bold=True)

        # 沟槽参数
        rw = self.row_groove
        rw.clear()
        rw.add("槽深 h", f"{g['h']:.2f} mm", bold=True)
        rw.add("槽宽 b", f"{g['b']:.2f} mm", bold=True)
        if g["b_backup"] > 0:
            rw.add("槽宽构成",
                   f"O 圈腔 {g['b_base']:.2f} + 挡圈 {g['b_backup']:.2f}",
                   color=TEXT_DIM)
        rw.add(g["bottom_label"], f"φ{g['bottom']:.2f} mm", bold=True)
        rw.add(g["outer_label"], f"φ{g['outer']:.2f} mm", bold=True)
        rw.add("槽截面积", f"{g['area']:.2f} mm²")
        rw.add_sep()
        rw.add("槽深来源", g["h_src"], color=TEXT_DIM)
        rw.add("槽宽来源", g["b_src"], color=TEXT_DIM)
        mc = r["machining"]
        rw.add("槽深公差", f"± {mc['h_tol']:.2f} mm")
        rw.add("槽宽公差", f"+{mc['b_tol_plus']:.2f} / 0 mm")
        rw.add("槽底径公差", mc["bottom_tol"])
        rw.add("沟槽外径公差", mc["outer_tol"])
        asm = r["assembly"]
        rw.add("槽底圆角 r₁", f"{asm['r1'][0]:.2f} ~ {asm['r1'][1]:.2f} mm")
        rw.add("槽口圆角 r₂", f"{asm['r2'][0]:.2f} ~ {asm['r2'][1]:.2f} mm")
        rw.add("导入倒角", f"{asm['lead_angle'][0]:.0f}° ~ {asm['lead_angle'][1]:.0f}°"
                           f"（推荐 {asm['lead_angle_rec']:.0f}°）")
        rw.add("最小导角长度", f"Zmin ≥ {asm['lead_zmin']:.2f} mm", bold=True)
        rw.add("表面粗糙度", f"Ra ≤ {mc['ra_static']} μm")

        # 装配校核
        rw = self.row_fit
        rw.clear()
        rw.add("压缩量 c", f"{m['compression_mm']:.3f} mm", bold=True)
        rw.add("O 圈截面积", f"{m['oring_area']:.2f} mm²")
        if m["gap_allow"] is not None:
            gap_txt = f"{m['gap_allow']:.3f} mm（单侧）"
            rw.add("允许挤出间隙", gap_txt)
        else:
            rw.add("允许挤出间隙", "超出常规适用范围", color=BAD)
        if m["clearance"] is not None:
            cl = m["clearance"]
            ga = m["gap_allow"]
            st_color = OK if (ga is not None and cl <= ga) else BAD
            rw.add("设计单侧间隙", f"{cl:.3f} mm", color=st_color, bold=True)
        if m["backup_n"] > 0:
            rw.add("挡圈", f"需要 {m['backup_n']} 个"
                           f"（占槽宽 {g['b_backup']:.2f} mm）",
                   color=WARN, bold=True)
        else:
            rw.add("挡圈", "可不配置", color=TEXT)
        rw.add("挡圈判定", m["backup_src"], color=TEXT_DIM)
        ho = r.get("housing") or {}
        if ho.get("code"):
            rw.add_sep()
            rw.add("壳体材料", f"{ho['name']}（{ho['group']}）", bold=True)
            rw.add("线膨胀系数", f"{ho['alpha']:.1f} ×10⁻⁶/K")
            rw.add("热漂移", f"{ho['d_comp_pp']:+.2f} 个百分点（至 {ho['dT']:.0f} ℃）",
                   color=TEXT_DIM)
            if ho.get("creep_pp"):
                rw.add("蠕变补偿", f"+{ho['creep_pp']:.1f} 个百分点", color=WARN)
        rw.add_sep()
        rw.add("填充率 K", f"{m['fill_pct']:.1f}%")

        # 输入框下方的自动推荐提示
        self.lbl_d2.setText(self._d2_hint(o, r))
        self.lbl_b.setText(self._b_hint(g))

        # 校核结论
        self._clear_warn()
        if r["warnings"]:
            for w in r["warnings"]:
                self._add_warn(w, "warn")
        else:
            self._add_warn("各项校核均在推荐范围内，设计可用。", "ok")
        for n in r["notes"]:
            self._add_warn(n, "warn")

        # 材料面板
        rw = self.row_mat
        rw.clear()
        rw.add("推荐材料", mat["code"], bold=True, color=ACCENT)
        rw.add("材料名称", mat["name"])
        rw.add("耐温范围", f"{mat['t_range'][0]} ~ {mat['t_range'][1]} ℃",
               color=OK if (mat["t_range"][0] <= r["input"]["t_low"]
                            and mat["t_range"][1] >= r["input"]["t_high"]) else BAD)
        rw.add("介质相容性", f"{mat['media_score']} / 5")
        rw.add("相对成本", "◆" * mat["cost"] + "◇" * (5 - mat["cost"]))
        rw.add_sep()
        rw.add("推荐硬度", f"{hd['value']} Shore A", bold=True, color=ACCENT)
        rw.add("硬度依据", hd["why"], color=TEXT_DIM)
        rw.add("压缩率依据", r["compression_src"]["why"], color=TEXT_DIM)
        self.lbl_mat_note.setText(
            f"优点：{mat['pros']}\n局限：{mat['cons']}\n适用：{mat['usage']}")

        rank = mat["ranking"][:6]
        self.tbl_alt.setRowCount(len(rank))
        for i, it in enumerate(rank):
            vals = [f"{it['code']}　{it['name']}", f"{it['score']:.2f}",
                    f"{it['temp_range'][0]}~{it['temp_range'][1]} ℃",
                    "★" * it["media_score"] + "☆" * (5 - it["media_score"])]
            for j, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                if j == 1:
                    cell.setForeground(QColor(OK if i == 0 else TEXT))
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 3:
                    cell.setForeground(QColor(ACCENT))
                self.tbl_alt.setItem(i, j, cell)
        self.tbl_alt.resizeRowsToContents()

        self.diagram.set_result(r)

    def _d2_hint(self, o, r) -> str:
        """线径输入框下方的说明：当前取值 + 自动推荐值。"""
        auto = recommend_d2(r["input"]["surface_dia"], r["input"]["pressure"],
                            "axial" if self.group != "radial" else "radial")
        tag = d2_family(o["d2"])[1]
        if o["d2_src"] == "自动推荐":
            return f"自动推荐 {o['d2']:.2f} mm（{tag}系列）"
        if abs(auto - o["d2"]) < 1e-9:
            return f"手动选定 {o['d2']:.2f} mm（{tag}系列），与自动推荐一致"
        return (f"手动选定 {o['d2']:.2f} mm（{tag}系列）；"
                f"按密封面直径与压力自动推荐为 {auto:.2f} mm")

    def _b_hint(self, g) -> str:
        """槽宽输入框下方的说明：自动推荐值与它的构成。"""
        if g["b_src"] == "手动指定":
            return (f"自动推荐 {g['b_auto']:.2f} mm，"
                    f"当前手动取值 {g['b']:.2f} mm")
        parts = [f"标准槽宽 {g['b_std']:.2f}"]
        if g["temp_factor"] > 1.001:
            parts.append(f"× 高温修正 {g['temp_factor']:.3f}")
        if g["b_backup"] > 0:
            parts.append(f"+ 挡圈占位 {g['b_backup']:.2f}")
        return f"自动推荐 {g['b']:.2f} mm（{' '.join(parts)}）"

    def _mode_name(self) -> str:
        for k, n in self.kinds:
            if k == self.mode:
                return n
        return self.mode

    # ---------------- 导出 ----------------
    def _export(self):
        if self._res is None:
            QMessageBox.warning(self, "无可导出内容", "请先完成一次有效计算。")
            return
        default = (f"O圈设计报告_{self._mode_name()}_"
                   f"{datetime.datetime.now():%Y%m%d_%H%M}.html")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出设计报告", default, "网页报告 (*.html);;文本文件 (*.txt)")
        if not path:
            return
        try:
            if path.lower().endswith(".txt"):
                content = self._report_text()
            else:
                content = self._report_html()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            QMessageBox.critical(self, "写入失败", str(e))
            return
        QMessageBox.information(self, "导出完成", f"报告已保存到：\n{path}")

    def _rows_of(self, rl: RowList):
        """取出键值行，跳过 add_sep() 插入的分隔线（QFrame 没有 text()）。"""
        out = []
        g = rl.grid
        for i in range(g.rowCount()):
            k = g.itemAtPosition(i, 0)
            v = g.itemAtPosition(i, 1)
            if not (k and v):
                continue
            kw, vw = k.widget(), v.widget()
            if isinstance(kw, QLabel) and isinstance(vw, QLabel):
                out.append((kw.text(), vw.text()))
        return out

    def _preset_text(self) -> str:
        idx = self.in_preset.combo.currentIndex()
        if idx <= 0:
            return "手动输入"
        return PRESSURE_PRESETS[idx]["label"]

    def _report_text(self) -> str:
        r = self._res
        L = []
        L.append("=" * 62)
        L.append("           O 形密封圈设计计算报告")
        L.append("=" * 62)
        L.append(f"生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
        L.append(f"密封型式：{self._mode_name()}")
        i = r["input"]
        L.append("")
        L.append("【一、工况参数】")
        L.append(f"  {r['geometry']['surface_label']}：{i['surface_dia']:.2f} mm")
        L.append(f"  工作压力：{i['pressure']:.2f} MPa")
        L.append(f"  压力来源：{self._preset_text()}")
        L.append(f"  工作介质：{i['medium']}")
        L.append(f"  运动方式：{i['motion']}")
        L.append(f"  工作温度：{i['t_low']:.0f} ~ {i['t_high']:.0f} ℃")
        for title, rl in (("【二、密封圈规格】", self.row_oring),
                          ("【三、沟槽设计参数】", self.row_groove),
                          ("【四、装配校核】", self.row_fit)):
            L.append("")
            L.append(title)
            for k, v in self._rows_of(rl):
                L.append(f"  {k}：{v}")
        L.append("")
        L.append("【五、材料与硬度】")
        for k, v in self._rows_of(self.row_mat):
            L.append(f"  {k}：{v}")
        L.append("")
        L.append("【六、校核结论】")
        if r["warnings"]:
            for w in r["warnings"]:
                L.append(f"  ⚠ {w}")
        else:
            L.append("  ✓ 各项校核均在推荐范围内。")
        for n in r["notes"]:
            L.append(f"  · {n}")
        L.append("")
        L.append("-" * 62)
        L.append(DESIGN_DOC)
        return "\n".join(L)

    def _report_html(self) -> str:
        r = self._res
        i = r["input"]

        def tbl(rl):
            rows = "".join(
                f"<tr><td class='k'>{html.escape(k)}</td>"
                f"<td class='v'>{html.escape(v)}</td></tr>"
                for k, v in self._rows_of(rl))
            return f"<table>{rows}</table>"

        warn = "".join(f"<li class='w'>{html.escape(w)}</li>" for w in r["warnings"]) \
            or "<li class='o'>各项校核均在推荐范围内，设计可用。</li>"
        notes = "".join(f"<li>{html.escape(n)}</li>" for n in r["notes"])
        alt = "".join(
            f"<tr><td>{it['code']}　{it['name']}</td><td class='c'>{it['score']:.2f}</td>"
            f"<td class='c'>{it['temp_range'][0]}~{it['temp_range'][1]} ℃</td>"
            f"<td class='c'>{'★' * it['media_score']}{'☆' * (5 - it['media_score'])}</td></tr>"
            for it in r["material"]["ranking"][:6])

        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>O 形密封圈设计计算报告</title>
<style>
 body {{ font-family:"Microsoft YaHei","Segoe UI",sans-serif; color:#1F2933;
        max-width:880px; margin:36px auto; padding:0 22px; line-height:1.7; }}
 h1 {{ font-size:22px; border-bottom:2px solid #2F6FED; padding-bottom:10px; }}
 h2 {{ font-size:15px; color:#2F6FED; margin-top:26px;
       border-left:3px solid #2F6FED; padding-left:9px; }}
 table {{ width:100%; border-collapse:collapse; margin:8px 0; font-size:13.5px; }}
 td {{ border:1px solid #E3E7ED; padding:7px 11px; }}
 td.k {{ background:#F7F9FC; width:42%; color:#4A5A6A; }}
 td.v {{ font-weight:600; text-align:right; }}
 td.c {{ text-align:center; }}
 ul {{ padding-left:20px; }}
 li.w {{ color:#8A5A12; background:#FFF9F0; margin:5px 0; padding:6px 10px;
         border-radius:5px; list-style:none; }}
 li.o {{ color:#0B7A3C; background:#F1FBF5; padding:6px 10px; border-radius:5px;
         list-style:none; }}
 .meta {{ color:#7A8794; font-size:12.5px; }}
 footer {{ margin-top:34px; padding-top:14px; border-top:1px solid #E3E7ED;
           color:#7A8794; font-size:11.5px; white-space:pre-wrap; }}
</style></head><body>
<h1>O 形密封圈设计计算报告</h1>
<p class="meta">生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}　|　
密封型式：{html.escape(self._mode_name())}</p>

<h2>一、工况参数</h2>
<table>
<tr><td class="k">{html.escape(r['geometry']['surface_label'])}</td>
    <td class="v">{i['surface_dia']:.2f} mm</td></tr>
<tr><td class="k">工作压力</td><td class="v">{i['pressure']:.2f} MPa</td></tr>
<tr><td class="k">压力来源</td>
    <td class="v">{html.escape(self._preset_text())}</td></tr>
<tr><td class="k">工作介质</td><td class="v">{html.escape(i['medium'])}</td></tr>
<tr><td class="k">运动方式</td><td class="v">{html.escape(i['motion'])}</td></tr>
<tr><td class="k">工作温度</td>
    <td class="v">{i['t_low']:.0f} ~ {i['t_high']:.0f} ℃</td></tr>
</table>

<h2>二、密封圈规格</h2>{tbl(self.row_oring)}
<h2>三、沟槽设计参数</h2>{tbl(self.row_groove)}
<h2>四、装配校核</h2>{tbl(self.row_fit)}

<h2>五、材料与硬度选型</h2>{tbl(self.row_mat)}
<h3 style="font-size:13.5px;margin-top:16px">备选材料排序</h3>
<table><tr><td class="k">材料</td><td class="k">评分</td>
<td class="k">耐温</td><td class="k">介质相容性</td></tr>{alt}</table>

<h2>六、校核结论</h2>
<ul>{warn}</ul>
{f"<ul>{notes}</ul>" if notes else ""}

<footer>{html.escape(DESIGN_DOC)}</footer>
</body></html>"""


# =====================================================================
# 标准尺寸库
# =====================================================================

class StandardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        bar = Card()
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel("筛选"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("输入内径 / 外径数值，例如 25")
        self.search.setMaximumWidth(260)
        row.addWidget(self.search)
        row.addWidget(QLabel("线径"))
        self.cb_d2 = QComboBox()
        self.cb_d2.addItem("全部")
        for x in D2_ALL:
            self.cb_d2.addItem(f"{x:.2f}")
        self.cb_d2.setMinimumWidth(90)
        row.addWidget(self.cb_d2)
        row.addWidget(QLabel("系列"))
        self.cb_tag = QComboBox()
        self.cb_tag.addItems(["全部", "公制", "英制", "通用"])
        row.addWidget(self.cb_tag)
        row.addStretch(1)
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("CardHint")
        row.addWidget(self.lbl_count)
        bar.body.addLayout(row)
        root.addWidget(bar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "内径 d1 (mm)", "线径 d2 (mm)", "外径 d0 (mm)", "截面积 (mm²)",
            "静密封槽深", "静密封槽宽", "动密封槽深", "动密封槽宽", "轴向槽深 / 槽宽"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        hint = QLabel("提示：双击任意一行可将该规格复制到剪贴板。槽深 / 槽宽按 GB/T 3452.3 "
                      "标准锚点值随线径插值（未计入挡圈占位与高温修正），供选型参考。")
        hint.setObjectName("CardHint")
        root.addWidget(hint)

        self._all = []
        self._build()
        self.search.textChanged.connect(self._filter)
        self.cb_d2.currentIndexChanged.connect(self._filter)
        self.cb_tag.currentIndexChanged.connect(self._filter)
        self.table.itemDoubleClicked.connect(self._copy_row)

    def _build(self):
        rows = []
        for d2 in D2_ALL:
            lo, hi = d1_range(d2)
            st = groove_std_pair(d2, "static")
            dy = groove_std_pair(d2, "dynamic")
            ax = groove_std_pair(d2, "axial")
            tag = D2_TAG[d2]
            for d1 in D1_SERIES:
                if not (lo <= d1 <= hi):
                    continue
                d0 = d1 + 2 * d2
                area = math.pi * (d2 / 2) ** 2
                rows.append([f"{d1:.2f}", f"{d2:.2f}", f"{d0:.2f}", f"{area:.2f}",
                             f"{st[0]:.2f}", f"{st[1]:.2f}",
                             f"{dy[0]:.2f}", f"{dy[1]:.2f}",
                             f"{ax[0]:.2f} / {ax[1]:.2f}", tag])
        self._all = rows
        self._render(rows)

    def _render(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate(r[:9]):
                cell = QTableWidgetItem(v)
                if j >= 1:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, j, cell)
        self.table.setSortingEnabled(True)
        self.lbl_count.setText(f"共 {len(rows)} 条规格")

    def _filter(self):
        kw = self.search.text().strip()
        d2f = self.cb_d2.currentText()
        tagf = self.cb_tag.currentText()
        rows = []
        for r in self._all:
            if d2f != "全部" and r[1] != d2f:
                continue
            if tagf != "全部" and r[9] != tagf:
                continue
            if kw:
                try:
                    v = float(kw)
                    if abs(float(r[0]) - v) > 0.6 and abs(float(r[2]) - v) > 0.6:
                        continue
                except ValueError:
                    continue
            rows.append(r)
        self._render(rows)

    def _copy_row(self, item):
        row = item.row()
        vals = [self.table.item(row, c).text() for c in range(self.table.columnCount())]
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(
            f"内径 d1={vals[0]} mm，线径 d2={vals[1]} mm，外径 d0={vals[2]} mm")
        QMessageBox.information(self, "已复制", f"O 形圈规格已复制：\n"
                                f"φ{vals[0]} × {vals[1]}（外径 φ{vals[2]}）")


# =====================================================================
# 材料选型库
# =====================================================================

class MaterialPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        c0 = Card("按介质快速筛选", "选择介质与温度区间，查看材料推荐排序")
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(QLabel("介质"))
        self.cb_med = QComboBox()
        self.cb_med.addItems(MEDIA_LIST)
        row.addWidget(self.cb_med, 2)
        row.addWidget(QLabel("最低温"))
        self.ed_lo = QLineEdit("20")
        self.ed_lo.setMaximumWidth(70)
        row.addWidget(self.ed_lo)
        row.addWidget(QLabel("最高温"))
        self.ed_hi = QLineEdit("80")
        self.ed_hi.setMaximumWidth(70)
        row.addWidget(self.ed_hi)
        btn = QPushButton("筛选")
        btn.setObjectName("Primary")
        btn.clicked.connect(self._rank)
        row.addWidget(btn)
        row.addStretch(1)
        self.lbl_res = QLabel("")
        self.lbl_res.setObjectName("CardHint")
        row.addWidget(self.lbl_res, 2)
        c0.body.addLayout(row)
        root.addWidget(c0)

        c1 = Card("材料性能总表")
        self.tbl_mat = QTableWidget(0, 6)
        self.tbl_mat.setHorizontalHeaderLabels(
            ["代号", "材料名称", "耐温范围 (℃)", "常用硬度 (Shore A)", "相对成本", "特点与适用"])
        self.tbl_mat.verticalHeader().setVisible(False)
        self.tbl_mat.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_mat.setWordWrap(True)
        hh = self.tbl_mat.horizontalHeader()
        for i in range(5):
            hh.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl_mat.setMinimumHeight(300)
        self._fill_materials()
        c1.add(self.tbl_mat)
        root.addWidget(c1, 2)

        c2 = Card("介质相容性矩阵", "5 = 优异，0 = 不可用")
        self.tbl_mx = QTableWidget(0, len(MEDIA_LIST) + 1)
        self.tbl_mx.setHorizontalHeaderLabels(["材料"] + MEDIA_LIST)
        self.tbl_mx.verticalHeader().setVisible(False)
        self.tbl_mx.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_mx.setMinimumHeight(280)
        self._fill_matrix()
        c2.add(self.tbl_mx)
        root.addWidget(c2, 2)

        self._rank()

    def _fill_materials(self):
        self.tbl_mat.setRowCount(len(MATERIALS))
        for i, m in enumerate(MATERIALS):
            vals = [m.code, m.name, f"{m.tmin} ~ {m.tmax}",
                    f"{m.hard_range[0]} ~ {m.hard_range[1]}",
                    "◆" * m.cost + "◇" * (5 - m.cost),
                    f"{m.pros}。局限：{m.cons}。适用：{m.usage}"]
            for j, v in enumerate(vals):
                cell = QTableWidgetItem(v)
                if j == 0:
                    cell.setForeground(QColor(ACCENT))
                    f = QFont()
                    f.setBold(True)
                    cell.setFont(f)
                if j in (2, 3, 4):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_mat.setItem(i, j, cell)
        self.tbl_mat.resizeRowsToContents()

    def _fill_matrix(self):
        colors = {0: "#F3C4C4", 1: "#F6DCC2", 2: "#F8EFC6", 3: "#DCEBC7",
                  4: "#C2E4C8", 5: "#A0DEB1"}
        self.tbl_mx.setRowCount(len(MATERIALS))
        for i, m in enumerate(MATERIALS):
            cell = QTableWidgetItem(m.code)
            f = QFont()
            f.setBold(True)
            cell.setFont(f)
            self.tbl_mx.setItem(i, 0, cell)
            for j, med in enumerate(MEDIA_LIST, start=1):
                s = m.media.get(med, 2)
                c = QTableWidgetItem(str(s))
                c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                c.setBackground(QColor(colors[s]))
                c.setForeground(QColor("#2B3A4A"))
                self.tbl_mx.setItem(i, j, c)
        self.tbl_mx.resizeColumnsToContents()
        self.tbl_mx.setColumnWidth(0, 76)

    def _rank(self):
        try:
            lo = float(self.ed_lo.text() or 20)
            hi = float(self.ed_hi.text() or 80)
        except ValueError:
            self.lbl_res.setText("温度需为数值")
            return
        rk = recommend_materials(lo, hi, self.cb_med.currentText())
        top = [f"{x['code']}" for x in rk[:3]]
        best = rk[0]
        self.lbl_res.setText(
            f"推荐序：{' > '.join(top)}　｜　首选 {best['code']} "
            f"（{best['name']}，评分 {best['score']:.2f}）")

        order = {x["code"]: i for i, x in enumerate(rk)}
        for i, m in enumerate(MATERIALS):
            self.tbl_mat.item(i, 0).setText(
                f"{m.code}" + ("　★推荐" if order[m.code] == 0 else ""))
            self.tbl_mat.item(i, 0).setForeground(
                QColor(OK) if order[m.code] == 0 else QColor(ACCENT))


# =====================================================================
# 使用说明
# =====================================================================

HELP_HTML = """
<style>
 body { font-family:"Microsoft YaHei UI","Microsoft YaHei",sans-serif;
        color:#1F2933; font-size:13.5px; line-height:1.85; }
 h2 { font-size:15px; color:#2F6FED; border-left:3px solid #2F6FED;
      padding-left:9px; margin-top:22px; }
 h3 { font-size:13.5px; margin-top:16px; color:#2B3A4A; }
 code { background:#F1F4F8; padding:2px 6px; border-radius:4px;
        font-family:Consolas,monospace; color:#1B4DA0; }
 table { border-collapse:collapse; width:100%; margin:8px 0; font-size:13px; }
 td, th { border:1px solid #E3E7ED; padding:6px 10px; }
 th { background:#F7F9FC; text-align:left; font-weight:600; color:#4A5A6A; }
 .warn { background:#FFF9F0; border-left:3px solid #E8901A; padding:9px 13px;
         border-radius:5px; color:#8A5A12; margin:10px 0; }
</style>

<h2>一、三种密封型式的输入口径</h2>
<table>
<tr><th>型式</th><th>「密封面直径」填写什么</th><th>密封发生位置</th></tr>
<tr><td>活塞密封</td><td>缸孔（缸筒内壁）直径 D</td><td>O 圈外径压向缸孔壁</td></tr>
<tr><td>活塞杆密封</td><td>活塞杆外径 d</td><td>O 圈内径压向杆的外圆</td></tr>
<tr><td>端面密封</td><td>沟槽中心直径 dm</td><td>两个法兰平面夹紧 O 圈</td></tr>
</table>

<h2>二、核心计算公式</h2>
<h3>压缩率与压缩量</h3>
<p><code>压缩量 c = d2 − h</code>　　<code>压缩率 ε = (d2 − h) / d2 × 100%</code></p>
<p>其中 d2 为 O 圈线径（截面直径），h 为沟槽深度。压缩率是 O 圈产生初始接触应力、
实现密封的根本来源。取值过大装配困难且加速老化，过小则回弹补偿不足而泄漏。</p>
<p><b>压缩率允许范围取自 GB/T 3452.3-2005 附录 A</b>。该表按「工况类别 × 线径」给出区间：
<b>静密封明显高于动密封，且线径越大允许区间越低</b>。本程序推荐值与校核区间都直接用这张表，
非标准线径在相邻档之间线性插值（超出 1.80~7.00 时收敛到最近档，不作外推）：</p>
<table>
<tr><th>压缩率 %</th><th>1.80</th><th>2.65</th><th>3.55</th><th>5.30</th><th>7.00</th></tr>
<tr><td>图A.3 液压、气动静密封</td><td>13.5~30.5</td><td>13.0~28.0</td><td>11.5~27.5</td><td>11.0~26.0</td><td>10.5~24.0</td></tr>
<tr><td>图A.1 液压动密封</td><td>13.0~28.5</td><td>11.5~24.0</td><td>9.5~23.0</td><td>9.0~20.5</td><td>9.0~19.5</td></tr>
<tr><td>图A.2 气动动密封</td><td>9.5~25.5</td><td>8.5~22.0</td><td>6.5~20.0</td><td>5.5~17.0</td><td>5.0~15.5</td></tr>
<tr><td>图A.4 轴向密封</td><td>22.5~34.5</td><td>21.0~30.0</td><td>19.0~26.0</td><td>16.0~24.0</td><td>15.0~21.0</td></tr>
</table>
<p>取值方法：先算<b>标准沟槽深度</b>（同标准表1/表2/表3）隐含的压缩率作为基准，
静密封再向区间上部靠拢（建立可靠初始接触应力），动密封向中下部靠拢（减小摩擦与发热），
最后按压力与硬度在区间内微调。回转密封国标未单列，按动密封中最低的一档从严取值。</p>
<div class="warn"><b>浸水防护（IPX7 / IPX8）属静密封工况</b>，运动方式应选「静态」，
压缩率按图A.3 静密封表取值——通常落在 15%~30%，远高于动密封的 10%~20%。
若误按「往复」设计，压缩量会明显不足，深水或长期浸泡时极易渗漏。
深水或长期浸泡建议取区间上部，并加装挡圈抑制挤出。</div>

<h3>拉伸率</h3>
<p><code>δ = (沟槽底径 − O 圈内径) / O 圈内径 × 100%</code>（径向密封）</p>
<p>轻微的拉伸（通常 1%~4%）能让 O 圈紧贴沟槽、装配时不易脱落；但拉伸过大
会使截面变细、加速老化，导致密封失效。轴向密封则按「自由中径 = 内径 + 线径
与沟槽中心直径对齐」校核。</p>

<h3>填充率</h3>
<p><code>K = O 圈截面积 / 沟槽截面积 × 100%</code></p>
<p>典型值 65%~85%。偏高说明沟槽空间不足，胶料受热膨胀或介质溶胀后无处可去；
偏低说明沟槽过空，O 圈可能在介质压力下翻滚、扭曲（螺旋损伤）。</p>

<h3>槽宽与槽深</h3>
<p>槽深由压缩率反算：<code>h = d2 × (1 − ε)</code>。槽宽 <code>b</code> 与标准槽深
逐值取自 <b>GB/T 3452.3-2005 表1 / 表2 / 表3</b>（径向密封与轴向密封）。标准只列出
1.80 / 2.65 / 3.55 / 5.30 / 7.00 mm 五档线径，其余线径按相邻档线性插值。另有两项修正：</p>
<p>· <b>高温修正</b>：工作温度超过 100 ℃ 时按温升放宽容槽 1%~5%，为胶料热膨胀留空间。<br>
· <b>挡圈占位</b>：需要挡圈时，每个挡圈按标准表1 的 b → b₁ → b₂ 差值占用槽宽，即
1.40 mm（d₂ ≤ 3.55）、1.90 mm（d₂ = 5.30）、2.80 mm（d₂ = 7.00）；
往复 / 回转为双作用，自动按两侧各一个计。</p>
<p>槽宽可以留空交给程序推荐，也可以手动填写覆盖它 —— 输入框下方会同时显示
自动推荐值，便于对比。</p>

<h3>壳体（沟槽）材料</h3>
<p>壳体材料从三方面影响设计，选定后程序会自动计入：</p>
<table>
<tr><th>影响途径</th><th>机理</th><th>程序处理</th></tr>
<tr><td>线膨胀系数 α</td><td>温度变化时沟槽与 O 圈各自胀缩，压缩率漂移 ≈ ΔT·(α<sub>橡胶</sub> − α<sub>壳体</sub>)</td><td>给出漂移量；高温下越出允许区间则告警</td></tr>
<tr><td>弹性模量 E</td><td>塑料壳体刚度低，受压后沟槽变形、张开间隙</td><td>超出经验许用压力时告警，建议加挡圈或加金属嵌件</td></tr>
<tr><td>蠕变 / 应力松弛</td><td>塑料长期受压会失去部分压缩量</td><td>初始压缩率在标准区间内上浮 1.5 个百分点补偿</td></tr>
</table>
<p>金属壳体 α：铸铁 10.5、碳钢 11.7、不锈钢 17.3、黄铜 19.0、铝合金 23.6 ×10⁻⁶/K
—— 尺寸稳定，但 α 越小升温后压缩率增量越大。塑料壳体 α 明显更大：PC 68、ABS 85、
PA66 90、POM 110、PP 120 ×10⁻⁶/K，温变时压缩率更稳定，但需重点关注受压变形与蠕变。</p>

<h3>安装圆角与导入倒角</h3>
<p>O 圈在装配时非常脆弱，锐利棱边会像刀片一样割伤它。按 GB/T 3452.3-2005 表1 / 表3：</p>
<table>
<tr><th>项目</th><th>符号</th><th>推荐值</th></tr>
<tr><td>槽底圆角</td><td>r₁</td><td>0.20~0.40（d₂ ≤ 2.65）/ 0.40~0.80（3.55~5.30）/ 0.80~1.20（≥ 7.00）mm</td></tr>
<tr><td>槽口（棱）圆角</td><td>r₂</td><td>0.10~0.30 mm</td></tr>
<tr><td>导入倒角角度</td><td>θ</td><td>15°~30°，推荐 20°（国标未规定角度，此为行业通行值）</td></tr>
<tr><td>最小导角长度</td><td>Z<sub>min</sub></td><td>1.10 / 1.50 / 1.80 / 2.70 / 3.60 mm（按线径，标准表1 明列）</td></tr>
</table>
<p>表面粗糙度：静密封 Ra ≤ 0.8 μm，动密封 Ra ≤ 0.4 μm；所有 O 圈经过的棱边必须
去毛刺、去飞边。装配前在 O 圈与导入角涂抹与介质相容的润滑剂，可显著降低安装损伤。</p>

<h2>三、常用工况压力与水深的换算</h2>
<p>工作压力可手动填写，也可以从「常用工况预设」里直接选：真空 / 微压、气动
（0.4 / 0.63 / 1.0 MPa）、水深、液压公称压力（GB/T 2346 系列）以及民用管路
（自来水、热水、制动系统）。选中预设会一并带入该场景的介质、运动方式与温度，
压力值随后仍可手动修改。</p>
<p>水深按静水压换算：<code>p = ρ g h</code>，取 ρ = 1000 kg/m³、g = 9.80665 m/s²，
即 <b>1 m 水柱 ≈ 0.0098 MPa</b>。</p>
<table>
<tr><th>水深</th><th>3 m</th><th>5 m</th><th>10 m</th><th>20 m</th><th>30 m</th><th>50 m</th><th>100 m</th><th>300 m</th></tr>
<tr><td>静水压 (MPa)</td><td>0.029</td><td>0.049</td><td>0.098</td><td>0.196</td>
<td>0.294</td><td>0.491</td><td>0.981</td><td>2.94</td></tr>
</table>
<div class="warn">水深给出的是<b>静水压</b>。潜水泵、水下执行机构等场合还要叠加
泵的出口压力或机构动作压力，应按「静水压 + 工作压差」的合成值填写，程序不会
替你叠加。</div>

<h2>四、线径系列</h2>
<p>线径下拉框给出 26 种常用规格：GB/T 3452.1 公制优先数系（1.80 / 2.65 /
3.55 / 5.30 / 7.00）、AS568 与 ISO 3601-1 英制折算值（1.78 / 2.62 / 3.53 /
5.33 / 6.99 / 9.53），以及常见的通用商用品径（1.0 ~ 12 mm）。线径公差按
GB/T 3452.1 分档自动给出。若供货规格不在列表中，可直接在下拉框里输入任意
数值（0.8 ~ 15 mm）。</p>

<h2>五、挤出间隙与挡圈</h2>
<p>压力把 O 圈推向密封间隙，硬度和压力共同决定了允许的单侧间隙上限。程序按
Parker 工程手册的间隙表插值。一旦设计间隙超过允许值（或压力超过 10 MPa），
会提示需要挡圈，否则胶料被挤入间隙后会被剪切咬伤。</p>
<p>挡圈配置可选「自动判定 / 不加挡圈 / 单侧挡圈 / 两侧各一个」。需要挡圈时，
程序会把挡圈占用的宽度计入槽宽推荐值；由于挡圈本身占去了一部分沟槽空间，
填充率的校核下限也相应从 60% 放宽到 45%。<b>挡圈厚度是估算值，订货前请以
挡圈供应商样本复核槽宽。</b></p>

<h2>六、槽深槽宽的加工公差</h2>
<table>
<tr><th>项目</th><th>建议公差</th></tr>
<tr><td>槽深 h</td><td>±0.03 ~ ±0.08 mm（按线径分档）</td></tr>
<tr><td>槽宽 b</td><td>+0.10 / 0</td></tr>
<tr><td>槽底径</td><td>h9</td></tr>
<tr><td>沟槽外径</td><td>H9</td></tr>
<tr><td>槽口</td><td>倒角或圆角并去毛刺，导入角 15°~30°</td></tr>
<tr><td>表面粗糙度</td><td>静密封 Ra ≤ 0.8 μm；动密封 Ra ≤ 0.4 μm</td></tr>
</table>

<h2>七、材料与硬度选型要点</h2>
<p>程序先按「温度区间能否覆盖」筛选，再按介质相容性打分，最后按运动方式
和成本微调。硬度则主要随工作压力升高：真空与微压用 60 A 左右的软胶以保证
贴合，中压 70 A，高压 80 A，超高压 90 A 以上并必须配挡圈。</p>
<div class="warn">典型的致命误选：用 NBR 接触制动液（DOT3/DOT4）或磷酸酯液压油，
用 EPDM 接触矿物液压油与燃油。前者会被溶胀腐蚀，后者会直接溶胀失效。
请在选型前务必核对介质。</div>

<h2>八、使用建议</h2>
<p>1. 界面上除「密封面直径」外均有自动推荐值，可先全部留空看一遍推荐结果，
再按实际供货规格逐项覆盖。线径、槽宽、压力、硬度都支持手动填写覆盖自动值。</p>
<p>2. 关键参数（压缩率、拉伸率、填充率）卡片显示绿色为落在推荐区间，
橙色为临界，红色为超出，请以红色项为重点复核对象。</p>
<p>3. 「导出报告」可生成 HTML 或 TXT 设计报告，含全部输入输出与校核结论，
可直接归档或发给供应商。</p>
"""


class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        c = Card()
        from PySide6.QtWidgets import QTextBrowser
        tb = QTextBrowser()
        tb.setOpenExternalLinks(False)
        tb.setFrameShape(QFrame.Shape.NoFrame)
        tb.setStyleSheet("background:transparent;border:none;")
        tb.setHtml(HELP_HTML)
        c.add(tb)
        root.addWidget(c, 1)
