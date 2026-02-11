import pytest

from varaosabotti.models import Category, CategoryStatus


SAMPLE_HTML = """\
<html><body>
<div class="col-12">
  <h4>Test Group</h4>
  <div ngbdropdown class="col-lg-4 col-sm-12 my-1">
    <a queryparamshandling="preserve" class="my-2" href="/active" title="Active Simple" rel="follow" tabindex="0">
      <span>Active Simple</span>
    </a>
  </div>
  <div ngbdropdown class="col-lg-4 col-sm-12 my-1">
    <a queryparamshandling="preserve" class="my-2 disabled-link text-danger" href="/inactive" title="Inactive Simple" rel="nofollow" tabindex="-1" disabled="true">
      <span>Inactive Simple</span>
    </a>
  </div>
  <div ngbdropdown class="col-lg-4 col-sm-12 my-1">
    <a ngbdropdowntoggle queryparamshandling="preserve" class="my-2" href="/parent" title="Parent Toggle" rel="follow" tabindex="0">
      <span>Parent Toggle</span>
    </a>
    <div ngbdropdownmenu>
      <a ngbdropdownitem class="my-2" href="/kaikki" title="Kaikki"><span>Kaikki</span></a>
      <a ngbdropdownitem class="my-2" href="/child-a" title="Child Active"><span>Child Active</span></a>
      <a ngbdropdownitem class="my-2 disabled-link text-danger" href="/child-i" title="Child Inactive" disabled="true"><span>Child Inactive</span></a>
    </div>
  </div>
</div>
<div class="col-12">
  <h4>Suosittuja osia</h4>
  <div ngbdropdown class="col-lg-4 col-sm-12 my-1">
    <a queryparamshandling="preserve" class="my-2" href="/popular" title="Popular Item" rel="follow" tabindex="0">
      <span>Popular Item</span>
    </a>
  </div>
</div>
</body></html>
"""


@pytest.fixture
def sample_html():
    return SAMPLE_HTML


@pytest.fixture
def sample_categories():
    return [
        Category(name="Active Simple", title="Active Simple", href="/active", status=CategoryStatus.ACTIVE, group="Test Group"),
        Category(name="Inactive Simple", title="Inactive Simple", href="/inactive", status=CategoryStatus.INACTIVE, group="Test Group"),
        Category(name="Parent Toggle", title="Parent Toggle", href="/parent", status=CategoryStatus.ACTIVE, group="Test Group"),
        Category(name="Child Active", title="Child Active", href="/child-a", status=CategoryStatus.ACTIVE, group="Test Group", parent="Parent Toggle"),
        Category(name="Child Inactive", title="Child Inactive", href="/child-i", status=CategoryStatus.INACTIVE, group="Test Group", parent="Parent Toggle"),
    ]
