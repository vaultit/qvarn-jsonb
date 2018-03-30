import pytest


from qvarn.mongo import (
    find_field_paths,
    flat_query_to_mongo,
)
from qvarn.sql import FieldQuery


PROTO = {
    'bolagsfakta_status': '',
    'contract_end_date': '',
    'contract_start_date': '',
    'id': '',
    'internal_project_id': '',
    'materialized_path': [''],
    'parent_org_id': '',
    'parent_supplier_id': '',
    'project_resource_id': '',
    'revision': '',
    'supplier_contacts': [{'supplier_contact_email': '',
                           'supplier_contact_person_id': '',
                           'some_list': [''],
                           'type': ''}],
    'supplier_org_id': '',
    'supplier_role': '',
    'supplier_type': '',
    'type': '',
}


@pytest.mark.parametrize(['target', 'path'],
                         [('internal_project_id',
                           [['internal_project_id']]),
                          ('supplier_contact_email',
                           [['supplier_contacts', 'supplier_contact_email']]),
                          ('materialized_path',
                           [['materialized_path']]),
                          ('nonexisting_field',
                           []),
                          ('some_list',
                           [['supplier_contacts', 'some_list']]),
                          ('type',
                           [['supplier_contacts', 'type'],
                            ['type']]),
                          ])
def test_find_field_paths(target, path):
    assert find_field_paths(target, PROTO) == path


@pytest.mark.parametrize(
    ['query', 'result'],
    [([FieldQuery('some_list', '$gte', 'a'),
       FieldQuery('some_list', None, 'b')],
      {'$and': [{'supplier_contacts.some_list': {'$gte': 'a'}},
                {'supplier_contacts.some_list': 'b'}]}),
     ([FieldQuery('type', None, 'a')],
      {'$or': [{'supplier_contacts.type': 'a'}, {'type': 'a'}]})],
)
def test_flat_query_to_mongo(query, result):
    assert flat_query_to_mongo(query, [PROTO]) == result
