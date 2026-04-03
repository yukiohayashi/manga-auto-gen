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
        # GitHub Actions環境とローカル環境の両方に対応
        font_paths = [
            # GitHub Actions (Ubuntu)
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            # macOS
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()

    def _get_title_font(self, size: int) -> ImageFont.FreeTypeFont:
        """タイトル用フォントを取得（太字）"""
        font_paths = [
            # GitHub Actions (Ubuntu) - Noto Sans CJK
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
            # macOS
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        print("[Module3] 警告: 日本語フォントが見つかりません。デフォルトフォントを使用します。")
        return ImageFont.load_default()

    def generate_panel_prompt(self, panel: dict, scenario: dict, panel_number: int) -> str:
        """Gemini画像生成用のプロンプトを生成"""
        characters = panel.get("characters", [])
        description = panel.get("description", "")
        background = panel.get("background", "シンプルな背景")
        effects = panel.get("effects", [])
        dialogues = panel.get("dialogue", [])
        panel_names = ["起", "承", "転", "結"]
        
        # セリフを整形（吹き出しの色と内容を指定）
        dialogue_instructions = []
        if dialogues:
            for d in dialogues:
                char = d.get("character", "")
                text = d.get("text", "")
                bubble_type = d.get("type", "normal")
                
                # 吹き出しの色を決定
                if bubble_type == "thought" or "モノローグ" in str(d):
                    bubble_color = "白い雲形の吹き出し"
                elif bubble_type == "shout" or "！" in text or "!!" in text:
                    bubble_color = "黄色いギザギザの吹き出し"
                else:
                    bubble_color = "白い楕円の吹き出し"
                
                dialogue_instructions.append(f"- {bubble_color}に「{text}」と書く")

        # 英語プロンプト（Geminiは英語の方が指示を正確に理解する）
        prompt = f"""
Generate a single panel of Japanese 4-koma manga.

CRITICAL RULES - DO NOT VIOLATE:
- NO speech bubbles of any kind
- NO text, letters, or words anywhere in the image
- NO character names visible
- Characters only - no dialogue elements
- NO children - all characters are ADULTS in their 20s-30s

STYLE:
- Japanese shoujo manga style
- Cel shading (no gradients)
- Pastel colors, low saturation
- Dark brown border (#5D4037)

CHARACTER AGES (IMPORTANT):
- All characters are ADULTS (20-30 years old)
- "元高校球児" means "former high school baseball player" - he is NOW an ADULT man in his 20s
- Do NOT draw children or teenagers

SCENE (Panel {panel_number}):
{description}

BACKGROUND:
{background}

CHARACTER CLOTHING:
- Use EXACT same clothing as shown in the character reference sheet
- Do not change colors, design, or patterns

TECHNICAL:
- Aspect ratio: 1:1 (square)
- Dark brown border (#5D4037)
- Clean illustration without any text or speech bubbles
"""
        return prompt

    def _get_character_images_for_panel(self, panel: dict) -> list:
        """パネルに登場するキャラクターの参照画像を取得"""
        from google.genai import types
        character_parts = []
        characters = panel.get("characters", [])
        
        for char_name in characters:
            if char_name in self.character_images:
                img = self.character_images[char_name]
                # 画像をbase64エンコード
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()
                
                character_parts.append(types.Part.from_bytes(
                    data=img_bytes,
                    mime_type="image/png"
                ))
                print(f"[Module3] キャラクター参照画像追加: {char_name}")
        
        return character_parts

    def generate_panel_with_gemini(self, panel: dict, scenario: dict, panel_number: int, max_retries: int = 3) -> Optional[Image.Image]:
        """Gemini APIで画像を生成（リトライ機能付き）"""
        if not self.client:
            return None
        
        prompt = self.generate_panel_prompt(panel, scenario, panel_number)
        from google.genai import types
        import time
        
        # キャラクター参照画像を取得
        character_parts = self._get_character_images_for_panel(panel)
        
        # コンテンツを構築（参照画像 + プロンプト）
        contents = []
        if character_parts:
            contents.extend(character_parts)
            contents.append(f"上記のキャラクターシートを参照して、以下の指示に従って画像を生成してください。キャラクターの外見（髪型、服装、顔の特徴）を正確に再現してください。\n\n{prompt}")
        else:
            contents.append(prompt)
        
        for attempt in range(max_retries):
            print(f"[Module3] Gemini APIで画像生成中... (パネル{panel_number}, 試行{attempt + 1}/{max_retries})")
            
            try:
                response = self.client.models.generate_content(
                    model="gemini-3-pro-image-preview",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    )
                )
                
                # レスポンスから画像を抽出
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data and hasattr(part.inline_data, 'data') and part.inline_data.data:
                        print(f"[Module3] DEBUG: inline_data found, mime_type = {getattr(part.inline_data, 'mime_type', 'unknown')}")
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        image = Image.open(BytesIO(image_data))
                        print(f"[Module3] Gemini画像生成成功: パネル{panel_number}")
                        return image.resize(CANVAS_SIZE)
                
                print(f"[Module3] 警告: Gemini応答に画像が含まれていません（試行{attempt + 1}）")
                
            except Exception as e:
                print(f"[Module3] Gemini画像生成エラー (試行{attempt + 1}): {e}")
            
            # リトライ前に少し待機
            if attempt < max_retries - 1:
                time.sleep(2)
        
        print(f"[Module3] パネル{panel_number}の画像生成に失敗しました（{max_retries}回試行）")
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
        吹き出しは画像の上下左右に自由に配置する。

        Args:
            img: ベースとなるパネル画像
            panel: パネル情報（dialogue配列を含む）
            is_final_panel: 4コマ目（オチ）かどうか
        
        Returns:
            吹き出しが描画された画像
        """
        dialogues = panel.get("dialogue", [])
        num_dialogues = len(dialogues)
        if num_dialogues == 0:
            return img

        panel_w, panel_h = img.size
        font_size = 44
        margin = 15
        bubble_gap = 15

        # === 1. 各吹き出しのサイズを計算 ===
        bubble_infos = []
        for i, dialogue in enumerate(dialogues):
            text = dialogue.get("text", "")
            bubble_type = dialogue.get("type", dialogue.get("bubble_type", "normal"))
            is_caption = bubble_type == "caption"

            if is_caption:
                text_clean = text.replace("「", "").replace("」", "")
                caption_font_size = 28
                bw = len(text_clean) * caption_font_size + 40
                bh = caption_font_size + 24
            else:
                # 吹き出しの高さはパネル全体を使う
                bh = panel_h - margin * 2
                # 高さに合わせて1列あたりの文字数を逆算
                char_h = font_size + 12
                padding = 30
                max_chars = max(1, (bh - padding * 2) // char_h)
                _, bw, _ = self.bubble_renderer.calculate_vertical_layout(
                    text, font_size, max_chars_per_col=max_chars
                )
                bw = int(bw * 1.2)
                # パネル幅の半分を超えないように制限
                max_bw = int(panel_w * 0.55)
                if bw > max_bw:
                    bw = max_bw

            bubble_infos.append({
                "dialogue": dialogue,
                "width": bw,
                "height": bh,
                "is_caption": is_caption,
            })

        # === 2. 吹き出し配置位置を決定 ===
        # 配置パターン: 上下左右に分散（漫画らしい自然な配置）
        # positions: (横位置, 縦位置) のペア
        #   横: "right", "left"
        #   縦: "top", "bottom"
        if num_dialogues == 1:
            positions = [("right", "top")]
        elif num_dialogues == 2:
            positions = [("right", "top"), ("left", "bottom")]
        elif num_dialogues == 3:
            positions = [("right", "top"), ("left", "bottom"), ("right", "bottom")]
        else:
            positions = [("right", "top"), ("left", "bottom"), ("right", "bottom"), ("left", "top")]

        draw = ImageDraw.Draw(img)

        for i, info in enumerate(bubble_infos):
            dialogue = info["dialogue"]
            character = dialogue.get("character", "")
            text = dialogue.get("text", "")
            bubble_type = dialogue.get("type", dialogue.get("bubble_type", "normal"))
            keyword = dialogue.get("highlight", dialogue.get("keyword", ""))
            bw = info["width"]
            bh = info["height"]
            is_caption = info["is_caption"]

            if is_caption:
                # キャプションはパネル下部中央に配置（キャラの下あたり）
                x1 = (panel_w - bw) // 2
                y1 = panel_h - bh - margin - 30
            else:
                pos = positions[i % len(positions)]
                h_pos, v_pos = pos

                # 横位置
                if h_pos == "right":
                    x1 = panel_w - bw - margin
                else:
                    x1 = margin

                # 縦位置
                if v_pos == "top":
                    y1 = margin
                else:
                    y1 = panel_h - bh - margin

            # パネル内に収まるように調整
            x1 = max(margin, min(x1, panel_w - bw - margin))
            y1 = max(margin, min(y1, panel_h - bh - margin))
            x2 = x1 + bw
            y2 = y1 + bh

            # 吹き出しタイプの判定
            is_tsukkomi = bubble_type in ["tsukkomi", "shout"] or (is_final_panel and i == num_dialogues - 1)
            is_monologue = bubble_type == "monologue"
            is_thought = bubble_type == "thought"

            # パネル端に接する辺を判定（ギザギザをクリップ）
            edge_threshold = margin + 5
            clip_edges = set()
            if y1 <= edge_threshold:
                clip_edges.add("top")
            if y2 >= panel_h - edge_threshold:
                clip_edges.add("bottom")
            if x2 >= panel_w - edge_threshold:
                clip_edges.add("right")
            if x1 <= edge_threshold:
                clip_edges.add("left")

            # しっぽの位置（クリップされていない辺にのみ描画）
            tail_x = None
            tail_y = None
            if not is_caption:
                pos = positions[i % len(positions)]
                _, v_pos = pos
                if v_pos == "top" and "bottom" not in clip_edges:
                    tail_x = x1 + bw // 2
                    tail_y = y2 + 20
                elif v_pos == "bottom" and "top" not in clip_edges:
                    tail_x = x1 + bw // 2
                    tail_y = y1 - 20

            self.bubble_renderer.draw_speech_bubble(
                draw=draw,
                character=character,
                text=text,
                position=(x1, y1, x2, y2),
                tail_point=(tail_x, tail_y) if tail_x is not None else None,
                is_tsukkomi=is_tsukkomi,
                is_monologue=is_monologue,
                is_thought=is_thought,
                is_caption=is_caption,
                keyword=keyword if is_tsukkomi else None,
                font_size=font_size,
                clip_edges=clip_edges,
                img=img
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

    def generate_all_panels(self, scenario: dict, output_dir: Path, max_panels: int = 4) -> list[Path]:
        """全パネルを生成（吹き出し描画付き）
        
        Args:
            scenario: シナリオデータ
            output_dir: 出力ディレクトリ
            max_panels: 生成するパネル数（デバッグ用: 1-4）
        """
        output_files = []
        title = scenario.get("title", "無題")
        panels = scenario.get("panels", [])[:max_panels]  # max_panels枚まで

        for i, panel in enumerate(panels, start=1):
            print(f"[Module3] パネル{i}を生成中...")
            
            # パネルを生成（吹き出し付き）
            img = self.create_panel_with_dialogues(i, panel, scenario)
            
            # 1コマ目の場合はタイトルを追加
            if i == 1:
                print(f"[Module3] タイトル「{title}」を追加中...")
                title_height = 100
                panel_width = img.width
                panel_height = img.height
                
                # タイトル付きの新しい画像を作成（パネルと同じ幅）
                combined = Image.new("RGB", (panel_width, panel_height + title_height), "#FFFFFF")
                
                # タイトルエリア背景（パステルピンク）
                title_area = Image.new("RGB", (panel_width, title_height), "#FFE4E1")
                draw = ImageDraw.Draw(title_area)
                
                # フォント取得（日本語対応）
                font = self._get_title_font(48)
                
                # タイトルテキストの位置計算
                text_bbox = draw.textbbox((0, 0), title, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (panel_width - text_width) // 2
                text_y = (title_height - text_height) // 2
                
                # 白アウトライン（太め）
                outline_offsets = [(-3, -3), (-3, 0), (-3, 3), (0, -3), (0, 3), (3, -3), (3, 0), (3, 3)]
                for dx, dy in outline_offsets:
                    draw.text((text_x + dx, text_y + dy), title, font=font, fill="#FFFFFF")
                # 黒文字
                draw.text((text_x, text_y), title, font=font, fill="#000000")
                
                # 境界線（上部と下部）
                draw.line([(0, 2), (panel_width, 2)], fill="#5D4037", width=4)
                draw.line([(0, title_height - 2), (panel_width, title_height - 2)], fill="#5D4037", width=4)
                
                # 結合
                combined.paste(title_area, (0, 0))
                combined.paste(img, (0, title_height))
                
                # 外枠（茶色）
                draw_combined = ImageDraw.Draw(combined)
                draw_combined.rectangle(
                    [(0, 0), (panel_width - 1, panel_height + title_height - 1)],
                    outline="#5D4037", width=4
                )
                
                img = combined
                print(f"[Module3] タイトル追加完了")
            
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
    parser.add_argument("--panels", type=int, default=4, help="生成するパネル数（デバッグ用: 1-4）")
    parser.add_argument("--no-combine", action="store_true", help="結合画像を生成しない")
    args = parser.parse_args()

    # シナリオ読み込み
    with open(args.scenario, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    # 出力ディレクトリ作成
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 画像生成
    generator = ImageGenerator(args.spec, args.characters)
    panel_files = generator.generate_all_panels(scenario, output_dir, max_panels=args.panels)

    # 結合（--no-combineが指定されていない場合のみ）
    if not args.no_combine and len(panel_files) == 4:
        combined_path = output_dir / "4koma_combined.png"
        generator.combine_panels(panel_files, combined_path)
        print(f"[Module3] 画像生成完了: {len(panel_files)}枚 + 結合画像1枚")
    else:
        print(f"[Module3] 画像生成完了: {len(panel_files)}枚")


if __name__ == "__main__":
    main()
