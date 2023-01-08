from drf_yasg import openapi

from accesses.serializers import DataRightSerializer, DataReadRightSerializer, ProfileCheckSerializer

# ************************************* access

access_list_manual_parameters = list(map(
    lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                                pattern=x[3] if len(x) == 4 else None),
    [["perimeter_id", "Filter type", openapi.TYPE_STRING],
     ["target_perimeter_id", "Filter type. Used to get accesses on parents of this perimeter", openapi.TYPE_STRING],
     ["profile_email", "Search type", openapi.TYPE_STRING],
     ["profile_name", "Search type", openapi.TYPE_STRING],
     ["profile_lastname", "Search type", openapi.TYPE_STRING],
     ["profile_firstname", "Search type", openapi.TYPE_STRING],
     ["profile_user_id", "Search type", openapi.TYPE_STRING, r'\d{1,7}'],
     ["profile_id", "Filter type", openapi.TYPE_STRING],
     ["search", "Will search in multiple fields (perimeter_name, provider_name, lastname, firstname, "
                "provider_source_value, email)", openapi.TYPE_STRING],
     ["ordering", "To sort the result. Can be care_site_name, role_name, start_datetime, end_datetime, is_valid. "
                  "Use -field for descending order", openapi.TYPE_STRING]]))

access_create_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={"provider_history_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                      description="(to deprecate -> profile_id) Correspond à "
                                                                  "Provider_history_id"),
                "profile_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Correspond à un profile_id"),
                "care_site_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="2deprecate -> perimeter_id"),
                "perimeter_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "role_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                 description="Doit être dans le futur.\nSi vide ou null, sera défini à "
                                                             "now().\nDoit contenir la timezone ou bien sera considéré "
                                                             "comme UTC."),
                "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                               description="Doit être dans le futur. \nSi vide ou null, sera défini à "
                                                           "start_datetime + 1 un an.\nDoit contenir la timezone ou "
                                                           "bien sera considéré comme UTC.")},
    required=['profile', 'perimeter', 'role'])

access_partial_update_request_body = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={"start_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                     description="Doit être dans le futur.\nNe peut pas être modifié "
                                                                 "si start_datetime actuel est déja passé.\nSera mis à "
                                                                 "now() si null.\nDoit contenir la timezone ou bien "
                                                                 "sera considéré comme UTC."),
                    "end_datetime": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME,
                                                   description="Doit être dans le futur.\nNe peut pas être modifié si "
                                                               "end_datetime actuel est déja passé.\nNe peut pas être "
                                                               "mise à null.\nDoit contenir la timezone ou bien sera "
                                                               "considéré comme UTC.")})

data_right_op_desc = "Returns particular type of objects, describing the data rights that a user has on a "\
                            "care-sites. AT LEAST one parameter is necessary"

data_right_manual_parameters = list(map(
    lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                                pattern=x[3] if len(x) == 4 else None),
    [["care-site-ids", "(to deprecate -> perimeters_ids) List of care-sites to limit the result on. Sep: ','",
      openapi.TYPE_STRING],
     ["perimeters_ids", "List of perimeters to limit the result on. Sep: ','", openapi.TYPE_STRING],
     ["pop-children", "2deprecate(pop_children) If True, keeps only the biggest parents for each right",
      openapi.TYPE_BOOLEAN],
     ["pop_children", "If True, keeps only the biggest parents for each right", openapi.TYPE_BOOLEAN]]))

data_right_responses = {200: openapi.Response('Rights found', DataRightSerializer),
                        403: openapi.Response('perimeters_ids and pop_children are both null')}


# ************************************* perimeter

get_manageable_op_summary = "Get the top hierarchy perimeters on which the user has at least one role that allows to "\
                            "give accesses. 1. Same level right give access to current perimeter and lower levels."\
                            "2. Inferior level right give only access to children of current perimeter."

get_perimeters_read_right_accesses_op_summary = "Give perimeters and associated read patient roles for current user "\
                                                "and search IPP If no perimeters param search are present, it "\
                                                "shows top hierarchy"

get_perimeters_read_right_accesses_responses = {'201': openapi.Response("give rights in caresite perimeters found",
                                                                        DataReadRightSerializer())}

perimeter_list_manual_parameters = list(map(
    lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                                pattern=x[3] if len(x) == 4 else None),
    [["ordering", "'field' or '-field' in care_site_name, care_site_type_source_value, care_site_source_value",
      openapi.TYPE_STRING],
     ["search", "Will search in multiple fields (care_site_name, care_site_type_source_value, care_site_source_value)",
      openapi.TYPE_STRING],
     ["treefy", "If true, returns a tree-organised json, else a list", openapi.TYPE_BOOLEAN]]))


# ************************************* profile

profile_list_manual_parameters = list(map(
    lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                                pattern=x[3] if len(x) == 4 else None),
    [["provider_source_value", "(to deprecate -> user) Search type", openapi.TYPE_STRING, r"\d{1,7}"],
     ["user", "Filter type (User's id)", openapi.TYPE_STRING, r"\d{1,7}"],
     ["provider_name", "Search type", openapi.TYPE_STRING],
     ["email", "Search type", openapi.TYPE_STRING],
     ["lastname", "Search type", openapi.TYPE_STRING],
     ["firstname", "Search type", openapi.TYPE_STRING],
     ["provider_history_id", "(to deprecate -> id) Filter type", openapi.TYPE_INTEGER],
     ["id", "Filter type", openapi.TYPE_INTEGER],
     ["provider_id", "Filter type", openapi.TYPE_INTEGER],
     ["cdm_source", "(to deprecate -> source) Filter type ('MANUAL', 'ORBIS', etc.)", openapi.TYPE_STRING],
     ["source", "Filter type ('MANUAL', 'ORBIS', etc.)", openapi.TYPE_STRING],
     ["is_active", "Filter type", openapi.TYPE_BOOLEAN],
     ["search", "Filter on several fields (provider_source_value, provider_name, lastname, firstname, email)",
      openapi.TYPE_STRING]]))

profile_partial_update_request_body = openapi.Schema(type=openapi.TYPE_OBJECT,
                                                     properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "email": openapi.Schema(type=openapi.TYPE_STRING),
                                                                 "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                                                 })

profile_create_request_body = openapi.Schema(type=openapi.TYPE_OBJECT,
                                             properties={"firstname": openapi.Schema(type=openapi.TYPE_STRING),
                                                         "lastname": openapi.Schema(type=openapi.TYPE_STRING),
                                                         "email": openapi.Schema(type=openapi.TYPE_STRING),
                                                         "provider_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                                                       description="(to deprecate)"),
                                                         "user": openapi.Schema(type=openapi.TYPE_STRING),
                                                         "provider_source_value": openapi.Schema(
                                                             type=openapi.TYPE_STRING,
                                                             description="(to deprecate)")
                                                         })

check_existing_user_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={"provider_source_value": openapi.Schema(type=openapi.TYPE_STRING,
                                                        description="(to deprecate, use 'user_id' instead)"),
                "user_id": openapi.Schema(type=openapi.TYPE_STRING)
                })

check_existing_user_responses = {'201': openapi.Response("User found", ProfileCheckSerializer()),
                                 '204': openapi.Response("No user found")}


# ************************************* role

assignable_manual_parameters = [openapi.Parameter(name="care_site_id", in_=openapi.IN_QUERY,
                                                  description="(to deprecate -> perimeter_id) Required",
                                                  type=openapi.TYPE_INTEGER),
                                openapi.Parameter(name="perimeter_id", in_=openapi.IN_QUERY,
                                                  description="Required", type=openapi.TYPE_INTEGER)]

assignable_op_summary = "Get roles that the user can assign to a user on the perimeter provided."
