from query_understanding import (
    QuerySlots,
    get_missing_required_slots,
    build_metadata_filter,
)


def test_general_qa_does_not_require_model():
    """普通知识问答不需要产品型号。"""

    slots = QuerySlots()

    missing_slots = get_missing_required_slots(
        intent="general_qa",
        slots=slots,
    )

    assert missing_slots == []


def test_product_specific_qa_requires_model():
    """产品专属问题必须有产品型号。"""

    slots = QuerySlots(
        product_brand="海尔",
    )

    missing_slots = get_missing_required_slots(
        intent="product_specific_qa",
        slots=slots,
    )

    assert missing_slots == ["product_model"]


def test_product_specific_qa_has_model():
    """已经提供型号，不再触发型号追问。"""

    slots = QuerySlots(
        product_model="BCD-500",
    )

    missing_slots = get_missing_required_slots(
        intent="product_specific_qa",
        slots=slots,
    )

    assert missing_slots == []


def test_metadata_filter_is_disabled_by_default():
    """未确认 Metadata 字段存在时，不生成 Filter。"""

    slots = QuerySlots(
        product_model="BCD-500",
    )

    metadata_filter = build_metadata_filter(
        slots=slots,
        enabled_metadata_fields=set(),
    )

    assert metadata_filter is None


def test_metadata_filter_is_generated_when_enabled():
    """确认产品型号 Metadata 存在后，才生成 Filter。"""

    slots = QuerySlots(
        product_model="BCD-500",
    )

    metadata_filter = build_metadata_filter(
        slots=slots,
        enabled_metadata_fields={"product_model"},
    )

    assert metadata_filter == {
        "product_model": {
            "$eq": "BCD-500"
        }
    }


def test_multiple_metadata_filters_use_and():
    """多个 Metadata 条件必须同时满足。"""

    slots = QuerySlots(
        product_brand="海尔",
        product_model="BCD-500",
    )

    metadata_filter = build_metadata_filter(
        slots=slots,
        enabled_metadata_fields={
            "product_brand",
            "product_model",
        },
    )

    assert metadata_filter == {
        "$and": [
            {"product_brand": {"$eq": "海尔"}},
            {"product_model": {"$eq": "BCD-500"}},
        ]
    }