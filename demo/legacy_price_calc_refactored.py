"""`legacy_price_calc.calculate_price` に対する「善意のリファクタ」デモ版。

`base_price % 10 == 5` のときだけ税額を切り上げ相当にする特別分岐を削除し、
Python標準の `round()`（銀行丸め/偶数丸め）に統一した。「意図不明な特殊ケースを
なくして単純化した」だけに見える変更だが、実際には挙動が変わる。

保護テスト（`tests/test_characterization.py`）を実行すると何件・どのパターンで
検知されるかは `demo/README.md` を参照。
"""

_SPECIAL_CATEGORY = "special"
_SPECIAL_CATEGORY_ADJUSTMENT = 1
_NEGATIVE_PRICE_FALLBACK = 0


def calculate_price(
    base_price: int, category: str = "normal", tax_rate: float = 0.10
) -> int:
    """税込み価格を計算する（リファクタ後: 特別分岐を削除し `round()` に統一）。"""
    if base_price < _NEGATIVE_PRICE_FALLBACK:
        return _NEGATIVE_PRICE_FALLBACK

    tax_amount = round(base_price * tax_rate)

    total = base_price + tax_amount
    if category == _SPECIAL_CATEGORY:
        total -= _SPECIAL_CATEGORY_ADJUSTMENT

    return total
