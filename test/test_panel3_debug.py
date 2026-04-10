#!/usr/bin/env python3
"""
吹き出し単体テストスクリプト
Gemini APIを使わず、プレースホルダー画像に吹き出しを描画してテスト
"""

import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir / "src"))

from PIL import Image, ImageDraw
from module3_image_gen import ImageGenerator

# 定数定義
SS = 2  # スーパーサンプリング倍率
PANEL_SIZE = (600, 600)  # パネルサイズ

def test_panel3_bubbles():
    """パネル3の吹き出しテスト"""
    
    # テスト用出力ディレクトリ
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # エピソードJSON読み込み
    episode_path = project_dir / "episodes" / "シークレット・ブーツ" / "episode.json"
    with open(episode_path, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    
    # パネル3のデータを取得
    panels = scenario.get("panels", [])
    if len(panels) < 3:
        print("エラー: パネル3が見つかりません")
        return
    
    panel3 = panels[2]  # 0-indexed
    
    print("=== パネル3 データ ===")
    print(f"description: {panel3.get('description', '')}")
    print(f"characters: {panel3.get('characters', [])}")
    print(f"dialogue:")
    for i, d in enumerate(panel3.get('dialogue', [])):
        print(f"  [{i}] type={d.get('type')}, char={d.get('character')}, text={d.get('text', '')[:40]}...")
    
    # ImageGenerator初期化（APIなし）
    spec_path = project_dir / "config" / "manga_spec.yml"
    chars_path = project_dir / "characters"
    
    # APIキーを空にして初期化（プレースホルダー生成のみ）
    import os
    original_key = os.environ.get("GEMINI_API_KEY", "")
    os.environ["GEMINI_API_KEY"] = ""
    
    generator = ImageGenerator(str(spec_path), str(chars_path))
    
    # パネル3を生成（プレースホルダー + 吹き出し）
    print("\n=== パネル3 生成（プレースホルダー + 吹き出し）===")
    
    # プレースホルダー画像作成
    panel_w, panel_h = PANEL_SIZE
    
    # デバッグ用に背景色を変えて作成
    img = Image.new("RGB", (panel_w * SS, panel_h * SS), "#E0F0FF")  # 薄い青背景
    draw = ImageDraw.Draw(img)
    
    # パネル番号と説明を描画
    draw.text((50, 50), f"Panel 3 (DEBUG)", fill="#FF0000")
    draw.text((50, 100), f"Desc: {panel3.get('description', '')[:50]}...", fill="#000000")
    
    # ダウンスケールしてパネルサイズに
    orig_size = (panel_w, panel_h)
    img = img.resize(orig_size, Image.LANCZOS)
    
    # 吹き出し描画
    print("吹き出し描画開始...")
    img = generator.draw_panel_with_dialogues(img, panel3, is_final_panel=False)
    
    # 保存
    output_path = output_dir / "panel3_debug.png"
    img.save(output_path)
    print(f"\n保存完了: {output_path}")
    
    # 環境変数を元に戻す
    os.environ["GEMINI_API_KEY"] = original_key

if __name__ == "__main__":
    test_panel3_bubbles()
