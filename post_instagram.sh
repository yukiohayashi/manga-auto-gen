#!/bin/bash
# Instagram投稿ヘルパースクリプト
# 使い方: ./post_instagram.sh output-episodes/エピソード名

if [ -z "$1" ]; then
  echo "使い方: ./post_instagram.sh <エピソードディレクトリ>"
  echo ""
  echo "例:"
  echo "  ./post_instagram.sh output-episodes/彼はサイコパス？"
  exit 1
fi

EPISODE_DIR="$1"

if [ ! -d "$EPISODE_DIR" ]; then
  echo "エラー: ディレクトリが見つかりません: $EPISODE_DIR"
  exit 1
fi

# .envから環境変数を読み込む
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

if [ -z "$INSTAGRAM_ACCESS_TOKEN" ] || [ -z "$INSTAGRAM_ACCOUNT_ID" ]; then
  echo "エラー: .envファイルに以下を設定してください："
  echo "  INSTAGRAM_ACCESS_TOKEN=トークン"
  echo "  INSTAGRAM_ACCOUNT_ID=17841407672340828"
  exit 1
fi

echo "============================================"
echo "Instagram投稿"
echo "============================================"
echo "エピソード: $EPISODE_DIR"
echo ""

python3 src/module7_instagram_publisher.py --episode-dir "$EPISODE_DIR"
