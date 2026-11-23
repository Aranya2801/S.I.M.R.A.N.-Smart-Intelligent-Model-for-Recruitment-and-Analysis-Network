from simran.redact import redact


def test_redacts_contact_and_name():
    t = "Priya Sharma — Data Scientist\npriya@x.com | +91 98300 12345 | github.com/priya"
    out = redact(t)
    assert "Priya" not in out and "priya@" not in out and "98300" not in out and "github" not in out
    assert "Data Scientist" in out


def test_dates_survive_redaction():
    assert "2019 - 2021" in redact("Name\nAnalyst (2019 - 2021)")


def test_group_marker_removed():
    assert "Women" not in redact("Name\nMember, Women in Engineering Society")
