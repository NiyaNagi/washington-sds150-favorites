"""Digital contact directory capability on radio profiles."""
from __future__ import annotations

import pytest

from wasds150.radios.profile import ContactCapability
from wasds150.radios.registry import get_profile, profile_ids


def test_atd890uv_holds_dmr_and_nxdn_contacts():
    contacts = get_profile("at-d890uv").contacts
    assert contacts is not None
    assert contacts.supports("dmr") and contacts.supports("NXDN")
    assert contacts.max_contacts == 500_000
    assert contacts.call_type == "Private Call"


def test_radios_without_a_directory_say_so():
    for radio_id in profile_ids():
        if radio_id != "at-d890uv":
            assert get_profile(radio_id).contacts is None, radio_id


def test_contact_capability_validates_its_inputs():
    with pytest.raises(ValueError):
        ContactCapability(protocols=frozenset(), max_contacts=10)
    with pytest.raises(ValueError):
        ContactCapability(protocols=frozenset({"DMR"}), max_contacts=0)
