#!/usr/bin/env python3
"""
モジュール3：画像生成＆レイアウト描画

manga_spec.ymlの指示とキャラクターリファレンスに基づき、
Gemini APIで各コマを生成し、吹き出しを描画・結合する。

吹き出し描画は bubble_renderer.py モジュールを使用。
"""

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Optional
from io import BytesIO

import yaml
from PIL import Image, ImageDraw, ImageFont
from google import genai

from bubble_renderer import BubbleRenderer

# キャンバスサイズ
CANVAS_SIZE = (1000, 1000)
PANEL_SIZE = (1365, 768)  # 16:11


class ImageGenerator:
    """画像生成クラス"""

    def __init__(self, spec_path: str, assets_path: str, api_key: str = None):
        with open(spec_path, "r", encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)
        self.assets_path = Path(assets_path)
        self.character_images = self._load_character_images()
        self.bubble_renderer = BubbleRenderer(font_dir=Path(assets_path).parent / "fonts")
        
        # Gemini API クライアント初期化
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            print("[Module3] Gemini API クライアント初期化完了")
        else:
            self.client = None
            print("[Module3] 警告: GEMINI_API_KEY未設定、プレースホルダー画像を使用")

    def _load_character_images(self) -> dict:
        """キャラクター画像を読み込み"""
        images = {}
        character_files = {
            "はな": "hana.png",
            "さき": "saki.png",
            "まさと": "masato.png",
            "ともや": "tomoya.png",
            "ようた": "yota.png",
        }
        for name, filename in character_files.items():
            path = self.assets_path / filename
            if path.exists():
                images[name] = Image.open(path)
                print(f"[Module3] キャラクター画像読み込み: {name}")
            else:
                print(f"[Module3] 警告: キャラクター画像が見つかりません: {path}")
        return images

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """フォントを取得"""
        # システムフォントを使用（実際の環境ではNoto Sans JPを指定）
        try:
            if bold:
                return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", size)
            return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", size)
        except:
            return ImageFont.load_default()

    def generate_panel_prompt(self, panel: dict, scenario: dict, panel_number: int) -> str:
        """Gemini画像生成用のプロンプトを生成"""
        characters = panel.get("characters", [])
        description = panel.get("description", "")
        background = panel.get("background", "シンプルな背景")
        effects = panel.get("effects", [])
        panel_names = ["起", "承", "転", "結"]

        prompt = f"""
Generate a single panel for a Japanese 4-koma manga (4-panel comic).

## Style Requirements
- Japanese manga style with clean lines
- Cel-shading (no gradients)
- Pastel colors, low saturation
- Minimal abstract background
- NO speech bubbles or text (will be added separately)

## Scene Description
Panel {panel_number} ({panel_names[panel_number-1]}): {description}

## Characters
{', '.join(characters) if characters else 'No characters'}

## Background
{background}

## Visual Effects
{', '.join(effects) if effects else 'None'}

## Technical Specs
- Aspect ratio: 1:1 (square)
- Clean composition with space for speech bubbles
- Brown border (#5D4037)
"""
        return prompt

    def generate_panel_with_gemini(self, panel: dict, scenario: dict, panel_number: int) -> Optional[Image.Image]:
        """Gemini APIで画像を生成"""
        if not self.client:
            return None
        
        prompt = self.generate_panel_prompt(panel, scenario, panel_number)
        print(f"[Module3] Gemini APIで画像生成中... (パネル{panel_number})")
        
        try:
            # Gemini 3.1 Proで画像生成
            from google.genai import types
            
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                )
            )
            
            # デバッグ: レスポンス構造を出力
            print(f"[Module3] DEBUG: response type = {type(response)}")
            if hasattr(response, 'candidates') and response.candidates:
                print(f"[Module3] DEBUG: candidates count = {len(response.candidates)}")
                if response.candidates[0].content:
                    print(f"[Module3] DEBUG: parts count = {len(response.candidates[0].content.parts)}")
                    for i, part in enumerate(response.candidates[0].content.parts):
                        print(f"[Module3] DEBUG: part[{i}] type = {type(part)}, has inline_data = {hasattr(part, 'inline_data')}")
                        if hasattr(part, 'text'):
                            print(f"[Module3] DEBUG: part[{i}] text = {part.text[:100] if part.text else 'None'}...")
            
            # レスポンスから画像を抽出
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    print(f"[Module3] DEBUG: inline_data found, mime_type = {part.inline_data.mime_type if hasattr(part.inline_data, 'mime_type') else 'unknown'}")
                    image_data = base64.b64decode(part.inline_data.data)
                    image = Image.open(BytesIO(image_data))
                    print(f"[Module3] Gemini画像生成成功: パネル{panel_number}")
                    return image.resize(CANVAS_SIZE)
            
            print(f"[Module3] 警告: Gemini応答に画像が含まれていません")
            return None
            
        except Exception as e:
            print(f"[Module3] Gemini画像生成エラー: {e}")
            return None

    def create_title_panel(self, title: str) -> Image.Image:
        """タイトルパネルを生成"""
        img = Image.new("RGB", CANVAS_SIZE, "#FFFFFF")
        draw = ImageDraw.Draw(img)

        # タイトルエリア背景（パステルカラー）
        title_area_height = 150
        draw.rectangle(
            [(0, 0), (CANVAS_SIZE[0], title_area_height)],
            fill="#FFE4E1"  # パステルピンク
        )

        # 境界線
        draw.line([(0, title_area_height), (CANVAS_SIZE[0], title_area_height)], 
                  fill="#5D4037", width=3)

        # タイトルテキスト
        font = self._get_font(48, bold=True)
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (CANVAS_SIZE[0] - text_width) // 2
        text_y = (title_area_height - 48) // 2

        # 白アウトライン
        for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            draw.text((text_x + dx, text_y + dy), title, font=font, fill="#FFFFFF")
        # 黒文字
        draw.text((text_x, text_y), title, font=font, fill="#000000")

        # 外枠
        draw.rectangle(
            [(5, 5), (CANVAS_SIZE[0] - 5, CANVAS_SIZE[1] - 5)],
            outline="#5D4037", width=10
        )

        return img

    def create_placeholder_panel(self, panel_number: int, description: str) -> Image.Image:
        """プレースホルダーパネルを生成（実際のAPI呼び出し前のテスト用）"""
        img = Image.new("RGB", CANVAS_SIZE, "#FFFFFF")
        draw = ImageDraw.Draw(img)

        # 背景色（パネル番号に応じて変更）
        bg_colors = ["#FFE4E1", "#E0FFFF", "#F0FFF0", "#FFF0F5"]
        draw.rectangle(
            [(50, 50), (CANVAS_SIZE[0] - 50, CANVAS_SIZE[1] - 50)],
            fill=bg_colors[panel_number - 1]
        )

        # パネル番号
        font = self._get_font(72, bold=True)
        panel_names = ["起", "承", "転", "結"]
        text = f"{panel_names[panel_number - 1]}（{panel_number}コマ目）"
        draw.text((100, 100), text, font=font, fill="#333333")

        # 説明文
        font_small = self._get_font(24)
        # 長い説明文を折り返し
        max_width = CANVAS_SIZE[0] - 200
        words = description
        lines = []
        current_line = ""
        for char in words:
            test_line = current_line + char
            bbox = draw.textbbox((0, 0), test_line, font=font_small)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)

        y = 250
        for line in lines:
            draw.text((100, y), line, font=font_small, fill="#666666")
            y += 35

        # 外枠
        draw.rectangle(
            [(5, 5), (CANVAS_SIZE[0] - 5, CANVAS_SIZE[1] - 5)],
            outline="#5D4037", width=10
        )

        return img

    def draw_panel_with_dialogues(
        self, 
        img: Image.Image, 
        panel: dict,
        is_final_panel: bool = False
    ) -> Image.Image:
        """
        パネルにセリフ（吹き出し）を描画

        Args:
            img: ベースとなるパネル画像
            panel: パネル情報（dialogue配列を含む）
            is_final_panel: 4コマ目（オチ）かどうか
        
        Returns:
            吹き出しが描画された画像
        """
        draw = ImageDraw.Draw(img)
        dialogues = panel.get("dialogue", [])
        
        # 吹き出しの配置位置を計算（簡易的な自動配置）
        num_dialogues = len(dialogues)
        bubble_height = 100
        bubble_width = 280
        start_y = 400
        spacing = 120

        for i, dialogue in enumerate(dialogues):
            character = dialogue.get("character", "")
            text = dialogue.get("text", "")
            bubble_type = dialogue.get("bubble_type", "normal")
            keyword = dialogue.get("keyword", "")

            # 吹き出しの位置を計算
            if i % 2 == 0:
                x1 = 80
            else:
                x1 = CANVAS_SIZE[0] - bubble_width - 80
            
            y1 = start_y + i * spacing
            x2 = x1 + bubble_width
            y2 = y1 + bubble_height

            # しっぽの位置（キャラクターの方向を想定）
            tail_x = x1 + bubble_width // 2
            tail_y = y2 + 30

            # 吹き出しタイプの判定
            is_tsukkomi = bubble_type == "tsukkomi" or (is_final_panel and i == num_dialogues - 1)
            is_monologue = bubble_type == "monologue"
            is_thought = bubble_type == "thought"

            # 吹き出しを描画
            self.bubble_renderer.draw_speech_bubble(
                draw=draw,
                character=character,
                text=text,
                position=(x1, y1, x2, y2),
                tail_point=(tail_x, tail_y),
                is_tsukkomi=is_tsukkomi,
                is_monologue=is_monologue,
                is_thought=is_thought,
                keyword=keyword if is_tsukkomi else None,
                font_size=24
            )

        return img

    def create_panel_with_dialogues(
        self, 
        panel_number: int, 
        panel: dict,
        scenario: dict = None
    ) -> Image.Image:
        """パネルを生成し、セリフを描画"""
        description = panel.get("description", "")
        is_final_panel = panel_number == 4

        # Gemini APIで画像生成を試行
        img = None
        if self.client and scenario:
            img = self.generate_panel_with_gemini(panel, scenario, panel_number)
        
        # Gemini生成失敗時はプレースホルダーを使用
        if img is None:
            img = self.create_placeholder_panel(panel_number, description)

        # セリフを描画
        img = self.draw_panel_with_dialogues(img, panel, is_final_panel)

        return img

    def generate_all_panels(self, scenario: dict, output_dir: Path) -> list[Path]:
        """全パネルを生成（吹き出し描画付き）"""
        output_files = []
        title = scenario.get("title", "無題")
        panels = scenario.get("panels", [])

        for i, panel in enumerate(panels, start=1):
            print(f"[Module3] パネル{i}を生成中...")
            
            # パネルを生成（吹き出し付き）
            img = self.create_panel_with_dialogues(i, panel, scenario)
            
            # 1コマ目の場合はタイトルを追加
            if i == 1:
                title_img = self.create_title_panel(title)
                # タイトルとパネルを結合
                combined = Image.new("RGB", (CANVAS_SIZE[0], CANVAS_SIZE[1] + 150), "#FFFFFF")
                combined.paste(title_img.crop((0, 0, CANVAS_SIZE[0], 150)), (0, 0))
                combined.paste(img, (0, 150))
                img = combined
            
            output_path = output_dir / f"4koma_panel_{i:02d}.png"
            img.save(output_path)
            output_files.append(output_path)
            print(f"[Module3] 保存: {output_path}")

        return output_files

    def combine_panels(self, panel_files: list[Path], output_path: Path) -> None:
        """全パネルを1枚に結合"""
        panels = [Image.open(f) for f in panel_files]
        
        # 縦に結合
        total_height = sum(p.height for p in panels)
        max_width = max(p.width for p in panels)
        
        combined = Image.new("RGB", (max_width, total_height), "#FFFFFF")
        y_offset = 0
        for panel in panels:
            combined.paste(panel, (0, y_offset))
            y_offset += panel.height

        combined.save(output_path)
        print(f"[Module3] 結合画像保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="画像生成")
    parser.add_argument("--scenario", required=True, help="検証済みシナリオJSON")
    parser.add_argument("--spec", required=True, help="manga_spec.ymlのパス")
    parser.add_argument("--characters", required=True, help="キャラクター画像フォルダ")
    parser.add_argument("--output", required=True, help="出力フォルダ")
    args = parser.parse_args()

    # シナリオ読み込み
    with open(args.scenario, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    # 出力ディレクトリ作成
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 画像生成
    generator = ImageGenerator(args.spec, args.characters)
    panel_files = generator.generate_all_panels(scenario, output_dir)

    # 結合
    combined_path = output_dir / "4koma_combined.png"
    generator.combine_panels(panel_files, combined_path)

    print(f"[Module3] 画像生成完了: {len(panel_files)}枚 + 結合画像1枚")


if __name__ == "__main__":
    main()
