from drf_yasg import openapi

accesses_list = list(map(lambda x: openapi.Parameter(name=x[0], in_=openapi.IN_QUERY, description=x[1], type=x[2],
                                                     pattern=x[3] if len(x) == 4 else None),
                         [["perimeter_id", "Filter type", openapi.TYPE_STRING],
                          ["target_perimeter_id", "Filter type. Used to also get accesses on parents of this perimeter",
                           openapi.TYPE_STRING],
                          ["profile_email", "Search type", openapi.TYPE_STRING],
                          ["profile_name", "Search type", openapi.TYPE_STRING],
                          ["profile_lastname", "Search type", openapi.TYPE_STRING],
                          ["profile_firstname", "Search type", openapi.TYPE_STRING],
                          ["profile_user_id", "Search type", openapi.TYPE_STRING, r'\d{1,7}'],
                          ["profile_id", "Filter type", openapi.TYPE_STRING],
                          ["search", "Will search in multiple fields (perimeter_name, provider_name, lastname, "
                                     "firstname, provider_source_value, email)", openapi.TYPE_STRING],
                          ["ordering", "To sort the result. Can be care_site_name, role_name, start_datetime, "
                                       "end_datetime, is_valid. Use -field for descending order", openapi.TYPE_STRING]
                          ]))
