# Copyright (C) 2017  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from .version import __version__, __version_info__
from .logging import log, setup_logging
from .idgen import ResourceIdGenerator
from .schema import schema
from .resource_type import (
    ResourceType,
    load_resource_types,
    add_missing_fields,
)
from .sql import (
    PostgresAdapter,
    quote,
    placeholder,
    get_unique_name,
    All,
    Contains,
    Equal,
    GreaterThan,
    GreaterOrEqual,
    LessThan,
    LessOrEqual,
    NotEqual,
    ResourceTypeIs,
    Startswith,
    Yes,
)
from .sql_select import sql_select

from .objstore import (
    ObjectStoreInterface,
    MemoryObjectStore,
    PostgresObjectStore,
    KeyCollision,
    UnknownKey,
    WrongKeyType,
    KeyValueError,
    flatten_object,
)

from .validator import (
    Validator,
    ValidationError,
    NotADict,
    NoType,
    HasId,
    HasRevision,
    NoId,
    NoRevision,
    UnknownField,
    WrongType,
)

from .search_parser import (
    SearchParser,
    SearchParameters,
    SearchParserError,
)

from .collection import (
    CollectionAPI,
    NoSearchCriteria,
    NoSuchResource,
    WrongRevision,
)

from .api import QvarnAPI, NoSuchResourceType
