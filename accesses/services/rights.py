from accesses.models import Right


class RightsService:

    @staticmethod
    def all_rights():
        return Right.objects.all()

    def list_rights(self):
        right_categories = {}
        for right in self.all_rights():
            if right.category not in right_categories:
                right_categories[right.category] = {"name": right.category,
                                                    "is_global": right.is_global,
                                                    "rights": [{"name": right.name,
                                                                "label": right.label,
                                                                "depends_on": right.depends_on and right.depends_on.name or None}]}
            else:
                right_categories[right.category]["rights"].append({"name": right.name,
                                                                   "label": right.label,
                                                                   "depends_on": right.depends_on and right.depends_on.name or None})
        return right_categories.values()


rights_service = RightsService()

all_rights = rights_service.all_rights()
