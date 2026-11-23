from unittest import TestCase

from historical_layout_xy import match_package_row, placements


def xml(x="153.5", player="12", unit="TownMoonwellL2"):
    return (
        f'<PlacedObjects><ObjectUnit Id="1609" Player="{player}" UnitType="{unit}" '
        f'Position="{x},143.5,0"/></PlacedObjects>'
    ).encode()


class HistoricalLayoutTests(TestCase):
    def setUp(self):
        self.original = placements(xml())
        self.command = dict(object_id=1609, type="TownMoonwellL2", xy=[628736, 587776])

    def test_verified_fractional_building(self):
        self.assertEqual(
            match_package_row(self.command, self.original, placements(xml())), (628736, 587776)
        )

    def test_reject_changed_coordinate_owner_or_type(self):
        for change in (dict(x="150.5"), dict(player="11"), dict(unit="VehicleDragon")):
            with self.subTest(change=change), self.assertRaises(ValueError):
                match_package_row(self.command, self.original, placements(xml(**change)))

    def test_reject_missing_placement_or_changed_snapshot(self):
        with self.assertRaises(ValueError):
            match_package_row(self.command, self.original, {})
        with self.assertRaises(ValueError):
            match_package_row(dict(self.command, xy=[628737, 587776]), self.original, self.original)

    def test_inexact_authored_coordinate_never_rounded(self):
        source = placements(xml(x="150.5001"))
        with self.assertRaises(ValueError):
            match_package_row(self.command, source, source)
