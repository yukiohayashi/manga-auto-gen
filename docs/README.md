# 4コマ漫画自動生成システム

GitHub ActionsとGemini APIを活用し、PlotTwistガイドの法則に則った4コマ漫画を毎日自動生成するシステム。

## ドキュメント

詳細は **[docs/SYSTEM_GUIDE.md](./docs/SYSTEM_GUIDE.md)** を参照してください。

## クイックスタート

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
export GEMINI_API_KEY="your-api-key"
export GOOGLE_DRIVE_CREDENTIALS="your-credentials-json"

# Instagram自動投稿用（オプション）
export INSTAGRAM_ACCESS_TOKEN="your-instagram-access-token"
export INSTAGRAM_ACCOUNT_ID="your-instagram-account-id"
```

## ライセンス

Private
