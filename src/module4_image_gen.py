#!/usr/bin/env python3
"""
モジュール3：画像生成＆レイアウト描画

キャラクターリファレンスに基づき、Gemini APIで各コマを生成し、
吹き出しを描画・結合する。

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

    def __init__(self, assets_path: str, api_key: str = None):
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
            "なおみ": "naomi.png",
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
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
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
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
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

    # デフォルトのキャラクター服装（episode.jsonで上書き可能）
    DEFAULT_OUTFITS = {
        "はな": "white and blue horizontal striped T-shirt, light blue jeans",
        "さき": "pink cardigan over white top, long brown hair",
        "なおみ": "glasses (MUST wear glasses), beige knit sweater, brown skirt",
        "まさと": "casual shirt, jeans",
        "ともや": "hoodie, casual pants",
        "ようた": "polo shirt, chinos",
    }

    def _format_character_outfits(self, characters: list, episode_outfits: dict) -> str:
        """パネルに登場するキャラクターの服装指定を生成"""
        lines = []
        for char in characters:
            # エピソード固有の服装があればそれを使用、なければデフォルト
            outfit = episode_outfits.get(char, self.DEFAULT_OUTFITS.get(char, "casual outfit"))
            lines.append(f"- {char}: {outfit}")
        return "\n".join(lines)

    def _compute_bubble_placement(self, panel: dict) -> str:
        """
        セリフ量と配置を分析し、Gemini構図指示用の空きスペース情報を返す。

        縦書き漫画の読み進め方ルール:
        - 日本の縦書き漫画は「右から左」へ読み進める（右=過去、左=未来）
        - セリフが2つある場合: 1つ目=右上、2つ目=左下
        - セリフが1つの場合: 中央または自然な位置（無理に右に寄せない）
        - キャラクターも同様に: 先に話す人物が右側、後に話す人物が左側
        """
        dialogues = panel.get("dialogue", [])
        speech_items = [d for d in dialogues if d.get("type", "") not in ("effect_text", "caption")]
        num_speech = len(speech_items)

        if num_speech == 0:
            return "COMPOSITION: The BACKGROUND must fill the ENTIRE canvas. Make sure characters are clearly visible."
        elif num_speech == 1:
            # セリフ1つ: 中央か自然な位置。右上に無理に寄せない。
            return (
                "COMPOSITION: The BACKGROUND must fill the ENTIRE canvas. "
                "Characters should be clearly visible. "
                "Leave some empty space at the top-center or top area for a single speech bubble. "
                "Do NOT force characters to one side."
            )
        else:
            # セリフ2つ以上: 右から左へ読む縦書き漫画ルール
            # 1つ目のセリフ=右上エリア、2つ目のセリフ=左下エリア
            return (
                "COMPOSITION: The BACKGROUND must fill the ENTIRE canvas. "
                "IMPORTANT - Japanese manga reads RIGHT to LEFT (right=past, left=future). "
                "The character who speaks FIRST should be positioned on the RIGHT side of the panel. "
                "The character who speaks SECOND should be positioned on the LEFT side of the panel. "
                "Leave empty space in the TOP-RIGHT corner for the first speech bubble. "
                "Leave empty space in the BOTTOM-LEFT corner for the second speech bubble. "
                "Characters must be clearly visible and not hidden by speech bubbles."
            )

    def generate_panel_prompt(self, panel: dict, scenario: dict, panel_number: int) -> str:
        """Gemini画像生成用のプロンプトを生成"""
        characters = panel.get("characters", [])
        description = panel.get("description", "")
        background = panel.get("background", "シンプルな背景")
        effects = panel.get("effects", [])
        dialogues = panel.get("dialogue", [])
        
        # エピソード固有の服装設定を取得
        character_outfits = scenario.get("character_outfits", {})

        composition_hint = self._compute_bubble_placement(panel)

        prompt = f"""
Generate ONE SINGLE PANEL (not multiple panels, not a 4-panel comic strip).
This is just ONE scene, ONE illustration.

CRITICAL RULES - DO NOT VIOLATE:
- Generate ONLY ONE panel - DO NOT create a 4-panel layout or comic strip
- NO panel borders or divisions - this is a SINGLE illustration
- NO character reference sheets or expression charts in the output
- DO NOT show multiple face expressions or head shots - draw full scene only
- NO speech bubbles of any kind
- NO text, letters, or words anywhere in the image
- NO character names visible
- Characters only - no dialogue elements
- NO children - all characters are ADULTS in their 20s-30s

STYLE (CRITICAL - MUST match reference images):
- Copy the EXACT art style from the character reference sheets
- Same line thickness, same eye style, same face proportions as reference
- Japanese shoujo manga style with soft features
- Cel shading (no gradients)
- Pastel colors, low saturation
- No border or frame around the image
- DO NOT change the art style - keep it consistent with reference images

CHARACTER AGES (IMPORTANT):
- All characters are ADULTS (20-30 years old)
- "元高校球児" means "former high school baseball player" - he is NOW an ADULT man in his 20s
- Do NOT draw children or teenagers

{composition_hint}

SCENE (Panel {panel_number}):
{description}

BACKGROUND:
{background}

CHARACTER APPEARANCE (CRITICAL - MUST match reference images EXACTLY):
- FACE: Copy the EXACT face, eyes, nose, mouth from the reference image
- HAIR: Copy the EXACT hairstyle, hair color, hair length from the reference image
- CLOTHING: Use EXACT same outfit for each character throughout ALL panels
- Do NOT create new character designs - ONLY copy from reference images
- If you cannot match the reference, do NOT draw that character differently
{self._format_character_outfits(characters, character_outfits)}

COMPOSITION (CRITICAL - NO empty space):
- Fill the ENTIRE panel with the scene - NO white or empty areas
- Characters and background must extend to ALL edges of the image
- NO blank corners or margins inside the panel

OBJECT RULES:
- When a character holds a smartphone facing themselves, the VIEWER sees only the BACK of the phone (a dark/black rectangle). NEVER show the screen content to the viewer.

TECHNICAL:
- Aspect ratio: 1:1 (square)
- No border or frame - the illustration should extend to the edges
- Clean illustration without any text or speech bubbles
"""
        effect_texts = [d for d in dialogues if d.get("type") == "effect_text"]
        if effect_texts:
            prompt += "\nMANGA EFFECT TEXT (draw as stylized manga sound effects / emotion text directly on the image, NOT in speech bubbles):\n"
            for et in effect_texts:
                char = et.get("character", "")
                text = et.get("text", "")
                prompt += f"- Draw '{text}' as a large manga-style effect text near {char}'s character\n"

        return prompt

    def _get_character_images_for_panel(self, panel: dict) -> list:
        """パネルに登場するキャラクターの参照画像を取得"""
        from google.genai import types
        character_parts = []
        characters = panel.get("characters", [])
        
        for char_name in characters:
            if char_name in self.character_images:
                img = self.character_images[char_name]
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
        
        character_parts = self._get_character_images_for_panel(panel)
        
        contents = []
        if character_parts:
            contents.extend(character_parts)
            contents.append(f"IMPORTANT: Study the character reference sheet(s) above VERY carefully. You MUST reproduce the EXACT same face, hairstyle, hair color, eye shape, eye color, facial proportions, and clothing as shown in the reference sheet. The generated character must look like the SAME PERSON as in the reference. Do NOT change the art style of the face.\n\n{prompt}")
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
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data and hasattr(part.inline_data, 'data') and part.inline_data.data:
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        image = Image.open(BytesIO(image_data))
                        print(f"[Module3] Gemini画像生成成功: パネル{panel_number}")
                        return image.resize(CANVAS_SIZE)
                
                print(f"[Module3] 警告: Gemini応答に画像が含まれていません（試行{attempt + 1}）")
                
            except Exception as e:
                print(f"[Module3] Gemini画像生成エラー (試行{attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2)
        
        print(f"[Module3] パネル{panel_number}の画像生成に失敗しました（{max_retries}回試行）")
        return None

    def create_placeholder_panel(self, panel_number: int, description: str) -> Image.Image:
        """プレースホルダーパネルを生成"""
        img = Image.new("RGB", CANVAS_SIZE, "#FFFFFF")
        draw = ImageDraw.Draw(img)

        bg_colors = ["#FFE4E1", "#E0FFFF", "#F0FFF0", "#FFF0F5"]
        draw.rectangle(
            [(50, 50), (CANVAS_SIZE[0] - 50, CANVAS_SIZE[1] - 50)],
            fill=bg_colors[panel_number - 1]
        )

        font = self._get_font(72, bold=True)
        panel_names = ["起", "承", "転", "結"]
        text = f"{panel_names[panel_number - 1]}（{panel_number}コマ目）"
        draw.text((100, 100), text, font=font, fill="#333333")

        font_small = self._get_font(24)
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

        return img

    def draw_panel_with_dialogues(
        self, 
        img: Image.Image, 
        panel: dict,
        is_final_panel: bool = False
    ) -> Image.Image:
        """パネルにセリフ（吹き出し）を描画"""
        dialogues = panel.get("dialogue", [])
        if not dialogues:
            return img

        # アンチエイリアス: 2倍解像度で描画してダウンスケール
        SS = 2
        orig_size = img.size
        img = img.resize((orig_size[0] * SS, orig_size[1] * SS), Image.LANCZOS)

        panel_w, panel_h = img.size
        font_size = 52 * SS
        border_width = 10 * SS
        margin = border_width + 10 * SS

        speech_items = []
        caption_items = []

        for dialogue in dialogues:
            bubble_type = dialogue.get("type", dialogue.get("bubble_type", "normal"))
            if bubble_type == "effect_text":
                continue
            elif bubble_type == "caption":
                caption_items.append(dialogue)
            else:
                speech_items.append(dialogue)

        num_speech = len(speech_items)

        # 吹き出しサイズ計算
        max_h = int(panel_h * 0.95)
        if num_speech == 1:
            available_h = min(panel_h - margin * 2, max_h)
        elif num_speech == 2:
            available_h = min(panel_h - margin * 2, max_h)
        else:
            available_h = (panel_h - margin * 3) // 2

        bubble_infos = []
        has_long_text = any(len(d.get("text", "")) > 20 for d in speech_items)
        if has_long_text and num_speech == 1:
            max_bw = int(panel_w * 0.32)
        else:
            max_bw = int(panel_w * 0.45)

        for dialogue in speech_items:
            text = dialogue.get("text", "")
            text_len = len(text.replace('\n', ''))
            
            # 改行が含まれている場合は、改行で分割した列数を使用
            if '\n' in text:
                lines = text.split('\n')
                num_cols = len(lines)
                chars_per_col = max(len(line) for line in lines)
                force_cols = True
            else:
                force_cols = text_len <= 12 and num_speech >= 2
                num_cols = 2 if force_cols else None
                chars_per_col = None

            fs = font_size
            min_fs = 20 * SS
            while fs >= min_fs:
                ch = fs + 4 * SS
                cw = fs + 16 * SS
                pd = 35 * SS
                if force_cols and num_cols:
                    max_chars_col = chars_per_col
                else:
                    max_chars_col = max(1, (available_h - pd * 2) // ch)
                    num_cols = max(1, -(-text_len // max_chars_col))
                bw = num_cols * cw + pd * 2 + 10 * SS
                if bw <= max_bw:
                    break
                fs -= 2 * SS

            ch = fs + 4 * SS
            cw = fs + 16 * SS
            pd = 50 * SS
            if force_cols and chars_per_col:
                bh = min(available_h, max(chars_per_col * ch + pd * 2, 150 * SS))
            else:
                max_chars_col = max(1, (available_h - pd * 2) // ch)
                num_cols = max(1, -(-text_len // max_chars_col))
                chars_per_col = min(max_chars_col, -(-text_len // num_cols))
                bh = min(available_h, max(chars_per_col * ch + pd * 2, 200 * SS))
            bw = num_cols * cw + pd * 2 + 10 * SS
            bw = min(bw, max_bw)

            bubble_infos.append({
                "dialogue": dialogue,
                "width": bw, "height": bh,
                "is_caption": False,
                "font_size": fs,
            })

        for dialogue in caption_items:
            text = dialogue.get("text", "")
            text_clean = text.replace("「", "").replace("」", "")
            caption_fs = 28 * SS
            bw = len(text_clean) * caption_fs + 40 * SS
            bh = caption_fs + 24 * SS
            bubble_infos.append({
                "dialogue": dialogue,
                "width": bw, "height": bh,
                "is_caption": True,
                "font_size": caption_fs,
            })

        def get_bubble_position(dialogue: dict, idx: int, total: int) -> tuple:
            """
            吹き出し位置を決定。

            縦書き漫画の読み進め方ルール（右=過去、左=未来）:
            - セリフが1つ: 中央上部（無理に右に寄せない）
            - セリフが2つ以上:
                idx=0 (1つ目) → 右上
                idx=1 (2つ目) → 左下
                idx=2以降     → 交互に配置
            - bubble_positionが明示指定されている場合はそれを優先
            """
            manual_pos = dialogue.get("bubble_position", "")
            if manual_pos:
                h_pos = "left" if "left" in manual_pos else "right"
                v_pos = "bottom" if "bottom" in manual_pos else "top"
                if manual_pos in ["left", "right"]:
                    v_pos = "top" if idx == 0 else "bottom"
                return (h_pos, v_pos)

            if total == 1:
                # セリフ1つ: 中央配置（右に無理に寄せない）
                return ("center", "top")
            else:
                # 縦書き右から左ルール: 1つ目=右上、2つ目=左下、以降交互
                if idx == 0:
                    return ("right", "top")
                elif idx == 1:
                    return ("left", "bottom")
                else:
                    # 3つ目以降は交互
                    h_pos = "right" if idx % 2 == 0 else "left"
                    v_pos = "top" if idx % 2 == 0 else "bottom"
                    return (h_pos, v_pos)

        positions = []
        speech_count = sum(1 for info in bubble_infos if not info["is_caption"])
        speech_i = 0
        for i, info in enumerate(bubble_infos):
            if not info["is_caption"]:
                positions.append(get_bubble_position(info["dialogue"], speech_i, speech_count))
                speech_i += 1

        draw = ImageDraw.Draw(img)
        speech_idx = 0

        for info in bubble_infos:
            dialogue = info["dialogue"]
            character = dialogue.get("character", "")
            text = dialogue.get("text", "")
            bubble_type = dialogue.get("type", dialogue.get("bubble_type", "normal"))
            keyword = dialogue.get("highlight", dialogue.get("keyword", ""))
            bw = info["width"]
            bh = info["height"]
            is_caption = info["is_caption"]

            if is_caption:
                x1 = (panel_w - bw) // 2
                y1 = panel_h - bh - margin - 30 * SS
            else:
                pos = positions[speech_idx % len(positions)]
                h_pos, v_pos = pos

                if h_pos == "right":
                    x1 = panel_w - bw
                elif h_pos == "left":
                    x1 = margin
                else:  # center
                    x1 = (panel_w - bw) // 2
                y1 = margin if v_pos == "top" else panel_h - bh - margin

                speech_idx += 1

            x1 = max(0, min(x1, panel_w - bw))
            y1 = max(0, min(y1, panel_h - bh))
            x2 = x1 + bw
            y2 = y1 + bh

            is_tsukkomi = bubble_type in ["tsukkomi", "shout"]
            is_monologue = bubble_type == "monologue"
            is_thought = bubble_type == "thought"

            border_threshold = border_width + 2 * SS
            clip_edges = set()
            if y1 <= border_threshold:
                clip_edges.add("top")
            if y2 >= panel_h - border_threshold:
                clip_edges.add("bottom")
            if x2 >= panel_w - border_threshold:
                clip_edges.add("right")
            if x1 <= border_threshold:
                clip_edges.add("left")

            bubble_fs = info.get("font_size", font_size)
            self.bubble_renderer.draw_speech_bubble(
                draw=draw,
                character=character,
                text=text,
                position=(x1, y1, x2, y2),
                is_tsukkomi=is_tsukkomi,
                is_monologue=is_monologue,
                is_thought=is_thought,
                is_caption=is_caption,
                keyword=keyword or None,
                font_size=bubble_fs,
                clip_edges=clip_edges,
                img=img
            )

        draw.rectangle([0, 0, panel_w - 1, panel_h - 1], outline="#5D4037", width=border_width)

        img = img.resize(orig_size, Image.LANCZOS)
        return img

    def create_panel_with_dialogues(
        self, 
        panel_number: int, 
        panel: dict,
        scenario: dict = None
    ) -> Image.Image:
        description = panel.get("description", "")
        is_final_panel = panel_number == 4

        img = None
        if self.client and scenario:
            img = self.generate_panel_with_gemini(panel, scenario, panel_number)
        
        if img is None:
            img = self.create_placeholder_panel(panel_number, description)

        img = self.draw_panel_with_dialogues(img, panel, is_final_panel)

        return img

    def generate_all_panels(self, scenario: dict, output_dir: Path, max_panels: int = 4, only_panels: list[int] = None) -> list[Path]:
        output_files = []
        title = scenario.get("title", "無題")
        panels = scenario.get("panels", [])[:max_panels]

        for i, panel in enumerate(panels, start=1):
            output_path = output_dir / f"4koma_panel_{i:02d}.png"

            if only_panels and i not in only_panels:
                if output_path.exists():
                    output_files.append(output_path)
                    print(f"[Module3] パネル{i}をスキップ（既存画像を維持）")
                else:
                    print(f"[Module3] パネル{i}をスキップ（画像なし）")
                continue

            print(f"[Module3] パネル{i}を生成中...")
            
            img = self.create_panel_with_dialogues(i, panel, scenario)
            
            if i == 1:
                print(f"[Module3] タイトル「{title}」を追加中...")
                title_height = 100
                panel_width = img.width
                panel_height = img.height
                
                # 白背景のタイトルエリア
                combined = Image.new("RGB", (panel_width, panel_height + title_height), "#FFFFFF")
                draw = ImageDraw.Draw(combined)
                
                font = self._get_title_font(48)
                
                # タイトルを白背景の中央に描画
                text_bbox = draw.textbbox((0, 0), title, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                text_x = (panel_width - text_width) // 2
                text_y = (title_height - text_height) // 2 +10
                
                # シンプルに黒文字で描画
                draw.text((text_x, text_y), title, font=font, fill="#000000")
                
                # パネルを下部に貼り付け
                combined.paste(img, (0, title_height))
                
                img = combined
                print(f"[Module3] タイトル追加完了")
            
            white_margin = 30
            padded = Image.new("RGB", (img.width + white_margin * 2, img.height + white_margin * 2), "#FFFFFF")
            padded.paste(img, (white_margin, white_margin))
            img = padded

            img.save(output_path)
            output_files.append(output_path)
            print(f"[Module3] 保存: {output_path}")

        return output_files

    def combine_panels(self, panel_files: list[Path], output_path: Path) -> None:
        panels = [Image.open(f) for f in panel_files]
        
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
    parser.add_argument("--episode", required=True, help="検証済みエピソードJSON")
    parser.add_argument("--characters", required=True, help="キャラクター画像フォルダ")
    parser.add_argument("--output", required=True, help="出力フォルダ")
    parser.add_argument("--panels", type=int, default=4, help="生成するパネル数（デバッグ用: 1-4）")
    parser.add_argument("--no-combine", action="store_true", help="結合画像を生成しない")
    parser.add_argument("--only", type=str, default="", help="再生成するパネル番号（カンマ区切り、例: 1,3）")
    args = parser.parse_args()

    with open(args.episode, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = ImageGenerator(args.characters)
    only_panels = [int(x) for x in args.only.split(",") if x.strip()] if args.only else None
    panel_files = generator.generate_all_panels(scenario, output_dir, max_panels=args.panels, only_panels=only_panels)

    if not args.no_combine and len(panel_files) == 4:
        combined_path = output_dir / "4koma_combined.png"
        generator.combine_panels(panel_files, combined_path)
        print(f"[Module3] 画像生成完了: {len(panel_files)}枚 + 結合画像1枚")
    else:
        print(f"[Module3] 画像生成完了: {len(panel_files)}枚")


if __name__ == "__main__":
    main()
