import logging
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QProgressBar, QScrollArea,
    QFormLayout, QTabWidget, QToolButton, QMenu)
from memecam.camera.camera_manager import CameraDiscovery
from memecam.camera.pipeline import Pipeline
from memecam.config.settings import ROOT, write_json
from memecam.ui.output_window import OutputWindow
from memecam.ui.widgets.video_widget import VideoWidget
from memecam.gestures.facial import load_rules

LOG = logging.getLogger(__name__)
STYLE = """
QWidget { color:#e9e9ed; font-family:'Segoe UI'; font-size:13px; }
QMainWindow, QDialog { background:#101216; }
QLabel { background:transparent; }
QLabel#brand { font-size:24px; font-weight:700; letter-spacing:-1px; }
QLabel#hero { font-size:25px; font-weight:600; letter-spacing:-1px; }
QLabel#eyebrow { color:#777b87; font-size:11px; font-weight:600; letter-spacing:2px; }
QLabel#section { font-size:16px; font-weight:600; }
QLabel#subtle { color:#9295a1; font-size:12px; }
QLabel#live { color:#a8abba; background:#202228; border-radius:12px; padding:5px 12px; font-size:11px; }
QWidget#panel, QTabWidget::pane { background:#18191e; border:1px solid #2a2c33; border-radius:12px; }
QWidget#tabPage, QScrollArea, QScrollArea > QWidget > QWidget { background:#18191e; }
QGroupBox { border:0; border-top:1px solid #2a2c33; margin-top:18px; padding:20px 0 0; }
QGroupBox::title { subcontrol-origin:margin; left:0; color:#9295a1; font-size:11px; font-weight:600; }
QPushButton, QComboBox, QToolButton { background:#24262d; border:1px solid #34363f; border-radius:8px; padding:9px 14px; }
QPushButton:hover, QToolButton:hover { background:#30333c; border-color:#656a79; }
QPushButton:pressed, QToolButton:pressed { background:#383d47; }
QPushButton:disabled { color:#646774; background:#202127; border-color:#292b32; }
QPushButton#primary { background:#c0f2d5; color:#172a21; font-weight:600; border:1px solid #c0f2d5; }
QPushButton#primary:hover { background:#d6f9e4; }
QPushButton#primary:disabled { background:#24282a; color:#727d77; border-color:#343d37; }
QPushButton#quiet { background:transparent; border:1px solid #34363f; }
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus { border:1px solid #c0f2d5; }
QComboBox { padding:8px 10px; min-height:18px; }
QComboBox::drop-down { border:0; width:22px; }
QComboBox QAbstractItemView { background:#24262d; color:#e9e9ed; selection-background-color:#3b4540; }
QCheckBox { spacing:10px; padding:5px 0; background:transparent; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #515562; border-radius:4px; background:#24262d; }
QCheckBox::indicator:checked { background:#c0f2d5; border-color:#c0f2d5; image:url(CHECK_ICON); }
QProgressBar { border:0; border-radius:3px; background:#30323b; }
QProgressBar::chunk { background:#c0f2d5; border-radius:3px; }
QScrollArea { border:0; }
QScrollBar:vertical { background:transparent; width:6px; margin:0; }
QScrollBar:horizontal { background:transparent; height:6px; margin:0; }
QScrollBar::handle { background:#41444e; border-radius:3px; min-height:24px; min-width:24px; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
QTabWidget::pane { top:8px; }
QTabBar { background:#101114; }
QTabBar::tab { background:transparent; color:#9295a1; padding:10px 22px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#e9e9ed; border-bottom:2px solid #c0f2d5; }
QTabBar::tab:hover { color:#c0f2d5; }
QLineEdit, QDoubleSpinBox { background:#24262d; border:1px solid #34363f; border-radius:6px; padding:6px; }
QTableWidget { background:#18191e; alternate-background-color:#202228; gridline-color:#2a2c33; }
QHeaderView::section { background:#24262d; border:0; padding:6px; }
""".replace("CHECK_ICON", (ROOT / "assets/ui/check.svg").as_posix())


def button(text, callback, primary=False):
    result = QPushButton(text)
    if primary:
        result.setObjectName("primary")
    result.clicked.connect(callback)
    return result


class MainWindow(QMainWindow):
    def __init__(self, settings, assets, mappings, warning=None, demo=False):
        super().__init__()
        self.settings, self.assets, self.mappings = settings, assets, mappings
        self.pipeline = None
        self.face_setup = None
        self.reaction_editor = None
        try:
            self.facial_rules = load_rules(ROOT / "config/facial_gestures.json", assets.images)
        except ValueError as exc:
            self.facial_rules = []
            warning = f"Facial gestures disabled: {exc}"
        self.closing = False
        self.stopping = False
        self.camera_blocked = False
        self.demo = demo
        self.output = OutputWindow()
        self.setWindowTitle("MemeCam — Tu estudio de reacciones")
        self.resize(1240, 820)
        self.setMinimumSize(960, 700)
        self.setStyleSheet(STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 16)
        root.setSpacing(20)

        header = QHBoxLayout()
        identity = QVBoxLayout()
        identity.setSpacing(2)
        brand = QLabel("memecam")
        brand.setObjectName("brand")
        identity.addWidget(brand)
        subtitle = QLabel("REACTION STUDIO")
        subtitle.setObjectName("eyebrow")
        identity.addWidget(subtitle)
        header.addLayout(identity)
        header.addStretch()
        self.live = QLabel("●  CAMERA OFF")
        self.live.setObjectName("live")
        header.addWidget(self.live)
        header.addSpacing(12)
        self.upload_button = button("+ Subir mi imagen", self.add_overlay, True)
        header.addWidget(self.upload_button)
        self.start_button = button("Encender cámara", self.start_camera)
        self.stop_button = button("Stop", self.stop_camera)
        self.stop_button.setEnabled(False)
        self.stop_button.setVisible(False)
        header.addWidget(self.start_button)
        header.addWidget(self.stop_button)
        header.addWidget(button("Salida OBS ↗", self.open_output))
        root.addLayout(header)

        introduction = QVBoxLayout()
        introduction.setSpacing(4)
        headline = QLabel("Reacciona a tu manera.")
        headline.setObjectName("hero")
        introduction.addWidget(headline)
        description = QLabel("Sube tu imagen. Ponla sobre tu rostro. Dale vida con una expresión.")
        description.setObjectName("subtle")
        introduction.addWidget(description)
        root.addLayout(introduction)

        body = QHBoxLayout()
        body.setSpacing(20)
        stage = QWidget()
        stage.setObjectName("panel")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(16, 14, 16, 12)
        stage_layout.setSpacing(12)
        stage_header = QHBoxLayout()
        title = QLabel("Tu escenario")
        title.setObjectName("section")
        stage_header.addWidget(title)
        stage_header.addStretch()
        note = QLabel("Todo sucede en tu equipo")
        note.setObjectName("subtle")
        stage_header.addWidget(note)
        stage_layout.addLayout(stage_header)
        self.preview = VideoWidget("Tu próxima reacción empieza aquí.\n\nEnciende la cámara y sube tu propia imagen.")
        stage_layout.addWidget(self.preview, 1)
        self.metrics = QLabel("Camera idle")
        self.metrics.setObjectName("subtle")
        stage_layout.addWidget(self.metrics)
        body.addWidget(stage, 1)

        self.inspector = QTabWidget()
        self.inspector.setFixedWidth(304)
        self.inspector.setDocumentMode(True)
        gesture_page = QWidget()
        gesture_page.setObjectName("tabPage")
        gestures_layout = QVBoxLayout(gesture_page)
        gestures_layout.setContentsMargins(18, 22, 18, 18)
        gestures_layout.setSpacing(8)
        title = QLabel("Hazla tuya")
        title.setObjectName("section")
        gestures_layout.addWidget(title)
        welcome = QLabel("Tu foto, meme o sticker siguiendo tu rostro. Listo en tres pasos.")
        welcome.setWordWrap(True)
        welcome.setObjectName("subtle")
        gestures_layout.addWidget(welcome)
        gestures_layout.addWidget(button("+ Crear mi reacción", self.add_overlay, True))
        steps = QLabel("01  Sube una imagen\n02  Elige rostro, ojos o pantalla\n03  Guarda y úsala con un clic")
        steps.setStyleSheet("color:#c4c9d3; padding:12px 0;")
        gestures_layout.addWidget(steps)
        guide = QLabel("También puedes usar tus manos")
        guide.setObjectName("section")
        gestures_layout.addWidget(guide)
        hint = QLabel(f"Mantén el gesto {settings['confirmation']:.2f}s y suelta.")
        hint.setObjectName("subtle")
        gestures_layout.addWidget(hint)
        self.gesture_labels = {}
        labels = [("peace", "Peace", "Toggle glasses"),
                  ("thumbs_up", "Thumbs up", "Approved"),
                  ("thumbs_down", "Thumbs down", "Rejected"),
                  ("open_palm", "Open palm", "Reaction"),
                  ("fist", "Fist", "Clear effects")]
        for key, title, description in labels:
            label = QLabel(f"<b>{title}</b><br><span style='font-size:11px;color:#9295a1'>{description}</span>")
            label.setMinimumHeight(36)
            gestures_layout.addWidget(label)
            self.gesture_labels[key] = label
        gestures_layout.addStretch()
        self.gesture_status = QLabel("Candidate: —")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.confirmed = QLabel("Last confirmed: —")
        self.confirmed.setObjectName("subtle")
        self.confirmed.setWordWrap(True)
        self.face_status = QLabel("Facial: —")
        self.face_status.setObjectName("subtle")
        self.face_status.setWordWrap(True)
        setup = button("Activar con mi expresión →", self.open_face_setup)
        setup.setToolTip("Configurar gestos faciales")

        settings_page = QWidget()
        settings_page.setObjectName("tabPage")
        settings_layout = QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(18, 22, 18, 18)
        settings_layout.setSpacing(12)
        camera_title = QLabel("Camera")
        camera_title.setObjectName("section")
        settings_layout.addWidget(camera_title)
        camera_row = QHBoxLayout()
        self.camera = QComboBox()
        self.camera.setMinimumWidth(0)
        self.camera.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.camera.setMinimumContentsLength(12)
        self.camera.setAccessibleName("Camera device")
        camera_row.addWidget(self.camera, 1)
        self.refresh = button("↻", self.discover)
        self.refresh.setToolTip("Refresh cameras")
        self.refresh.setAccessibleName("Refresh cameras")
        camera_row.addWidget(self.refresh)
        settings_layout.addLayout(camera_row)
        format_form = QFormLayout()
        format_form.setSpacing(10)
        self.resolution = QComboBox()
        for width, height in ((640,480), (1280,720), (1920,1080)):
            self.resolution.addItem(f"{width} × {height}", (width, height))
        current = (settings["width"], settings["height"])
        index = self.resolution.findData(current)
        if index < 0:
            self.resolution.addItem(f"{current[0]} × {current[1]}", current)
            index = self.resolution.count()-1
        self.resolution.setCurrentIndex(index)
        format_form.addRow("Resolution", self.resolution)
        self.fps_target = QComboBox()
        for fps in sorted({15, 24, 30, 60, settings["fps"]}):
            self.fps_target.addItem(f"{fps} FPS", fps)
        self.fps_target.setCurrentIndex(self.fps_target.findData(settings["fps"]))
        format_form.addRow("Frame rate", self.fps_target)
        settings_layout.addLayout(format_form)
        detection = QGroupBox("DETECTION")
        detection_layout = QVBoxLayout(detection)
        detection_layout.setContentsMargins(0, 8, 0, 0)
        self.checks = {}
        for key, title in (("hands", "Hand gestures"), ("face", "Face tracking"),
                           ("mirror", "Mirror camera"), ("debug", "Preview landmarks")):
            check = QCheckBox(title)
            check.setChecked(settings[key])
            check.toggled.connect(lambda value, k=key: self.setting(k, value))
            self.checks[key] = check
            detection_layout.addWidget(check)
        for widget in (self.gesture_status, self.progress, self.confirmed, self.face_status):
            detection_layout.addWidget(widget)
        settings_layout.addWidget(detection)
        output_group = QGroupBox("OUTPUT WINDOW")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(0, 8, 0, 0)
        self.borderless = QCheckBox("Borderless")
        self.fullscreen = QCheckBox("Fullscreen")
        self.borderless.setChecked(settings["borderless"])
        self.fullscreen.setChecked(settings["fullscreen"])
        self.output_debug = QCheckBox("Include debug in output")
        self.output_debug.setToolTip("Enable preview landmarks too. Output is clean by default.")
        for check in (self.borderless, self.fullscreen, self.output_debug):
            output_layout.addWidget(check)
        self.borderless.toggled.connect(self.output_mode)
        self.fullscreen.toggled.connect(self.output_mode)
        settings_layout.addWidget(output_group)
        settings_layout.addStretch()
        for page, title in ((gesture_page, "Mi estudio"), (settings_page, "Ajustes")):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(page)
            self.inspector.addTab(scroll, title)
        side = QVBoxLayout()
        side.setSpacing(16)
        side.addWidget(self.inspector, 1)
        side.addWidget(setup)
        body.addLayout(side)
        root.addLayout(body, 1)

        library = QWidget()
        library.setObjectName("panel")
        library_layout = QVBoxLayout(library)
        library_layout.setContentsMargins(16, 14, 16, 12)
        library_layout.setSpacing(10)
        library_header = QHBoxLayout()
        self.library_title = QLabel("Tu biblioteca")
        title = self.library_title
        title.setObjectName("section")
        library_header.addWidget(title)
        hint = QLabel("Clic para mostrar · Editar debajo")
        hint.setObjectName("subtle")
        library_header.addWidget(hint)
        library_header.addStretch()
        clear = button("Quitar todas", self.clear_overlays)
        clear.setObjectName("quiet")
        library_header.addWidget(clear)
        library_header.addWidget(button("+ Subir imagen", self.add_overlay, True))
        library_layout.addLayout(library_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(144)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self.library_layout = QHBoxLayout(container)
        self.library_layout.setContentsMargins(0, 0, 0, 6)
        self.library_layout.setSpacing(10)
        scroll.setWidget(container)
        library_layout.addWidget(scroll)
        root.addWidget(library)
        self.refresh_library()
        self.message = QLabel(warning or "Empieza con + Subir mi imagen · PNG, JPG o WebP desde tu computadora")
        self.message.setWordWrap(True)
        self.message.setObjectName("subtle")
        root.addWidget(self.message)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.discovery = None
        if not demo:
            self.discover()
        else:
            self.camera.addItem("Demo · synthetic frames", 0)
            self.start_button.setEnabled(False)
            self.message.setText("DEMO MODE · synthetic video; webcam and tracking are not running")

    def save(self):
        try:
            write_json(ROOT / "config/settings.json", self.settings)
        except OSError as exc:
            self.message.setText(f"Cannot save settings: {exc}")
            LOG.exception("Settings persistence failed")

    def setting(self, key, value):
        self.settings[key] = value
        if self.pipeline and self.pipeline.isRunning() and not self.stopping:
            self.pipeline.command("setting", key, value)
        self.save()

    def discover(self):
        if self.discovery and self.discovery.isRunning():
            return
        self.refresh.setEnabled(False)
        self.start_button.setEnabled(False)
        self.discovery = CameraDiscovery(self)
        self.discovery.discovered.connect(self.cameras_found)
        self.discovery.failed.connect(self.discovery_error)
        self.discovery.finished.connect(lambda: self.refresh.setEnabled(True))
        self.discovery.start()

    def discovery_error(self, error):
        self.message.setText(f"Camera discovery failed: {error}")

    def cameras_found(self, cameras):
        self.camera.clear()
        for index, name in cameras:
            self.camera.addItem(f"{name} · {index}", index)
        selected = self.camera.findData(self.settings["camera"])
        self.camera.setCurrentIndex(max(0, selected))
        if not cameras:
            self.message.setText("No webcams found. Connect a camera, check Windows camera permissions, then refresh.")
        self.start_button.setEnabled(bool(cameras) and not self.camera_blocked and not self.closing)

    def start_camera(self):
        if self.pipeline and self.pipeline.isRunning():
            return
        if self.camera.currentData() is None or self.camera_blocked:
            return
        self.settings.update(camera=self.camera.currentData(),
                             width=self.resolution.currentData()[0], height=self.resolution.currentData()[1],
                             fps=self.fps_target.currentData())
        self.save()
        self.pipeline = Pipeline(self.settings, self.assets, self.mappings, self.facial_rules)
        if self.face_setup:
            self.pipeline.command("setup", True)
        if self.reaction_editor:
            self.pipeline.command("preview", True)
        self.pipeline.error.connect(self.pipeline_error)
        self.pipeline.ready.connect(self.camera_ready)
        self.pipeline.finished.connect(self.camera_finished)
        self.stopping = False
        self.set_controls(True)
        self.live.setText("●  STARTING")
        self.message.setText("Initializing local vision models and camera…")
        self.pipeline.start()

    def set_controls(self, running):
        for control in (self.camera, self.resolution, self.fps_target, self.refresh):
            control.setEnabled(not running)
        self.start_button.setEnabled(not running and self.camera.count() > 0 and not self.camera_blocked)
        self.stop_button.setEnabled(running)
        self.stop_button.setVisible(running)
        self.start_button.setVisible(not running)

    def camera_ready(self):
        if not self.stopping:
            self.live.setText("●  CAMERA LIVE")
            self.message.setText("Live · hold a gesture deliberately to trigger an effect")

    def pipeline_error(self, error):
        self.message.setText(error)

    def stop_camera(self):
        if self.pipeline and self.pipeline.isRunning():
            self.stopping = True
            self.pipeline.stop()
            self.stop_button.setEnabled(False)
            self.live.setText("●  STOPPING")

    def camera_finished(self):
        self.camera_blocked = self.pipeline.capture_stuck
        self.set_controls(False)
        self.live.setText("●  CAMERA OFF")
        self.preview.clear()
        self.output.clear()
        if self.face_setup:
            self.face_setup.clear_live()
        if self.reaction_editor:
            self.reaction_editor.clear_live()
        self.face_status.setText("Facial: —")
        self.progress.setValue(0)
        self.metrics.setText("Camera idle")
        if self.stopping:
            self.message.setText("Camera stopped" if not self.camera_blocked else
                                 "Camera driver did not stop; restart MemeCam before opening it again.")
        self.stopping = False

    def refresh_library(self):
        self.library_title.setText(f"Tu biblioteca · {len(self.assets.items)}")
        while self.library_layout.count():
            widget = self.library_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        for item in self.assets.items:
            tile = QToolButton()
            tile.setText(item.name)
            tile.clicked.connect(lambda checked=False, key=item.id: self.trigger(key))
            tile.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            tile.setIcon(QIcon(str(self.assets.directory / item.file)))
            tile.setIconSize(QSize(88, 44))
            tile.setFixedSize(144, 88)
            tile.setToolTip(f"{item.tracking_mode} · {'persistent' if not item.duration else str(item.duration)+'s'}")
            tile.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tile.customContextMenuRequested.connect(lambda pos, key=item.id: self.reaction_menu(key))
            tile.mouseDoubleClickEvent = lambda event, key=item.id: self.edit_reaction(key)
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)
            card_layout.addWidget(tile)
            edit = button("Editar / vincular", lambda checked=False, key=item.id: self.edit_reaction(key))
            edit.setObjectName("quiet")
            edit.setFixedWidth(144)
            edit.setStyleSheet("padding:4px; font-size:11px;")
            card_layout.addWidget(edit)
            self.library_layout.addWidget(card)
        self.library_layout.addStretch()

    def trigger(self, identifier):
        if self.pipeline and self.pipeline.isRunning() and not self.stopping:
            self.pipeline.command("trigger", identifier)
        else:
            self.message.setText("Enciende la cámara para mostrar tu reacción. Doble clic en la tarjeta para editarla.")

    def clear_overlays(self):
        if self.pipeline and self.pipeline.isRunning():
            self.pipeline.command("clear")

    def add_overlay(self):
        self.edit_reaction()

    def edit_reaction(self, identifier=None):
        if self.reaction_editor is None:
            from memecam.ui.reaction_editor import ReactionEditor
            item = next((v for v in self.assets.items if v.id == identifier), None)
            self.reaction_editor = ReactionEditor(self, item)
            if self.pipeline and self.pipeline.isRunning():
                self.pipeline.command("preview", True)
        self.reaction_editor.show()
        self.reaction_editor.raise_()
        self.reaction_editor.activateWindow()

    def reaction_menu(self, identifier):
        menu = QMenu(self)
        edit = menu.addAction("Editar imagen y posición")
        link = menu.addAction("Activar con una expresión")
        selected = menu.exec(self.cursor().pos())
        if selected == edit:
            self.edit_reaction(identifier)
        elif selected == link:
            self.open_face_setup()
            self.face_setup.saved.setCurrentIndex(0)
            self.face_setup.overlay.setCurrentIndex(self.face_setup.overlay.findData(identifier))

    def open_output(self):
        self.output.configure(self.borderless.isChecked(), self.fullscreen.isChecked())
        self.output.raise_()

    def open_face_setup(self):
        if self.face_setup is None:
            from memecam.ui.face_setup import FaceSetup
            self.face_setup = FaceSetup(self)
            if self.pipeline and self.pipeline.isRunning():
                self.pipeline.command("setup", True)
        self.face_setup.show()
        self.face_setup.raise_()
        self.face_setup.activateWindow()

    def output_mode(self):
        self.settings["borderless"] = self.borderless.isChecked()
        self.settings["fullscreen"] = self.fullscreen.isChecked()
        if not self.demo:
            self.save()
        if self.output.isVisible():
            self.output.configure(self.borderless.isChecked(), self.fullscreen.isChecked())

    def tick(self):
        if self.pipeline and not self.stopping and self.pipeline.isRunning():
            packet = self.pipeline.take()
            if packet:
                clean, debug, status = packet
                if self.face_setup:
                    self.face_setup.update_frame(clean, status)
                if self.reaction_editor and status.get("preview_frame") is not None:
                    self.reaction_editor.update_frame(status["preview_frame"], status)
                self.preview.set_frame(debug)
                self.output.set_frame(debug if self.output_debug.isChecked() else clean)
                self.metrics.setText(f"{status['fps']:.1f} FPS  •  {status['size']}  •  {status['latency']:.0f} ms processing")
                candidate = status['candidate']
                self.gesture_status.setText(f"Candidate: {(candidate or '—').replace('_', ' ')}")
                self.confirmed.setText(f"Last confirmed: {(status['confirmed'] or '—').replace('_', ' ')}")
                self.progress.setValue(int(status['progress'] * 100))
                face_key = status.get("face_candidate")
                rule = next((r for r in self.facial_rules if r["id"] == face_key), None)
                self.face_status.setText(f"Facial: {rule['name']} · {status.get('face_progress', 0):.0%}" if rule
                                         else "Facial: esperando expresión")
                for key, label in self.gesture_labels.items():
                    label.setStyleSheet("color:#c0f2d5;" if key == candidate else "")
                self.message.setText(f"Detection: {'hand found' if status['hands'] else 'no hand'} · "
                                     f"{'face tracked' if status['face'] else 'no face'} · "
                                     f"{len(status['active'])} active overlay(s)")
        if self.closing:
            busy = ((self.pipeline and self.pipeline.isRunning()) or
                    (self.discovery and self.discovery.isRunning()))
            if not busy:
                self.close()

    def closeEvent(self, event):
        self.closing = True
        self.stop_camera()
        if ((self.pipeline and self.pipeline.isRunning()) or
                (self.discovery and self.discovery.isRunning())):
            self.message.setText("Releasing camera and vision resources…")
            event.ignore()
            return
        if self.camera.currentData() is not None and not self.demo:
            self.settings["camera"] = self.camera.currentData()
            self.settings["width"], self.settings["height"] = self.resolution.currentData()
            self.settings["fps"] = self.fps_target.currentData()
        if not self.demo:
            self.save()
        self.output.close()
        if self.reaction_editor:
            self.reaction_editor.close()
        if self.face_setup:
            self.face_setup.close()
        self.timer.stop()
        event.accept()
