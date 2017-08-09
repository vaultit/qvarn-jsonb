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
from .resource_type import ResourceType, load_resource_types
from .schema import schema
from .sql import (
    PostgresAdapter,
    quote,
    placeholder,
    All,
    Equal,
)

from .objstore import (
    ObjectStoreInterface,
    MemoryObjectStore,
    PostgresObjectStore,
    KeyCollision,
    UnknownKey,
    KeyValueError,
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
)

from .collection import (
    CollectionAPI,
    NoSuchResource,
    WrongRevision,
    WrongType,
)

from .api import QvarnAPI, NoSuchResourceType
