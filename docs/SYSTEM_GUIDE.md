# 4コマ漫画自動生成システム - 統合ガイド

**バージョン**: v2.0  
**最終更新**: 2026-04-07  
**リポジトリ**: https://github.com/yukiohayashi/manga-auto-gen

---

## 目次

1. [システム概要](#1-システム概要)
2. [ディレクトリ構成](#2-ディレクトリ構成)
3. [ローカル実行（run.sh）](#3-ローカル実行runsh)
4. [シナリオJSON仕様](#4-シナリオjson仕様)
5. [5つのコアモジュール](#5-5つのコアモジュール)
6. [吹き出し描画エンジン（bubble_renderer.py）](#6-吹き出し描画エンジンbubble_rendererpy)
7. [画像生成パイプライン（module3）詳細](#7-画像生成パイプラインmodule3詳細)
8. [キャラクター素材](#8-キャラクター素材)
9. [参照用素材](#9-参照用素材)
10. [GitHub Actions CI/CD](#10-github-actions-cicd)
11. [GitHub + Google Drive 連携](#11-github--google-drive-連携)
12. [セットアップ手順](#12-セットアップ手順)
13. [Instagram マーケティング戦略](#13-instagram-マーケティング戦略)
14. [トラブルシューティング](#14-トラブルシューティング)
15. [更新履歴](#15-更新履歴)

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
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   └── manga_request.yml          # Issue経由の手動実行フォーム
│   └── workflows/
│       ├── daily_manga_gen.yml        # CI/CD定期実行（毎日JST 9:00）
│       └── issue_manga_gen.yml        # Issue起動ワークフロー
├── src/
│   ├── module1_scenario_gen.py        # シナリオ生成（Gemini API）
│   ├── module2_preflight_check.py     # プリフライト検証・テキスト補正
│   ├── module3_image_gen.py           # 画像生成・レイアウト描画（主要モジュール）
│   ├── module4_drive_sync.py          # Google Drive同期・素材取得
│   ├── module5_sns_publisher.py       # Instagram投稿文生成
│   └── bubble_renderer.py            # 吹き出し・縦書きテキスト描画エンジン
├── config/
│   ├── manga_spec.yml                 # 制作ルール・描画指示（40KB）
│   └── PlotTwist_plain.txt            # どんでん返し10パターン定義（20KB）
├── characters/                        # キャラクターリファレンス画像
│   ├── hana.png                       # 主人公・はな
│   ├── saki.png                       # 友人・さき
│   ├── masato.png                     # 彼氏・まさと
│   ├── tomoya.png                     # 友人・ともや
│   ├── yota.png                       # 弟・ようた
│   └── naomi.png                      # 友人・なおみ
├── references/                        # スタイル参照用素材
│   └── successful_panel_4.png         # 4コマスタイル参照・オチの成功例
├── templates/                         # テンプレート
├── test/                              # テスト用
│   ├── test_bubble_only.py            # 吹き出し単体テスト（プレースホルダー画像）
│   ├── test_scenario.json             # テスト用シナリオ
│   ├── run_local.sh                   # テスト実行スクリプト
│   └── output/                        # テスト出力先
├── episodes/                          # 本番出力先（エピソード名別フォルダ）
│   └── <エピソード名>/
│       ├── scenario.json              # シナリオ定義
│       ├── 4koma_panel_01.png         # パネル1（タイトル付き）
│       ├── 4koma_panel_02.png         # パネル2
│       ├── 4koma_panel_03.png         # パネル3
│       └── 4koma_panel_04.png         # パネル4（オチ）
├── docs/
│   └── SYSTEM_GUIDE.md                # 本ドキュメント（統合ガイド）
├── run.sh                             # ローカル統合実行スクリプト
├── requirements.txt                   # Python依存パッケージ
├── .env                               # 環境変数（Git除外、GEMINI_API_KEY等）
├── .venv/                             # Python仮想環境（Git除外）
└── .gitignore
```

---

## 3. ローカル実行（run.sh）

### 基本コマンド

```bash
# 全4パネル生成（デフォルト）
./run.sh episodes/婚活スラッガー/scenario.json

# パネル1,3だけ再生成（既存の2,4は維持）
./run.sh episodes/婚活スラッガー/scenario.json --only 1,3

# 2枚だけ生成
./run.sh episodes/婚活スラッガー/scenario.json --panels 2

# Google Drive同期あり
./run.sh episodes/婚活スラッガー/scenario.json --drive
```

### オプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--panels N` | 生成するパネル数（1-4） | `4` |
| `--only 1,3` | 再生成するパネル番号（カンマ区切り）。指定外のパネルは既存画像を維持 | 全パネル |
| `--drive` | Google Driveへの同期を有効化 | 無効 |
| `--no-combine` | 結合画像を生成しない | 結合しない（デフォルト） |
| `--name NAME` | エピソード名を手動指定 | scenario.jsonのtitleから自動取得 |

### 動作フロー

1. `.env`から環境変数を読み込み（`GEMINI_API_KEY`等）
2. シナリオJSONを解析
3. `module3_image_gen.py`で各パネルを生成（`--only`指定時はスキップ対象あり）
4. 出力先: シナリオJSONと同じディレクトリ
5. `--drive`指定時のみ`module4_drive_sync.py`でDrive同期

---

## 4. シナリオJSON仕様

```json
{
  "title": "婚活スラッガー",
  "theme": "マッチングアプリで男性が次々フェードアウトする女性の話",
  "twist_pattern": "ドラフランケン (D→F)",
  "panels": [
    {
      "panel_number": 1,
      "structure": "起",
      "characters": ["はな"],
      "description": "スマホを見てイライラしているはな。",
      "background": "モダンなリビングルーム",
      "effects": ["怒りマーク"],
      "dialogue": [
        {
          "type": "shout",
          "character": "はな",
          "text": "なんで私とマッチングした男、\nすぐフェードアウト(敬遠）していくの！？ 勝負を避けるな！"
        }
      ]
    }
  ]
}
```

### dialogueのtype一覧

| type | 用途 | 吹き出し形状 |
|------|------|-------------|
| `normal` | 通常のセリフ | キャラクター別スタイル |
| `shout` | 叫び・ツッコミ | 黄色ギザギザ（TSUKKOMI_STYLE） |
| `monologue` | モノローグ・小声 | 白い楕円 |
| `thought` | 心の声 | 白い雲型 |
| `caption` | 紹介テロップ | パネル下部に白い四角 |
| `effect_text` | 効果音（ガーン等） | 吹き出し無し。AI画像に直接描画 |

### dialogue追加プロパティ

| プロパティ | 説明 | 例 |
|-----------|------|-----|
| `character` | 発話キャラクター名 | `"はな"` |
| `text` | セリフ本文（`\n`で改行=列区切り） | `"初球から\nフルスイング"` |
| `highlight` | 赤文字強調するキーワード | `"フルスイング"` |

---

## 5. 5つのコアモジュール

### モジュール1：シナリオ・プロット生成（`module1_scenario_gen.py`）

| 項目 | 要件 |
|------|------|
| **機能** | PlotTwist_plain.txtのルールに基づき起承転結シナリオを生成 |
| **キャラクター** | はな（主人公）、さき（友人）、まさと（彼氏）、ともや（友人）、ようた（弟）の固定5名 |
| **構成** | 行動ベースで描写。オチはツッコミで締める |
| **禁止** | セリフにキャラクターの固有名詞を含めない |

### モジュール2：プリフライト検証（`module2_preflight_check.py`）

| 項目 | 要件 |
|------|------|
| **機能** | 画像生成前にシナリオの仕様違反・AI特有エラーを自動検知 |
| **テキスト補正** | 連続重複テキストの自動修正 |
| **チェック項目** | キャンバスサイズ1000×1000、フォント指定、吹き出し色、固有名詞混入 |
| **注意** | 現在`run.sh`には未組み込み（GitHub Actionsでのみ実行） |

### モジュール3：画像生成（`module3_image_gen.py`） → 詳細はセクション7

| 項目 | 要件 |
|------|------|
| **機能** | Gemini APIでイラスト生成→吹き出し・テキストをコード側で合成 |
| **出力** | 1000×1000px正方形PNG（白余白20px付き） |

### モジュール4：Google Drive同期（`module4_drive_sync.py`）

| 項目 | 要件 |
|------|------|
| **機能** | 生成画像をDriveのエピソード別フォルダに自動アップロード |
| **親フォルダID** | `0AFCTATYikdWmUk9PVA`（共有ドライブ） |
| **ローカル実行時** | `--drive`フラグが無い限り実行されない |

### モジュール5：SNS投稿文生成（`module5_sns_publisher.py`）

| 項目 | 要件 |
|------|------|
| **機能** | 完成した4コマ漫画のInstagram投稿キャプションを自動生成 |
| **出力** | フック→あらすじ→CTA→プロフ誘導→ハッシュタグ |

---

## 6. 吹き出し描画エンジン（bubble_renderer.py）

### キャラクター別吹き出しスタイル

| キャラクター | 吹き出し色 | 形状 | outline_width |
|-------------|-----------|------|:------------:|
| はな・さき（女性陣） | 黄色 `#FFE800` | SOFT_POLYGON | 6 |
| まさと・ともや・ようた（男性陣） | パステルブルー `#D4E8FF` | SOFT_POLYGON | 6 |
| モノローグ・小声 | 白 `#FFFFFF` | OVAL | 6 |
| ツッコミ（shout） | 黄色 `#FFE800` | SOFT_POLYGON | 7 |
| 考え事（thought） | 白 `#FFFFFF` | CLOUD | 6 |
| キャプション | 白 `#FFFFFF` | SOFT_POLYGON | 4 |

### SOFT_POLYGON形状パラメータ

吹き出し形状は**スーパー楕円 + 低周波ランダム変位**で生成：

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `n_power` | 4.5 | スーパー楕円指数（大きいほど角丸四角形に近い） |
| `num_points` | 120 | ポリゴン頂点数 |
| `num_harmonics` | 4 | ランダム変位の調和成分数 |
| `amp_ratio` | 0.005〜0.018 | 変位の振幅比（控えめで膨らみ抑制） |
| しっぽ | ポリゴン頂点に一体化 | 隙間のない自然な接続 |

### テキスト描画パラメータ

| パラメータ | 値 | 説明 |
|-----------|-----|------|
| `font_size` | 52px（基本） | 吹き出し幅に収まらない場合、24pxまで2px刻みで縮小 |
| `char_h` | font_size + 4 | 1文字の縦幅 |
| `col_w` | font_size + 16 | 1列の横幅 |
| `padding` | 50px | 吹き出し内側余白 |
| 縦書き | 右→左に列配置 | `\n`は強制改列、括弧内は改行しない |
| 強調キーワード | 赤 `#FF0000` | `highlight`指定時、括弧`『』`以外を赤文字かつ1.2倍フォント |

### 縦書き特殊処理

- **句読点・記号**: VERTICAL_PUNCTUATION辞書で位置オフセット
- **回転文字**: `ー`、`〜`、`…`等は90°回転描画
- **括弧類**: `（）「」『』`は縦書き用Unicode文字に変換
- **小さいかな**: `っゃゅょ`等は右上寄せ
- **縦中横**: `！！`→`‼`として1文字分に横並び描画

---

## 7. 画像生成パイプライン（module3）詳細

### 処理フロー

```
1. シナリオJSONからパネル情報を取得
2. Gemini APIでイラスト生成（1024×1024、テキスト・吹き出し・枠なし）
3. アンチエイリアス: 2倍解像度にアップスケール（SS=2）
4. 吹き出しサイズ計算・配置
5. bubble_renderer.pyで吹き出し＋テキスト描画
6. パネル枠（茶色 #5D4037、10px）を最前面に描画
7. ダウンスケール（LANCZOS）でアンチエイリアス効果
8. 1コマ目: タイトルバー（100px高、パステルピンク#FFE4E1背景）を上部に追加
9. 白余白20pxを追加して保存
```

### Gemini APIプロンプト構成

```
CRITICAL RULES: テキスト・吹き出し・枠の描画を禁止
STYLE: 少女漫画風、セル影、パステル、枠なし
CHARACTER AGES: 全キャラ20-30代の大人
SCENE: シナリオのdescription
BACKGROUND: シナリオのbackground
CHARACTER CLOTHING: リファレンス画像通り
OBJECT RULES: スマホは背面（黒）のみ表示
TECHNICAL: 1:1正方形、枠なし
MANGA EFFECT TEXT: effect_typeのテキストをAI画像に直接描画
```

### 吹き出し配置ロジック

| セリフ数 | 配置パターン |
|---------|-------------|
| 1つ | 右上（margin付き） |
| 2つ | 右上、左下 |
| 3つ | 右上、左上、左下 |
| 4つ以上 | 右上、左上、左下、右下を順番に |

### サイズ制約

| パラメータ | 値 |
|-----------|-----|
| 吹き出し最大幅 | パネル幅の45% |
| 吹き出し最大高さ | パネル高さの80% |
| パネル枠色 | 茶色 `#5D4037` |
| パネル枠幅 | 10px |
| アンチエイリアス | 2xスーパーサンプリング |

### clip_edges（パネル端との接着）

吹き出しがパネル枠に近い場合（`border_width + 2`px以内）、その辺のアウトラインを省略して枠と一体化させる。

---

## 8. キャラクター素材

`characters/` フォルダには、4コマ漫画生成で使用するキャラクターの表情シート（リファレンス画像）を格納。

### ファイル一覧

| ファイル名 | キャラクター | 役割 | 性別 | 吹き出し色 |
|-----------|-------------|------|------|-----------|
| `hana.png` | はな | 主人公 | 女性 | 黄色 `#FFE800` |
| `saki.png` | さき | 友人 | 女性 | 黄色 `#FFE800` |
| `masato.png` | まさと | 彼氏 | 男性 | パステルブルー `#D4E8FF` |
| `tomoya.png` | ともや | 友人 | 男性 | パステルブルー `#D4E8FF` |
| `yota.png` | YOTA | 弟 | 男性 | パステルブルー `#D4E8FF` |
| `naomi.png` | なおみ | 友人 | 女性 | 黄色 `#FFE800` |

### Google Drive ファイルID

| ファイル名 | ファイルID |
|-----------|-----------|
| `hana.png` | `18e5ANog_Ba0l3yBpkzuCOeRFWGpAC9cZ` |
| `saki.png` | `1U8g26rhdPwyg9yhXRvgeXOi_ENvywzjV` |
| `masato.png` | `1ELEO3FJBlV3O7WMyXm2_cI8twX_NEvKU` |
| `tomoya.png` | `1Qo-l-w8MsdtOOCOdBCfZeCZMKF-oPy_s` |
| `yota.png` | `1Bz1MMsSppsd9dl9Dh0rTXF1Zl2YSh53n` |
| `naomi.png` | `11d10DBfiN8KC8xG7g9LH4Up2KHwfn9sO` |

### 使用ルール

1. **セリフにキャラクターの固有名詞を含めない**
2. **女性陣（はな・さき・なおみ）**: 黄色の角ばった多角形吹き出し
3. **男性陣（まさと・ともや・YOTA）**: パステルブルーの柔らかい多角形吹き出し

---

## 9. 参照用素材

`references/` フォルダには、4コマ漫画生成時にスタイルやレイアウトの参照として使用する素材を格納。

### ファイル一覧

| ファイル名 | 用途 | 説明 |
|-----------|------|------|
| `successful_panel_4.png` | 4コマスタイル参照・オチの成功例 | レイアウト・枠線・配色・ツッコミ吹き出しの基準 |

### Google Drive ファイルID

| ファイル名 | ファイルID |
|-----------|-----------|
| `successful_panel_4.png` | `1HHGfAmo56csdyHx83XOzyfAQiXx1mmXt` |

### 使用方法

- **successful_panel_4.png**: 4コマ漫画全体のレイアウト・枠線・余白・配色の基準、およびツッコミ吹き出し（黄色ギザギザ爆発型）の描画参照

---

## 10. GitHub Actions CI/CD

### ワークフロー

| ファイル | トリガー | 説明 |
|---------|---------|------|
| `daily_manga_gen.yml` | cron (毎日JST 9:00) | 日次自動生成 |
| `issue_manga_gen.yml` | Issue作成時 | 手動リクエスト経由の生成 |

### Issue経由の手動実行

1. **Issues** タブ → **New issue** → 「漫画生成リクエスト」を選択
2. タイトル・テーマ・どんでん返しパターン・詳細シナリオを入力
3. Submit → ワークフローが自動起動
4. 完了後にIssueが自動クローズ

### 必要なGitHub Secrets

| Secret名 | 説明 |
|---------|------|
| `GEMINI_API_KEY` | Gemini API認証キー |
| `GOOGLE_DRIVE_CREDENTIALS` | サービスアカウントJSON（Base64） |

---

## 11. GitHub + Google Drive 連携

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
| `manga_spec.yml` | `175RGsYrey-I4EOqO9a8UlXAKliIgoBl1` | 制作ルール |
| `hana.png` | `18e5ANog_Ba0l3yBpkzuCOeRFWGpAC9cZ` | 主人公・はな |
| `saki.png` | `1U8g26rhdPwyg9yhXRvgeXOi_ENvywzjV` | 友人・さき |
| `masato.png` | `1ELEO3FJBlV3O7WMyXm2_cI8twX_NEvKU` | 彼氏・まさと |
| `tomoya.png` | `1Qo-l-w8MsdtOOCOdBCfZeCZMKF-oPy_s` | 友人・ともや |
| `yota.png` | `1Bz1MMsSppsd9dl9Dh0rTXF1Zl2YSh53n` | 弟・YOTA |
| `naomi.png` | `11d10DBfiN8KC8xG7g9LH4Up2KHwfn9sO` | 友人・なおみ |
| `successful_panel_4.png` | `1HHGfAmo56csdyHx83XOzyfAQiXx1mmXt` | 4コマスタイル参照・オチの成功例 |

---

## 12. セットアップ手順

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

### 環境変数（.env）

```bash
GEMINI_API_KEY=your_api_key_here
```

`.env`はプロジェクトルートに配置。`.gitignore`に含まれるためGitにコミットされない。

---

## 13. Instagram マーケティング戦略

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

## 14. トラブルシューティング

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

### GEMINI_API_KEY未設定時

- プレースホルダー画像（テキスト描写のみ）が生成される
- `.env`に`GEMINI_API_KEY`を設定して再実行
- APIキー取得先: https://aistudio.google.com/apikey

---

## 15. 更新履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| v2.0 | 2026-04-07 | ローカル実行(run.sh)、--only選択的再生成、シナリオJSON仕様、描画エンジン詳細、Geminiプロンプト仕様を追加。ディレクトリ構成を現状に更新 |
| v1.0 | 2026-04-02 | 初版作成 |

---

**END OF SYSTEM GUIDE**
