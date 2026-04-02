# 4コマ漫画自動生成システム 仕様書

**バージョン**: v1.0  
**作成日**: 2026-04-02  
**ステータス**: ドラフト

---

## 1. システム目的

GitHub ActionsとGemini APIを活用し、**PlotTwistガイドの法則に則った4コマ漫画を毎日自動生成・検証・保存**し、Instagramへの投稿準備までを完結させるシステム。

### 達成目標
- 厳格な制作ルールとPlotTwistの物語論（全10パターンのどんでん返し）を統合
- 品質のブレないSNS向け4コマ漫画を完全自動で日次制作

---

## 2. 処理フローと5つのコアモジュール要件

### モジュール1：シナリオ・プロット生成（Gemini API）

| 項目 | 要件 |
|------|------|
| **機能要件** | PlotTwist_plain.txtのルールを学習し、「正体の転換（ドラキュラ、ウルフ、フランケン等の8パターン）」または「存在の転換（2パターン）」に基づく起承転結のシナリオを生成 |
| **キャラクター制限** | 主人公の名前は「はな」で統一（「あや」は使用禁止）。友人「さき」、彼氏「まさと」、友人「ともや」、弟「ようた」などの固定キャラクターを使用 |
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

#### 吹き出し・テキストルール（厳格）

| キャラクター | 吹き出し色 | 形状 |
|-------------|-----------|------|
| はな・さき（女性陣） | 黄色 `#FFE800` | 丸み禁止の角ばった多角形 |
| まさと・ともや（男性陣） | パステルブルー `#D4E8FF` または白 | 角ばった多角形または楕円形 |
| モノローグ・小声 | 白 `#FFFFFF` | 楕円形または角丸四角形 |
| ツッコミ（オチ） | 黄色 `#FFE800` | ギザギザ爆発型 |

#### ツッコミ強調ルール
- キーワードを**赤文字** `#FF0000`
- サイズは他より**1.2〜1.5倍**の大きさで強調

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

## 3. ディレクトリ構成

自動化と保守性を担保するため、以下の構成でリポジトリを管理します。

```
manga-auto-gen/
├── .github/workflows/
│   └── daily_manga_gen.yml        # CI/CDの定期実行スケジュール定義
├── src/                           
│   ├── module1_scenario_gen.py    # Gemini連携：PlotTwist準拠シナリオ生成
│   ├── module2_preflight_check.py # preflight_check.py（検証・補正ロジック）
│   ├── module3_image_gen.py       # 画像生成API連携・結合・文字入れ
│   ├── module4_drive_sync.py      # GWS CLI連携（親フォルダID固定指定）
│   └── module5_sns_publisher.py   # Gemini連携：投稿用テキスト生成
├── config/                        
│   ├── manga_spec.yml             # 全体ルール・描画指示プロンプト
│   ├── PlotTwist_plain.txt        # シナリオロジック定義
│   └── instagram_marketing_strategy.md # SNS投稿フォーマット
├── characters/                    # キャラクターリファレンス画像
│   ├── INDEX.md                   # Gemini用インデックス（ファイル一覧・役割）
│   └── hana.png, saki.png, ...    # 表情シート
├── references/                    # 参照用素材
│   ├── INDEX.md                   # Gemini用インデックス
│   ├── reference_4koma.png        # 4コマ全体のスタイル参照
│   └── successful_panel_4.png     # オチ（4コマ目）の成功例
└── episodes/                      # GitHub Actionsランナー上の一時作業・出力先
```

---

## 4. 技術スタック

| カテゴリ | 技術 |
|---------|------|
| CI/CD | GitHub Actions |
| シナリオ生成 | Gemini API |
| 画像生成 | Gemini API (Imagen) / 外部画像生成API |
| ストレージ | Google Drive API (GWS CLI) |
| 言語 | Python 3.11+ |

---

## 5. GitHub + Google Drive 連携要件

### 役割分担

| プラットフォーム | 役割 | 管理対象 |
|----------------|------|---------|
| **GitHub** | コード管理・実行指示 | `src/*.py`, `.github/workflows/*.yml`, `config/*.txt` |
| **Google Drive** | 素材保管庫・成果物納品先 | キャラクター画像、生成された4コマ、バックアップ |

### Google Drive 連携が必須な理由

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
| `masto.png` | `1ooIUb1iYOZBAHowkjPwMBGy08EmblyKn` | 彼氏・まさと |
| `tomoya.png` | `1gt4a9_wbPYcVfjj4GDXaknnekiYMfuf8` | 友人・ともや |
| `yota.png` | `1Vg_ZvcbdwUxTH9CcnAZ4OT4zVlPWPeaE` | 弟・YOTA |
| `reference_4koma.png` | `1rh-477oeOOEuFmvIoZ0WKrd4uKdNuGxx` | 参照用4コマ |
| `preflight_check.py` | `1DXrInNDgPgV8DAA8Rr6nqdlcavWMDa5t` | 検証スクリプト |

詳細は `docs/INTEGRATION_GUIDE.md` を参照。

---

## 6. 環境変数・シークレット

GitHub Actionsで使用するシークレット：

| 変数名 | 説明 |
|--------|------|
| `GEMINI_API_KEY` | Gemini API認証キー |
| `GOOGLE_DRIVE_CREDENTIALS` | Google Drive API認証情報（JSON） |
| `DRIVE_PARENT_FOLDER_ID` | 親フォルダID `1InxhF6u1ToFBTsnfMeJ1xIW3ibNynUq_` |

---

## 6. 実行スケジュール

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # 毎日 UTC 0:00（JST 9:00）に実行
  workflow_dispatch:      # 手動実行も可能
```

---

## 7. 参照ドキュメント

- `manga_spec.yml` - 4コマ漫画制作ルール全体
- `PlotTwist_plain.txt` - どんでん返し10パターンの定義
- `instagram_marketing_strategy.md` - SNS投稿戦略

---

## 8. 更新履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| v1.0 | 2026-04-02 | 初版作成 |

---

**END OF SPEC**
