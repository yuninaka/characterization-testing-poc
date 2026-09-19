"""`legacy_price_calc.calculate_price` のゴールデンマスター生成スクリプト。

対象コードの中身を読んで期待値を予測するのではなく、境界値・典型値・ゼロ・負数・
未知のcategory値を広く入力し、実際に返ってきた値をそのまま記録する
「ブラックボックス探索」を行う。tax_rateは旧税率(0.08)・現行税率(0.10)の両方を含める。

実行方法（リポジトリ直下から）:
    uv run python -m scripts.generate_golden_master
"""

import itertools
import json
from pathlib import Path
from typing import TypedDict

from src.legacy_price_calc import calculate_price

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GOLDEN_MASTER_PATH = _REPO_ROOT / "tests" / "golden_master.json"

# base_price % 10 == 5 の分岐境界を広く踏むための値（0〜30・90〜110・990〜1010の全剰余）
_BOUNDARY_BASE_PRICES = [*range(0, 31), *range(90, 111), *range(990, 1011)]

# 典型的な価格帯
_TYPICAL_BASE_PRICES = [100, 500, 999, 1234, 1500, 2500, 9999, 12345, 100000]

# ゼロ・負数（バリデーション漏れの可能性がある領域）
_ZERO_AND_NEGATIVE_BASE_PRICES = [0, -1, -5, -10, -15, -100, -9999]

_BASE_PRICES = sorted(
    {*_BOUNDARY_BASE_PRICES, *_TYPICAL_BASE_PRICES, *_ZERO_AND_NEGATIVE_BASE_PRICES}
)

# "normal" / "special" に加え、未知の値・空文字・表記ゆれを含める
_CATEGORIES = ["normal", "special", "unknown", "", "SPECIAL", "special "]

# 旧税率(0.08)と現行税率(0.10)の両方
_TAX_RATES = [0.08, 0.10]


class GoldenMasterCase(TypedDict):
    """ゴールデンマスター1件分（入力と、実際に観測された出力）。"""

    base_price: int
    category: str
    tax_rate: float
    result: int


def generate_cases() -> list[GoldenMasterCase]:
    """入力空間の全組み合わせについて、実際に返ってきた値をそのまま記録する。"""
    combinations = itertools.product(_BASE_PRICES, _CATEGORIES, _TAX_RATES)
    return [
        {
            "base_price": base_price,
            "category": category,
            "tax_rate": tax_rate,
            "result": calculate_price(base_price, category, tax_rate),
        }
        for base_price, category, tax_rate in combinations
    ]


def main() -> None:
    cases = generate_cases()
    _GOLDEN_MASTER_PATH.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(cases)}件のケースを {_GOLDEN_MASTER_PATH} に書き出しました")


if __name__ == "__main__":
    main()
