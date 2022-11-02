from accesses.models import Perimeter, Access


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


# ------------------------- FUNCTION DEFINITION -------------------------
def data_read_access_mapper(accesses: [Access]) -> [DataReadRight]:
    data_read_response_list = []
    for access in accesses:
        data_read = DataReadRight(user_id=access.profile.user_id,
                                  provider_id=access.profile_id,
                                  pseudo=access.role.right_read_patient_pseudo_anonymised,
                                  nomi=access.role.right_read_patient_nominative,
                                  perimeter=access.perimeter)
        data_read_response_list.append(data_read)
    return data_read_response_list
