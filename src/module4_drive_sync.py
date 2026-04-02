#!/usr/bin/env python3
"""
モジュール4：Google Drive 自動同期・アセット管理

機能:
1. 生成された画像やログをGoogle Drive上のエピソード別フォルダに自動アップロード
2. キャラクター素材（hana.png等）をDriveから取得
3. ストーリーフォルダの存在確認（プリフライトチェック用）

必ず親フォルダIDを指定し、マイドライブ直下への誤保存を防止する。
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io


# 必須：親フォルダID（manga-auto-genフォルダ）
# ⚠️ この値は絶対に変更しないこと
REQUIRED_PARENT_FOLDER_ID = "1KjFd6ImfHBivg4SEWfrZzKekVaj7N80b"

# 登録済みファイルインデックス（manga_spec.yml準拠）
REGISTERED_FILES = {
    "manga_spec.yml": "1oET1V34HPCDcgxqRzpXZ5ZSA9fO5WsxH",
    "hana.png": "1Szs4wPmo_-en3iWlo4XlfkOJPTmAV_y2",
    "saki.png": "1FUdszNEBTNWclsuy1g8PxACqQC2FijQo",
    "masato.png": "1ooIUb1iYOZBAHowkjPwMBGy08EmblyKn",
    "tomoya.png": "1gt4a9_wbPYcVfjj4GDXaknnekiYMfuf8",
    "yota.png": "1Vg_ZvcbdwUxTH9CcnAZ4OT4zVlPWPeaE",
    "reference_4koma.png": "1rh-477oeOOEuFmvIoZ0WKrd4uKdNuGxx",
    "successful_panel_4.png": "1fnSNJ3u7PbdBHspYpYMLiy3mjPnhMDTj",
    "preflight_check.py": "1DXrInNDgPgV8DAA8Rr6nqdlcavWMDa5t",
}


class DriveSync:
    """Google Drive同期クラス"""

    def __init__(self, parent_folder_id: str):
        if parent_folder_id != REQUIRED_PARENT_FOLDER_ID:
            raise ValueError(
                f"親フォルダIDが不正です。"
                f"期待値: {REQUIRED_PARENT_FOLDER_ID}, "
                f"受信値: {parent_folder_id}"
            )
        self.parent_folder_id = parent_folder_id
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """認証情報の検証とDriveサービスの初期化"""
        creds_json = os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
        if not creds_json:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable is not set")
        
        creds_data = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_data,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=credentials)
        print("[Module4] Google Drive認証情報を確認しました")

    def create_episode_folder(self, episode_name: str) -> str:
        """エピソードフォルダを作成（必ず親フォルダID指定）"""
        print(f"[Module4] エピソードフォルダ作成: {episode_name}")
        
        # 既存フォルダの確認
        query = (
            f'name="{episode_name}" and '
            f'"{self.parent_folder_id}" in parents and '
            f'mimeType="application/vnd.google-apps.folder" and '
            f'trashed=false'
        )
        
        result = self.service.files().list(q=query, fields="files(id, name)").execute()
        files = result.get("files", [])
        if files:
            folder_id = files[0]["id"]
            print(f"[Module4] 既存フォルダを使用: {folder_id}")
            return folder_id
        
        # 新規作成（必ずparentsを指定）
        metadata = {
            "name": episode_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [self.parent_folder_id]  # ⚠️ 必須
        }
        
        result = self.service.files().create(body=metadata, fields="id").execute()
        folder_id = result.get("id")
        if not folder_id:
            raise RuntimeError("フォルダ作成に失敗しました")
        
        print(f"[Module4] 新規フォルダ作成: {folder_id}")
        
        # 作成後の検証
        self._verify_folder_location(folder_id, episode_name)
        
        return folder_id

    def check_story_folder_exists(self, story_name: str) -> dict:
        """
        ストーリーフォルダの存在確認（プリフライトチェック STEP 2 用）
        
        Args:
            story_name: ストーリー名
        
        Returns:
            {"exists": bool, "folder_id": str or None, "files": list}
        """
        print(f"[Module4] ストーリーフォルダ検索: {story_name}")
        
        query = (
            f'name="{story_name}" and '
            f'mimeType="application/vnd.google-apps.folder" and '
            f'trashed=false'
        )
        
        result = self.service.files().list(q=query, fields="files(id, name)").execute()
        
        folders = result.get("files", [])
        if not folders:
            print(f"[Module4] フォルダが見つかりません: {story_name}")
            return {"exists": False, "folder_id": None, "files": []}
        
        folder_id = folders[0]["id"]
        print(f"[Module4] フォルダ発見: {folder_id}")
        
        # フォルダ内のファイル一覧を取得
        files_query = f'"{folder_id}" in parents and trashed=false'
        files_result = self.service.files().list(q=files_query, fields="files(id, name)").execute()
        
        files = files_result.get("files", [])
        print(f"[Module4] フォルダ内ファイル数: {len(files)}")
        
        return {
            "exists": True,
            "folder_id": folder_id,
            "files": [f.get("name") for f in files]
        }

    def download_registered_file(self, filename: str, output_path: Path) -> bool:
        """
        登録済みファイルをダウンロード（キャラクター素材取得用）
        
        Args:
            filename: ファイル名（REGISTERED_FILESに登録されている必要あり）
            output_path: 保存先パス
        
        Returns:
            成功したかどうか
        """
        if filename not in REGISTERED_FILES:
            print(f"[Module4] エラー: 未登録のファイル: {filename}")
            return False
        
        file_id = REGISTERED_FILES[filename]
        print(f"[Module4] ダウンロード: {filename} (ID: {file_id})")
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())
            
            print(f"[Module4] ダウンロード完了: {output_path}")
            return True
        except Exception as e:
            print(f"[Module4] ダウンロード失敗: {e}")
            return False

    def download_all_character_assets(self, output_dir: Path) -> dict:
        """
        全キャラクター素材をダウンロード
        
        Args:
            output_dir: 保存先ディレクトリ
        
        Returns:
            {"success": list, "failed": list}
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        character_files = ["hana.png", "saki.png", "masato.png", "tomoya.png", "yota.png"]
        success = []
        failed = []
        
        for filename in character_files:
            output_path = output_dir / filename
            if self.download_registered_file(filename, output_path):
                success.append(filename)
            else:
                failed.append(filename)
        
        print(f"[Module4] キャラクター素材: 成功 {len(success)}, 失敗 {len(failed)}")
        return {"success": success, "failed": failed}

    def download_all_reference_assets(self, output_dir: Path) -> dict:
        """
        全参照用素材をダウンロード
        
        Args:
            output_dir: 保存先ディレクトリ
        
        Returns:
            {"success": list, "failed": list}
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reference_files = ["reference_4koma.png", "successful_panel_4.png"]
        success = []
        failed = []
        
        for filename in reference_files:
            output_path = output_dir / filename
            if self.download_registered_file(filename, output_path):
                success.append(filename)
            else:
                failed.append(filename)
        
        print(f"[Module4] 参照用素材: 成功 {len(success)}, 失敗 {len(failed)}")
        return {"success": success, "failed": failed}

    def _verify_folder_location(self, folder_id: str, expected_name: str) -> None:
        """フォルダが正しい場所に作成されたか検証"""
        query = (
            f'"{self.parent_folder_id}" in parents and '
            f'name="{expected_name}" and '
            f'trashed=false'
        )
        
        result = self.service.files().list(q=query, fields="files(id, name)").execute()
        
        files = result.get("files", [])
        found = any(f.get("id") == folder_id for f in files)
        
        if not found:
            raise RuntimeError(
                f"フォルダが正しい場所に作成されていません。"
                f"フォルダID: {folder_id}, 親フォルダID: {self.parent_folder_id}"
            )
        
        print(f"[Module4] フォルダ位置検証OK: {folder_id}")

    def upload_file(self, local_path: Path, folder_id: str) -> str:
        """ファイルをアップロード（必ず親フォルダID指定）"""
        print(f"[Module4] アップロード: {local_path.name}")
        
        metadata = {
            "name": local_path.name,
            "parents": [folder_id]  # ⚠️ 必須
        }
        
        media = MediaFileUpload(str(local_path), resumable=True)
        result = self.service.files().create(body=metadata, media_body=media, fields="id").execute()
        
        file_id = result.get("id")
        if not file_id:
            raise RuntimeError(f"アップロード失敗: {local_path}")
        
        print(f"[Module4] アップロード完了: {file_id}")
        return file_id

    def sync_folder(self, source_dir: Path, episode_name: str) -> dict:
        """フォルダ全体を同期"""
        print(f"[Module4] 同期開始: {source_dir} → {episode_name}")
        
        # エピソードフォルダ作成
        folder_id = self.create_episode_folder(episode_name)
        
        # ファイルをアップロード
        uploaded_files = {}
        for file_path in source_dir.iterdir():
            if file_path.is_file():
                file_id = self.upload_file(file_path, folder_id)
                uploaded_files[file_path.name] = file_id
        
        result = {
            "episode_name": episode_name,
            "folder_id": folder_id,
            "parent_folder_id": self.parent_folder_id,
            "uploaded_files": uploaded_files,
            "synced_at": datetime.now().isoformat(),
        }
        
        print(f"[Module4] 同期完了: {len(uploaded_files)}ファイル")
        return result


def main():
    parser = argparse.ArgumentParser(description="Google Drive同期")
    parser.add_argument("--source", required=True, help="同期元フォルダ")
    parser.add_argument("--parent-folder-id", required=True, help="親フォルダID")
    parser.add_argument("--episode-name", required=True, help="エピソード名")
    args = parser.parse_args()

    # 親フォルダIDの検証
    if args.parent_folder_id != REQUIRED_PARENT_FOLDER_ID:
        print(f"[Module4] エラー: 親フォルダIDが不正です")
        print(f"  期待値: {REQUIRED_PARENT_FOLDER_ID}")
        print(f"  受信値: {args.parent_folder_id}")
        exit(1)

    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"[Module4] エラー: 同期元フォルダが存在しません: {source_dir}")
        exit(1)

    # 同期実行
    syncer = DriveSync(args.parent_folder_id)
    result = syncer.sync_folder(source_dir, args.episode_name)

    # 結果をログファイルに保存
    log_path = source_dir / "drive_sync_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"[Module4] 同期ログ保存: {log_path}")


if __name__ == "__main__":
    main()
