from datetime import datetime

from mock import patch, MagicMock
import pytest
from mies.buildings.model import build_bldg_address, _get_next_free, get_nearby_addresses
from mies.buildings.model import is_vacant
from mies.buildings.model import find_spot
from mies.constants import FLOOR_W, FLOOR_H, PROXIMITY
from mies.buildings.model import construct_bldg, create_buildings
from mies.buildings.utils import extract_bldg_coordinates


@pytest.mark.parametrize("flr,x,y,address", [
    ("g", 1, 2, "g-b(1,2)"),
    ("g", 12, 3, "g-b(12,3)"),
    ("g", 123, 456, "g-b(123,456)")])
def test_build_ground_level_bldg_address(flr, x, y, address):
    got = build_bldg_address(flr, x, y)
    assert got == address

@pytest.mark.parametrize("flr,x,y,address", [
    ("g-b(1,2)-l0", 1, 2, "g-b(1,2)-l0-b(1,2)"),
    ("g-b(1,2)-l0-b(3,4)-l1", 1, 2, "g-b(1,2)-l0-b(3,4)-l1-b(1,2)"),
    ("g-b(1,2)-l3", 123, 456, "g-b(1,2)-l3-b(123,456)")])
def test_build_upper_level_bldg_address(flr, x, y, address):
    got = build_bldg_address(flr, x, y)
    assert got == address


def test_is_vacant():
    db = MagicMock()
    db.buildings.find_one = MagicMock(return_value=None)
    assert True == is_vacant("g-b(1,2)", db)
    db.buildings.find_one.assert_called_once_with({'address': 'g-b(1,2)'})


def test_get_next_free():
    vacancies = [{}]*350 + [None]
    db = MagicMock()
    db.buildings.find_one = MagicMock(side_effect=vacancies)
    got = _get_next_free("g-b(1,2)-l0", db)
    assert got == (150, 1)


def test_find_spot():
    flr = "g-b(1,2)-l1"
    state = {}
    address, x, y = find_spot(flr, state)
    assert address is not None
    assert address == "{flr}-b({x},{y})".format(**locals())
    assert 0 <= x <= FLOOR_W
    assert 0 <= y <= FLOOR_H


def test_find_spot_near():
    flr = "g-b(1,2)-l1"
    near_x = 12
    near_y = 34
    pos_hints = {
        "near_x": near_x,
        "near_y": near_y
    }
    address, x, y = find_spot(flr, position_hints=pos_hints)
    assert address is not None
    assert address == "{flr}-b({x},{y})".format(**locals())
    assert 0 <= x <= FLOOR_W
    assert 0 <= y <= FLOOR_H
    assert abs(x - near_x) <= PROXIMITY
    assert abs(y - near_y) <= PROXIMITY


def test_find_spot_next_free():
    flr = "g-b(1,2)-l1"
    pos_hints = {
        "next_free": True,
    }
    vacancies = [{}]*350 + [None]
    db = MagicMock()
    db.buildings.find_one = MagicMock(side_effect=vacancies)
    address, got_x, got_y = find_spot(flr, position_hints=pos_hints, db=db)
    expected_x, expected_y = 150, 1
    assert got_x == expected_x
    assert got_y == expected_y
    assert address is not None
    assert address == "{flr}-b({expected_x},{expected_y})".format(**locals())


def test_construct_bldg():
    flr = "g-b(1,2)-l1"
    near_x = 75
    near_y = 6
    pos_hints = {
        "near_x": near_x,
        "near_y": near_y
    }
    content_type = "SomeContent"
    payload = {
        "field1": "value 1",
        "field2": "value 2",
        "field3": "value 3",
    }
    db = MagicMock()
    db.buildings.find_one = MagicMock(return_value=None)
    got = construct_bldg(flr, content_type, "key", payload,
                         position_hints=pos_hints, db=db)
    assert got is not None
    assert got['address'].startswith(flr)
    assert got['flr'] == flr
    assert abs(got['x'] - near_x) <= PROXIMITY
    assert abs(got['y'] - near_y) <= PROXIMITY
    assert (datetime.utcnow() - got['createdAt']).seconds < 10
    assert got['payload'] == payload
    assert not got['processed']
    assert not got['occupied']
    assert got['occupiedBy'] is None


@patch('mies.buildings.model.get_db')
@patch('mies.buildings.model.create_smell_source')
def test_create_buildings(create_smell_source, get_db):
    db = MagicMock()
    db.buildings.find_one = MagicMock(return_value=None)
    db.buildings.insert = MagicMock(return_value=None)
    get_db.return_value = db

    content_type = "SomeContent"
    nbuildings = 35
    keys = ["key-{}".format(i) for i in xrange(nbuildings)]
    heads = [dict(key=key) for key in keys]
    payloads = [
        {
            "field1": "value 1.1",
            "field2": "value 1.2",
            "field3": "value 1.3",
        },
    ]* nbuildings
    bodies = [dict(summary_payload=p, result_payload=p, raw_payload=p) for p in payloads]
    flr = "g-b(1,2)-l1"
    got = create_buildings(flr, content_type, heads, bodies)
    assert len(got) == nbuildings
    assert db.buildings.insert.call_count == 4  # 4 batch inserts
    create_smell_source.assert_has_calls([

    ])

def test_get_nearby_addresses():
    addr = "g-b(1,2)-l0-b(50,50)"
    res = get_nearby_addresses(addr)
    assert len(res) == 99
    assert addr not in res
    nearby_addr = res[47]
    x, y = extract_bldg_coordinates(nearby_addr)
    assert abs(x - 50) < 10
    assert abs(y - 50) < 10
