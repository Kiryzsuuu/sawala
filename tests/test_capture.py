import numpy as np

from src.capture.tile_splitter import TileSplitter


def test_fixed_grid_splits_evenly():
    frame = np.zeros((400, 400, 3), dtype=np.uint8)
    splitter = TileSplitter(grid="2x2", min_tile_size=50)
    tiles = splitter.split(frame)
    assert len(tiles) == 4
    for tile in tiles:
        assert tile.image.shape[:2] == (224, 224)


def test_auto_grid_falls_back_when_no_gutters():
    frame = np.full((300, 300, 3), 200, dtype=np.uint8)  # uniform bright frame
    splitter = TileSplitter(grid="auto", min_tile_size=50)
    tiles = splitter.split(frame)
    assert len(tiles) >= 1


def test_min_tile_size_filters_small_tiles():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    splitter = TileSplitter(grid="4x4", min_tile_size=80)
    tiles = splitter.split(frame)
    assert len(tiles) == 0  # each tile would be 25x25, below min_tile_size
