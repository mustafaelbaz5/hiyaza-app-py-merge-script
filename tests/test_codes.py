from core.codes import CodesDB
from core.models import AssociationType


def test_exact_association_match(codes_files):
    db = CodesDB(*codes_files)
    info = db.find_association("شنشا-الائتمان الزراعي", AssociationType.CREDIT)
    assert info is not None
    assert info.code == "323925"
    assert info.directorate == "الدقهليه"
    assert info.administration == "اجا"


def test_partial_association_match(codes_files):
    db = CodesDB(*codes_files)
    info = db.find_association("شنشا", AssociationType.CREDIT)
    assert info is not None
    assert info.name == "شنشا-الائتمان الزراعي"


def test_missing_association_returns_none(codes_files):
    db = CodesDB(*codes_files)
    assert db.find_association("جمعية غير موجودة", AssociationType.CREDIT) is None


def test_basin_name_is_not_cleaned_or_fuzzy_matched(codes_files):
    db = CodesDB(*codes_files)
    code = db.find_basin_code("داير الناصيه", "323925", AssociationType.CREDIT)
    assert code == "غير محدد"


def test_basin_exact_name_returns_its_unique_code(codes_files):
    db = CodesDB(*codes_files)
    code = db.find_basin_code("داير الناصيه**", "323925", AssociationType.CREDIT)
    assert code == "06323000003239000012"


def test_basin_missing_returns_placeholder(codes_files):
    db = CodesDB(*codes_files)
    code = db.find_basin_code("حوض غير موجود", "323925", AssociationType.CREDIT)
    assert code == "غير محدد"


def test_get_basins_for_association(codes_files):
    db = CodesDB(*codes_files)
    basins = db.get_basins("323925", AssociationType.CREDIT)
    assert len(basins) == 2
    names = {b.name for b in basins}
    assert "الدماسه" in names


def test_reform_table_separate_from_credit(codes_files):
    db = CodesDB(*codes_files)
    info = db.find_association("جمعية إصلاح تجريبية", AssociationType.REFORM)
    assert info is not None
    assert info.code == "111111"
    assert db.find_association("جمعية إصلاح تجريبية", AssociationType.CREDIT) is None
