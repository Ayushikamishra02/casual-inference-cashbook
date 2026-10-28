"""The datasets load, match their published descriptions, and the downloads are checksum-pinned."""
from causalbook import data


def test_downloads_are_pinned():
    for url, sha in data.DOWNLOADS.values():
        assert url.startswith("https://") and len(sha) == 64


def test_card_krueger_matches_paper_table_3(ck):
    assert len(ck) == 410
    assert (ck.state == "NJ").sum() == 331 and (ck.state == "PA").sum() == 79
    m = ck.groupby("state")[["fte_before", "fte_after"]].mean().round(2)
    assert m.loc["NJ"].tolist() == [20.44, 21.03]
    assert m.loc["PA"].tolist() == [23.33, 21.17]


def test_nsw_samples():
    e = data.nsw_experiment()
    assert e.treat.sum() == 185 and (e.treat == 0).sum() == 260
    o = data.nsw_observational()
    assert o.treat.sum() == 185 and (o.treat == 0).sum() == 15_992


def test_prop99_panel(smoking):
    assert smoking.state.nunique() == 39
    assert smoking.year.min() == 1970 and smoking.year.max() == 2000
    assert len(smoking) == 39 * 31


def test_organ_panel():
    d = data.organ_donations()
    assert d.state.nunique() == 27 and d.t.nunique() == 6
    assert d.treated.sum() == 3          # California, 3 post-policy quarters
