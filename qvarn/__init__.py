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
from .log_setup import log, setup_logging
from .stopwatch import Stopwatch, stopwatch
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
    AccessIsAllowed,
    All,
    Cmp,
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
    No,
)
from .sql_select import sql_select, flatten

from .objstore import (
    ObjectStoreInterface,
    MemoryObjectStore,
    PostgresObjectStore,
    KeyCollision,
    UnknownKey,
    WrongKeyType,
    KeyValueError,
    NoSuchObject,
    BlobKeyCollision,
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
    UnknownSubpath,
    WrongType,
)

from .search_parser import (
    SearchParser,
    SearchParameters,
    SearchParserError,
    NeedSortOperator,
)

from .collection import (
    CollectionAPI,
    NoSearchCriteria,
    NoSuchResource,
    UnknownSearchField,
    WrongRevision,
)

from .responses import (
    bad_request_response,
    forbidden_request_response,
    conflict_response,
    created_response,
    need_sort_response,
    no_such_resource_response,
    ok_response,
    search_parser_error_response,
    unknown_search_field_response,
)

from .api_errors import (
    IdMismatch,
    NoSuchResourceType,
    NotJson,
    TooManyResources,
    TooManyResourceTypes,
)

from .router import Router
from .file_router import FileRouter
from .notification_router import NotificationRouter
from .resource_router import ResourceRouter
from .subresource_router import SubresourceRouter
from .version_router import VersionRouter
from .allow_router import AllowRouter
from .timestamp import get_current_timestamp

from .api import QvarnAPI
