from admin_cohort.tests.tests_tools import ViewSetTests, new_random_user


class CohortAppTests(ViewSetTests):
    def setUp(self):
        super(CohortAppTests, self).setUp()
        self.user1 = new_random_user()
        self.user2 = new_random_user()
        self.users = [self.user1, self.user2]
