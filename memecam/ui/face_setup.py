"""Modeless expression calibration; frames are delivered by the existing camera worker."""
import time
import uuid
from dataclasses import replace
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QDoubleSpinBox, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QWidget, QMessageBox, QScrollArea)
from memecam.config.settings import ROOT, write_json
from memecam.gestures.facial import learn_features, match_score, validate_rules
from memecam.ui.widgets.video_widget import VideoWidget


class FaceSetup(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Configurar gestos faciales · MemeCam")
        self.resize(1120, 800)
        self.scores = {}
        self.last_frame = 0
        self.neutral = None
        self.features = None
        self.capture = None
        self.samples = []
        root = QVBoxLayout(self)
        intro = QLabel("Configura tu expresión\n1. Captura tu rostro relajado.  2. Haz tu gesto y captúralo.  "
                       "3. Elige una imagen, prueba y guarda.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        body = QHBoxLayout()
        left = QVBoxLayout()
        tabs = QTabWidget()
        self.video = VideoWidget("Inicia la cámara en la ventana principal.\nActiva Face tracking.")
        self.result = VideoWidget("Aquí verás la imagen siguiendo tu rostro al probarla.")
        tabs.addTab(self.video, "Cámara + líneas de seguimiento")
        tabs.addTab(self.result, "Resultado con imagen")
        left.addWidget(tabs, 1)
        self.state = QLabel("Esperando cámara…")
        self.state.setWordWrap(True)
        left.addWidget(self.state)
        self.table = QTableWidget(8, 2)
        self.table.setHorizontalHeaderLabels(["Parámetro facial", "Valor en vivo"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMaximumHeight(215)
        left.addWidget(self.table)
        body.addLayout(left, 3)
        panel = QWidget()
        form = QFormLayout(panel)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.saved = QComboBox()
        form.addRow("Gestos guardados", self.saved)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ej. sonrisa, guiño, boca abierta")
        form.addRow("Nombre", self.name)
        self.enabled = QCheckBox("Activación automática habilitada")
        self.enabled.setChecked(True)
        form.addRow(self.enabled)
        self.neutral_button = QPushButton("1 · Capturar neutral (1 s)")
        self.expression_button = QPushButton("2 · Capturar gesto (1 s)")
        self.neutral_button.clicked.connect(lambda: self.begin_capture("neutral"))
        self.expression_button.clicked.connect(lambda: self.begin_capture("expression"))
        form.addRow(self.neutral_button)
        form.addRow(self.expression_button)
        self.threshold = self.spin(.2, 1, .65, .05)
        form.addRow("Umbral de activación", self.threshold)
        help_text = QLabel("Menor umbral = más sensible. Mantén el gesto para confirmarlo; "
                           "vuelve a neutral antes de repetir. Durante la configuración solo se activan imágenes por clic.")
        help_text.setWordWrap(True)
        form.addRow(help_text)
        self.match = QProgressBar()
        self.match.setFormat("Coincidencia: %p%")
        self.match.setMinimumHeight(24)
        form.addRow(self.match)
        self.parameters = QLabel("Aún no hay gesto capturado.")
        self.parameters.setWordWrap(True)
        form.addRow(self.parameters)
        self.overlay = QComboBox()
        form.addRow("Imagen vinculada", self.overlay)
        self.tracking = QComboBox()
        self.tracking.addItem("Rostro", "face")
        self.tracking.addItem("Ojos", "eyes")
        self.tracking.addItem("Pantalla", "screen")
        form.addRow("Seguir", self.tracking)
        self.scale = self.spin(.01, 5, 1, .05)
        self.x = self.spin(-2, 2, 0, .01)
        self.y = self.spin(-2, 2, 0, .01)
        self.duration = self.spin(0, 3600, 2, .5)
        self.duration.setSpecialValueText("Hasta quitarla")
        form.addRow("Tamaño", self.scale)
        form.addRow("Desplazamiento X", self.x)
        form.addRow("Desplazamiento Y", self.y)
        form.addRow("Duración (s)", self.duration)
        self.rotate = QCheckBox("Seguir inclinación de la cabeza")
        form.addRow(self.rotate)
        test = QPushButton("Aplicar posición y probar imagen")
        test.clicked.connect(self.test_overlay)
        form.addRow(test)
        save = QPushButton("Guardar gesto y vincular imagen")
        save.setObjectName("primary")
        save.clicked.connect(self.save_rule)
        actions = QHBoxLayout()
        actions.addWidget(save)
        delete = QPushButton("Eliminar gesto seleccionado")
        delete.clicked.connect(self.delete_rule)
        actions.addWidget(delete)
        close = QPushButton("Cerrar configuración")
        close.clicked.connect(self.close)
        actions.addWidget(close)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(360)
        scroll.setWidget(panel)
        body.addWidget(scroll, 2)
        root.addLayout(body, 1)
        root.addLayout(actions)
        self.notice = QLabel("Las muestras usan valores numéricos locales; no se guardan fotos ni video.")
        self.notice.setWordWrap(True)
        root.addWidget(self.notice)
        self.saved.currentIndexChanged.connect(self.select_rule)
        self.overlay.currentIndexChanged.connect(self.select_overlay)
        self.refresh_overlays()
        self.refresh_rules()

    @staticmethod
    def spin(low, high, value, step):
        widget = QDoubleSpinBox()
        widget.setRange(low, high)
        widget.setDecimals(2)
        widget.setSingleStep(step)
        widget.setValue(value)
        return widget

    def refresh_overlays(self):
        selected = self.overlay.currentData()
        self.overlay.blockSignals(True)
        self.overlay.clear()
        for item in self.owner.assets.items:
            self.overlay.addItem(item.name, item.id)
        self.overlay.setCurrentIndex(max(0, self.overlay.findData(selected)))
        self.overlay.blockSignals(False)
        self.select_overlay()

    def refresh_rules(self, selected=None):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("+ Nuevo gesto", None)
        for rule in self.owner.facial_rules:
            self.saved.addItem(rule["name"], rule["id"])
        self.saved.setCurrentIndex(max(0, self.saved.findData(selected)))
        self.saved.blockSignals(False)
        self.select_rule()

    def select_rule(self):
        self.capture = None
        key = self.saved.currentData()
        rule = next((r for r in self.owner.facial_rules if r["id"] == key), None)
        self.name.setText(rule["name"] if rule else "")
        self.enabled.setChecked(rule["enabled"] if rule else True)
        self.threshold.setValue(rule["threshold"] if rule else .65)
        self.features = rule["features"].copy() if rule else None
        self.neutral = None
        if rule:
            self.overlay.setCurrentIndex(self.overlay.findData(rule["overlay"]))
        self.show_features()

    def select_overlay(self):
        item = next((v for v in self.owner.assets.items if v.id == self.overlay.currentData()), None)
        if item:
            self.tracking.setCurrentIndex(self.tracking.findData(item.tracking_mode))
            for widget, value in ((self.scale, item.scale), (self.x, item.offset_x),
                                  (self.y, item.offset_y), (self.duration, item.duration)):
                widget.setValue(value)
            self.rotate.setChecked(item.rotation_mode == "face")

    def begin_capture(self, kind):
        if not self.scores or time.monotonic() - self.last_frame > .5:
            self.notice.setText("Necesitas un rostro visible y Face tracking activado para capturar.")
            return
        if kind == "expression" and self.neutral is None:
            self.notice.setText("Primero captura tu rostro neutral.")
            return
        self.capture = (kind, time.monotonic())
        self.samples = []
        self.notice.setText("Mantén el rostro relajado…" if kind == "neutral" else "Mantén tu gesto…")

    def show_features(self):
        self.parameters.setText("Parámetros: " + ", ".join(self.features) if self.features else
                                "Aún no hay gesto capturado.")

    def update_frame(self, clean, status):
        self.last_frame = time.monotonic()
        self.scores = status.get("face_scores", {})
        frame = status.get("setup_frame")
        if frame is not None:
            self.video.set_frame(frame)
        self.result.set_frame(clean)
        self.state.setText("Rostro detectado · sigue las líneas de ojos, cejas y boca" if self.scores else
                           "Sin rostro · mira a la cámara y activa Face tracking")
        keys = list(self.features) if self.features else sorted(self.scores, key=self.scores.get, reverse=True)[:8]
        self.table.setRowCount(len(keys))
        for row, key in enumerate(keys):
            self.table.setItem(row, 0, QTableWidgetItem(key))
            self.table.setItem(row, 1, QTableWidgetItem(f"{self.scores.get(key, 0):.2f}"))
        self.match.setValue(round(100 * match_score({"features": self.features}, self.scores))
                            if self.features else 0)
        if self.capture:
            kind, start = self.capture
            if not self.scores:
                self.capture = None
                self.notice.setText("Se perdió el rostro. Repite la captura.")
                return
            self.samples.append(self.scores.copy())
            if self.last_frame - start >= 1:
                self.capture = None
                if len(self.samples) < 5:
                    self.notice.setText("Muy pocas muestras. Repite la captura con mejor iluminación.")
                    return
                keys = set.intersection(*(set(s) for s in self.samples))
                average = {k: float(np.median([s[k] for s in self.samples])) for k in keys}
                if kind == "neutral":
                    self.neutral = average
                    self.features = None
                    self.notice.setText("Neutral capturado. Haz tu gesto y pulsa Capturar gesto.")
                else:
                    try:
                        self.features = learn_features(self.neutral, average)
                        self.notice.setText("Gesto capturado. Repite y observa la coincidencia; luego guarda.")
                    except ValueError as exc:
                        self.notice.setText(str(exc))
                self.show_features()

    def clear_live(self):
        self.capture = None
        self.scores = {}
        self.video.clear()
        self.result.clear()
        self.match.setValue(0)
        self.state.setText("Cámara detenida. Iníciala desde la ventana principal.")

    def apply_overlay(self):
        item = next((v for v in self.owner.assets.items if v.id == self.overlay.currentData()), None)
        if item is None:
            raise ValueError("Agrega una imagen a la biblioteca primero.")
        item = replace(item, tracking_mode=self.tracking.currentData(), scale=self.scale.value(),
                       offset_x=self.x.value(), offset_y=self.y.value(), duration=self.duration.value(),
                       rotation_mode="face" if self.rotate.isChecked() else "none")
        self.owner.assets.update(item)
        if self.owner.pipeline and self.owner.pipeline.isRunning():
            self.owner.pipeline.command("register", item, self.owner.assets.images[item.id])
        self.owner.refresh_library()

    def test_overlay(self):
        try:
            self.apply_overlay()
            self.owner.trigger(self.overlay.currentData())
            running = self.owner.pipeline and self.owner.pipeline.isRunning() and not self.owner.stopping
            self.notice.setText("Posición guardada. Revisa la pestaña Resultado; otro clic quita la imagen." if running
                                else "Posición guardada. Inicia la cámara para probar la imagen.")
        except (ValueError, OSError) as exc:
            self.notice.setText(str(exc))

    def persist(self, rules):
        validate_rules(rules, self.owner.assets.images)
        write_json(ROOT / "config/facial_gestures.json", rules)
        self.owner.facial_rules = rules
        if self.owner.pipeline and self.owner.pipeline.isRunning():
            self.owner.pipeline.command("facial_rules", rules)

    def save_rule(self):
        try:
            if not self.features or not self.name.text().strip():
                raise ValueError("Escribe un nombre y captura neutral y gesto antes de guardar.")
            key = self.saved.currentData() or uuid.uuid4().hex
            rule = dict(id=key, name=self.name.text().strip(), overlay=self.overlay.currentData(),
                        enabled=self.enabled.isChecked(), threshold=self.threshold.value(), features=self.features)
            rules = [r for r in self.owner.facial_rules if r["id"] != key] + [rule]
            validate_rules(rules, self.owner.assets.images)
            self.apply_overlay()
            self.persist(rules)
            self.refresh_rules(key)
            self.notice.setText("Gesto guardado. Cierra esta ventana para activar la detección automática.")
        except (ValueError, OSError) as exc:
            self.notice.setText(str(exc))

    def delete_rule(self):
        key = self.saved.currentData()
        if key is None:
            return
        if QMessageBox.question(self, "Eliminar gesto", "¿Eliminar este gesto guardado?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.persist([r for r in self.owner.facial_rules if r["id"] != key])
            self.refresh_rules()
            self.notice.setText("Gesto eliminado.")
        except (ValueError, OSError) as exc:
            self.notice.setText(str(exc))

    def closeEvent(self, event):
        self.owner.face_setup = None
        if self.owner.pipeline and self.owner.pipeline.isRunning():
            self.owner.pipeline.command("setup", False)
        super().closeEvent(event)
