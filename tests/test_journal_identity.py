from journal.identity import (
    build_object_source_index,
    build_source_index,
    find_source_index,
    get_qso_keys,
)


def test_qso_keys_distinguish_identical_records_by_occurrence():
    first = {"call": "R1BQE", "comment": "same"}
    second = {"call": "R1BQE", "comment": "same"}

    assert get_qso_keys([first, second]) == [
        ('{"call": "R1BQE", "comment": "same"}', 0),
        ('{"call": "R1BQE", "comment": "same"}', 1),
    ]


def test_source_index_resolves_duplicate_occurrences_in_linear_index():
    qsos = [
        {"call": "R1AAA"},
        {"call": "R1BBB"},
        {"call": "R1AAA"},
    ]
    keys = get_qso_keys(qsos)
    index = build_source_index(keys)

    assert find_source_index(index, keys[0][0], 0) == 0
    assert find_source_index(index, keys[0][0], 1) == 2
    assert find_source_index(index, "missing", 0) == -1
    assert find_source_index(index, keys[0][0], 2) == -1


def test_source_index_preserves_source_order_for_identical_qsos():
    qso = {"call": "R1BQE", "datetime": "2026-10-31 10:00"}
    keys = get_qso_keys([qso, qso.copy(), qso.copy()])
    index = build_source_index(keys)

    assert [find_source_index(index, keys[0][0], n) for n in range(3)] == [0, 1, 2]


def test_object_source_index_maps_duplicate_dict_objects_to_distinct_rows():
    first = {"call": "R1BQE", "comment": "same"}
    second = {"call": "R1BQE", "comment": "same"}
    source = [first, second]

    index = build_object_source_index(source)

    assert index[id(first)] == 0
    assert index[id(second)] == 1
    assert index.get(id({"call": "R1BQE", "comment": "same"}), -1) == -1
