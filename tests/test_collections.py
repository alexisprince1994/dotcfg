import pytest
from box import Box
from dotcfg import collections
from dotcfg.collections import as_nested_dict, merge_dicts


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


def test_as_nested_dict_defaults_box():
    orig_d = dict(a=1, b=[2, dict(c=3)], d=dict(e=[dict(f=4)]))
    bx = as_nested_dict(orig_d)
    assert isinstance(bx, Box)
    assert bx.a == 1
    assert bx.b[1].c == 3
    assert bx.d.e[0].f == 4


def test_as_nested_dict_works_with_box():

    orig_d = Box(dict(a=1, b=[2, dict(c=3)], d=dict(e=[dict(f=4)])))
    out_d = as_nested_dict(orig_d)
    assert isinstance(out_d, dict)
    assert out_d["a"] == 1
    assert out_d["b"][1]["c"] == 3
    assert out_d["d"]["e"][0]["f"] == 4


def test_as_nested_dict_dct_class():
    orig_d = dict(a=1, b=[2, dict(c=3)], d=dict(e=[dict(f=4)]))
    box_d = as_nested_dict(orig_d, Box)
    dict_d = as_nested_dict(box_d, dict)
    print(f"Dict_d is: {dict_d}")
    assert type(dict_d) is dict
    assert type(dict_d["d"]["e"][0]) is dict


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


def test_as_nested_dict_breaks_when_critical_keys_shadowed():
    x = dict(update=1, items=2)
    y = as_nested_dict(x, Box)
    assert not isinstance(y.update, int)
    assert not isinstance(y.items, int)
    assert callable(y.update)
    assert callable(y.items)


@pytest.mark.parametrize("after", [dict, Box])
@pytest.mark.parametrize("before", [dict, Box])
def test_as_nested_dict_list_unboxed(before: type, after: type):

    a = before(a=[before(b=10)], b="hello")
    print(f"a is: {a}")

    result = as_nested_dict(a, dct_class=after)

    assert isinstance(result, after)

    assert isinstance(result["a"][0], after)
