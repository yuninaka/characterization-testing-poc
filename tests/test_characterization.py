"""`legacy_price_calc.calculate_price` に対する保護テスト（Characterization Test）。

このテストは「正しさ」を一切判断しない。`tests/golden_master.json` に記録された
既存の挙動との一致だけを検証する。失敗した場合、それが意図した仕様変更（税率変更等）
によるものか、意図しない挙動変化（リファクタ事故等）によるものかは、この場で
判断せず人間に委ねる。
"""

import json
from pathlib import Path
from typing import TypedDict

import pytest

from src.legacy_price_calc import calculate_price

_GOLDEN_MASTER_PATH = Path(__file__).resolve().parent / "golden_master.json"


class GoldenMasterCase(TypedDict):
    """ゴールデンマスター1件分（入力と、記録済みの出力）。"""

    base_price: int
    category: str
    tax_rate: float
    result: int


def _load_golden_master() -> list[GoldenMasterCase]:
    with _GOLDEN_MASTER_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _case_id(case: GoldenMasterCase) -> str:
    return (
        f"base_price={case['base_price']},"
        f"category={case['category']!r},"
        f"tax_rate={case['tax_rate']}"
    )


_CASES = _load_golden_master()


@pytest.mark.parametrize("case", _CASES, ids=[_case_id(c) for c in _CASES])
def test_matches_golden_master(case: GoldenMasterCase) -> None:
    actual = calculate_price(case["base_price"], case["category"], case["tax_rate"])
    expected = case["result"]
    assert actual == expected, (
        f"挙動が変化しました: calculate_price("
        f"base_price={case['base_price']}, "
        f"category={case['category']!r}, "
        f"tax_rate={case['tax_rate']}) "
        f"は golden master では {expected} でしたが、実際は {actual} でした "
        f"(差分: {actual - expected:+d})"
    )
