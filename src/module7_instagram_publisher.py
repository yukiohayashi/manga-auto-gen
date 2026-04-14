#!/usr/bin/env python3
"""
モジュール7：Instagram自動投稿（Meta Graph API）

フロー:
1. episode_dir内のinstagram_post.jsonを読み込む
2. 4koma_panel_*.pngをGitHub Raw URLで参照
3. Instagram Graph APIでカルーセル投稿
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
import time


GITHUB_RAW_BASE = "https://raw.githubusercontent.com/yukiohayashi/manga-auto-gen/main"


class InstagramPublisher:
    """Instagram Graph APIを使用した投稿クラス"""

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: str, instagram_account_id: str):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id

    def _local_path_to_github_url(self, image_path: Path) -> str:
        """ローカルパスをGitHub Raw URLに変換"""
        import time
        parts = image_path.parts
        try:
            idx = next(i for i, p in enumerate(parts) if p == "output-episodes")
            rel = "/".join(parts[idx:])
        except StopIteration:
            rel = image_path.name
        # キャッシュ破壊のためタイムスタンプを追加
        timestamp = int(time.time())
        return f"{GITHUB_RAW_BASE}/{quote(rel, safe='/')}?t={timestamp}"

    def create_image_container(self, image_url: str, is_carousel_item: bool = False) -> Optional[str]:
        """単一画像のMediaコンテナを作成"""
        params = {
            "access_token": self.access_token,
            "image_url": image_url,
        }
        if is_carousel_item:
            params["is_carousel_item"] = "true"

        result = requests.post(
            f"{self.API_BASE}/{self.instagram_account_id}/media",
            data=params
        ).json()

        if "id" not in result:
            print(f"[Module7] 画像コンテナ作成失敗: {result}")
            return None

        print(f"[Module7] 画像コンテナ作成成功: {result['id']} ({image_url.split('/')[-1]})")
        return result["id"]

    def create_carousel_container(self, media_ids: list, caption: str) -> Optional[str]:
        """カルーセルコンテナを作成"""
        result = requests.post(
            f"{self.API_BASE}/{self.instagram_account_id}/media",
            data={
                "access_token": self.access_token,
                "media_type": "CAROUSEL",
                "children": ",".join(media_ids),
                "caption": caption,
            }
        ).json()

        if "id" not in result:
            print(f"[Module7] カルーセルコンテナ作成失敗: {result}")
            return None

        print(f"[Module7] カルーセルコンテナ作成成功: {result['id']}")
        return result["id"]

    def publish_media(self, creation_id: str) -> bool:
        """Mediaコンテナを公開"""
        result = requests.post(
            f"{self.API_BASE}/{self.instagram_account_id}/media_publish",
            data={
                "access_token": self.access_token,
                "creation_id": creation_id,
            }
        ).json()

        if "id" not in result:
            print(f"[Module7] 公開失敗: {result}")
            return False

        print(f"[Module7] ✅ 投稿成功！ Post ID: {result['id']}")
        return True

    def post_carousel(self, image_paths: list, caption: str) -> bool:
        """4枚カルーセル投稿"""
        print(f"[Module7] カルーセル投稿開始 ({len(image_paths)}枚)")

        media_ids = []
        for path in image_paths:
            url = self._local_path_to_github_url(path)
            print(f"[Module7] URL: {url}")
            media_id = self.create_image_container(url, is_carousel_item=True)
            if not media_id:
                return False
            media_ids.append(media_id)

        creation_id = self.create_carousel_container(media_ids, caption)
        if not creation_id:
            return False

        print("[Module7] 5秒待機中...")
        time.sleep(5)
        return self.publish_media(creation_id)

    def post_single(self, image_path: Path, caption: str) -> bool:
        """単一画像投稿"""
        url = self._local_path_to_github_url(image_path)
        print(f"[Module7] URL: {url}")

        result = requests.post(
            f"{self.API_BASE}/{self.instagram_account_id}/media",
            data={
                "access_token": self.access_token,
                "image_url": url,
                "caption": caption,
            }
        ).json()

        if "id" not in result:
            print(f"[Module7] 単一画像コンテナ作成失敗: {result}")
            return False

        return self.publish_media(result["id"])


def main():
    parser = argparse.ArgumentParser(description="Instagram自動投稿")
    parser.add_argument("--episode-dir", required=True, help="エピソードディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="投稿せず内容を表示のみ")
    args = parser.parse_args()

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    instagram_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not access_token or not instagram_account_id:
        print("[Module7] エラー: 環境変数 INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_ACCOUNT_ID が未設定")
        sys.exit(1)

    episode_dir = Path(args.episode_dir)
    if not episode_dir.exists():
        print(f"[Module7] エラー: ディレクトリが見つかりません: {episode_dir}")
        sys.exit(1)

    # instagram_post.json 読み込み（txtはフォールバック）
    json_path = episode_dir / "instagram_post.json"
    txt_path = episode_dir / "instagram_post.txt"

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            post_data = json.load(f)
        print(f"[Module7] JSON読み込み成功: {json_path}")
    elif txt_path.exists():
        post_data = {"caption": txt_path.read_text(encoding="utf-8"), "hashtags": [], "images": []}
        print(f"[Module7] TXT読み込み成功: {txt_path}")
    else:
        print(f"[Module7] エラー: instagram_post.json または instagram_post.txt が必要です")
        sys.exit(1)

    # キャプション構築
    caption = post_data.get("caption", "")
    if not caption:
        caption = post_data.get("formatted_caption", "")
    hashtags = post_data.get("hashtags", [])
    if hashtags:
        caption += "\n\n" + " ".join(hashtags)

    # 画像リスト取得
    json_images = post_data.get("images", [])
    if json_images:
        image_paths = [episode_dir / img for img in json_images]
    else:
        image_paths = sorted(episode_dir.glob("4koma_panel_*.png"))

    if not image_paths:
        print("[Module7] エラー: 投稿する画像が見つかりません")
        sys.exit(1)

    missing = [p for p in image_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"[Module7] エラー: ファイルが見つかりません: {p}")
        sys.exit(1)

    print(f"[Module7] 投稿画像: {len(image_paths)}枚")
    for p in image_paths:
        print(f"  - {p.name}")
    print(f"[Module7] キャプション({len(caption)}文字): {caption[:80]}...")

    if args.dry_run:
        print("\n[Module7] === DRY RUN（実際には投稿しません）===")
        return

    publisher = InstagramPublisher(access_token, instagram_account_id)
    success = publisher.post_single(image_paths[0], caption) if len(image_paths) == 1 else publisher.post_carousel(image_paths, caption)

    print("\n[Module7] 投稿処理完了" if success else "\n[Module7] 投稿処理失敗")
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
