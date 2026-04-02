# 4コマ漫画自動生成システム

GitHub ActionsとGemini APIを活用し、PlotTwistガイドの法則に則った4コマ漫画を毎日自動生成するシステム。

## 概要

- **目的**: 品質のブレないSNS向け4コマ漫画を完全自動で日次制作
- **技術スタック**: Python 3.11+, GitHub Actions, Gemini API, Google Drive API

## ディレクトリ構成

```
manga-auto-gen/
├── .github/workflows/
│   └── daily_manga_gen.yml        # CI/CD定期実行
├── src/
│   ├── module1_scenario_gen.py    # シナリオ生成
│   ├── module2_preflight_check.py # プリフライト検証
│   ├── module3_image_gen.py       # 画像生成
│   ├── module4_drive_sync.py      # Google Drive同期
│   └── module5_sns_publisher.py   # SNS投稿文生成
├── config/
│   ├── manga_spec.yml             # 制作ルール
│   ├── PlotTwist_plain.txt        # どんでん返しロジック
│   └── instagram_marketing_strategy.md
├── characters/                    # キャラクター画像
│   ├── INDEX.md                   # Gemini用インデックス
│   └── hana.png, saki.png, ...    # 表情シート
├── references/                    # 参照用素材
│   ├── INDEX.md                   # Gemini用インデックス
│   ├── reference_4koma.png        # 4コマ全体のスタイル参照
│   └── successful_panel_4.png     # オチの成功例
├── docs/
│   └── INTEGRATION_GUIDE.md       # GitHub+Drive連携ガイド
└── episodes/                      # 出力先
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
export GEMINI_API_KEY="your-api-key"
export GOOGLE_DRIVE_CREDENTIALS="your-credentials-json"
```

### 3. GitHub Secretsの設定

- `GEMINI_API_KEY`
- `GOOGLE_DRIVE_CREDENTIALS`

## 手動実行

```bash
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
  --strategy config/instagram_marketing_strategy.md \
  --output episodes/test/instagram_caption.txt
```

## 自動実行スケジュール

- 毎日 UTC 0:00（JST 9:00）に自動実行
- GitHub Actionsの「Actions」タブから手動実行も可能

## 詳細仕様

[SPEC.md](./SPEC.md) を参照してください。

## ライセンス

Private
