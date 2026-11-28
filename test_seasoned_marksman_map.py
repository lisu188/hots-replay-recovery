import json
import unittest

import build_seasoned_marksman_map as sm

HERO = sm.HERO
OTHER = "Base.StormData\\GameData\\TalentData.xml"
BASE_HERO = (b'<?xml version="1.0" encoding="us-ascii"?>\r\n<Catalog>\r\n'
             b'<CHero id="Nova"><TalentTreeArray index="3" Talent="X" /></CHero>\r\n</Catalog>\r\n')


def tyrande_xml(slot_talent=sm.STOCK, extra=""):
    rows = [f'<TalentTreeArray Talent="T{i}" Tier="{1 + i // 3}" Column="{1 + i % 3}"/>' for i in range(21)]
    rows[2] = f'<TalentTreeArray Talent="{slot_talent}" Tier="1" Column="3"/>'
    return f'<Catalog><CHero id="Tyrande">{"".join(rows)}</CHero>{extra}</Catalog>'.encode()


def shared(behaviors=None, target="40"):
    rows = "".join(f'<BehaviorArray value="{b}"/>' for b in (behaviors or sm.TARGET_BEHAVIORS))
    return (f'<Catalog><CTalent id="{sm.TALENT}"><RankArray>{rows}</RankArray>'
            f'<QuestData StackBehavior="TalentSeasonedMarksmanTokenCounter" TargetCount="{target}"/></CTalent></Catalog>').encode()


def historical(slot_id=sm.TALENT, description=sm.DESCRIPTION):
    tier = [{"id": "A"}, {"id": "B"}, {"id": slot_id, "description": description}, {"id": "D"}]
    return json.dumps([{"id": "Nova", "talents": {}}, {"id": "Tyrande", "talents": {"1": tier}}]).encode()


class PrepareTests(unittest.TestCase):
    def members(self, **extra):
        return {HERO: BASE_HERO, OTHER: b'<?xml version="1.0"?>\r\n<Catalog>\r\n</Catalog>\r\n', **extra}

    def test_appends_exactly_one_tyrande_record(self):
        edits = sm.prepare(self.members(), tyrande_xml(), shared(), historical())
        self.assertEqual(list(edits), [HERO])
        result = edits[HERO]
        self.assertTrue(result.startswith(BASE_HERO[:-len(b"</Catalog>\r\n")]))
        self.assertIn(b'<CHero id="Tyrande"><TalentTreeArray index="2" Talent="GenericTalentSeasonedMarksman" /></CHero>\r\n'
                      b'</Catalog>\r\n', result)
        self.assertEqual(result.count(b"<CHero"), 2)

    def test_refusals(self):
        conflicting = b'<Catalog><CTalent id="GenericTalentSeasonedMarksman"/></Catalog>'
        cases = {
            "historical slot": dict(historical_json=historical(slot_id="Other")),
            "historical rule": dict(historical_json=historical(description="Different")),
            "target slot": dict(tyrande_xml=tyrande_xml(slot_talent="TyrandeRanger")),
            "talent already in tree": dict(tyrande_xml=tyrande_xml().replace(b'"T5"', b'"GenericTalentSeasonedMarksman"')),
            "hero defines talent": dict(tyrande_xml=tyrande_xml(extra=f'<CTalent id="{sm.TALENT}"/>')),
            "shared behaviors": dict(shared_talents=shared(behaviors=["Only"])),
            "shared quest": dict(shared_talents=shared(target="25")),
            "map-local tyrande": dict(members=self.members(**{OTHER: b'<Catalog><CHero id="Tyrande"/></Catalog>'})),
            "map-local talent": dict(members=self.members(**{OTHER: conflicting})),
            "missing hero member": dict(members={OTHER: b'<Catalog/>'}),
        }
        for label, override in cases.items():
            args = {**dict(members=self.members(), tyrande_xml=tyrande_xml(), shared_talents=shared(),
                           historical_json=historical()), **override}
            with self.subTest(label), self.assertRaises(ValueError):
                sm.prepare(**args)


if __name__ == "__main__":
    unittest.main()
