"""Per-radio values the fleet wizard needs: a COM port, where a vendor
program is installed, the folder a programmer loads from.

Saved in ``state/fleet-settings.json`` beside :mod:`wasds150.sources.config`
and in the same shape. **No secrets**: nothing a radio needs to be updated is
a credential, and nothing here may become one.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from wasds150.fleet.model import FleetRadio, InputSpec


@dataclass
class FleetSettings:
    #: ``{radio_id: {input_id: value}}``
    radios: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def get(self, radio_id: str, input_id: str, default: str = "") -> str:
        return self.radios.get(radio_id, {}).get(input_id, default)

    def set(self, radio_id: str, input_id: str, value: str) -> None:
        """Store ``value``; an empty value clears the setting."""
        values = self.radios.setdefault(radio_id, {})
        if value:
            values[input_id] = value
        else:
            values.pop(input_id, None)
            if not values:
                self.radios.pop(radio_id, None)

    def values_for(self, radio: FleetRadio) -> Dict[str, str]:
        """Every input of ``radio``: the saved value, else the default."""
        return {spec.id: self.get(radio.radio_id, spec.id, spec.default) for spec in radio.inputs}

    def missing(self, radio: FleetRadio) -> List[InputSpec]:
        values = self.values_for(radio)
        return [spec for spec in radio.inputs if spec.required and not values.get(spec.id)]

    def to_dict(self) -> Dict[str, Any]:
        return {"radios": {radio: dict(values) for radio, values in sorted(self.radios.items())}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetSettings":
        radios = data.get("radios", {}) or {}
        return cls(radios={str(r): {str(k): str(v) for k, v in values.items()} for r, values in radios.items()})

    @classmethod
    def load(cls, path: Path) -> "FleetSettings":
        if not Path(path).exists():
            return cls()
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)


def parse_assignment(text: str) -> Tuple[str, str, str]:
    """``"td-h9.com_port=COM7"`` -> ``("td-h9", "com_port", "COM7")``."""
    target, sep, value = text.partition("=")
    radio_id, dot, input_id = target.strip().partition(".")
    if not sep or not dot or not radio_id or not input_id:
        raise ValueError(f"expected radio.input=value, got {text!r}")
    return radio_id.lower(), input_id, value.strip()
