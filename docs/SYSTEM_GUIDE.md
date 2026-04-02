# 4コマ漫画自動生成システム - 統合ガイド

**バージョン**: v1.0  
**最終更新**: 2026-04-02  
**リポジトリ**: https://github.com/yukiohayashi/manga-auto-gen

---

## 目次

1. [システム概要](#1-システム概要)
2. [ディレクトリ構成](#2-ディレクトリ構成)
3. [5つのコアモジュール](#3-5つのコアモジュール)
4. [キャラクター素材](#4-キャラクター素材)
5. [参照用素材](#5-参照用素材)
6. [吹き出し描画ルール](#6-吹き出し描画ルール)
7. [GitHub + Google Drive 連携](#7-github--google-drive-連携)
8. [セットアップ手順](#8-セットアップ手順)
9. [手動実行コマンド](#9-手動実行コマンド)
10. [Instagram マーケティング戦略](#10-instagram-マーケティング戦略)
11. [トラブルシューティング](#11-トラブルシューティング)
12. [更新履歴](#12-更新履歴)

---

## 1. システム概要

GitHub ActionsとGemini APIを活用し、**PlotTwistガイドの法則に則った4コマ漫画を毎日自動生成・検証・保存**し、Instagramへの投稿準備までを完結させるシステム。

### 達成目標

- 厳格な制作ルールとPlotTwistの物語論（全10パターンのどんでん返し）を統合
- 品質のブレないSNS向け4コマ漫画を完全自動で日次制作

### 技術スタック

| カテゴリ | 技術 |
|---------|------|
| CI/CD | GitHub Actions |
| シナリオ生成 | Gemini API |
| 画像生成 | Gemini API (Imagen) / 外部画像生成API |
| ストレージ | Google Drive API (GWS CLI) |
| 言語 | Python 3.13+ |

### システムアーキテクチャ

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

## 2. ディレクトリ構成

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
│   └── PlotTwist_plain.txt        # どんでん返し10パターン定義
├── .venv/                         # Python仮想環境（Git除外）
├── characters/                    # キャラクター表情シート
│   └── (hana.png, saki.png, ...)
├── references/                    # 参照用素材
│   ├── reference_4koma.png        # 4コマ全体のスタイル参照
│   └── successful_panel_4.png     # オチの成功例
├── docs/
│   └── SYSTEM_GUIDE.md            # 本ドキュメント（統合ガイド）
├── episodes/                      # 出力先（日付別フォルダ）
├── requirements.txt               # Python依存パッケージ
└── .gitignore
```

---

## 3. 5つのコアモジュール

### モジュール1：シナリオ・プロット生成（Gemini API）

| 項目 | 要件 |
|------|------|
| **機能要件** | PlotTwist_plain.txtのルールを学習し、「正体の転換（ドラキュラ、ウルフ、フランケン等の8パターン）」または「存在の転換（2パターン）」に基づく起承転結のシナリオを生成 |
| **キャラクター制限** | 主人公「はな」、友人「さき」、彼氏「まさと」、友人「ともや」、弟「ようた」の固定キャラクターを使用 |
| **構成要件** | 心理描写ではなく「実際の行動」ベースで描写。主人公の目的・戦い・変化の3つのストーリーラインが交錯する瞬間にオチ（ツッコミ）を発生させる |
| **禁止事項** | セリフにキャラクターの固有名詞は含めない |

### モジュール2：プリフライト検証＆テキスト補正（GitHub Actions）

| 項目 | 要件 |
|------|------|
| **機能要件** | 画像生成前に `preflight_check.py` を実行し、仕様違反やAI特有のエラーを自動検知・ブロック |
| **テキスト重複補正** | AI生成で発生しやすい「全部覚えて全部覚えて」などの連続重複テキストを自動検出し、1箇所に修正。非連続重複は警告ログを出力 |

#### 必須チェック項目

- [ ] キャンバスサイズが「1000px × 1000px 正方形」であること
- [ ] 指定フォント（Noto Sans JP Black / M PLUS Rounded 1c ExtraBold）が指定されていること
- [ ] 吹き出し色が仕様通りであること
- [ ] キャラクター名がセリフに含まれていないこと

### モジュール3：画像生成＆レイアウト描画（画像生成API）

| 項目 | 要件 |
|------|------|
| **機能要件** | manga_spec.yml の指示とキャラクターリファレンス（hana.png, yota.png等）に基づき、各コマを描画・結合 |
| **作画スタイル** | セル影を中心とし、グラデーションは禁止。背景は最小限で抽象的なものとする |

#### レイアウト

- 各コマは16:11の横長（1365 x 768等）で生成
- 冒頭にタイトルパネルを配置して1枚の画像に結合

### モジュール4：Google Drive 自動同期・アセット管理

| 項目 | 要件 |
|------|------|
| **機能要件** | 生成された画像やログをGoogle Drive上のエピソード別フォルダに自動アップロード |

#### 必須遵守ルール（誤保存防止）

```
⚠️ 重要：マイドライブ直下への保存を防ぐため、
新規フォルダ作成・アップロード時は必ず parents 属性に
指定の親フォルダID を強制付与すること

親フォルダID: 1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_
```

### モジュール5：Instagram投稿文＆メタデータ生成（Gemini API）

| 項目 | 要件 |
|------|------|
| **機能要件** | 完成した4コマ漫画のSNS拡散用キャプションを自動生成 |

#### 出力フォーマット

1. 読者の共感を呼ぶフック（1行目）
2. 漫画のあらすじ（オチのネタバレ禁止）
3. コメントを促すCTA（2択質問や絵文字など）
4. プロフィール誘導文
5. 指定ハッシュタグ（#4コマ漫画、#恋愛悩み など）

---

## 4. キャラクター素材

`characters/` フォルダには、4コマ漫画生成で使用するキャラクターの表情シート（リファレンス画像）を格納。

### ファイル一覧

| ファイル名 | キャラクター | 役割 | 性別 | 吹き出し色 |
|-----------|-------------|------|------|-----------|
| `hana.png` | はな | 主人公 | 女性 | 黄色 `#FFE800` |
| `saki.png` | さき | 友人 | 女性 | 黄色 `#FFE800` |
| `masato.png` | まさと | 彼氏 | 男性 | パステルブルー `#D4E8FF` |
| `tomoya.png` | ともや | 友人 | 男性 | パステルブルー `#D4E8FF` |
| `yota.png` | YOTA | 弟 | 男性 | パステルブルー `#D4E8FF` |

### Google Drive ファイルID

| ファイル名 | ファイルID |
|-----------|-----------|
| `hana.png` | `1Szs4wPmo_-en3iWlo4XlfkOJPTmAV_y2` |
| `saki.png` | `1FUdszNEBTNWclsuy1g8PxACqQC2FijQo` |
| `masato.png` | `1ooIUb1iYOZBAHowkjPwMBGy08EmblyKn` |
| `tomoya.png` | `1gt4a9_wbPYcVfjj4GDXaknnekiYMfuf8` |
| `yota.png` | `1Vg_ZvcbdwUxTH9CcnAZ4OT4zVlPWPeaE` |

### 使用ルール

1. **セリフにキャラクターの固有名詞を含めない**
2. **女性陣（はな・さき）**: 黄色の角ばった多角形吹き出し
3. **男性陣（まさと・ともや・YOTA）**: パステルブルーの柔らかい多角形吹き出し

---

## 5. 参照用素材

`references/` フォルダには、4コマ漫画生成時にスタイルやレイアウトの参照として使用する素材を格納。

### ファイル一覧

| ファイル名 | 用途 | 説明 |
|-----------|------|------|
| `reference_4koma.png` | 4コマ全体のスタイル参照 | レイアウト・枠線・配色の基準となる完成例 |
| `successful_panel_4.png` | オチ（4コマ目）の参照 | ツッコミ吹き出し・強調表現の成功例 |

### Google Drive ファイルID

| ファイル名 | ファイルID |
|-----------|-----------|
| `reference_4koma.png` | `1rh-477oeOOEuFmvIoZ0WKrd4uKdNuGxx` |
| `successful_panel_4.png` | `1fnSNJ3u7PbdBHspYpYMLiy3mjPnhMDTj` |

### 使用方法

- **reference_4koma.png**: 4コマ漫画全体のレイアウト・枠線・余白・配色の基準。新規生成時にこのスタイルを踏襲すること
- **successful_panel_4.png**: オチ（4コマ目）の成功例。ツッコミ吹き出し（黄色ギザギザ爆発型）の描画参照

---

## 6. 吹き出し描画ルール

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

### フォント指定

- **Noto Sans JP Black** - メインテキスト
- **M PLUS Rounded 1c ExtraBold** - 代替フォント

---

## 7. GitHub + Google Drive 連携

### 役割分担

| プラットフォーム | 役割 | 管理対象 |
|----------------|------|---------|
| **GitHub** | コード管理・実行指示 | `src/*.py`, `.github/workflows/*.yml`, `config/*` |
| **Google Drive** | 素材保管庫・成果物納品先 | キャラクター画像、生成された4コマ、バックアップ |

### Google Drive 連携が必須な3つの理由

1. **プリフライトチェックでDrive検索が必須**
   - STEP 2でストーリーフォルダの存在確認が必要
   - `gws drive files list` コマンドでDriveを直接検索

2. **キャラクター素材がDrive上で管理**
   - `hana.png`, `saki.png` 等の表情シートはDrive上にファイルIDで管理
   - 画像生成時にリファレンス画像として取得が必要

3. **成果物の保存先ルールが厳格**
   - 親フォルダID `1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_` を必ず指定
   - マイドライブ直下への誤保存を防止

### 登録済みファイルインデックス

| ファイル名 | ファイルID | 用途 |
|-----------|-----------|------|
| `manga_spec.yml` | `1oET1V34HPCDcgxqRzpXZ5ZSA9fO5WsxH` | 制作ルール |
| `hana.png` | `1Szs4wPmo_-en3iWlo4XlfkOJPTmAV_y2` | 主人公・はな |
| `saki.png` | `1FUdszNEBTNWclsuy1g8PxACqQC2FijQo` | 友人・さき |
| `masato.png` | `1ooIUb1iYOZBAHowkjPwMBGy08EmblyKn` | 彼氏・まさと |
| `tomoya.png` | `1gt4a9_wbPYcVfjj4GDXaknnekiYMfuf8` | 友人・ともや |
| `yota.png` | `1Vg_ZvcbdwUxTH9CcnAZ4OT4zVlPWPeaE` | 弟・YOTA |
| `reference_4koma.png` | `1rh-477oeOOEuFmvIoZ0WKrd4uKdNuGxx` | 参照用4コマ |
| `successful_panel_4.png` | `1fnSNJ3u7PbdBHspYpYMLiy3mjPnhMDTj` | オチの成功例 |

---

## 8. セットアップ手順

### Step 1: Python環境のセットアップ

```bash
# Python 3.13の仮想環境を作成
python3.13 -m venv .venv
source .venv/bin/activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### Step 2: 環境変数の設定

```bash
export GEMINI_API_KEY="your-api-key"
export GOOGLE_DRIVE_CREDENTIALS="your-credentials-json"
```

### Step 3: GitHub Secretsの設定

Settings → Secrets and variables → Actions で以下を設定：

| Secret名 | 説明 |
|---------|------|
| `GEMINI_API_KEY` | Gemini API認証キー |
| `GOOGLE_DRIVE_CREDENTIALS` | サービスアカウントのJSON認証情報（Base64エンコード推奨） |

### Step 4: Google Drive API の有効化

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」→ **Google Drive API** を有効化
3. 「認証情報」→「サービスアカウントを作成」
4. サービスアカウントのJSONキーをダウンロード
5. サービスアカウントのメールアドレス（`xxx@xxx.iam.gserviceaccount.com`）に `manga-auto-gen` フォルダの**編集者**権限を付与

### Step 5: Gemini への接続

Gemini UIで以下を接続：

1. **GitHub リポジトリ** → コードの参照・実行指示
2. **Google Drive** → 素材の取得・成果物の保存

---

## 9. 手動実行コマンド

```bash
# 仮想環境を有効化（初回のみ）
source .venv/bin/activate

# モジュール1: シナリオ生成
python src/module1_scenario_gen.py \
  --config config/PlotTwist_plain.txt \
  --output episodes/test/scenario.json

# モジュール2: プリフライト検証
python src/module2_preflight_check.py \
  --scenario episodes/test/scenario.json \
  --spec config/manga_spec.yml \
  --output episodes/test/validated_scenario.json

# モジュール3: 画像生成
python src/module3_image_gen.py \
  --scenario episodes/test/validated_scenario.json \
  --spec config/manga_spec.yml \
  --characters characters \
  --output episodes/test

# モジュール4: Google Drive同期
python src/module4_drive_sync.py \
  --source episodes/test \
  --parent-folder-id 1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_ \
  --episode-name test

# モジュール5: SNS投稿文生成
python src/module5_sns_publisher.py \
  --scenario episodes/test/validated_scenario.json \
  --strategy docs/SYSTEM_GUIDE.md \
  --output episodes/test/instagram_caption.txt
```

### 自動実行スケジュール

- 毎日 UTC 0:00（JST 9:00）に自動実行

### 手動実行方法

#### 方法1: Issueフォーム（推奨・広いテキストエリア）

GitHubの「Issues」タブから広い入力フォームを使って実行できます。

1. **Issues** タブ → **New issue** ボタン
2. 「漫画生成リクエスト (手動実行用)」を選択
3. フォームに入力して **Submit new issue**
4. 自動的にワークフローが起動し、完了後にIssueがクローズされます

**入力フィールド:**

| フィールド | 説明 | 必須 |
|-----------|------|:----:|
| **漫画のタイトル** | Google Driveのフォルダ名として使用 | ✅ |
| **テーマやシナリオ指示** | ざっくりとしたテーマや指示（複数行可） | ✅ |
| **どんでん返しパターン** | PlotTwistの10パターンから選択 | ❌ |
| **詳細シナリオ** | 起承転結・セリフ・表情指定を直接記述（複数行可） | ❌ |

**詳細シナリオの記述例:**

```
採用パターン：ドラフランケン（D→F）
起点（D：ドラキュラ）： 男たちが勝負してくれないという思い込み。
どんでん返し先（F：フランケン）： 自分の極端なアプローチが原因だった。

【1コマ目：起】（外部の敵への怒り）
登場人物： はな（怒り：表情5）
描写： スマホを見てイライラしているはな。
はなのセリフ（黄色・丸み禁止吹き出し）： 「なんで私とマッチングした男、すぐ『敬遠』していくの！？」

【2コマ目：承】（弟による分析）
登場人物： 弟（困惑：表情8）
紹介テロップ（四角い枠）： 弟（元高校球児）
弟のセリフ（パステルブルー吹き出し）： 「ピッチャーが勝負を避けるのは、バッターから異常な殺気を感じた時だけだ。」

【3コマ目：転】（真実の発見）
登場人物： はな（驚き：表情3）
はなのセリフ（黄色吹き出し）： 「マッチング直後に『年収は？』『いつまでに結婚したい？』って……あっ。」

【4コマ目：結】（オチ・ツッコミ）
登場人物： 弟（怒り：表情5）、はな（悲しみ：表情4）
弟のセリフ（黄色・ギザギザ爆発ツッコミ吹き出し）： 「初球から**フルスイング**しすぎだ！！ まずは**バント（挨拶）**から始めろ！！」
※「フルスイング」「バント」を赤文字・特大サイズで強調
はなのモノローグ（白・小声吹き出し）： 「三振どころかベンチに逃げられてたわ…」
```

#### 方法2: Actions タブから直接実行

1. **Actions** タブ → **Daily 4-Koma Manga Generation**
2. **Run workflow** ボタン → フォームに入力
3. **Run workflow** で実行

※ この方法は1行テキストボックスのため、長いシナリオには不向きです。

---

## 10. Instagram マーケティング戦略

### 投稿フォーマット

#### 1. 共感フック（1行目）
- 読者が「わかる！」と思える一言
- 絵文字を効果的に使用
- 例: 「マッチングアプリで出会った人、なんか重い…😅」

#### 2. あらすじ（2-3行目）
- オチのネタバレは絶対禁止
- 「続きは漫画で！」と誘導
- 例: 「友達に相談したら、意外な原因が判明して…」

#### 3. CTA（コメント促進）
- 2択質問が効果的
- 絵文字で選択肢を示す
- 例: 「あなたはどっち派？🙋‍♀️ A: 重い人好き / B: 軽い人がいい」

#### 4. プロフィール誘導
- 「他の漫画もプロフィールから見てね👆」
- 「フォローで最新話をお届け📩」

#### 5. ハッシュタグ

**必須タグ:**
- #4コマ漫画
- #恋愛漫画
- #恋愛悩み
- #マッチングアプリ
- #マッチングアプリあるある

**推奨タグ:**
- #恋愛あるある
- #漫画好きと繋がりたい
- #イラスト
- #創作漫画
- #恋愛相談
- #彼氏あるある
- #カップル漫画

### 投稿タイミング

- **平日**: 12:00-13:00（昼休み）、21:00-22:00（夜のリラックスタイム）
- **週末**: 10:00-11:00、20:00-21:00

### エンゲージメント向上のコツ

1. コメントには必ず返信する
2. ストーリーズで投稿を告知
3. リールで漫画のダイジェストを作成
4. 他のクリエイターとコラボ

### 禁止事項

- オチのネタバレ
- 過度な宣伝文句
- 無関係なハッシュタグの乱用
- 他作品の批判

---

## 11. トラブルシューティング

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

1. `characters/` と `references/` フォルダに画像ファイルが存在するか確認
2. 画像ファイルがフォルダ内に配置されているか確認

### プリフライトチェックでエラー

1. セリフに固有名詞（はな、さき等）が含まれていないか確認
2. パネル数が4であるか確認

---

## 12. 更新履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| v1.0 | 2026-04-02 | 初版作成 |

---

**END OF SYSTEM GUIDE**
