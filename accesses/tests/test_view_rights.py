from rest_framework import status

from accesses.models import Right
from accesses.views import RightsViewSet
from admin_cohort.tests.tests_tools import ViewSetTests, ListCase, new_user_and_profile


class RightsViewTests(ViewSetTests):
    objects_url = "/rights/"
    list_view = RightsViewSet.as_view({'get': 'list'})
    model = Right
    model_objects = Right.objects

    def setUp(self):
        super().setUp()
        self.user, _ = new_user_and_profile(email="user.rights_tests@aphp.fr")
        self.rights = self.create_rights()

    def create_rights(self):
        self.model_objects.all().delete()
        rights = []
        for i in range(10):
            rights.append(self.model_objects.create(name=f'right_{i}',
                                                    label=f'right_label_{i}',
                                                    category=f'category_{i%2}'))
        return rights

    def test_list_rights(self):
        right_categories_to_find = [
            {'name': 'category_0', 'rights': [r for r in self.rights if r.name.endswith('0')]},
            {'name': 'category_1', 'rights': [r for r in self.rights if r.name.endswith('1')]}
        ]
        case = ListCase(to_find=right_categories_to_find,
                        user=self.user,
                        status=status.HTTP_200_OK,
                        success=True)
        self.check_list_case(case=case)

