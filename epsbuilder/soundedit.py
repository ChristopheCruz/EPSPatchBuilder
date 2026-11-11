"""Editeur du son selectionne : forme d'onde, debut et fin, boucle, frequence, resolution, compression."""
from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import i18n
from .i18n import T
from . import audio, instrument as ins
from .project import SoundEdit

MARKERS = ("start", "end", "loop_start", "loop_end")
MARKER_COLORS = {"start": "#1F8A4C", "end": "#C0392B", "loop_start": "#B7791F", "loop_end": "#B7791F"}
def marker_labels() -> dict[str, str]:
    """Lettres des reperes : Debut, Fin, Boucle (Start, End, Loop en anglais)."""
    d, f, b = (T("D"), T("F"), T("B"))
    return {"start": d, "end": f, "loop_start": b, "loop_end": b}
LOOP_MODES = [(ins.LOOP_FORWARD_NO_LOOP, T("Sans boucle")), (ins.LOOP_FORWARD, T("Boucle avant")),
              (ins.LOOP_BIDIRECTIONAL, T("Boucle aller-retour")), (ins.LOOP_AND_RELEASE, T("Boucle puis relâchement")),
              (ins.LOOP_BACKWARD_NO_LOOP, T("À l'envers, sans boucle"))]
BIT_CHOICES = [(13, T("13 bits (EPS)")), (12, T("12 bits")), (10, T("10 bits")), (8, T("8 bits")), (6, T("6 bits"))]


class WaveView(QtWidgets.QWidget):
    """Forme d'onde avec reperes deplacables : D (debut), F (fin) et les deux bords de la boucle."""
    markerMoved = QtCore.Signal(str, int)
    markerReleased = QtCore.Signal()
    GRAB = 7

    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = np.zeros(0)
        self.positions: dict[str, int] = {}
        self.show_loop = False
        self._peaks = None
        self._drag = None
        self.setMinimumHeight(96)
        self.setMouseTracking(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_sound(self, samples: np.ndarray):
        self.samples = np.asarray(samples, dtype=np.float64)
        self._peaks = None
        self.update()

    def set_markers(self, positions: dict[str, int], show_loop: bool):
        self.positions, self.show_loop = dict(positions), show_loop
        self.update()

    # -- geometrie
    def _x(self, index: int) -> float:
        n = max(1, len(self.samples) - 1)
        return index / n * (self.width() - 1)

    def _index(self, x: float) -> int:
        n = max(1, len(self.samples) - 1)
        return int(round(max(0.0, min(x, self.width() - 1)) / max(1, self.width() - 1) * n))

    def _visible(self):
        return [m for m in MARKERS if m in self.positions and (self.show_loop or not m.startswith("loop"))]

    def _marker_at(self, x: float):
        best = None
        for name in self._visible():
            d = abs(x - self._x(self.positions[name]))
            if d <= self.GRAB and (best is None or d < best[0]):
                best = (d, name)
        return best[1] if best else None

    def resizeEvent(self, _event):
        self._peaks = None

    def _compute_peaks(self):
        w = max(1, self.width())
        n = len(self.samples)
        if n == 0:
            return np.zeros(w), np.zeros(w)
        edges = np.linspace(0, n, w + 1).astype(np.int64)
        starts = np.minimum(edges[:-1], n - 1)
        hi = np.maximum.reduceat(self.samples, starts)
        lo = np.minimum.reduceat(self.samples, starts)
        return lo, hi

    # -- souris
    def mousePressEvent(self, event):
        self._drag = self._marker_at(event.position().x())

    def mouseMoveEvent(self, event):
        x = event.position().x()
        if self._drag and event.buttons() & Qt.LeftButton:
            self.markerMoved.emit(self._drag, self._index(x))
        else:
            self.setCursor(Qt.SizeHorCursor if self._marker_at(x) else Qt.ArrowCursor)

    def mouseReleaseEvent(self, _event):
        if self._drag:
            self._drag = None
            self.markerReleased.emit()

    # -- dessin
    def paintEvent(self, _event):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QtGui.QColor("#FBFBFC"))
        if len(self.samples) == 0:
            p.setPen(QtGui.QColor("#8A8F98"))
            p.drawText(self.rect(), Qt.AlignCenter, T("Sélectionnez un son dans la liste pour le régler."))
            p.end()
            return
        if self._peaks is None:
            self._peaks = self._compute_peaks()
        lo, hi = self._peaks
        mid, scale = h / 2.0, (h / 2.0 - 12)
        start = self.positions.get("start", 0)
        end = self.positions.get("end", len(self.samples) - 1)
        xs, xe = self._x(start), self._x(end)
        if self.show_loop and "loop_start" in self.positions:
            xl, xr = self._x(self.positions["loop_start"]), self._x(self.positions["loop_end"])
            p.fillRect(QtCore.QRectF(xl, 0, max(1.0, xr - xl), h), QtGui.QColor(247, 201, 72, 70))
        p.setPen(QtGui.QColor("#D5D8DD"))
        p.drawLine(0, int(mid), w, int(mid))
        kept, cut = QtGui.QColor("#2F6FDB"), QtGui.QColor("#B9C0CB")
        for x in range(min(w, len(lo))):
            p.setPen(kept if xs - 0.5 <= x <= xe + 0.5 else cut)
            p.drawLine(x, int(mid - hi[x] * scale), x, int(mid - lo[x] * scale))
        p.fillRect(QtCore.QRectF(0, 0, xs, h), QtGui.QColor(120, 128, 140, 45))
        p.fillRect(QtCore.QRectF(xe, 0, w - xe, h), QtGui.QColor(120, 128, 140, 45))
        font = p.font()
        font.setPointSizeF(7.5)
        font.setBold(True)
        p.setFont(font)
        for name in self._visible():
            x = self._x(self.positions[name])
            color = QtGui.QColor(MARKER_COLORS[name])
            p.setPen(QtGui.QPen(color, 1.6))
            p.drawLine(QtCore.QPointF(x, 0), QtCore.QPointF(x, h))
            top = name in ("start", "end")
            box = QtCore.QRectF(min(max(x - 7, 0), w - 14), 0 if top else h - 13, 14, 13)
            p.fillRect(box, color)
            p.setPen(QtGui.QColor("#FFFFFF"))
            p.drawText(box, Qt.AlignCenter, marker_labels()[name])
        p.end()


class SoundEditor(QtWidgets.QGroupBox):
    """Panneau de reglage d'un son. `changed` signale une modification ; `group_setting(nom, valeur)`
    signale un reglage a etendre aux autres sons selectionnes (frequence, resolution, etc.)."""
    changed = QtCore.Signal()
    group_setting = QtCore.Signal(str, object)
    reset_requested = QtCore.Signal()

    def __init__(self, rates: list[tuple[int, str]], parent=None):
        super().__init__(T("Son sélectionné"), parent)
        self.edit: SoundEdit | None = None
        self.samples = np.zeros(0)
        self.rate = 1.0
        self.auto = (0, 0)
        self._filling = False

        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(4)
        self.wave = WaveView()
        self.wave.markerMoved.connect(self._marker_moved)
        self.wave.markerReleased.connect(self.changed)
        self.wave.setToolTip(T("Faites glisser les repères : D = début, F = fin, B = bords de la boucle.\nLes "
                               "parties grisées ne sont pas gardées."))
        lay.addWidget(self.wave, 1)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(3)

        def seconds_box(tip):
            b = QtWidgets.QDoubleSpinBox()
            b.setDecimals(3)
            b.setSingleStep(0.005)
            b.setSuffix(" s")
            b.setToolTip(tip)
            b.setMaximumWidth(92)
            return b

        def ms_box(tip):
            b = QtWidgets.QSpinBox()
            b.setRange(0, 5000)
            b.setSingleStep(5)
            b.setSuffix(" ms")
            b.setToolTip(tip)
            b.setMaximumWidth(80)
            return b

        self.start_box = seconds_box(T("Début du son gardé."))
        self.end_box = seconds_box(T("Fin du son gardé."))
        self.fade_in = ms_box(T("Fondu d'entrée : évite un clic si le début est coupé en plein son."))
        self.fade_out = ms_box(T("Fondu de sortie : évite un clic si la fin est coupée en plein son."))
        self.rate_box = QtWidgets.QComboBox()
        self.rate_box.addItem(T("Celle de l'instrument"), None)
        for code, label in rates:
            self.rate_box.addItem(label.split(" (")[0], code)
        self.rate_box.setToolTip(T("Fréquence d'échantillonnage de ce son dans l'EPS.\nPlus basse : moins de mémoire, "
                                   "son plus sourd."))
        self.bits_box = QtWidgets.QComboBox()
        for bits, label in BIT_CHOICES:
            self.bits_box.addItem(label, bits)
        self.bits_box.setToolTip(T("Résolution. L'EPS classique enregistre sur 13 bits ; moins de bits donne un grain « "
                                   "lo-fi ».\nLa place occupée ne change pas."))
        self.comp = QtWidgets.QSlider(Qt.Horizontal)
        self.comp.setRange(0, 100)
        self.comp.setMinimumWidth(80)
        self.comp.setToolTip(T("Compression de dynamique : atténue les passages forts et remonte le niveau "
                               "d'ensemble."))
        self.comp_label = QtWidgets.QLabel("0 %")
        self.comp_label.setMinimumWidth(36)

        row = 0
        for col, (label, widget) in enumerate(((T("Début"), self.start_box), (T("Fin"), self.end_box),
                                               (T("Fondu début"), self.fade_in), (T("Fondu fin"), self.fade_out),
                                               (T("Fréquence"), self.rate_box), (T("Résolution"), self.bits_box))):
            grid.addWidget(QtWidgets.QLabel(label), row, col * 2, Qt.AlignRight)
            grid.addWidget(widget, row, col * 2 + 1)
        row = 1
        self.loop_box = QtWidgets.QComboBox()
        for mode, label in LOOP_MODES:
            self.loop_box.addItem(label, mode)
        self.loop_start = QtWidgets.QSpinBox()
        self.loop_end = QtWidgets.QSpinBox()
        for b in (self.loop_start, self.loop_end):
            b.setMaximumWidth(92)
            b.setToolTip(T("Position en échantillons du son d'origine."))
        self.zero_btn = QtWidgets.QPushButton(T("Passages par zéro"))
        self.zero_btn.setToolTip(T("Cale les deux bords de la boucle sur le passage par zéro le plus proche."))
        self.auto_btn = QtWidgets.QPushButton(T("Raccord auto"))
        self.auto_btn.setToolTip(T("Cherche près de la fin de boucle le point où le raccord s'entend le moins."))
        self.reset_btn = QtWidgets.QPushButton(T("Réinitialiser"))
        self.reset_btn.setToolTip(T("Annule tous les réglages de ce son."))
        grid.addWidget(QtWidgets.QLabel(T("Boucle")), row, 0, Qt.AlignRight)
        grid.addWidget(self.loop_box, row, 1, 1, 3)
        grid.addWidget(QtWidgets.QLabel(T("de")), row, 4, Qt.AlignRight)
        grid.addWidget(self.loop_start, row, 5)
        grid.addWidget(QtWidgets.QLabel(T("à")), row, 6, Qt.AlignRight)
        grid.addWidget(self.loop_end, row, 7)
        loop_buttons = QtWidgets.QHBoxLayout()
        loop_buttons.addWidget(self.zero_btn)
        loop_buttons.addWidget(self.auto_btn)
        grid.addLayout(loop_buttons, row, 8, 1, 2)
        comp_row = QtWidgets.QHBoxLayout()
        comp_row.addWidget(QtWidgets.QLabel(T("Compression")))
        comp_row.addWidget(self.comp, 1)
        comp_row.addWidget(self.comp_label)
        comp_row.addWidget(self.reset_btn)
        grid.addLayout(comp_row, row, 10, 1, 2)
        grid.setColumnStretch(11, 1)
        lay.addLayout(grid)

        self.start_box.valueChanged.connect(lambda v: self._set_position("start", int(round(v * self.rate))))
        self.end_box.valueChanged.connect(lambda v: self._set_position("end", int(round(v * self.rate))))
        self.loop_start.valueChanged.connect(lambda v: self._set_position("loop_start", v))
        self.loop_end.valueChanged.connect(lambda v: self._set_position("loop_end", v))
        self.fade_in.valueChanged.connect(lambda v: self._set_group("fade_in_ms", float(v)))
        self.fade_out.valueChanged.connect(lambda v: self._set_group("fade_out_ms", float(v)))
        self.rate_box.activated.connect(lambda _i: self._set_group("rate_code", self.rate_box.currentData()))
        self.bits_box.activated.connect(lambda _i: self._set_group("bits", self.bits_box.currentData()))
        self.comp.valueChanged.connect(self._compress_changed)
        self.comp.sliderReleased.connect(self.changed)
        self.loop_box.activated.connect(lambda _i: self._set_group("loop_mode", self.loop_box.currentData()))
        self.zero_btn.clicked.connect(self.snap_to_zero)
        self.auto_btn.clicked.connect(self.auto_loop)
        self.reset_btn.clicked.connect(self.reset_requested)
        self.set_sound(None, None, 1.0, (0, 0), "")

    # ------------------------------------------------------------------ affichage
    def set_sound(self, edit: SoundEdit | None, samples, rate: float, auto: tuple[int, int], title: str):
        """Affiche un son. auto : debut et fin utilises tant que l'utilisateur ne les a pas fixes."""
        self.edit = edit
        self.samples = np.zeros(0) if samples is None else np.asarray(samples, dtype=np.float64)
        self.rate, self.auto = float(rate), auto
        self.setTitle(T("Son sélectionné : {0}").format(title) if edit is not None else T("Son sélectionné"))
        self.wave.set_sound(self.samples)
        for w in (self.start_box, self.end_box, self.fade_in, self.fade_out, self.rate_box, self.bits_box,
                  self.comp, self.loop_box, self.reset_btn):
            w.setEnabled(edit is not None)
        self.refresh()

    def positions(self) -> dict[str, int]:
        """Positions effectives des reperes, bornees et ordonnees."""
        n = len(self.samples)
        e = self.edit
        start = self.auto[0] if e.start is None else e.start
        end = self.auto[1] if e.end is None else e.end
        start = max(0, min(start, n - 2))
        end = max(start + 1, min(end, n - 1))
        ls = start if e.loop_start is None else e.loop_start
        le = end if e.loop_end is None else e.loop_end
        ls = max(start, min(ls, end - 1))
        le = max(ls + 1, min(le, end))
        return {"start": start, "end": end, "loop_start": ls, "loop_end": le}

    def refresh(self):
        self._filling = True
        e = self.edit
        looped = bool(e and e.looped)
        for w in (self.loop_start, self.loop_end, self.zero_btn, self.auto_btn):
            w.setEnabled(looped)
        if e is None or len(self.samples) < 2:
            self.wave.set_markers({}, False)
            self._filling = False
            return
        pos = self.positions()
        n = len(self.samples)
        duration = (n - 1) / self.rate
        for box, name in ((self.start_box, "start"), (self.end_box, "end")):
            box.setRange(0.0, duration)
            box.setValue(pos[name] / self.rate)
        for box, name in ((self.loop_start, "loop_start"), (self.loop_end, "loop_end")):
            box.setRange(0, n - 1)
            box.setSingleStep(max(1, n // 2000))
            box.setValue(pos[name])
        self.fade_in.setValue(int(e.fade_in_ms))
        self.fade_out.setValue(int(e.fade_out_ms))
        if e.rate_code is not None and self.rate_box.findData(e.rate_code) < 0:      # frequence hors liste
            self.rate_box.addItem(i18n.number(f"{ins.rate_hz(e.rate_code) / 1000:.1f} kHz"), e.rate_code)
        self.rate_box.setCurrentIndex(max(0, self.rate_box.findData(e.rate_code)))
        self.bits_box.setCurrentIndex(max(0, self.bits_box.findData(e.bits)))
        self.comp.setValue(e.compress)
        self.comp_label.setText(f"{e.compress} %")
        self.loop_box.setCurrentIndex(max(0, self.loop_box.findData(e.loop_mode)))
        self.wave.set_markers(pos, looped)
        self._filling = False

    # ------------------------------------------------------------------ modifications
    def _set_position(self, name: str, value: int, emit: bool = True):
        if self._filling or self.edit is None or len(self.samples) < 2:
            return
        n = len(self.samples)
        pos = self.positions()
        e = self.edit
        if name == "start":
            e.start = max(0, min(value, pos["end"] - 16 if pos["end"] > 16 else 0))
        elif name == "end":
            e.end = max(pos["start"] + 16 if pos["start"] + 16 < n else n - 1, min(value, n - 1))
        elif name == "loop_start":
            e.loop_start = max(pos["start"], min(value, pos["loop_end"] - 1))
            e.loop_end = pos["loop_end"]
        elif name == "loop_end":
            e.loop_end = max(pos["loop_start"] + 1, min(value, pos["end"]))
            e.loop_start = pos["loop_start"]
        if e.looped and name in ("start", "end") and (e.loop_start is not None or e.loop_end is not None):
            new = self.positions()                    # la boucle reste a l'interieur du son garde
            e.loop_start, e.loop_end = new["loop_start"], new["loop_end"]
        self.refresh()
        if emit:
            self.changed.emit()

    def _marker_moved(self, name: str, index: int):
        self._set_position(name, index, emit=False)   # « changed » est emis au relachement

    def _set_group(self, name: str, value):
        if self._filling or self.edit is None:
            return
        setattr(self.edit, name, value)
        self.group_setting.emit(name, value)
        self.refresh()
        self.changed.emit()

    def _compress_changed(self, value: int):
        if self._filling or self.edit is None:
            return
        self.edit.compress = value
        self.comp_label.setText(f"{value} %")
        self.group_setting.emit("compress", value)
        if not self.comp.isSliderDown():
            self.changed.emit()

    def snap_to_zero(self):
        if self.edit is None or not self.edit.looped:
            return
        pos = self.positions()
        ls = audio.nearest_zero_crossing(self.samples, pos["loop_start"])
        le = audio.nearest_zero_crossing(self.samples, pos["loop_end"] + 1) - 1
        if pos["start"] <= ls < le <= pos["end"]:
            self.edit.loop_start, self.edit.loop_end = ls, le
        self.refresh()
        self.changed.emit()

    def auto_loop(self):
        if self.edit is None or not self.edit.looped:
            return
        pos = self.positions()
        le = audio.best_loop_end(self.samples, pos["loop_start"], pos["loop_end"])
        le = max(pos["loop_start"] + 1, min(le, pos["end"]))
        self.edit.loop_start, self.edit.loop_end = pos["loop_start"], le
        self.refresh()
        self.changed.emit()
