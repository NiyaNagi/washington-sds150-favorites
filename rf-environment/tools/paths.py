"""Shared locations for the RF-environment tools.

Raw sweeps from new runs and anything derived from the licensed local catalog
(RadioReference rows) go under .wasds150-home/, which is gitignored. Only
measured frequency/level data is ever copied into rf-environment/ for commit.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORK = REPO / ".wasds150-home" / "rf-environment"
RF = Path(os.environ.get("RF_OUT", WORK / "rf"))
RF.mkdir(parents=True, exist_ok=True)
CATALOG = REPO / ".wasds150-home" / "catalog.json"
FREQ_INDEX = WORK / "freq_index.json"      # built from the licensed catalog: never commit
PROGRAMMED = WORK / "programmed.json"      # built from radio-data/*/exports reports
RADIO_DATA = REPO / "radio-data"
HOME_QTH = (47.6351, -121.9954)
