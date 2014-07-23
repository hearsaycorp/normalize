#
# This file is a part of the normalize python library
#
# normalize is free software: you can redistribute it and/or modify
# it under the terms of the MIT License.
#
# normalize is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# MIT License for more details.
#
# You should have received a copy of the MIT license along with
# normalize.  If not, refer to the upstream repository at
# http://github.com/hearsaycorp/normalize

import copy
from datetime import datetime
from time import time
import types

from normalize import RecordList
from normalize.record import Record
from normalize.record.json import JsonRecordList
from normalize.property import Property
from normalize.property import SafeProperty
from normalize.property.coll import ListProperty
from normalize.property.types import DatetimeProperty


class LegalPerson(Record):
    id = Property(required=True, isa=int)
    name = Property(isa=basestring, coerce=str)


class Person(LegalPerson):
    age = Property(isa=int)
    kids = Property(isa=int, extraneous=True)
    interests = SafeProperty(isa=list)
    info = SafeProperty(isa=dict)
    primary_key = ['id']


class Circle(Record):
    members = ListProperty(of=Person)


class Comment(Record):
    content = Property()
    edited = DatetimeProperty(required=True)
    id = Property(required=True, isa=int)
    primary_key = [id]
    poster = Property(isa=Person)


class Post(Record):
    comments = ListProperty(of=Comment)
    content = Property()
    edited = DatetimeProperty(required=True)
    post_id = Property(required=True, isa=int)
    wall_id = Property(required=True, isa=int)
    primary_key = [wall_id, post_id]


class Wall(Record):
    id = Property(required=True, isa=int)
    owner = Property(isa=Person)
    posts = ListProperty(of=Post)


# for testing comparison with "alien" classes
class Spartan(object):
    def __init__(self, data):
        for k, v in data.iteritems():
            setattr(self, k, v)


gary = dict(
    info={"title": "Superintendent", "manner": "Military"},
    id=1,
    interests=["coffee", "alcohol", "Agnes Skinner"],
    name="Gary Chamlers",
)
seymour = dict(
    info={"hair": "grey", "title": "Principal"},
    id=2,
    interests=["quality education", "hounding children"],
    name="Seymour Skinner",
)
willie = dict(
    info={"hair": "orange", "title": "Groundskeeper"},
    id=3,
    interests=["wolf wrestling", "swearing at French people"],
    name="Willie McLeod",
)
dialogue = [
    (seymour, "S-Superintendent Chalmers!"),
    (gary, "Whose tractor is this?!"),
    (seymour, "I-i-I'll look right into it, sir!"),
    (willie, "It's MINE, ya flippin' sock-sniffin' tatie eater!"),
]
comments = []
when = 1000000000
id = 14
for character, line in dialogue:
    when += 42
    id += 3
    comments.append(dict(id=id, edited=datetime.utcfromtimestamp(when),
                         poster=character, content=line))

wall_one = Wall(
    id=123,
    owner=copy.deepcopy(gary),
    posts=[
        {
            "comments": copy.deepcopy(comments[0:3]),
            "content": "SEY-MOUR!!!",
            "edited": datetime.utcfromtimestamp(1000000000),
            "post_id": 1,
            "wall_id": 123,
        }
    ]
)

del gary['interests'][1]
seymour['info']['birth name'] = "Armin Tamzarian"

wall_two = Wall(
    id=123,
    owner=gary,
    posts=[
        {
            "comments": comments[1:],
            "content": "SEY-MOUR!!!!",
            "edited": datetime.utcfromtimestamp(1000000240),
            "post_id": 1,
            "wall_id": 123,
        }
    ]
)


def fix_id(val):
    if isinstance(val, basestring) and val.upper().startswith("HIP"):
        return int(val.upper().lstrip("HIP "))
    else:
        return int(val)


class Star(Record):
    hip_id = Property(isa=int, required=True,
                      coerce=fix_id,
                      check=lambda i: 0 < i < 120000)
    name = Property(isa=str)
    spectral_type = Property(isa=str)


class Binary(Record):
    name = Property(isa=str)
    primary = Property(isa=Star)
    secondary = Property(isa=Star)


class StarList(RecordList):
    itemtype = Star


class JsonStarList(JsonRecordList):
    itemtype = Star


class NamedStarList(StarList):
    name = Property()


class StarSystem(Record):
    name = Property(isa=str)
    components = Property(isa=StarList)


maia = Star(hip_id=17573, name="maia")
acent = StarSystem(
    name="Alpha Centauri",
    components=(
        {"name": "Alpha Centauri A", "hip_id": 71683},
        {"name": "Alpha Centauri B", "hip_id": 71681},
        {"name": "Alpha Centauri C", "hip_id": 70890},
    ),
)


# for those APIs that use 'None' to signify meaning.
class PullRequest(Record):
    number = Property()
    created_at = DatetimeProperty(default=lambda: datetime.now())
    merged_at = DatetimeProperty(isa=(datetime, types.NoneType))
