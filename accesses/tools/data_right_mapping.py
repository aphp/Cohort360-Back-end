from accesses.models import Perimeter


# ------------------------- CLASS DEFINITION -------------------------
class DataReadRight:
    def __init__(self, user_id: str, provider_id: int, pseudo: bool = False, nomi: bool = False,
                 **kwargs):
        """
        @return: a default DataRight as required by the serializer
        """
        if 'perimeter' in kwargs:
            self.perimeter: Perimeter = kwargs['perimeter']
        self.provider_id = provider_id
        self.user_id = user_id
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.read_role = "NO READ PATIENT RIGHT"
        if nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"


class PerimeterReadRight:
    def __init__(self, perimeter: Perimeter, pseudo: bool = False, nomi: bool = False, ipp: bool = False):
        """
        @return: a default DataRight as required by the serializer
        """

        self.perimeter: Perimeter = perimeter
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.right_search_patient_with_ipp = ipp
        self.read_role = "NO READ PATIENT RIGHT"
        if nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"


