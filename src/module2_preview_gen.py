#!/usr/bin/env python3
"""
モジュール2：エピソードプレビューHTML生成

episode.jsonをビジュアル確認するためのpreview.htmlを生成する。

使い方:
  python src/module2_preview_gen.py                    # 全エピソード
  python src/module2_preview_gen.py "彼はサイコパス？"  # 特定エピソード
"""

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EPISODES_DIR = PROJECT_ROOT / "output-episodes"
ASSETS_DIR = PROJECT_ROOT / "src" / "assets"
TEMPLATE_PATH = ASSETS_DIR / "preview_template.html"


def generate_preview(episode_name: str = None):
    """プレビューHTMLを生成"""
    
    if not TEMPLATE_PATH.exists():
        print(f"❌ テンプレートが見つかりません: {TEMPLATE_PATH}")
        return
    
    # 対象エピソードを取得
    if episode_name:
        episode_dirs = [EPISODES_DIR / episode_name]
    else:
        episode_dirs = [
            d for d in EPISODES_DIR.iterdir()
            if d.is_dir() and d.name != "assets" and (d / "episode.json").exists()
        ]
    
    for episode_dir in episode_dirs:
        if not episode_dir.exists():
            print(f"⚠️ エピソードが見つかりません: {episode_dir.name}")
            continue
        
        episode_json = episode_dir / "episode.json"
        if not episode_json.exists():
            print(f"⚠️ episode.json が見つかりません: {episode_dir.name}")
            continue
        
        # テンプレートをコピー
        preview_path = episode_dir / "preview.html"
        shutil.copy(TEMPLATE_PATH, preview_path)
        print(f"✅ 生成完了: {episode_dir.name}/preview.html")
    
    print(f"\n📂 プレビューを開くには:")
    print(f"   cd output-episodes/<エピソード名>")
    print(f"   python3 -m http.server 8080")
    print(f"   → http://localhost:8080/preview.html")


def main():
    parser = argparse.ArgumentParser(description="エピソードプレビューHTML生成")
    parser.add_argument("episode", nargs="?", help="エピソード名（省略時は全エピソード）")
    args = parser.parse_args()
    
    generate_preview(args.episode)


if __name__ == "__main__":
    main()
