from admin_cohort.tools.tests_tools import ViewSetTests, new_random_user


class CohortAppTests(ViewSetTests):
    def setUp(self):
        super(CohortAppTests, self).setUp()
        self.user1 = new_random_user(firstname="Squall", lastname="Leonheart",
                                     email='s.l@aphp.fr')
        self.user2 = new_random_user(firstname="Seifer", lastname="Almasy",
                                     email='s.a@aphp.fr')
        self.users = [self.user1, self.user2]
