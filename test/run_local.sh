#!/bin/bash
# ローカルテスト用スクリプト
# Issue作成不要で module3 を直接実行
#
# 使い方:
#   ./test/run_local.sh                # 2枚生成（デフォルト）
#   ./test/run_local.sh 4              # 全4枚生成
#   ./test/run_local.sh 1              # 1枚だけ（最速）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

OUTPUT_DIR="$PROJECT_DIR/test/output"
SCENARIO="$SCRIPT_DIR/test_scenario.json"
SPEC="$PROJECT_DIR/config/manga_spec.yml"
CHARS="$PROJECT_DIR/characters"
PANELS="${1:-2}"

mkdir -p "$OUTPUT_DIR"

echo "=== ローカルテスト: ${PANELS}枚生成 ==="
echo "シナリオ: $SCENARIO"
echo "出力先:   $OUTPUT_DIR"

python "$PROJECT_DIR/src/module3_image_gen.py" \
  --scenario "$SCENARIO" \
  --spec "$SPEC" \
  --characters "$CHARS" \
  --output "$OUTPUT_DIR" \
  --panels "$PANELS" \
  --no-combine

echo "=== 完了！ $OUTPUT_DIR を確認してください ==="
