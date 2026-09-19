# デモ: 「善意のリファクタ」で意図せず挙動が変わるケース

`demo/legacy_price_calc_refactored.py` は、`src/legacy_price_calc.py` に対して
以下の1点だけを変更したものです。

- `base_price % 10 == 5` のときだけ税額を切り上げ相当（`math.floor(tax) + 1`）に
  する特別分岐を削除し、Python標準の `round()`（銀行丸め/偶数丸め）に統一した

「意図不明な特殊ケースをなくして単純化した」だけに見える、レビューも通りやすそうな
変更ですが、実際には挙動が変わります。

## 再現手順

```bash
cp src/legacy_price_calc.py /tmp/legacy_price_calc.py.bak
cp demo/legacy_price_calc_refactored.py src/legacy_price_calc.py
uv run pytest tests/ -q
cp /tmp/legacy_price_calc.py.bak src/legacy_price_calc.py
```

## 実行結果

```
60 failed, 972 passed in 0.60s
```

`tests/golden_master.json` の全1032件のうち、**60件**が保護テストによって検知
されました。失敗はすべて `base_price % 10 == 5` に該当する値（5, 15, 25, 105,
1005, 12345）に集中しています。

| base_price | 失敗件数 | 内訳（categoryは6種 × tax_rateは2種 = 最大12） |
|---|---|---|
| 5 | 12 | 全パターンで検知 |
| 15 | 6 | tax_rate=0.08のみ検知（0.10は後述の理由で非検知） |
| 25 | 12 | 全パターンで検知 |
| 105 | 12 | 全パターンで検知 |
| 1005 | 12 | 全パターンで検知 |
| 12345 | 6 | tax_rate=0.10のみ検知（0.08は非検知） |

失敗メッセージの例（`base_price=25, category="normal", tax_rate=0.10`）:

```
E   AssertionError: 挙動が変化しました: calculate_price(base_price=25, category='normal', tax_rate=0.1) は golden master では 28 でしたが、実際は 27 でした (差分: -1)
```

## 副産物としての発見: 一部のケースは「たまたま」検知されない

`base_price=15` は `tax_rate=0.08` では検知されますが、`tax_rate=0.10` では
**検知されません**（新旧の出力が偶然一致するため）。

- `tax_rate=0.08`: `15 * 0.08 = 1.2` → 旧: `floor(1.2) + 1 = 2` / 新: `round(1.2) = 1` → **不一致**
- `tax_rate=0.10`: `15 * 0.10 = 1.5` → 旧: `floor(1.5) + 1 = 2` / 新: `round(1.5) = 2`
  （偶数丸めで`1.5`は`2`に丸まる） → **偶然一致**

`base_price=12345` も同様に、`tax_rate=0.10`でのみ検知され、`tax_rate=0.08`では
偶然一致して非検知になります。

これは「代表的な数パターンだけでテストしていたら、たまたま挙動変化を見逃していた
かもしれない」ことを示す実例です。もし境界値を `tax_rate=0.10` の1パターンだけで
サンプリングしていた場合、`base_price=15`の変化は検知できませんでした。
`scripts/generate_golden_master.py` が旧税率・現行税率の両方を機械的に広く
含めていたことで、この見逃しを防げています。
