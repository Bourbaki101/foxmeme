"""A visual, non-destructive image import and placement flow."""
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QLineEdit, QComboBox, QFormLayout, QDoubleSpinBox,
    QCheckBox, QScrollArea)

from memecam.overlays.asset_manager import read_import_image
from memecam.overlays.overlay_model import Overlay
from memecam.overlays.overlay_engine import OverlayEngine
from memecam.ui.widgets.video_widget import VideoWidget
from memecam.vision.smoothing import FacePose


class ReactionEditor(QDialog):
    def __init__(self, owner, item=None):
        super().__init__(owner)
        self.owner, self.item = owner, item
        self.source = None
        self.image = owner.assets.images[item.id] if item else None
        self.live_frame = None
        self.pose = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Tu reacción · MemeCam")
        self.resize(940, 680)
        self.setMinimumSize(780, 600)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)
        heading = QLabel("Tu imagen. Tu reacción.")
        heading.setObjectName("hero")
        root.addWidget(heading)
        intro = QLabel("Elige una imagen, ajusta cómo sigue tu rostro y guárdala. Sin configurar gestos todavía.")
        intro.setObjectName("subtle")
        intro.setWordWrap(True)
        root.addWidget(intro)
        body = QHBoxLayout()
        body.setSpacing(20)
        stage = QVBoxLayout()
        self.preview = VideoWidget("1 · Sube una imagen para ver cómo quedará")
        stage.addWidget(self.preview, 1)
        self.preview_note = QLabel()
        self.preview_note.setObjectName("subtle")
        self.preview_note.setWordWrap(True)
        stage.addWidget(self.preview_note)
        self.camera_button = QPushButton("Encender cámara para probar en mi rostro")
        self.camera_button.clicked.connect(self.start_camera)
        stage.addWidget(self.camera_button)
        body.addLayout(stage, 3)
        controls = QWidget()
        form = QFormLayout(controls)
        form.setContentsMargins(8, 0, 8, 8)
        form.setSpacing(12)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.upload = QPushButton("1 · Subir mi imagen…")
        self.upload.setObjectName("primary")
        self.upload.clicked.connect(self.choose_image)
        self.upload.setVisible(item is None)
        form.addRow(self.upload)
        self.file_label = QLabel(item.name if item else "PNG, JPG o WebP · desde tu computadora")
        self.file_label.setWordWrap(True)
        self.file_label.setObjectName("subtle")
        form.addRow(self.file_label)
        self.name = QLineEdit(item.name if item else "")
        self.name.setPlaceholderText("Ej. Mi cara de lunes")
        form.addRow("Nombre de la reacción", self.name)
        self.placement = QComboBox()
        for title, value in (("Sobre mi rostro", "face"), ("Sobre mis ojos · gafas", "eyes"),
                             ("Encima de mi cabeza", "above"), ("Fija en la pantalla", "screen")):
            self.placement.addItem(title, value)
        form.addRow("2 · ¿Dónde la quieres?", self.placement)
        self.size = self.spin(1, 500, 100, 5, " %")
        self.horizontal = self.spin(-200, 200, 0, 1, " %")
        self.vertical = self.spin(-200, 200, 0, 1, " %")
        form.addRow("Tamaño", self.size)
        form.addRow("Mover izquierda / derecha", self.horizontal)
        form.addRow("Mover arriba / abajo", self.vertical)
        self.rotate = QCheckBox("Seguir la inclinación de mi cabeza")
        self.rotate.setChecked(True)
        form.addRow(self.rotate)
        self.duration = self.spin(0, 3600, 0, 1, " s")
        self.duration.setSpecialValueText("Hasta que la quite con otro clic")
        form.addRow("¿Cuánto tiempo se muestra?", self.duration)
        tip = QLabel("PNG transparente: solo aparece el recorte. JPG y otras imágenes sin transparencia conservan su fondo.")
        tip.setWordWrap(True)
        tip.setObjectName("subtle")
        form.addRow(tip)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(290)
        scroll.setWidget(controls)
        body.addWidget(scroll, 2)
        root.addLayout(body, 1)
        self.notice = QLabel("Tu imagen se guarda solo cuando pulses Guardar.")
        self.notice.setWordWrap(True)
        root.addWidget(self.notice)
        actions = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.close)
        actions.addWidget(cancel)
        actions.addStretch()
        self.link_button = QPushButton("Guardar y activar con una expresión →")
        self.link_button.clicked.connect(lambda: self.save_reaction(link=True))
        actions.addWidget(self.link_button)
        self.save_button = QPushButton("3 · Guardar y usar")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(lambda: self.save_reaction())
        actions.addWidget(self.save_button)
        root.addLayout(actions)
        self.placement.currentIndexChanged.connect(self.apply_preset)
        for control in (self.size, self.horizontal, self.vertical, self.duration):
            control.valueChanged.connect(self.render_preview)
        self.rotate.toggled.connect(self.render_preview)
        if item:
            self.placement.setCurrentIndex(self.placement.findData(item.tracking_mode))
            self.size.setValue(item.scale * 100)
            self.horizontal.setValue(item.offset_x * 100)
            self.vertical.setValue(item.offset_y * 100)
            self.rotate.setChecked(item.rotation_mode == "face")
            self.duration.setValue(item.duration)
        self.render_preview()

    @staticmethod
    def spin(low, high, value, step, suffix):
        result = QDoubleSpinBox()
        result.setRange(low, high)
        result.setDecimals(1)
        result.setSingleStep(step)
        result.setValue(value)
        result.setSuffix(suffix)
        return result

    def choose_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Sube tu imagen", "",
                                                "Imágenes (*.png *.jpg *.jpeg *.webp)")
        if filename:
            self.load_image(Path(filename))

    def load_image(self, source):
        try:
            image = read_import_image(source)
        except (ValueError, OSError) as exc:
            self.notice.setText(f"No pudimos abrir esa imagen: {exc}")
            return False
        self.source, self.image = source, image
        if not self.name.text().strip():
            self.name.setText(source.stem)
        self.file_label.setText(source.name)
        self.upload.setText("Cambiar imagen…")
        self.notice.setText("Ajusta la posición en la vista previa. Todavía no se ha guardado.")
        self.render_preview()
        return True

    def apply_preset(self):
        mode = self.placement.currentData()
        self.size.setValue({"face": 100, "eyes": 240, "above": 85, "screen": 50}[mode])
        self.horizontal.setValue(0)
        self.vertical.setValue(-30 if mode == "above" else 0)
        self.rotate.setChecked(mode != "screen")
        self.render_preview()

    def draft(self):
        mode = self.placement.currentData()
        return Overlay.parse(dict(id="preview", name=self.name.text().strip() or "Mi reacción",
            file="preview.png", tracking_mode="face" if mode == "above" else mode,
            anchor="center", scale=self.size.value() / 100,
            offset_x=self.horizontal.value() / 100, offset_y=self.vertical.value() / 100,
            rotation_mode="face" if self.rotate.isChecked() else "none", duration=self.duration.value()))

    def update_frame(self, frame, status):
        self.live_frame, self.pose = frame, status.get("pose")
        self.render_preview()

    def clear_live(self):
        self.live_frame, self.pose = None, None
        self.render_preview()

    def render_preview(self):
        if self.live_frame is None:
            frame = np.full((450, 640, 3), (30, 27, 25), np.uint8)
            cv2.ellipse(frame, (320, 400), (135, 100), 0, 0, 360, (66, 60, 54), -1)
            cv2.ellipse(frame, (320, 195), (80, 105), 0, 0, 360, (126, 117, 105), -1)
            for x in (290, 350):
                cv2.circle(frame, (x, 175), 5, (40, 36, 32), -1)
            cv2.ellipse(frame, (320, 225), (25, 12), 0, 0, 180, (50, 43, 38), 2)
            pose = FacePose(320, 175, 60, 0, 320, 195, 160)
            note = "VISTA DE EJEMPLO · Enciende la cámara para probar en tu rostro."
        else:
            frame, pose = self.live_frame.copy(), self.pose
            note = "EN VIVO · Ajusta tu imagen sin cambiar la salida de OBS."
            if pose is None and self.placement.currentData() != "screen":
                note = "No vemos tu rostro. Mira a la cámara y activa Face tracking en Ajustes."
        if self.image is not None:
            draft = self.draft()
            engine = OverlayEngine([draft], {draft.id: self.image})
            engine.active[draft.id] = None
            engine.render(frame, pose, 0)
        self.preview.set_frame(frame)
        self.preview_note.setText(note)
        self.save_button.setEnabled(self.image is not None)
        self.link_button.setEnabled(self.image is not None)
        self.camera_button.setVisible(self.live_frame is None and not self.owner.demo)

    def start_camera(self):
        self.owner.checks["face"].setChecked(True)
        self.owner.start_camera()
        self.notice.setText("Si la cámara no inicia, selecciónala en Ajustes de la ventana principal.")

    def save_reaction(self, link=False):
        if self.image is None:
            return
        if not self.name.text().strip():
            self.notice.setText("Ponle un nombre a tu reacción para encontrarla en tu biblioteca.")
            self.name.setFocus()
            return
        try:
            draft = self.draft()
            placement = dict(scale=draft.scale, offset_x=draft.offset_x, offset_y=draft.offset_y,
                             anchor=draft.anchor, rotation_mode=draft.rotation_mode)
            if self.item is None:
                item = self.owner.assets.add(self.source, self.name.text().strip(), draft.tracking_mode,
                                             draft.duration, **placement)
            else:
                # Editing an existing reaction keeps its ID and all gesture links.
                if self.source is not None:
                    self.notice.setText("Para usar otra imagen, crea una reacción nueva desde Subir mi imagen.")
                    return
                item = replace(self.item, name=self.name.text().strip(), tracking_mode=draft.tracking_mode,
                               duration=draft.duration, **placement)
                self.owner.assets.update(item)
            if self.owner.pipeline and self.owner.pipeline.isRunning():
                self.owner.pipeline.command("register", item, self.owner.assets.images[item.id])
            self.owner.refresh_library()
            if self.owner.face_setup:
                self.owner.face_setup.refresh_overlays()
                self.owner.face_setup.overlay.setCurrentIndex(self.owner.face_setup.overlay.findData(item.id))
            self.owner.message.setText(f"{item.name} guardada · Haz clic en su tarjeta para mostrarla. Doble clic para editar.")
            if link:
                self.owner.open_face_setup()
                setup = self.owner.face_setup
                setup.saved.setCurrentIndex(0)
                setup.overlay.setCurrentIndex(setup.overlay.findData(item.id))
                if setup.saved.currentData() is None:
                    setup.name.setText(item.name)
                setup.notice.setText("Imagen lista. Captura tu rostro relajado, después tu expresión y guarda el gesto.")
            elif not self.owner.demo:
                self.owner.trigger(item.id)
            self.close()
        except (ValueError, OSError) as exc:
            self.notice.setText(f"No pudimos guardar: {exc}")

    def closeEvent(self, event):
        self.owner.reaction_editor = None
        if self.owner.pipeline and self.owner.pipeline.isRunning():
            self.owner.pipeline.command("preview", False)
        super().closeEvent(event)
