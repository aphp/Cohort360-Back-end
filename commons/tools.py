def cast_string_to_ids_list(str_ids: str) -> [int]:
    try:
        return [int(i) for i in str_ids.split(",") if i]
    except Exception as err:
        raise f"Error in element str list conversion to integer: {err}"


def value_to_string(field_value) -> str:
    if type(field_value) == list:
        return "".join(field_value)
    return str(field_value)
