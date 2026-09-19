"""レガシー価格計算モジュール。

経緯不明・引き継ぎ資料なし。このモジュールの仕様は、本リポジトリでの
ブラックボックス探索（`scripts/generate_golden_master.py`）により判明したもので、
「なぜそうなっているか」の意図は不明なまま保護対象として扱う。
"""

import math

_ROUND_UP_REMAINDER = 5
_REMAINDER_DIVISOR = 10
_ROUND_UP_ADJUSTMENT = 1
_SPECIAL_CATEGORY = "special"
_SPECIAL_CATEGORY_ADJUSTMENT = 1
_NEGATIVE_PRICE_FALLBACK = 0


def calculate_price(
    base_price: int, category: str = "normal", tax_rate: float = 0.10
) -> int:
    """税込み価格を計算する。

    以下は挙動観察により判明した「謎仕様」（意図不明、保護対象）。

    - `base_price % 10 == 5` のときのみ税額が切り上げ相当
      （`math.floor(tax) + 1`）になり、それ以外はPython標準の`round()`
      （銀行丸め/偶数丸め）になる
    - `category == "special"` のとき、計算後の総額から1円引かれる
    - `base_price < 0` のときは検証なしに`0`を返す（バリデーション漏れの可能性）
    - `"normal"` / `"special"` 以外の未知のcategory値は`"normal"`と同じ扱いになる
      （category値のバリデーションはない）
    """
    if base_price < _NEGATIVE_PRICE_FALLBACK:
        return _NEGATIVE_PRICE_FALLBACK

    tax = base_price * tax_rate
    if base_price % _REMAINDER_DIVISOR == _ROUND_UP_REMAINDER:
        tax_amount = math.floor(tax) + _ROUND_UP_ADJUSTMENT
    else:
        tax_amount = round(tax)

    total = base_price + tax_amount
    if category == _SPECIAL_CATEGORY:
        total -= _SPECIAL_CATEGORY_ADJUSTMENT

    return total
