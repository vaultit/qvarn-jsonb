def _is_nested_field(proto):
    return (isinstance(proto, list) and isinstance(proto[0], dict)
            or isinstance(proto, dict))


def _get_nested_proto(proto, field):
    if isinstance(proto[field], list):
        return proto[field][0]
    else:
        return proto[field]


def find_field_paths(target_field, proto, prefix=[]):
    found_paths = []
    for field in proto.keys():
        if _is_nested_field(proto[field]):
            found_fields = find_field_paths(
                target_field,
                _get_nested_proto(proto, field),
                prefix=prefix + [field],
            )
            found_paths += found_fields
        else:
            if field == target_field:
                found_paths.append(prefix + [field])
    return list(sorted(found_paths))


def flat_query_to_mongo(query, protos):
    """Takes flat qvarn query and proto and constructs a mongo query"""
    assert query, 'Query cannot be empty'
    find_conds = []
    for proto in protos:
        for field, op, predicate in query:
            field_paths = find_field_paths(field, proto)
            conds = []
            for field_path in field_paths:
                joined_path = '.'.join(field_path)
                if op is None:
                    cond = {joined_path: predicate}
                else:
                    cond = {joined_path: {op: predicate}}
                conds.append(cond)
            if len(conds) == 1:
                find_conds.append(conds[0])
            elif len(conds) > 1:
                find_conds.append({'$or': conds})
    if len(find_conds) == 1:
        return find_conds[0]
    else:
        return {'$and': find_conds}
