import numpy as np

from src.detection.oncam_detector import detect_oncam, has_video_feed
from src.detection.phone_detector import detect_phone
from src.engine.frame_buffer import FrameBuffer


def test_black_tile_is_offcam():
    black_tile = np.zeros((224, 224, 3), dtype=np.uint8)
    assert has_video_feed(black_tile) is False
    result = detect_oncam(black_tile)
    assert result["oncam"] is False


def test_noisy_tile_has_video_feed():
    noisy_tile = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    assert has_video_feed(noisy_tile) is True


def test_phone_detection_no_hand_returns_false():
    blank_tile = np.full((224, 224, 3), 255, dtype=np.uint8)
    result = detect_phone(blank_tile)
    assert result["holding_phone"] is False


def test_frame_buffer_assigns_stable_participant_ids():
    buffer = FrameBuffer()
    slot0 = buffer.get_slot(0)
    slot0_again = buffer.get_slot(0)
    slot1 = buffer.get_slot(1)
    assert slot0.participant_id == slot0_again.participant_id == "P001"
    assert slot1.participant_id == "P002"


def test_frame_buffer_has_slot_before_and_after_creation():
    buffer = FrameBuffer()
    assert buffer.has_slot(5) is False
    buffer.get_slot(5)
    assert buffer.has_slot(5) is True


def test_frame_buffer_string_key_uses_name_as_participant_id():
    buffer = FrameBuffer()
    slot = buffer.get_slot("Budi Santoso")
    assert slot.participant_id == "Budi Santoso"
    assert slot.name == "Budi Santoso"
    assert buffer.has_slot("Budi Santoso") is True
    assert buffer.has_slot("Ani Rahayu") is False


def test_process_named_frame_requires_active_session(tmp_path):
    import pytest
    from src.data.database import Database
    from src.engine.analysis_engine import AnalysisEngine

    db = Database(path=tmp_path / "test_session.db")
    engine = AnalysisEngine(db)
    blank = np.full((224, 224, 3), 255, dtype=np.uint8)
    with pytest.raises(RuntimeError):
        engine.process_named_frame("Budi Santoso", blank)
    engine.close()
    db.close()


def test_overlay_data_maps_tile_bbox_to_screen_coordinates(tmp_path, monkeypatch):
    """process_screen_frame(frame, screen_offset=(left, top)) should record
    each confirmed participant's tile position in absolute screen
    coordinates (tile bbox + capture region offset), which is what the AR
    overlay window draws boxes at."""
    from src.data.database import Database
    from src.engine import analysis_engine as engine_module
    from src.engine.analysis_engine import AnalysisEngine

    # Force every tile to be treated as a confirmed face, regardless of
    # actual pixel content, so this test doesn't depend on a real face image.
    monkeypatch.setattr(
        engine_module.oncam_detector, "detect_oncam",
        lambda image: {"feed_present": True, "face_found": True, "oncam": True},
    )

    db = Database(path=tmp_path / "test_overlay.db")
    engine = AnalysisEngine(db)
    engine.splitter.grid = "2x2"
    engine.splitter.min_tile_size = 10
    engine.start_session()

    frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    engine.process_screen_frame(frame, screen_offset=(1920, 100))  # e.g. second monitor

    overlay = engine.overlay_data()
    assert len(overlay) == 4  # 2x2 grid, all confirmed

    top_left = next(p for p in overlay if p["x"] == 1920 and p["y"] == 100)
    assert top_left["width"] == 100
    assert top_left["height"] == 100

    engine.close()
    db.close()
