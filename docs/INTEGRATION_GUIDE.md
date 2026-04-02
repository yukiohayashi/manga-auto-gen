# GitHub + Google Drive 連携ガイド

**最終更新**: 2026-04-02

## 概要

4コマ漫画自動生成システムでは、**GitHub**と**Google Drive**の両方を連携させる必要があります。

```
┌─────────────────────────────────────────────────────────────────┐
│                    4コマ漫画自動生成システム                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐              ┌─────────────────┐         │
│   │    GitHub       │              │  Google Drive   │         │
│   │  (コード管理)    │              │  (素材/成果物)   │         │
│   └────────┬────────┘              └────────┬────────┘         │
│            │                                │                   │
│            ▼                                ▼                   │
│   ┌─────────────────────────────────────────────────────┐      │
│   │              GitHub Actions Runner                  │      │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │      │
│   │  │Module 1 │→│Module 2 │→│Module 3 │→│Module 4 │→│M5│     │
│   │  │シナリオ  │ │検証     │ │画像生成  │ │Drive同期 │ │SNS│    │
│   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │      │
│   └─────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ディレクトリ構成

```
manga-auto-gen/
├── .github/workflows/
│   └── daily_manga_gen.yml        # CI/CD定期実行（毎日JST 9:00）
├── src/
│   ├── module1_scenario_gen.py    # シナリオ生成（Gemini API）
│   ├── module2_preflight_check.py # プリフライト検証・テキスト補正
│   ├── module3_image_gen.py       # 画像生成・レイアウト描画
│   ├── module4_drive_sync.py      # Google Drive同期・素材取得
│   ├── module5_sns_publisher.py   # Instagram投稿文生成
│   └── bubble_renderer.py         # 吹き出し自動描画モジュール
├── config/
│   ├── manga_spec.yml             # 制作ルール・描画指示
│   ├── PlotTwist_plain.txt        # どんでん返し10パターン定義
│   └── instagram_marketing_strategy.md
├── characters/                    # キャラクター表情シート
│   ├── INDEX.md                   # Gemini用インデックス
│   └── hana.png, saki.png, ...
├── references/                    # 参照用素材
│   ├── INDEX.md                   # Gemini用インデックス
│   ├── reference_4koma.png        # 4コマ全体のスタイル参照
│   └── successful_panel_4.png     # オチの成功例
├── docs/
│   └── INTEGRATION_GUIDE.md       # 本ドキュメント
└── episodes/                      # 出力先（日付別フォルダ）
```

---

## 役割分担

### GitHub（コード管理・実行指示）

| 管理対象 | 説明 |
|---------|------|
| `src/*.py` | シナリオ生成、検証、画像生成、同期のPythonスクリプト |
| `.github/workflows/*.yml` | GitHub Actionsの定期実行スケジュール |
| `config/*.yml`, `*.txt`, `*.md` | 設定ファイル（テキストベース） |
| `characters/`, `references/` | キャラクター・参照素材（INDEX.md付き） |

### Google Drive（素材保管庫・成果物納品先）

| 管理対象 | 説明 |
|---------|------|
| `hana.png`, `saki.png` 等 | キャラクター表情シート（マスター） |
| `reference_4koma.png` | 参照用4コマ画像 |
| `successful_panel_4.png` | オチ（4コマ目）の成功例 |
| `episodes/YYYYMMDD/` | 生成された4コマ漫画の納品先 |
| `manga_spec.yml` (バックアップ) | Drive上のマスターコピー |

---

## Google Drive 連携が必須な3つの理由

### 1. プリフライトチェックでDrive検索が必須

`preflight_check.py` の STEP 2 では、画像生成前に以下のコマンドでDriveを検索します：

```bash
gws drive files list --params '{"q": "name=\"[ストーリー名]\" and mimeType=\"application/vnd.google-apps.folder\" and trashed=false"}'
```

- フォルダが存在する場合 → 既存素材を参照・リメイク元として使用
- フォルダが存在しない場合 → 新規ストーリーとして生成

**Driveが接続されていなければ、この必須チェックを通過できません。**

### 2. キャラクター素材・参照素材がDrive上で管理されている

以下のファイルは、Drive上で特定のファイルIDとして厳密にインデックス化されています：

#### キャラクター素材（`characters/`）

| ファイル名 | ファイルID | 用途 |
|-----------|-----------|------|
| `hana.png` | `1Szs4wPmo_-en3iWlo4XlfkOJPTmAV_y2` | 主人公・はな |
| `saki.png` | `1FUdszNEBTNWclsuy1g8PxACqQC2FijQo` | 友人・さき |
| `masto.png` | `1ooIUb1iYOZBAHowkjPwMBGy08EmblyKn` | 彼氏・まさと |
| `tomoya.png` | `1gt4a9_wbPYcVfjj4GDXaknnekiYMfuf8` | 友人・ともや |
| `yota.png` | `1Vg_ZvcbdwUxTH9CcnAZ4OT4zVlPWPeaE` | 弟・YOTA |

#### 参照用素材（`references/`）

| ファイル名 | ファイルID | 用途 |
|-----------|-----------|------|
| `reference_4koma.png` | `1rh-477oeOOEuFmvIoZ0WKrd4uKdNuGxx` | 4コマ全体のスタイル参照 |
| `successful_panel_4.png` | `1fnSNJ3u7PbdBHspYpYMLiy3mjPnhMDTj` | オチ（4コマ目）の成功例 |

#### 設定ファイル

| ファイル名 | ファイルID | 用途 |
|-----------|-----------|------|
| `manga_spec.yml` | `1oET1V34HPCDcgxqRzpXZ5ZSA9fO5WsxH` | 制作ルール（マスター） |
| `preflight_check.py` | `1DXrInNDgPgV8DAA8Rr6nqdlcavWMDa5t` | 検証スクリプト（アーカイブ） |

### 3. 成果物の保存先ルールが厳格

2026年4月2日の同期失敗を受け、以下のルールが必須化されています：

```
⚠️ 必須遵守ルール
新規フォルダ作成・アップロード時は必ず parents 属性に
親フォルダID を強制付与すること

親フォルダID: 1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_
パス: パソコン > マイ Mac > manga-auto-gen
```

---

## 連携設定手順

### Step 1: GitHub リポジトリの準備

1. `manga-auto-gen` フォルダをGitHubリポジトリとして初期化
   ```bash
   cd manga-auto-gen
   git init
   git add .
   git commit -m "Initial commit: 4コマ漫画自動生成システム"
   git remote add origin https://github.com/[username]/manga-auto-gen.git
   git push -u origin main
   ```

2. 以下のSecretsを設定（Settings → Secrets and variables → Actions）：

| Secret名 | 説明 |
|---------|------|
| `GEMINI_API_KEY` | Gemini API認証キー |
| `GOOGLE_DRIVE_CREDENTIALS` | サービスアカウントのJSON認証情報（Base64エンコード推奨） |

### Step 2: Google Drive API の有効化

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」→ **Google Drive API** を有効化
3. 「認証情報」→「サービスアカウントを作成」
4. サービスアカウントのJSONキーをダウンロード
5. サービスアカウントのメールアドレス（`xxx@xxx.iam.gserviceaccount.com`）に `manga-auto-gen` フォルダの**編集者**権限を付与

### Step 3: Gemini への接続

Gemini UIで以下を接続：

1. **GitHub リポジトリ** → コードの参照・実行指示
   - リポジトリをインポートし、`manga-auto-gen` を選択
2. **Google Drive** → 素材の取得・成果物の保存
   - `manga-auto-gen` フォルダへのアクセスを許可

### Step 4: キャラクター・参照素材の配置

GitHub側にも素材を配置（Gemini認識用）：

```bash
# Google Driveから素材をダウンロードして配置
manga-auto-gen/
├── characters/
│   ├── INDEX.md      # 必須：Gemini用インデックス
│   ├── hana.png
│   ├── saki.png
│   ├── masto.png
│   ├── tomoya.png
│   └── yota.png
└── references/
    ├── INDEX.md      # 必須：Gemini用インデックス
    ├── reference_4koma.png
    └── successful_panel_4.png
```

**重要**: `INDEX.md` があることで、Geminiがフォルダ内のファイルと役割を認識できます。

---

## ワークフロー実行時のデータフロー

```
[GitHub Actions 開始 - 毎日 JST 9:00 (UTC 0:00)]
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Module 1: シナリオ生成 (module1_scenario_gen.py)               │
│ - config/PlotTwist_plain.txt を読み込み（GitHub）               │
│ - Gemini API でどんでん返し10パターンからシナリオ生成            │
│ - episodes/YYYYMMDD/scenario.json を出力                       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Module 2: プリフライト検証 (module2_preflight_check.py)         │
│ - config/manga_spec.yml を読み込み（GitHub）                    │
│ - Google Drive でストーリーフォルダを検索 ★Drive連携必須         │
│ - 禁止名「あや」チェック、重複テキスト自動修正                    │
│ - episodes/YYYYMMDD/validated_scenario.json を出力             │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Module 3: 画像生成 (module3_image_gen.py + bubble_renderer.py) │
│ - characters/ からキャラクター画像を取得                         │
│ - references/ からスタイル参照画像を取得                         │
│ - Gemini API で画像生成                                         │
│ - 吹き出し自動描画（キャラ別色・形状、ツッコミ強調）              │
│ - episodes/YYYYMMDD/4koma_combined.png を出力                  │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Module 4: Google Drive 同期 (module4_drive_sync.py)            │
│ - 親フォルダID を必ず指定 ★Drive連携必須                         │
│ - エピソードフォルダを作成（YYYYMMDD）                           │
│ - 生成画像・ログをアップロード                                   │
│ - アップロード後の位置検証（誤保存防止）                          │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ Module 5: SNS投稿文生成 (module5_sns_publisher.py)             │
│ - config/instagram_marketing_strategy.md を読み込み（GitHub）   │
│ - Gemini API で投稿文生成（フック・CTA・ハッシュタグ）           │
│ - episodes/YYYYMMDD/instagram_caption.txt を出力               │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
[GitHub Actions 完了 → Artifacts に30日間バックアップ]
```

---

## 吹き出し描画ルール（manga_spec.yml準拠）

### キャラクター別吹き出しスタイル

| キャラクター | 吹き出し色 | 形状 |
|-------------|-----------|------|
| はな・さき（女性陣） | 黄色 `#FFE800` | 角ばった多角形（丸み禁止） |
| まさと・ともや・YOTA（男性陣） | パステルブルー `#D4E8FF` | 柔らかい多角形または楕円 |
| モノローグ・小声 | 白 `#FFFFFF` | 楕円形 |
| ツッコミ（オチ） | 黄色 `#FFE800` | ギザギザ爆発型 |

### ツッコミ強調ルール

- キーワードを **赤文字** `#FF0000`
- サイズは他より **1.2〜1.5倍** の大きさで強調

---

## トラブルシューティング

### Drive同期失敗時

1. `parents` 属性が正しく指定されているか確認
2. サービスアカウントに編集権限があるか確認
3. 親フォルダID `1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_` が正しいか確認
4. `module4_drive_sync.py` の `REQUIRED_PARENT_FOLDER_ID` を確認

### 素材が見つからない場合

1. `REGISTERED_FILES` のファイルIDが最新か確認（`module4_drive_sync.py`）
2. ファイルがゴミ箱に移動されていないか確認
3. `gws drive files get --file-id [ID]` でファイルの存在を確認

### Geminiがフォルダ内ファイルを認識しない場合

1. `characters/INDEX.md` と `references/INDEX.md` が存在するか確認
2. INDEX.md にファイル一覧と役割が記載されているか確認
3. 画像ファイルがフォルダ内に配置されているか確認

### プリフライトチェックでエラー

1. 禁止キャラクター名「あや」がシナリオに含まれていないか確認
2. セリフに固有名詞（はな、さき等）が含まれていないか確認
3. パネル数が4であるか確認

---

## 参照ドキュメント

| ドキュメント | 場所 | 説明 |
|-------------|------|------|
| `SPEC.md` | `manga-auto-gen/` | システム仕様書 |
| `manga_spec.yml` | `config/` | 制作ルール全体 |
| `PlotTwist_plain.txt` | `config/` | どんでん返し10パターン定義 |
| `instagram_marketing_strategy.md` | `config/` | SNS投稿戦略 |
| `characters/INDEX.md` | `characters/` | キャラクター素材インデックス |
| `references/INDEX.md` | `references/` | 参照素材インデックス |

---

## 更新履歴

| 日付 | 変更内容 |
|------|----------|
| 2026-04-02 | 初版作成 |
| 2026-04-02 | ディレクトリ構成更新（`characters/`, `references/` 追加） |
| 2026-04-02 | 吹き出し描画ルール追加、トラブルシューティング拡充 |

---

**END OF INTEGRATION GUIDE**
