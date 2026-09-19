# PoCセットアップ時の検討記録

会話内で決まった、コードやREADMEだけからは追いにくい方針・判断をここに残す。

## 背景

消費税率変更対応案件（2027年4月施行の1%減税、テスト工程強化が主担当）の
Phase0「保護テスト基盤（改修前の挙動を資産化）」に向けた準備として、
Characterization Testingの型を確立するPoC。

## 対象コードの仕様（`src/legacy_price_calc.py`）

以下は会話内で検証済みの仕様として実装した。「経緯不明・引き継ぎ資料なし」
という設定で、意図は一切推測せず、挙動のみを保護対象とする。

- `calculate_price(base_price: int, category: str = "normal", tax_rate: float = 0.10) -> int`
- `base_price % 10 == 5` のとき、税額は `math.floor(tax) + 1`（切り上げ相当）
- それ以外は標準の `round()`（銀行丸め/偶数丸め）
- `category == "special"` のとき、計算後の総額から1円引かれる
- `base_price < 0` のときは `0` を返す（早期return。category補正より先に判定する）
- 未知のcategory値は `"normal"` と同じ扱い

## CIガードレールのスコープ判断

当初案は「pytest + 任意でruff」の軽量CIだったが、途中で
「他のPoC（log-anomaly-detection-poc）と同等のガードレールにしたい」という
指示に変更した。ただし以下は明示的に対象外とした。

- **gitleaks / pip-audit は含めない**: log-anomaly-detection-pocでは
  Azure OpenAIのAPIキーを実際に扱うようになった際に追加された固有の拡張。
  本PoCは秘密情報・外部APIを一切扱わないため対象外と判断した
- `python-ci-guardrails` スキルの標準テンプレート（pytest + ruff strict +
  mypy strict + vulture report-only）をそのまま適用した
- `ci_check.sh` の `mypy` は `src` のみを対象にしている（テンプレートの
  デフォルトを踏襲）。`scripts/`・`demo/` は開発時に個別に
  `uv run mypy scripts` 等で確認済みだが、CIゲートには含めていない

## ゴールデンマスターの入力空間設計

`scripts/generate_golden_master.py` は以下を機械的に組み合わせて生成した
（1032件）。

- 境界値: `base_price % 10 == 5` の分岐を広く踏むための0〜30・90〜110・
  990〜1010の全剰余
- 典型値: 100〜100000の代表的な価格帯
- ゼロ・負数: 0, -1, -5, -10, -15, -100, -9999
- category: `normal` / `special` に加え、`unknown` / 空文字 / `SPECIAL`
  （大文字）/ `special `（末尾スペース）
- tax_rate: 旧税率(0.08)・現行税率(0.10)の両方

## デモで判明した知見

`demo/legacy_price_calc_refactored.py`（特別分岐を削除しround()に統一）を
保護テストにかけた結果、1032件中60件を検知。特に `base_price=15` や
`base_price=12345` は、片方の税率でのみ新旧の出力が偶然一致し検知されない
という非対称性が見つかった。詳細は [`demo/README.md`](../demo/README.md)。
