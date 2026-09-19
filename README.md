# characterization-testing-poc

[![CI](https://github.com/yuninaka/characterization-testing-poc/actions/workflows/test.yml/badge.svg)](https://github.com/yuninaka/characterization-testing-poc/actions/workflows/test.yml)

レガシーコードの意図不明な挙動を、中身を読まずに保護テスト（Characterization
Testing / ゴールデンマスターテスト）として資産化する型を確立するための実務ノート。

## このリポジトリの位置づけ

消費税率変更対応案件（2027年4月施行の1%減税、テスト工程強化が主担当）の
Phase0「保護テスト基盤（改修前の挙動を資産化）」に向けた準備として作成した。

「新しい技術の発見」を売りにするものではなく、**消費税率変更という具体的な実務
文脈で、レガシーコードに対する保護テストをどう組み立て、何を発見したか**を示す
実務ノートとして位置づけている。単発の軽量な参照リポジトリであり、姉妹PoC
[`log-anomaly-detection-poc`](https://github.com/yuninaka/log-anomaly-detection-poc)
のような重厚なCI構成（gitleaks・pip-audit等）は前提としていない
（品質ゲート自体はpytest/ruff/mypy strict/vultureで同等の水準に揃えている。
詳細は [`CLAUDE.md`](CLAUDE.md) 参照）。

## 題材: 経緯不明のレガシー価格計算コード

[`src/legacy_price_calc.py`](src/legacy_price_calc.py) の `calculate_price` は、
「経緯不明・引き継ぎ資料なし」という設定のレガシー風コードである。税額計算に
`base_price % 10 == 5` のときだけ切り上げ相当になる特別分岐があるなど、意図の
読めない挙動を複数含む。実際の税制改正対応の現場で遭遇しうる「なぜこうなって
いるか誰も知らないが、動いているので触れない」コードを模している。

## Characterization Testingの型（5ステップ）

このリポジトリで実践した型は以下の5ステップ。

1. **対象範囲の特定**: 変更対象の関数・モジュールの入出力境界を決める
   （本PoCでは `calculate_price(base_price, category, tax_rate) -> int`
   という1関数に絞った）
2. **入力空間の設計**: 中身を読んで「起こりうるケース」を頭で予測するのでは
   なく、境界値・典型値・ゼロ・負数・未知の値を機械的に広く洗い出す
   （[`scripts/generate_golden_master.py`](scripts/generate_golden_master.py)
   の `_BOUNDARY_BASE_PRICES` 等を参照）
3. **ゴールデンマスター生成**: 設計した入力空間に対して実際に対象コードを
   呼び出し、返ってきた値をそのまま記録する「ブラックボックス探索」を行う。
   期待値を手で書かない（[`tests/golden_master.json`](tests/golden_master.json)）
4. **保護テスト実装**: ゴールデンマスターとの一致だけを見るテストを書く。
   テストコード自体には「正しさ」の判断を一切持たせない
   （[`tests/test_characterization.py`](tests/test_characterization.py)）
5. **改修時の運用**: 意図した変更（税率変更等）の際は、該当範囲だけ
   ゴールデンマスターを再生成し、変更理由を記録する（後述）

## 使い方

```bash
# 依存関係のセットアップ
uv sync

# 保護テストの実行
uv run pytest tests/ -v
# または、lint/型チェックも含めたフルゲート
./scripts/ci_check.sh

# ゴールデンマスターの再生成（リポジトリ直下から）
uv run python -m scripts.generate_golden_master
```

現在のゴールデンマスターは、境界値（`base_price % 10 == 5` の分岐を広く踏む
0〜30・90〜110・990〜1010の全剰余）・典型値・ゼロ/負数・未知のcategory値
（大文字違い・末尾スペース・空文字を含む）× 軽減税率(0.08)/時限軽減税率(0.01)/
標準税率(0.10) の組み合わせで **1548件** を記録している（時限軽減税率0.01は
[意図した変更時のゴールデンマスター更新フロー](#意図した変更時のゴールデンマスター更新フロー)
を実際に動かして追加したもの）。

> **記事との数値の対応について**: [Zenn記事](https://zenn.dev/yuninaka/articles/characterization-testing-blind-spot)
> が参照している「1032件・60 failed」等の具体的な数値は、時限軽減税率0.01を
> 追加する前の状態のもの。その時点のコードは `article-1032-cases` タグから
> 参照できる（`git checkout article-1032-cases`）。リポジトリはPoCとして
> その後も発展させているため、`main`の現在値とは一致しない。

## デモ: 「善意のリファクタ」で意図せず挙動が変わった実例

[`demo/legacy_price_calc_refactored.py`](demo/legacy_price_calc_refactored.py)
で、`base_price % 10 == 5` の特別分岐を削除し `round()` に統一するという
「一見単純化しただけ」の変更を加え、保護テストにかけた。

```
96 failed, 1452 passed in 0.87s
```

1548件中96件を検知。さらに興味深いことに、`base_price=15` は `tax_rate=0.01`
・`0.08`では検知されるが `tax_rate=0.10` では新旧の出力が偶然一致して
**検知されない**（`base_price=12345`は逆に`0.08`でのみ非検知）。`base_price=95`・
`995`に至っては**3税率すべてで偶然一致し、完全に非検知**になる。広い入力
空間を用意しても、まだ見えていない偶然の一致は残りうる、という手法の限界
も示している。詳細な再現手順・失敗メッセージの実例は
[`demo/README.md`](demo/README.md) を参照。

## 副産物としての発見: 探索の過程で見つかった「謎仕様」

ブラックボックス探索の過程で、以下の「意図不明な仕様」が機械的に洗い出された。

| 謎仕様 | 内容 |
|---|---|
| special時の-1円調整 | `category == "special"` のとき、計算後の総額から1円引かれる。理由は不明 |
| 負数の扱い | `base_price < 0` のとき検証なしに`0`を返す。バリデーション漏れの可能性がある |
| 未知category値の扱い | `"normal"` / `"special"` 以外の値（大文字違い・空文字等）はすべて `"normal"` と同じ扱いになる。category値のバリデーションが一切ない |

**実案件でこれらを見つけた場合の扱い方針**: その場で「これはバグだろう」
「これは仕様だろう」と人間が判断・修正しない。ゴールデンマスター生成のような
機械的な探索で挙動を網羅的に洗い出し、一覧として人間（業務有識者・元担当者等）
に確認材料として渡す。保護テストの役割は「正しさを判定すること」ではなく
「現状の挙動を固定し、変更を可視化すること」であり、正しさの判断はテストの
外、人間の側に委ねる。

## 意図した変更時のゴールデンマスター更新フロー

税率変更のような**意図した仕様変更**の場合は、以下の手順で進める。

1. 変更が影響する範囲を特定する（例: 税率変更なら `tax_rate` に依存する
   全ケース。category追加なら該当categoryのケースのみ、等）
2. 影響範囲**だけ**を対象にゴールデンマスターを再生成する。無関係な範囲まで
   まとめて再生成すると、意図しない別の変更を一緒に「正解」として固定して
   しまう危険があるため、範囲を絞ることが重要
3. 再生成した理由（どの仕様変更に対応するものか、いつ・誰が判断したか）を
   コミットメッセージまたはPR説明に記録する。「なぜこの値に変わったか」が
   後から追えない再生成は、保護テストの意味を失わせる
4. 保護テストを実行し、影響範囲外のケースに差分が出ていないことを確認して
   からコミットする

この手順は説明だけでなく実際に一度動かしている。2027年4月〜2029年3月の
時限軽減税率(0.01)を想定して
`uv run python -m scripts.generate_golden_master --tax-rate 0.01` を実行し、
既存の0.08/0.10ケース(1032件)が1件も変化せず、0.01のケース(516件)だけが
追加されたことを確認した上でコミットした。詳細は
[`plans/2026-09-tax-rate-0.01-reduced-rate-update.md`](plans/2026-09-tax-rate-0.01-reduced-rate-update.md)
を参照。

## ディレクトリ構成

```
characterization-testing-poc/
├── src/legacy_price_calc.py              # 対象のレガシー風コード
├── scripts/generate_golden_master.py     # ゴールデンマスター生成スクリプト
├── tests/
│   ├── golden_master.json                # 生成されたゴールデンマスター
│   └── test_characterization.py          # 保護テスト
├── demo/
│   ├── legacy_price_calc_refactored.py   # 「善意のリファクタ」デモ版
│   └── README.md                         # デモの実行結果
├── plans/                                 # 検討記録
├── .github/workflows/test.yml             # CI（ci_check.shを呼ぶだけの薄いラッパー）
└── scripts/ci_check.sh                    # pytest/ruff/mypy/vultureの品質ゲート
```
