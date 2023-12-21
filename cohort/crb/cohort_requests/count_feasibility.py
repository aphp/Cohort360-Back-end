from __future__ import annotations

from cohort.crb import CohortCount
from cohort.crb.enums import Mode


class CohortCountFeasibility(CohortCount):
    def __init__(self, *args, **kwargs):
        super().__init__(mode=Mode.COUNT_WITH_DETAILS, *args, **kwargs)
