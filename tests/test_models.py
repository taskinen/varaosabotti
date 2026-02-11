from varaosabotti.models import Category, CategoryStatus


def test_category_status_values():
    assert CategoryStatus.ACTIVE.value == "active"
    assert CategoryStatus.INACTIVE.value == "inactive"


def test_category_is_frozen():
    cat = Category(name="X", title="X", href="/x", status=CategoryStatus.ACTIVE)
    try:
        cat.name = "Y"
        assert False, "Expected FrozenInstanceError"
    except AttributeError:
        pass


def test_category_defaults():
    cat = Category(name="X", title="X", href="/x", status=CategoryStatus.ACTIVE)
    assert cat.group is None
    assert cat.parent is None
