import unittest

from first_sync_selections import admitting_references, single


class FirstSyncSelectionTest(unittest.TestCase):
    def test_exact_type_link_and_priorities_required(self):
        evidence = {("HeroTest",80,15,1,1):{"ref"}}
        self.assertEqual(admitting_references("HeroTest",80,(15,1,1),evidence), {"ref"})
        for unit, link, priorities in [("HeroOther",80,(15,1,1)),("HeroTest",79,(15,1,1)),
                                      ("HeroTest",80,(15,2,1)),("HeroTest",80,(15,1,2))]:
            self.assertFalse(admitting_references(unit,link,priorities,evidence))

    def test_conflicting_link_withheld(self):
        evidence = {("HeroTest",80,15,1,1):{"ref1"}, ("HeroTest",81,15,1,1):{"ref2"}}
        self.assertFalse(admitting_references("HeroTest",80,(15,1,1),evidence))

    def test_opening_group_shape(self):
        event = {"m_controlGroupId":10, "m_delta":{
            "m_subgroupIndex":0, "m_removeMask":{"None":None},
            "m_addSubgroups":[{"m_count":1}], "m_addUnitTags":[7]}}
        self.assertEqual(single(event),(7,{"m_count":1}))
        event["m_delta"]["m_removeMask"]={"ZeroIndices":[]}
        self.assertIsNone(single(event))


if __name__ == "__main__":
    unittest.main()
