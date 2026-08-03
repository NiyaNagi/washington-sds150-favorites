from wasds150.hpe.record import parse_records
from wasds150.hpe.tree import build_tree, render_tree


def test_build_tree_groups_conventional_hierarchy():
    text = (
        "TargetModel\tBCDx36HP\r\n"
        "Conventional\t\t\tSys1\r\n"
        "C-Group\t\t\tGroup1\r\n"
        "C-Freq\t\t\tFreq1\r\n"
        "C-Freq\t\t\tFreq2\r\n"
    )
    doc = parse_records(text)
    forest = build_tree(doc)
    # TargetModel + Conventional are top-level
    tags_top = [n.record.tag for n in forest]
    assert tags_top == ["TargetModel", "Conventional"]
    conv_node = forest[1]
    assert len(conv_node.children) == 1
    group_node = conv_node.children[0]
    assert group_node.record.tag == "C-Group"
    assert [c.record.tag for c in group_node.children] == ["C-Freq", "C-Freq"]


def test_build_tree_groups_trunk_hierarchy_with_t_freq_under_trunk():
    text = (
        "Trunk\t\t\tSys1\r\n"
        "Site\t\t\tSite1\r\n"
        "T-Group\t\t\tGrp1\r\n"
        "TGID\t\t\tTg1\r\n"
        "T-Freq\t\t\t851000000\r\n"
    )
    doc = parse_records(text)
    forest = build_tree(doc)
    assert len(forest) == 1
    trunk_node = forest[0]
    assert trunk_node.record.tag == "Trunk"
    child_tags = [c.record.tag for c in trunk_node.children]
    assert child_tags == ["Site", "T-Freq"]
    site_node = trunk_node.children[0]
    assert site_node.children[0].record.tag == "T-Group"
    assert site_node.children[0].children[0].record.tag == "TGID"


def test_build_tree_attaches_orphan_records_at_top_level():
    text = "C-Freq\t\t\tOrphan\r\n"  # no preceding C-Group/Conventional
    doc = parse_records(text)
    forest = build_tree(doc)
    assert len(forest) == 1
    assert forest[0].record.tag == "C-Freq"  # not dropped


def test_render_tree_includes_arity_and_name():
    text = "Conventional\t\t\tSys1\r\n"
    doc = parse_records(text)
    forest = build_tree(doc)
    output = render_tree(forest)
    assert "Conventional" in output
    assert "arity=" in output
