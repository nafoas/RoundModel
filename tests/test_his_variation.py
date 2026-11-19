"""How much he varies between moments (tools/his_variation.py -> data/scene/his_variation.json)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_measure_is_offered_as_a_tolerance_yet():
    doc = json.loads((ROOT / "data/scene/his_variation.json").read_text())
    first, three = doc["first_try_eyes_flat"], doc["eyes_3d_between_moments"]
    assert first["usable"] is False and three["usable"] is False
    assert "tolerance_percent" not in first and "tolerance_percent" not in three   # nothing to pick up by mistake
    assert doc["rejected_fits"] == ["data/photos/by_angle/01_front/11_looking_up_slight.webp"]
    assert doc["surface_bumpiness"]["usable"] is False


def test_the_burst_is_one_moment():
    """Owner: the anchor, 01_front and 18_staring_at_boss are three shots of one moment."""
    idx = json.loads((ROOT / "data/photos/index.json").read_text())
    same = {e["file"].split("/")[-1] for e in idx["measuring_photos"] if e.get("same_moment_as_anchor")}
    assert same == {"01_front.webp", "18_staring_at_boss.webp"}
    first = json.loads((ROOT / "data/scene/his_variation.json").read_text())["first_try_eyes_flat"]
    assert "repeatability" in first["same_moment_is"]                  # not "head level": not his variation
