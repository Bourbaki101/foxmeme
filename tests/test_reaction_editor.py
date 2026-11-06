import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QCoreApplication, QEvent

from memecam.config.settings import DEFAULTS, write_json
from memecam.overlays.asset_manager import AssetManager
from memecam.ui.main_window import MainWindow
from memecam.vision.smoothing import FacePose


@pytest.fixture
def studio(qapp, tmp_path, monkeypatch):
    import memecam.ui.main_window as main
    import memecam.ui.face_setup as facial
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(facial, "ROOT", tmp_path)
    library = tmp_path / "library"
    library.mkdir()
    metadata = tmp_path / "overlays.json"
    write_json(metadata, [])
    window = MainWindow(DEFAULTS.copy(), AssetManager(library, metadata), {}, demo=True)
    window.facial_rules = []
    window.show()
    yield window
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def image_file(tmp_path):
    source = tmp_path / "Mi reacción.png"
    image = np.full((24, 32, 4), (20, 80, 230, 180), np.uint8)
    source.write_bytes(cv2.imencode(".png", image)[1].tobytes())
    return source


def test_visible_upload_preview_save_and_reload(studio, tmp_path, monkeypatch, qapp):
    source = image_file(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(source), ""))
    studio.upload_button.click()
    editor = studio.reaction_editor
    assert editor.isVisible() and not editor.save_button.isEnabled()
    editor.upload.click()
    assert editor.source == source and editor.name.text() == source.stem
    assert editor.preview.image is not None
    assert not studio.assets.items  # The preview never imports or changes the library.
    editor.placement.setCurrentIndex(editor.placement.findData("eyes"))
    editor.horizontal.setValue(12)
    editor.vertical.setValue(-8)
    editor.save_button.click()
    qapp.processEvents()
    restored = AssetManager(studio.assets.directory, studio.assets.metadata)
    item = restored.items[0]
    assert item.tracking_mode == "eyes" and item.scale == 2.4
    assert item.offset_x == .12 and item.offset_y == -.08
    assert item.duration == 0 and item.rotation_mode == "face"
    assert restored.images[item.id][0, 0, 3] == 180
    assert studio.reaction_editor is None


def test_cancel_invalid_image_and_missing_name_do_not_import(studio, tmp_path):
    studio.add_overlay()
    editor = studio.reaction_editor
    source = tmp_path / "bad.png"
    source.write_bytes(b"bad image")
    assert not editor.load_image(source)
    assert not editor.save_button.isEnabled()
    assert editor.load_image(image_file(tmp_path))
    editor.name.clear()
    editor.save_reaction()
    assert not studio.assets.items
    editor.close()
    assert not list(studio.assets.directory.iterdir())
    assert AssetManager(studio.assets.directory, studio.assets.metadata).items == []


def test_edit_preserves_links_and_links_new_expression_to_selected_image(studio, tmp_path):
    item = studio.assets.add(image_file(tmp_path), "Mi sticker", "face")
    studio.facial_rules = [dict(id="existing", name="Anterior", overlay=item.id,
                              enabled=True, threshold=.65, features={"jawOpen": [.1, .8]})]
    studio.edit_reaction(item.id)
    editor = studio.reaction_editor
    editor.size.setValue(135)
    editor.link_button.click()
    assert len(studio.assets.items) == 1
    assert studio.assets.items[0].id == item.id
    assert studio.assets.items[0].scale == 1.35
    assert studio.facial_rules[0]["overlay"] == item.id
    assert studio.face_setup.overlay.currentData() == item.id
    assert studio.face_setup.saved.currentData() is None
    assert studio.face_setup.name.text() == "Mi sticker"


def test_live_preview_respects_face_loss_and_does_not_modify_camera_frame(studio, tmp_path):
    studio.add_overlay()
    editor = studio.reaction_editor
    editor.load_image(image_file(tmp_path))
    frame = np.zeros((180, 320, 3), np.uint8)
    editor.update_frame(frame, {"pose": FacePose(160, 80, 50, 0, 160, 90, 100)})
    assert editor.preview.image.pixelColor(160, 90).red() > 0
    assert not frame.any()
    editor.update_frame(frame, {"pose": None})
    assert editor.preview.image.pixelColor(160, 90).red() == 0
    assert "No vemos tu rostro" in editor.preview_note.text()
    editor.placement.setCurrentIndex(editor.placement.findData("screen"))
    assert editor.preview.image.pixelColor(160, 90).red() > 0
    editor.clear_live()
    assert "EJEMPLO" in editor.preview_note.text()


def test_invalid_placement_cannot_leave_orphan_import(studio, tmp_path):
    with pytest.raises(ValueError):
        studio.assets.add(image_file(tmp_path), "Invalid", "face", scale=99)
    assert not list(studio.assets.directory.iterdir())
    assert not studio.assets.items
