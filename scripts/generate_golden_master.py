"""`legacy_price_calc.calculate_price` のゴールデンマスター生成スクリプト。

対象コードの中身を読んで期待値を予測するのではなく、境界値・典型値・ゼロ・負数・
未知のcategory値を広く入力し、実際に返ってきた値をそのまま記録する
「ブラックボックス探索」を行う。tax_rateは軽減税率(0.08)・時限軽減税率(0.01)・
標準税率(0.10)を含める。

実行方法（リポジトリ直下から）:
    uv run python -m scripts.generate_golden_master

意図した変更（税率変更等）で影響範囲だけを再生成する場合:
    uv run python -m scripts.generate_golden_master --tax-rate 0.01

`--tax-rate`を指定すると、そのtax_rateに該当する既存ケースだけを置き換え、
それ以外のケースは変更せずに既存のgolden_master.jsonへマージする。
"""

import argparse
import itertools
import json
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict, cast

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

# 軽減税率(0.08)・時限軽減税率(0.01、2027年4月〜2029年3月の時限措置で追加)・
# 標準税率(0.10)
_TAX_RATES = (0.08, 0.01, 0.10)


class GoldenMasterCase(TypedDict):
    """ゴールデンマスター1件分（入力と、実際に観測された出力）。"""

    base_price: int
    category: str
    tax_rate: float
    result: int


def generate_cases(tax_rates: Sequence[float] | None = None) -> list[GoldenMasterCase]:
    """指定した(または全)tax_rateの入力空間について、観測値をそのまま記録する。"""
    rates = tax_rates if tax_rates is not None else _TAX_RATES
    combinations = itertools.product(_BASE_PRICES, _CATEGORIES, rates)
    return [
        {
            "base_price": base_price,
            "category": category,
            "tax_rate": tax_rate,
            "result": calculate_price(base_price, category, tax_rate),
        }
        for base_price, category, tax_rate in combinations
    ]


def _load_existing_cases() -> list[GoldenMasterCase]:
    if not _GOLDEN_MASTER_PATH.exists():
        return []
    with _GOLDEN_MASTER_PATH.open(encoding="utf-8") as f:
        # このファイルは本スクリプト自身が書き出す唯一の書き手であり、
        # GoldenMasterCaseの形を保証できるためcastする(json.loadの戻り値はAny)。
        return cast(list[GoldenMasterCase], json.load(f))


def _merge_cases(
    existing: list[GoldenMasterCase],
    new: list[GoldenMasterCase],
    scoped_rates: Sequence[float],
) -> list[GoldenMasterCase]:
    """`scoped_rates`に該当する既存ケースだけを`new`で置き換える。それ以外は保持する。"""
    kept = [c for c in existing if c["tax_rate"] not in scoped_rates]
    merged = kept + new
    return sorted(merged, key=lambda c: (c["base_price"], c["category"], c["tax_rate"]))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tax-rate",
        type=float,
        action="append",
        help="指定したtax_rateのケースだけを再生成し、既存ファイルへマージする"
        "(未指定なら全件を再生成する)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.tax_rate:
        new_cases = generate_cases(tax_rates=args.tax_rate)
        cases = _merge_cases(_load_existing_cases(), new_cases, args.tax_rate)
    else:
        cases = generate_cases()

    _GOLDEN_MASTER_PATH.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(cases)}件のケースを {_GOLDEN_MASTER_PATH} に書き出しました")


if __name__ == "__main__":
    main()
