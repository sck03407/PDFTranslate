from pathlib import Path

from pdf2zh_next.config.cli_env_model import CLIEnvSettingsModel
from pdf2zh_next.fashion_defaults import FASHION_SYSTEM_PROMPT
from pdf2zh_next.fashion_defaults import get_bundled_customer_glossary_template_path
from pdf2zh_next.fashion_defaults import get_builtin_fashion_glossary_path
from pdf2zh_next.fashion_defaults import get_builtin_fashion_glossary_paths
from pdf2zh_next.fashion_defaults import get_effective_custom_system_prompt
from pdf2zh_next.fashion_defaults import get_effective_glossary_paths
from pdf2zh_next.fashion_defaults import load_glossary_rows
from pdf2zh_next.fashion_defaults import write_glossary_rows


def test_builtin_fashion_glossary_path_exists():
    glossary_path = get_builtin_fashion_glossary_path()

    assert glossary_path.exists()
    assert glossary_path.name.startswith("fashion-")


def test_builtin_fashion_glossary_paths_cover_glossary_pack():
    glossary_paths = get_builtin_fashion_glossary_paths()

    assert len(glossary_paths) >= 12
    assert any(
        path.name == "fashion-12-style-fit-and-silhouette.csv"
        for path in glossary_paths
    )
    assert all(path.exists() for path in glossary_paths)
    assert {path.suffix for path in glossary_paths} == {".csv"}


def test_builtin_fashion_glossary_pack_has_expanded_term_volume():
    total_rows = sum(
        len(load_glossary_rows(glossary_path))
        for glossary_path in get_builtin_fashion_glossary_paths()
    )

    assert total_rows >= 3300


def test_builtin_fashion_glossary_pack_contains_core_apparel_terms():
    glossary_terms: dict[str, set[str]] = {}

    for glossary_path in get_builtin_fashion_glossary_paths():
        for source, target, _target_language in load_glossary_rows(glossary_path):
            glossary_terms.setdefault(source, set()).add(target)

    expected_terms = {
        "front bodice": "前片",
        "under collar": "下领",
        "fabric composition": "面料成分",
        "polyurethane": "聚氨酯",
        "recycled nylon": "再生尼龙",
        "zipper teeth": "链牙",
        "cord end": "绳尾扣",
        "wash care label": "洗唛",
        "keyhole opening": "水滴形开口",
        "front body length": "前身长",
        "cotton poplin": "棉府绸",
        "flat felled seam": "双折包缝",
        "measurement out of tolerance": "尺寸超公差",
        "wash at 30 degrees": "30 度水洗",
        "time and action calendar": "生产进度表",
        "hydrostatic pressure test": "静水压测试",
        "self seal polybag": "自粘胶袋",
        "line plan": "生产线计划",
        "digital print": "数码印花",
        "slim fit": "修身版型",
        "graded pattern": "放码纸样",
        "t-shirt": "T 恤",
        "pima cotton": "匹马棉",
        "bar tack reinforcement": "打枣加固",
        "shipment sample approval": "船样确认",
        "inside collar stand": "内领座",
        "thigh 1 inch below crotch": "裆下 1 英寸大腿围",
        "tencel lyocell": "TENCEL 莱赛尔",
        "stitch in ditch": "落坑车缝",
        "zipper not functioning": "拉链不顺",
        "wash in laundry bag": "放入洗衣袋洗涤",
        "approved color standard": "确认色样标准",
        "azo dye test": "偶氮染料测试",
        "rfid tag": "RFID 吊牌",
        "time and action plan": "生产进度计划",
        "rotary screen print": "圆网印花",
        "cuttable width": "可裁幅宽",
        "hood drawcord opening": "帽绳孔",
        "front rise including waistband": "含腰头前裆长",
        "seacell": "海藻纤维",
        "ultrasonic bonding": "超声波粘合",
        "seam allowance exposed": "缝份外露",
        "professional dry clean gentle cycle": "专业轻柔干洗",
        "PP sample approval": "产前样确认",
        "phenolic yellowing": "酚黄变",
        "biodegradable polybag": "可降解胶袋",
        "root cause analysis": "根因分析",
        "rhinestone transfer": "烫钻转印",
        "shacket": "衬衫式夹克",
    }

    for source, target in expected_terms.items():
        assert target in glossary_terms.get(source, set())


def test_builtin_fashion_glossary_files_have_unique_sources():
    for glossary_path in get_builtin_fashion_glossary_paths():
        sources = [
            source.strip().lower()
            for source, _target, _target_language in load_glossary_rows(glossary_path)
        ]
        duplicate_sources = {
            source for source in sources if sources.count(source) > 1
        }

        assert duplicate_sources == set(), glossary_path.name


def test_bundled_customer_glossary_template_exists():
    glossary_path = get_bundled_customer_glossary_template_path()

    assert glossary_path.exists()
    assert glossary_path.name == "fashion-customer-glossary-template.csv"


def test_write_glossary_rows_uses_utf8_bom(tmp_path: Path):
    glossary_path = tmp_path / "customer.csv"
    write_glossary_rows(glossary_path, [["fit sample", "试身样", "zh"]])

    content = glossary_path.read_bytes()
    assert content.startswith(b"\xef\xbb\xbf")
    assert load_glossary_rows(glossary_path) == [["fit sample", "试身样", "zh"]]


def test_effective_glossary_paths_include_builtin_and_custom(tmp_path: Path):
    custom_glossary = tmp_path / "custom.csv"
    custom_glossary.write_text("source,target\nfit,版型\n", encoding="utf-8")

    glossary_paths = get_effective_glossary_paths(
        str(custom_glossary),
        disable_builtin_fashion_glossary=False,
    )

    assert glossary_paths[0] == custom_glossary
    for builtin_path in get_builtin_fashion_glossary_paths():
        assert builtin_path in glossary_paths
    assert custom_glossary in glossary_paths


def test_effective_glossary_paths_can_disable_builtin(tmp_path: Path):
    custom_glossary = tmp_path / "custom.csv"
    custom_glossary.write_text("source,target\nfit,版型\n", encoding="utf-8")

    glossary_paths = get_effective_glossary_paths(
        str(custom_glossary),
        disable_builtin_fashion_glossary=True,
    )

    for builtin_path in get_builtin_fashion_glossary_paths():
        assert builtin_path not in glossary_paths
    assert glossary_paths == [custom_glossary]


def test_effective_glossary_paths_resolve_relative_to_config_file(tmp_path: Path):
    config_dir = tmp_path / "profiles"
    config_dir.mkdir()
    config_file = config_dir / "fashion.toml"
    config_file.write_text("", encoding="utf-8")

    custom_dir = config_dir / "glossaries"
    custom_dir.mkdir()
    custom_glossary = custom_dir / "customer.csv"
    custom_glossary.write_text("source,target\nfit,版型\n", encoding="utf-8")

    glossary_paths = get_effective_glossary_paths(
        "./glossaries/customer.csv",
        disable_builtin_fashion_glossary=True,
        config_file=str(config_file),
    )

    assert glossary_paths == [custom_glossary.resolve()]


def test_effective_custom_system_prompt_uses_builtin_by_default():
    settings = CLIEnvSettingsModel(openai=True, openai_detail={"openai_api_key": "x"})
    runtime_settings = settings.to_settings_model()

    assert get_effective_custom_system_prompt(runtime_settings) == FASHION_SYSTEM_PROMPT


def test_effective_custom_system_prompt_prefers_user_prompt():
    settings = CLIEnvSettingsModel(
        openai=True,
        openai_detail={"openai_api_key": "x"},
        translation={"custom_system_prompt": "custom prompt"},
    )
    runtime_settings = settings.to_settings_model()

    assert get_effective_custom_system_prompt(runtime_settings) == "custom prompt"


def test_effective_custom_system_prompt_can_disable_builtin():
    settings = CLIEnvSettingsModel(
        openai=True,
        openai_detail={"openai_api_key": "x"},
        translation={"disable_builtin_fashion_prompt": True},
    )
    runtime_settings = settings.to_settings_model()

    assert get_effective_custom_system_prompt(runtime_settings) is None
