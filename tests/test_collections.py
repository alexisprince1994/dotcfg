from typing import cast

import pytest
from box import Box

from dotcfg import collections
from dotcfg.collections import merge_dicts


@pytest.fixture
def nested_dict():
    return {1: 2, 2: {1: 2, 3: 4}, 3: {1: 2, 3: {4: 5, 6: {7: 8}}}}


def test_flatten_dict(nested_dict):
    flat = collections.dict_to_flatdict(nested_dict)
    assert flat == {
        collections.CompoundKey([1]): 2,
        collections.CompoundKey([2, 1]): 2,
        collections.CompoundKey([2, 3]): 4,
        collections.CompoundKey([3, 1]): 2,
        collections.CompoundKey([3, 3, 4]): 5,
        collections.CompoundKey([3, 3, 6, 7]): 8,
    }


def test_restore_flattened_dict(nested_dict):
    flat = collections.dict_to_flatdict(nested_dict)
    restored = collections.flatdict_to_dict(flat)
    assert restored == nested_dict


def test_call_flatdict_to_dict_on_normal_dict(nested_dict):
    restored = collections.flatdict_to_dict({"a": "b"})
    assert restored == {"a": "b"}


def test_restore_flattened_dict_with_dict_class():
    nested_dict = Box(a=Box(x=1), b=Box(y=2))
    flat = collections.dict_to_flatdict(nested_dict)
    restored = collections.flatdict_to_dict(flat)
    assert isinstance(restored, dict)

    restored_Box = collections.flatdict_to_dict(flat, dct_class=Box)
    assert isinstance(restored_Box, Box)
    assert isinstance(restored_Box.a, Box)
    assert restored_Box.a == nested_dict.a


def test_restore_flattened_dict_with_box_class():
    nested_dict = Box(a=Box(x=1), b=Box(y=2))
    flat = collections.dict_to_flatdict(nested_dict)
    restored = collections.flatdict_to_dict(flat)
    assert isinstance(restored, dict)

    restored_Box = collections.flatdict_to_dict(flat, dct_class=Box)
    assert isinstance(restored_Box, Box)
    assert isinstance(restored_Box.a, Box)
    assert restored_Box.a == nested_dict.a


@pytest.mark.parametrize("dct_class", [dict, Box])
def test_merge_simple_dicts(dct_class):
    a = dct_class(x=1, y=2, z=3)
    b = dct_class(z=100, a=101)

    # merge b into a
    assert merge_dicts(a, b) == dct_class(x=1, y=2, z=100, a=101)

    # merge a into b
    assert merge_dicts(b, a) == dct_class(x=1, y=2, z=3, a=101)


@pytest.mark.parametrize("dct_class", [dict, Box])
def test_merge_nested_dicts_reverse_order(dct_class):
    a = dct_class(x=dct_class(one=1, two=2), y=dct_class(three=3, four=4), z=0)
    b = dct_class(x=dct_class(one=1, two=20), y=dct_class(four=40, five=5))
    # merge b into a
    assert merge_dicts(a, b) == dct_class(
        x=dct_class(one=1, two=20), y=dct_class(three=3, four=40, five=5), z=0
    )

    assert merge_dicts(b, a) == dct_class(
        x=dct_class(one=1, two=2), y=dct_class(three=3, four=4, five=5), z=0
    )


@pytest.mark.parametrize("dct_class", [dict, Box])
def test_merge_nested_dicts_with_empty_section(dct_class):
    a = dct_class(x=dct_class(one=1, two=2), y=dct_class(three=3, four=4))
    b = dct_class(x=dct_class(one=1, two=2), y=dct_class())
    # merge b into a
    assert merge_dicts(a, b) == a
    # merge a into b
    assert merge_dicts(b, a) == a
