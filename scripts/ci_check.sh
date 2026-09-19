#!/usr/bin/env bash
# ローカル・GitHub Actions共通の品質ゲート。
#
# 「ローカルでは通ったのにCIで落ちる」という食い違いを防ぐため、チェック内容は
# この1ファイルに集約している。ローカルでPRを出す前にこのスクリプトを実行し、
# 緑になってからpushする運用とする。CI側のワークフローファイルはこのスクリプトを
# 呼び出すだけの薄いラッパーにし、個別のチェックコマンドを直接書かないこと。
set -euo pipefail

echo "==> pytest"
uv run pytest tests/ -v

echo "==> ruff"
uv run ruff check .

echo "==> mypy"
uv run mypy src

echo "==> vulture (report only, does not fail the build)"
uv run vulture src/ --min-confidence 80 || true

echo "全チェック通過"
