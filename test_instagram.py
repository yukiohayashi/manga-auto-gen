import os
import json
import requests
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 認証情報
access_token = 'EAANu3r737y8BRGF35fZAydwBU0yZAVzKhcZCHzb760Mvk9JDypixaItDHqUYrqtfe01hQch6Gd93jN6QcvVwZBCqJ8rTHHSDHJ9RXfQtWpqlzhAQTCZAzlU1jScrDT5CexfzhgNZC01ckVOrw3ZA7Vy5yFVkcgXaGcM8gSxusdLj3oogdoTkZAy5x5JyM30KqLiciGS7nuIjG7jKwIpbRcckXDjcuKyecY7pwU30G97ph89YqL6DKrc2VhL3bySQC1YyZBFDg0gPcxoibKtxW7KVUwBxsYWuKPnnb0QZDZD'
instagram_account_id = '17841407672340828'
shared_drive_id = '0AMAG-90UJ_uqUk9PVA'
image_path = Path('output-episodes/彼はサイコパス？/4koma_panel_01.png')

# Google Drive認証
creds_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
creds_data = json.loads(creds_json)
credentials = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=['https://www.googleapis.com/auth/drive']
)
drive_service = build('drive', 'v3', credentials=credentials)
print('[Test] Google Drive認証成功')

# 共有ドライブに画像をアップロード
file_metadata = {
    "name": image_path.name,
    "parents": [shared_drive_id]
}
media = MediaFileUpload(str(image_path), mimetype='image/png')

result = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    fields="id, webViewLink",
    supportsAllDrives=True
).execute()

file_id = result.get("id")
print(f'[Test] Driveアップロード成功: {file_id}')

# 公開設定
drive_service.permissions().create(
    fileId=file_id,
    body={"role": "reader", "type": "anyone"},
    supportsAllDrives=True
).execute()

# 公開URL取得
file_info = drive_service.files().get(
    fileId=file_id,
    fields="webContentLink",
    supportsAllDrives=True
).execute()

image_url = file_info.get("webContentLink")
print(f'[Test] 公開URL: {image_url}')

# Instagram投稿
upload_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/media'
params = {
    'access_token': access_token,
    'image_url': image_url,
    'media_type': 'IMAGE',
}
response = requests.post(upload_url, params=params)
print(f'[Test] Instagramレスポンス: {response.json()}')
