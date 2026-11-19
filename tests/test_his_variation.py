"""How much he varies between moments (tools/his_variation.py -> data/scene/his_variation.json)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_first_measures_are_marked_not_usable_and_bad_fits_rejected():
    doc = json.loads((ROOT / "data/scene/his_variation.json").read_text())
    eyes = doc["eyes_between_moments"]
    assert eyes["usable"] is False and "nod" in eyes["finding"]            # follows his head's nod: no tolerance
    assert "tolerance_percent" not in eyes                                  # nothing anyone could pick up by mistake
    assert eyes["rejected_fits"] == ["data/photos/by_angle/01_front/11_looking_up_slight.webp"]
    assert eyes["n"] == len(eyes["per_photo"]) - len(eyes["rejected_fits"])
    level = eyes["head_level_only"]
    assert level["n"] == 3 and level["spread_percent"] < 3                  # anchor, 01, 18 only (not every front photo)
    assert doc["surface_bumpiness"]["usable"] is False
