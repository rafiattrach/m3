from m3.core.preset.base import Preset
from m3.core.preset.presets.default_preset import DefaultM3Preset

ALL_PRESETS: dict[str, type[Preset]] = {
    "default_m3": DefaultM3Preset,
}
