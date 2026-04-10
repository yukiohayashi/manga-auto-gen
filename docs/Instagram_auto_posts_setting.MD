# Instagram自動投稿設定完全ガイド

Meta Graph APIとGoogle Driveを連携して、Instagramへ自動投稿（コンテンツ公開）を行うための設定方法です。

---

## 概要

本システムは以下の構成でInstagram自動投稿を実現します：

1. **Google Drive**: 画像をホスティングし、公開URLを取得
2. **Meta Graph API**: Instagram Graph APIを使用して投稿
3. **環境変数**: API認証情報を管理

---

## 【重要】前提条件

### Instagram Graph API利用の必須条件

Instagramアカウント単体ではAPIを利用できません。以下の設定が完了している状態からスタートしてください：

1. **Instagramアカウントのプロアカウント化**
   - ビジネスアカウントまたはクリエイターアカウントに変更

2. **Facebookページの作成**
   - API連携の裏側として使用
   - 非公開や作り込んでいないページでも構いません

3. **InstagramアカウントとFacebookページのリンク（紐付け）**
   - Facebookページの設定 →「リンク済みのアカウント」→「Instagram」
   - 対象のInstagramアカウントへログインして紐付けを完了

4. **管理者権限**
   - アプリの設定を行うFacebookアカウントは、紐付けたFacebookページの管理者権限を持っている必要があります

---

## 手順1：Metaアプリに必須の権限を追加

Meta for Developersの「マイアプリ」から対象のアプリを開き、自動投稿に必要な権限をアプリに持たせます。

1. アプリのダッシュボード左メニューから「ユースケース」を開きます
2. 「Instagramでメッセージとコンテンツを管理」などのユースケースを選択し、「カスタマイズ」ボタンを押します
3. 左メニューの「アクセス許可と機能」をクリックします
4. 画面内の検索窓（虫眼鏡マーク）を使用して以下の権限を追加：
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`

---

## 手順2：Google Drive APIの設定

### 2-1. Google Cloud Consoleでプロジェクト設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクト `manga-auto-gen-drive-sync` を選択
3. **「APIとサービス」** → **「ライブラリ」** → **「Google Drive API」** を有効化

### 2-2. サービスアカウントの作成

1. **「IAMと管理」** → **「サービスアカウント」**
2. **「サービスアカウントを作成」**
   - 名前: `manga-auto-gen-drive-sync`
   - 説明: `Instagram自動投稿用画像ホスティング`
3. **「キー」** タブ → **「鍵を追加」** → **「新しい鍵を作成」**
   - キータイプ: **JSON**
   - JSONファイルがダウンロードされます（`sound-inn-432007-s0-...json`）

### 2-3. 共有ドライブの作成と設定

組織ポリシーでサービスアカウントの通常ドライブアクセスが制限されている場合、**共有ドライブ**を使用します：

1. [Google Drive](https://drive.google.com/) を開く
2. **左メニュー** → **「共有ドライブ」**
3. **「新しい共有ドライブ」** を作成
   - 名前: `new-manga-auto-gen`
4. 作成した共有ドライブを右クリック → **「共有」**
5. サービスアカウントを追加：
   - `manga-auto-gen-drive-sync@sound-inn-432007-s0.iam.gserviceaccount.com`
   - 権限: **「編集者」**

### 2-4. フォルダ構造の確認

自動投稿対象の画像フォルダ構造：

```
共有ドライブ: new-manga-auto-gen (ID: 0AMAG-90UJ_uqUk9PVA)
├── output-episodes/
│   ├── 彼はサイコパス？/ (ID: 1DyM1j8gMDruReBqzdUuxnYfRaYNHHNuc)
│   │   ├── 4koma_panel_01.png
│   │   ├── 4koma_panel_02.png
│   │   ├── 4koma_panel_03.png
│   │   └── 4koma_panel_04.png
│   └── ...
```

**重要フォルダID**:
- 共有ドライブルート: `0AMAG-90UJ_uqUk9PVA`
- 「彼はサイコパス？」フォルダ: `1DyM1j8gMDruReBqzdUuxnYfRaYNHHNuc`

---

## 手順3：環境変数の設定

### 3-1. `.env` ファイルの作成

プロジェクトルートに `.env` ファイルを作成し、以下を設定：

```bash
# Meta Graph API認証
INSTAGRAM_ACCESS_TOKEN='EAANu3r737y8B...（ページアクセストークン）'
INSTAGRAM_ACCOUNT_ID='17841407672340828'

# Google Drive認証（JSONファイルの内容を1行で記載）
GOOGLE_DRIVE_CREDENTIALS='{"type": "service_account", "project_id": "sound-inn-432007-s0", ...}'

# 共有ドライブ設定
SHARED_DRIVE_ID='0AMAG-90UJ_uqUk9PVA'
TARGET_FOLDER_ID='1DyM1j8gMDruReBqzdUuxnYfRaYNHHNuc'
```

### 3-2. 認証情報の取得方法

**Instagram Access Tokenの取得**:
1. [Meta for Developers](https://developers.facebook.com/tools/explorer/) のGraph API Explorerにアクセス
2. アプリを選択 → **「ページアクセストークンを取得」**
3. 必要な権限を選択：
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
4. **「アクセストークン」** をコピーして `.env` に貼り付け

**Google Drive Credentialsの設定**:
1. ダウンロードしたJSONファイルを開く
2. 内容を1行に変換（改行を削除）
3. `.env` の `GOOGLE_DRIVE_CREDENTIALS` に貼り付け

---

## 手順4：自動投稿の実行

### 4-1. テスト投稿（単一画像）

```bash
# 環境変数を読み込んで実行
export INSTAGRAM_ACCESS_TOKEN='（トークン）'
export INSTAGRAM_ACCOUNT_ID='17841407672340828'
export GOOGLE_DRIVE_CREDENTIALS='（JSON内容）'

python3 src/module7_instagram_publisher.py \
  --episode-dir 'output-episodes/彼はサイコパス？' \
  --combined-image 'output-episodes/彼はサイコパス？/4koma_panel_01.png'
```

### 4-2. カルーセル投稿（複数画像）

```bash
python3 src/module7_instagram_publisher.py \
  --episode-dir 'output-episodes/彼はサイコパス？'
```

### 4-3. 予約投稿

```bash
python3 src/module7_instagram_publisher.py \
  --episode-dir 'output-episodes/彼はサイコパス？' \
  --schedule '2024-01-15T10:00:00+09:00'
```

---

## トラブルシューティング

### エラー1: `Service Accounts do not have storage quota`

**原因**: 組織ポリシーでサービスアカウントの通常ドライブアクセスが制限されている

**解決策**: 
- 共有ドライブを使用（本ガイドの手順2-3を参照）
- または、Google Workspace管理者にサービスアカウントのドライブアクセス許可を依頼

### エラー2: `image_url is required`

**原因**: Instagram Graph API v18.0で、画像をURLで指定する必要がある

**解決策**:
- Google Driveに画像をアップロードして公開URLを取得（本システムで自動処理）
- または、Imgurなどの外部ホスティングサービスを使用

### エラー3: `(#200) Unpublished posts must be posted to a page as the page itself`

**原因**: Facebookページに投稿する際、ページアクセストークンが必要

**解決策**:
- ユーザーアクセストークンではなく、ページアクセストークンを使用
- Graph API Explorerで「ページアクセストークンを取得」を選択

---

## 関連ファイル

- `src/module7_instagram_publisher.py`: Instagram投稿メインスクリプト
- `src/module5_drive_sync.py`: Google Drive同期モジュール
- `run.sh`: 統合実行スクリプト（`--publish` オプションでInstagram投稿）

---

## 参考リンク

- [Instagram Graph API公式ドキュメント](https://developers.facebook.com/docs/instagram-api)
- [Google Drive API公式ドキュメント](https://developers.google.com/drive/api)
- [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/)
- [Google Cloud Console](https://console.cloud.google.com/)