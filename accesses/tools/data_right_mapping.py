from accesses.models import Perimeter


# ------------------------- CLASS DEFINITION -------------------------

class PerimeterReadRight:
    def __init__(self, perimeter: Perimeter, pseudo: bool = False, nomi: bool = False, ipp: bool = False):
        """
        @return: a default DataRight as required by the serializer
        """

        self.perimeter: Perimeter = perimeter
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.right_search_patients_by_ipp = ipp
        self.read_role = "NO READ PATIENT RIGHT"
        if nomi:
            self.read_role = "READ_PATIENT_NOMINATIVE"
        elif pseudo:
            self.read_role = "READ_PATIENT_PSEUDO_ANONYMIZE"
