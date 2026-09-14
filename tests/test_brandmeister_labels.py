from wasds150.catalog.brandmeister import favorites_from_snapshot


def test_a_talkgroup_named_for_its_repeater_does_not_repeat_the_call():
    row = (310001, "N7QT", "Everett", 442.325, 447.325, 1, 47.9, -122.2, "2026-09-01", ((9, 2), (91, 1)))
    favorite = favorites_from_snapshot({9: "N7QT Local", 91: "Worldwide"}, [row], "2026-09-01")[0]
    labels = sorted(c.label for s in favorite.systems for d in s.departments for c in d.channels)
    assert labels == ["N7QT Local", "N7QT Worldwide"]
