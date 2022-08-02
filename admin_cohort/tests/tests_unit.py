from accesses.models import get_all_level_children, \
    get_all_level_parents_perimeters
from admin_cohort.tests_tools import ViewSetTestsWithNumerousPerims


class ModelsUnitTest(ViewSetTestsWithNumerousPerims):
    def check_perim_list(self, perim_found, perim_to_find):
        perim_to_find_ids = [perim.care_site_id for perim in perim_to_find]
        msg = "\n".join(["", "got", str(perim_found), "should be",
                         str(perim_to_find_ids)])
        for i in perim_to_find_ids:
            self.assertIn(i, perim_found, msg=msg)
        self.assertEqual(len(perim_found), len(perim_to_find), msg=msg)

    # def test_get_direct_children_perim_ids_0(self):
    #     perim_found = get_direct_children_perim_ids(
    #         care_site_id=self.perim0.care_site_id)
    #     perim_to_find = [self.perim11, self.perim12]
    #     self.check_perim_list(perim_found, perim_to_find)

    def test_get_all_level_children_12(self):
        perim_found = [
            perim.id for perim in get_all_level_children(
                perimeters_ids=self.perim12.care_site_id
            )
        ]
        perim_to_find = [self.perim12, self.perim22, self.perim23,
                         self.perim32, self.perim33]
        self.check_perim_list(perim_found, perim_to_find)

    def test_get_all_level_children_11_23(self):
        perim_found = [
            perim.id for perim in get_all_level_children(
                perimeters_ids=[self.perim11.care_site_id,
                                self.perim23.care_site_id]
            )
        ]
        perim_to_find = [self.perim11, self.perim21, self.perim23, self.perim31,
                         self.perim32, self.perim33]
        self.check_perim_list(perim_found, perim_to_find)

    # def test_get_direct_parent_care_site_ids_32(self):
    #     perim_found = get_direct_parent_care_site_ids(
    #         care_site_id=self.perim32.care_site_id)
    #     perim_to_find = [self.perim21, self.perim23]
    #     self.check_perim_list(perim_found, perim_to_find)

    def test_get_all_level_parents_perimeters_32(self):
        perim_found = get_all_level_parents_perimeters(
            perimeter_ids=self.perim32.care_site_id)
        perim_to_find = [self.perim32, self.perim21, self.perim23, self.perim11,
                         self.perim12, self.perim0]
        self.check_perim_list(perim_found, perim_to_find)

    def test_get_all_level_parents_perimeters_21_23(self):
        perim_found = get_all_level_parents_perimeters(perimeter_ids=[
            self.perim21.care_site_id, self.perim23.care_site_id
        ])
        perim_to_find = [self.perim21, self.perim23, self.perim11, self.perim12,
                         self.perim0]
        self.check_perim_list(perim_found, perim_to_find)
