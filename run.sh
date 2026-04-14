#!/bin/bash
# ============================================================
# manga-auto-gen 統合実行スクリプト
#
# 使い方:
#   ./run.sh <episode.json>                       # ローカルのみ（out/に出力）
#   ./run.sh <episode.json> --drive                # ローカル + Google Drive同期
#   ./run.sh <episode.json> --panels 2             # 2枚だけ生成
#   ./run.sh <episode.json> --drive --panels 4     # 全4枚 + Drive同期
#
# オプション:
#   --drive       Google Driveに同期する（デフォルト: ローカルのみ）
#   --panels N    生成するパネル数（デフォルト: 4）
#   --no-combine  結合画像を生成しない
#   --name NAME   エピソード名（デフォルト: episode.jsonのtitleから自動取得）
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# .envファイルがあれば読み込む
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi
CHARS="$PROJECT_DIR/characters"

# --- 引数パース ---
SCENARIO=""
DRIVE_SYNC=false
PANELS=4
NO_COMBINE=false
EPISODE_NAME=""
ONLY_PANELS=""
CAPTION_ONLY=false
PUBLISH=false
SCHEDULE_TIME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --drive)
      DRIVE_SYNC=true
      shift
      ;;
    --panels)
      PANELS="$2"
      shift 2
      ;;
    --no-combine)
      NO_COMBINE=true
      shift
      ;;
    --name)
      EPISODE_NAME="$2"
      shift 2
      ;;
    --only)
      ONLY_PANELS="$2"
      shift 2
      ;;
    --caption-only)
      CAPTION_ONLY=true
      shift
      ;;
    --publish)
      PUBLISH=true
      shift
      ;;
    --schedule)
      SCHEDULE_TIME="$2"
      PUBLISH=true
      shift 2
      ;;
    -*)
      echo "不明なオプション: $1"
      exit 1
      ;;
    *)
      if [ -z "$SCENARIO" ]; then
        SCENARIO="$1"
      fi
      shift
      ;;
  esac
done

# --- バリデーション ---
if [ -z "$SCENARIO" ]; then
  echo "使い方: ./run.sh <episode.json> [--drive] [--panels N] [--only 1,3] [--name NAME] [--publish] [--schedule TIME]"
  echo ""
  echo "例:"
  echo "  ./run.sh test/test_scenario.json              # ローカル4枚生成（デフォルト）"
  echo "  ./run.sh episodes/xxx/episode.json            # 本番エピソードをローカル生成"
  echo "  ./run.sh episodes/xxx/episode.json --panels 2 # 2枚だけ生成"
  echo "  ./run.sh episodes/xxx/episode.json --only 1,3  # パネル1,3だけ再生成"
  echo "  ./run.sh episodes/xxx/episode.json --caption-only # 投稿文だけ生成"
  echo "  ./run.sh test/test_scenario.json --drive       # ローカル + Drive同期"
  echo "  ./run.sh episodes/xxx/episode.json --publish   # Instagramに即時投稿"
  echo "  ./run.sh episodes/xxx/episode.json --schedule '2024-01-15T10:00:00' # 予約投稿"
  exit 1
fi

if [ ! -f "$SCENARIO" ]; then
  echo "エラー: エピソードファイルが見つかりません: $SCENARIO"
  exit 1
fi

# --- エピソード名の決定 ---
if [ -z "$EPISODE_NAME" ]; then
  EPISODE_NAME=$(python3 -c "
import json, sys
with open('$SCENARIO', 'r') as f:
    data = json.load(f)
print(data.get('title', '無題'))
" 2>/dev/null || echo "無題")
fi

# 安全なフォルダ名に変換
SAFE_NAME=$(echo "$EPISODE_NAME" | sed 's/[\/\\:*?"<>|]/_/g')

# --- 出力先（episode.jsonと同じディレクトリ） ---
OUTPUT_DIR="$(cd "$(dirname "$SCENARIO")" && pwd)"
mkdir -p "$OUTPUT_DIR"

# --- 実行情報 ---
echo "============================================"
echo " manga-auto-gen"
echo "============================================"
echo "エピソード:     $SCENARIO"
echo "エピソード名: $EPISODE_NAME"
echo "出力先:       $OUTPUT_DIR"
echo "パネル数:     $PANELS"
if [ -n "$ONLY_PANELS" ]; then
  echo "再生成:       パネル $ONLY_PANELS のみ"
fi
echo "Drive同期:    $([ "$DRIVE_SYNC" = true ] && echo 'あり' || echo 'なし')"

if [ "$CAPTION_ONLY" = true ]; then
  echo "モード:       投稿文のみ生成"
fi

if [ "$PUBLISH" = true ]; then
  if [ -n "$SCHEDULE_TIME" ]; then
    echo "Instagram投稿: 予約 ($SCHEDULE_TIME)"
  else
    echo "Instagram投稿: 即時"
  fi
fi

echo "============================================"

# --- Module 5のみ実行（--caption-only指定時） ---
if [ "$CAPTION_ONLY" = true ]; then
  echo ""
  echo "--- Instagram投稿文生成 ---"
  python3 "$PROJECT_DIR/src/module6_sns_publisher.py" \
    --episode "$SCENARIO" \
    --output "$OUTPUT_DIR/instagram_post.txt" \
    || echo "[警告] Instagram投稿文生成に失敗しました"
  
  echo ""
  echo "============================================"
  echo " 完了！"
  echo " 出力: $OUTPUT_DIR/instagram_post.txt"
  echo "============================================"
  exit 0
fi

# --- Module 4: 画像生成 ---
COMBINE_FLAG="--no-combine"

ONLY_FLAG=""
if [ -n "$ONLY_PANELS" ]; then
  ONLY_FLAG="--only $ONLY_PANELS"
fi

python3 "$PROJECT_DIR/src/module4_image_gen.py" \
  --episode "$SCENARIO" \
  --characters "$CHARS" \
  --output "$OUTPUT_DIR" \
  --panels "$PANELS" \
  $COMBINE_FLAG \
  $ONLY_FLAG

echo ""
echo "画像生成完了: $OUTPUT_DIR"

# --- Module 6: Instagram投稿文生成 ---
echo ""
echo "--- Instagram投稿文生成 ---"
python3 "$PROJECT_DIR/src/module6_sns_publisher.py" \
  --episode "$SCENARIO" \
  --output "$OUTPUT_DIR/instagram_post.txt" \
  || echo "[警告] Instagram投稿文生成に失敗しました"

# --- Module 5: Google Drive同期（オプション） ---
if [ "$DRIVE_SYNC" = true ]; then
  echo ""
  echo "--- Google Drive同期 ---"
  PARENT_FOLDER_ID="0AFCTATYikdWmUk9PVA"

  python3 "$PROJECT_DIR/src/module5_drive_sync.py" \
    --source "$OUTPUT_DIR" \
    --parent-folder-id "$PARENT_FOLDER_ID" \
    --episode-name "$SAFE_NAME" \
    || echo "[警告] Google Drive同期に失敗しました"
fi

echo ""
echo "============================================"
echo " 完了！"
echo " 出力先: $OUTPUT_DIR"
if [ "$DRIVE_SYNC" = true ]; then
  echo " Drive:  manga-auto-gen/$SAFE_NAME/"
fi
echo "============================================"

# --- Module 7: Instagram投稿（オプション） ---
if [ "$PUBLISH" = true ]; then
  echo ""
  echo "--- Instagram投稿 ---"
  
  # 結合画像がある場合はそちらを優先
  COMBINED_IMAGE="$OUTPUT_DIR/4koma_combined.png"
  if [ -f "$COMBINED_IMAGE" ]; then
    PUBLISH_FLAG="--combined-image $COMBINED_IMAGE"
  else
    PUBLISH_FLAG=""
  fi
  
  # 予約投稿時間が指定されている場合
  if [ -n "$SCHEDULE_TIME" ]; then
    SCHEDULE_FLAG="--schedule $SCHEDULE_TIME"
  else
    SCHEDULE_FLAG=""
  fi
  
  python3 "$PROJECT_DIR/src/module7_instagram_publisher.py" \
    --episode-dir "$OUTPUT_DIR" \
    $PUBLISH_FLAG \
    $SCHEDULE_FLAG \
    || echo "[警告] Instagram投稿に失敗しました"
fi

echo ""
echo "============================================"
echo "📸 生成された画像を確認してください"
echo "============================================"
echo ""
echo "Instagram投稿する場合は以下を実行："
echo ""
echo "  export INSTAGRAM_ACCESS_TOKEN='トークン'"
echo "  export INSTAGRAM_ACCOUNT_ID='17841407672340828'"
echo "  python3 src/module7_instagram_publisher.py --episode-dir '$OUTPUT_DIR'"
echo ""
