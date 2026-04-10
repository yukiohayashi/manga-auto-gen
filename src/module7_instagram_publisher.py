#!/usr/bin/env python3
"""
モジュール7：Instagram自動投稿（Meta Graph API）

Instagram Graph APIを使用して、画像をInstagramに自動投稿または予約投稿する。
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class InstagramPublisher:
    """Instagram Graph APIを使用した投稿クラス"""

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: str, instagram_account_id: str):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.drive_service = None
        self._init_drive()

    def _init_drive(self):
        """Google Driveサービスを初期化"""
        try:
            creds_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
            if creds_json:
                creds_data = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_data,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self.drive_service = build('drive', 'v3', credentials=credentials)
                print("[Module7] Google Drive認証成功")
        except Exception as e:
            print(f"[Module7] Google Drive認証失敗: {e}")

    def upload_to_drive_and_get_url(self, image_path: Path, folder_id: str = "1DyM1j8gMDruReBqzdUuxnYfRaYNHHNuc") -> Optional[str]:
        """画像をGoogle Driveにアップロードして公開URLを取得"""
        if not self.drive_service:
            print("[Module7] Google Driveサービスが初期化されていません")
            return None

        if not image_path.exists():
            print(f"[Module7] エラー: 画像が見つかりません: {image_path}")
            return None

        try:
            # 画像をアップロード
            file_metadata = {
                "name": image_path.name,
                "parents": [folder_id]
            }
            media = MediaFileUpload(str(image_path), mimetype='image/png')

            result = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True
            ).execute()

            file_id = result.get("id")
            print(f"[Module7] Driveアップロード成功: {file_id}")

            # 公開設定
            self.drive_service.permissions().create(
                fileId=file_id,
                body={
                    "role": "reader",
                    "type": "anyone"
                },
                supportsAllDrives=True
            ).execute()

            # 公開URLを取得
            file_info = self.drive_service.files().get(
                fileId=file_id,
                fields="webViewLink",
                supportsAllDrives=True
            ).execute()

            public_url = file_info.get("webViewLink")
            print(f"[Module7] 公開URL取得: {public_url}")
            return public_url

        except Exception as e:
            print(f"[Module7] Driveアップロードエラー: {e}")
            return None

    def upload_image_to_facebook(self, image_path: Path, page_id: str) -> Optional[str]:
        """画像をFacebookにアップロードしてURLを取得"""
        if not image_path.exists():
            print(f"[Module7] エラー: 画像が見つかりません: {image_path}")
            return None

        upload_url = f"{self.API_BASE}/{page_id}/photos"

        with open(image_path, "rb") as f:
            files = {"file": f}
            params = {
                "access_token": self.access_token,
                "published": "false",  # タイムラインに投稿しない
            }

            response = requests.post(upload_url, files=files, params=params)

        if response.status_code != 200:
            print(f"[Module7] Facebookアップロードエラー: {response.text}")
            return None

        result = response.json()
        # 画像URLを取得
        image_url = result.get("url")
        if not image_url:
            # 別の方法でURLを取得
            photo_id = result.get("id")
            if photo_id:
                url = f"{self.API_BASE}/{photo_id}?fields=images&access_token={self.access_token}"
                r = requests.get(url)
                photo_data = r.json()
                images = photo_data.get("images", [])
                if images:
                    image_url = images[0].get("source")

        print(f"[Module7] Facebookアップロード成功: {image_url[:50]}...")
        return image_url

    def upload_image(self, image_path: Path, page_id: str = "1122938317560156") -> Optional[str]:
        """画像をInstagramにアップロードしてmedia IDを取得"""
        if not image_path.exists():
            print(f"[Module7] エラー: 画像が見つかりません: {image_path}")
            return None

        # Google Driveにアップロードして公開URLを取得
        image_url = self.upload_to_drive_and_get_url(image_path)
        if not image_url:
            print("[Module7] Driveアップロード失敗、Facebookアップロードを試行")
            return None

        # Instagram Graph API v18.0: image_urlパラメータで投稿
        upload_url = f"{self.API_BASE}/{self.instagram_account_id}/media"

        params = {
            "access_token": self.access_token,
            "image_url": image_url,
            "media_type": "IMAGE",
        }

        response = requests.post(upload_url, params=params)

        if response.status_code != 200:
            print(f"[Module7] Instagramアップロードエラー: {response.text}")
            return None

        result = response.json()
        media_id = result.get("id")
        print(f"[Module7] Instagramアップロード成功: media_id={media_id}")
        return media_id

    def upload_carousel(self, image_paths: list[Path]) -> Optional[list[str]]:
        """複数画像をアップロードしてカルーセル用のmedia IDリストを取得"""
        media_ids = []

        for image_path in image_paths:
            media_id = self.upload_image(image_path)
            if media_id:
                media_ids.append(media_id)
            else:
                print(f"[Module7] 警告: {image_path} のアップロードに失敗")

        if not media_ids:
            print("[Module7] エラー: 画像が1つもアップロードできませんでした")
            return None

        return media_ids

    def create_carousel_container(self, media_ids: list[str], caption: str) -> Optional[str]:
        """カルーセルコンテナを作成"""
        if len(media_ids) < 2:
            print("[Module7] エラー: カルーセルには2枚以上の画像が必要です")
            return None

        carousel_url = f"{self.API_BASE}/{self.instagram_account_id}/media"

        params = {
            "access_token": self.access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(media_ids),
            "caption": caption,
        }

        response = requests.post(carousel_url, params=params)

        if response.status_code != 200:
            print(f"[Module7] カルーセル作成エラー: {response.text}")
            return None

        result = response.json()
        container_id = result.get("id")
        print(f"[Module7] カルーセルコンテナ作成成功: {container_id}")
        return container_id

    def publish_media(self, creation_id: str) -> bool:
        """メディアを公開"""
        publish_url = f"{self.API_BASE}/{self.instagram_account_id}/media_publish"

        params = {
            "access_token": self.access_token,
            "creation_id": creation_id,
        }

        response = requests.post(publish_url, params=params)

        if response.status_code != 200:
            print(f"[Module7] 公開エラー: {response.text}")
            return False

        result = response.json()
        media_id = result.get("id")
        print(f"[Module7] 投稿成功: media_id={media_id}")
        return True

    def schedule_carousel(
        self,
        image_paths: list[Path],
        caption: str,
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        """カルーセルを投稿または予約"""
        # 画像をアップロード
        media_ids = self.upload_carousel(image_paths)
        if not media_ids:
            return False

        # カルーセルコンテナを作成
        creation_id = self.create_carousel_container(media_ids, caption)
        if not creation_id:
            return False

        # 即時公開または予約
        if schedule_time:
            # 予約投稿
            scheduled_publish_time = int(schedule_time.timestamp())

            # 予約投稿用にコンテナを更新
            update_url = f"{self.API_BASE}/{creation_id}"
            params = {
                "access_token": self.access_token,
                "scheduled_publish_time": scheduled_publish_time,
                "published": "false",
            }

            response = requests.post(update_url, params=params)

            if response.status_code != 200:
                print(f"[Module7] 予約設定エラー: {response.text}")
                return False

            print(f"[Module7] 予約投稿設定成功: {schedule_time.isoformat()}")
            return True
        else:
            # 即時公開
            return self.publish_media(creation_id)

    def publish_single(
        self,
        image_path: Path,
        caption: str,
        schedule_time: Optional[datetime] = None,
    ) -> bool:
        """単一画像を投稿または予約"""
        # 画像をアップロード
        media_id = self.upload_image(image_path)
        if not media_id:
            return False

        if schedule_time:
            # 予約投稿
            update_url = f"{self.API_BASE}/{media_id}"
            params = {
                "access_token": self.access_token,
                "scheduled_publish_time": int(schedule_time.timestamp()),
                "published": "false",
                "caption": caption,
            }

            response = requests.post(update_url, params=params)

            if response.status_code != 200:
                print(f"[Module7] 予約設定エラー: {response.text}")
                return False

            print(f"[Module7] 予約投稿設定成功: {schedule_time.isoformat()}")
            return True
        else:
            # 即時公開
            return self.publish_media(media_id)


def main():
    parser = argparse.ArgumentParser(description="Instagram自動投稿")
    parser.add_argument(
        "--episode-dir",
        required=True,
        help="エピソードディレクトリ（4コマ画像とinstagram_post.txtを含む）",
    )
    parser.add_argument(
        "--combined-image",
        help="結合済み4コマ画像のパス（単一画像投稿時）",
    )
    parser.add_argument(
        "--schedule",
        help="予約投稿時間（ISO 8601形式、例: 2024-01-15T10:00:00）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には投稿せず、投稿内容を表示のみ",
    )
    args = parser.parse_args()

    # 環境変数から認証情報を取得
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    instagram_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not access_token or not instagram_account_id:
        print("[Module7] エラー: 環境変数が設定されていません")
        print("  - INSTAGRAM_ACCESS_TOKEN")
        print("  - INSTAGRAM_ACCOUNT_ID")
        print("\n[Module7] Meta for Developersでアプリを作成し、")
        print("Instagram Graph APIのアクセストークンを取得してください。")
        sys.exit(1)

    # エピソードディレクトリを確認
    episode_dir = Path(args.episode_dir)
    if not episode_dir.exists():
        print(f"[Module7] エラー: ディレクトリが見つかりません: {episode_dir}")
        sys.exit(1)

    # 投稿情報を読み込み（JSON優先、txtはフォールバック）
    json_path = episode_dir / "instagram_post.json"
    txt_path = episode_dir / "instagram_post.txt"
    
    post_data = None
    if json_path.exists():
        # JSON形式で読み込み
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
            print(f"[Module7] JSON形式で投稿情報を読み込み成功: {json_path}")
        except json.JSONDecodeError as e:
            print(f"[Module7] JSON解析エラー: {e}")
    
    if post_data is None:
        # 従来のtxt形式で読み込み
        if not txt_path.exists():
            print(f"[Module7] エラー: キャプションファイルが見つかりません")
            print(f"  - {json_path} (推奨)")
            print(f"  - {txt_path} (フォールバック)")
            sys.exit(1)
        
        caption = txt_path.read_text(encoding="utf-8")
        print(f"[Module7] TXT形式でキャプション読み込み成功 ({len(caption)} 文字)")
        post_data = {
            "caption": caption,
            "hashtags": [],
            "images": [],
            "schedule_time": None
        }
    else:
        # JSONからキャプションとハッシュタグを構築
        caption = post_data.get("caption", "")
        hashtags = post_data.get("hashtags", [])
        if hashtags:
            caption += "\n\n" + " ".join(hashtags)
        print(f"[Module7] キャプション構築成功 ({len(caption)} 文字)")

    # 予約時間をパース
    schedule_time = None
    if args.schedule:
        schedule_time = datetime.fromisoformat(args.schedule)
        # UTCに変換（Meta APIはUTCを期待）
        schedule_time = schedule_time.replace(tzinfo=None)
        print(f"[Module7] 予約投稿時刻: {schedule_time.isoformat()}")

    # 画像を収集
    json_images = post_data.get("images", [])
    
    if args.combined_image:
        # 単一画像投稿（CLI引数優先）
        image_path = Path(args.combined_image)
        image_paths = [image_path]
    elif json_images:
        # JSONで指定された画像リストを使用
        image_paths = [episode_dir / img for img in json_images]
        # 存在しない画像をチェック
        missing = [p for p in image_paths if not p.exists()]
        if missing:
            print(f"[Module7] エラー: 以下の画像が見つかりません:")
            for p in missing:
                print(f"  - {p}")
            sys.exit(1)
    else:
        # 個別パネル投稿（自動検出）
        image_paths = sorted(episode_dir.glob("4koma_panel_*.png"))
        if not image_paths:
            print("[Module7] エラー: 画像が見つかりません")
            sys.exit(1)

    print(f"[Module7] 投稿画像: {len(image_paths)} 枚")
    for p in image_paths:
        print(f"  - {p.name}")

    if args.dry_run:
        print("\n[Module7] === DRY RUN MODE ===")
        print(f"投稿内容:\n{caption[:200]}...")
        print(f"\n画像数: {len(image_paths)}")
        if schedule_time:
            print(f"予約時刻: {schedule_time.isoformat()}")
        else:
            print("即時投稿")
        print("\n[Module7] 実際の投稿は行われませんでした")
        return

    # 投稿実行
    publisher = InstagramPublisher(access_token, instagram_account_id)

    if len(image_paths) == 1:
        # 単一画像投稿
        success = publisher.publish_single(image_paths[0], caption, schedule_time)
    else:
        # カルーセル投稿
        success = publisher.schedule_carousel(image_paths, caption, schedule_time)

    if success:
        print("\n[Module7] 投稿処理完了")
    else:
        print("\n[Module7] 投稿処理失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
