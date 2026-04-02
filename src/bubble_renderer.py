#!/usr/bin/env python3
"""
吹き出し自動描画モジュール

manga_spec.yml および preflight_check.py の厳格な仕様に基づく
吹き出しとテキストの自動描画を行う。

仕様準拠:
- はな・さき（女性陣）: 黄色 #FFE800、角ばった多角形（丸み禁止）
- まさと・ともや・ようた（男性陣）: パステルブルー #D4E8FF または白
- モノローグ・小声: 白 #FFFFFF
- ツッコミ（オチ）: 黄色ギザギザ爆発型、キーワードは赤文字1.2〜1.5倍
"""

import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


class BubbleShape(Enum):
    """吹き出しの形状タイプ"""
    ANGULAR_POLYGON = "angular_polygon"      # 角ばった多角形（女性陣用）
    SOFT_POLYGON = "soft_polygon"            # 柔らかい多角形（男性陣用）
    OVAL = "oval"                            # 楕円形（モノローグ用）
    EXPLOSION = "explosion"                  # ギザギザ爆発型（ツッコミ用）
    CLOUD = "cloud"                          # 雲型（考え事用）


@dataclass
class BubbleStyle:
    """吹き出しのスタイル定義"""
    fill_color: str
    outline_color: str
    shape: BubbleShape
    outline_width: int = 3


# キャラクター別吹き出しスタイル定義（manga_spec.yml準拠）
CHARACTER_BUBBLE_STYLES = {
    # 女性陣：高彩度黄色、角ばった多角形（丸み禁止）
    "はな": BubbleStyle("#FFE800", "#000000", BubbleShape.ANGULAR_POLYGON),
    "さき": BubbleStyle("#FFE800", "#000000", BubbleShape.ANGULAR_POLYGON),
    
    # 男性陣：パステルブルー、柔らかい多角形または楕円
    "まさと": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON),
    "ともや": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON),
    "ようた": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON),
}

# 特殊吹き出しスタイル
MONOLOGUE_STYLE = BubbleStyle("#FFFFFF", "#000000", BubbleShape.OVAL)
TSUKKOMI_STYLE = BubbleStyle("#FFE800", "#000000", BubbleShape.EXPLOSION, outline_width=4)
THOUGHT_STYLE = BubbleStyle("#FFFFFF", "#000000", BubbleShape.CLOUD)
CAPTION_STYLE = BubbleStyle("#FFFFFF", "#000000", BubbleShape.ANGULAR_POLYGON, outline_width=2)  # 紹介キャプション用

# テキスト色定義
TEXT_COLOR_PRIMARY = "#000000"      # 通常テキスト（黒）
TEXT_COLOR_EMPHASIS = "#FF0000"     # 強調キーワード（赤）

# フォントパス（GitHub Actions環境とローカル環境の両方に対応）
FONT_PATHS = {
    "main": "fonts/NotoSansJP-Black.ttf",
    "emphasis": "fonts/MPLUSRounded1c-ExtraBold.ttf",
    "fallback_mac": "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "fallback_ubuntu": "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "fallback_ubuntu2": "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
}


class BubbleRenderer:
    """吹き出し描画クラス"""

    def __init__(self, font_dir: Optional[Path] = None):
        self.font_dir = font_dir or Path("fonts")
        self._font_cache = {}

    def get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """フォントを取得（キャッシュ付き）"""
        cache_key = (size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_paths_to_try = [
            self.font_dir / "NotoSansJP-Black.ttf",
            self.font_dir / "MPLUSRounded1c-ExtraBold.ttf",
            Path(FONT_PATHS["fallback_ubuntu"]),
            Path(FONT_PATHS["fallback_ubuntu2"]),
            Path(FONT_PATHS["fallback_mac"]),
        ]

        for font_path in font_paths_to_try:
            try:
                font = ImageFont.truetype(str(font_path), size)
                self._font_cache[cache_key] = font
                return font
            except (OSError, IOError):
                continue

        # フォールバック
        font = ImageFont.load_default()
        self._font_cache[cache_key] = font
        return font

    def get_bubble_style(
        self, 
        character: str, 
        is_tsukkomi: bool = False,
        is_monologue: bool = False,
        is_thought: bool = False,
        is_caption: bool = False
    ) -> BubbleStyle:
        """キャラクターと状況に応じた吹き出しスタイルを取得"""
        if is_caption:
            return CAPTION_STYLE
        if is_tsukkomi:
            return TSUKKOMI_STYLE
        if is_monologue:
            return MONOLOGUE_STYLE
        if is_thought:
            return THOUGHT_STYLE
        return CHARACTER_BUBBLE_STYLES.get(character, MONOLOGUE_STYLE)

    def draw_angular_polygon(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """角ばった多角形（六角形ベース）を描画 - 女性陣用"""
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w // 2, y1 + h // 2

        # 六角形の頂点を計算（角ばった形状）
        points = [
            (x1 + w * 0.15, y1),           # 上辺左
            (x1 + w * 0.85, y1),           # 上辺右
            (x2, y1 + h * 0.3),            # 右上
            (x2, y1 + h * 0.7),            # 右下
            (x1 + w * 0.85, y2),           # 下辺右
            (x1 + w * 0.15, y2),           # 下辺左
            (x1, y1 + h * 0.7),            # 左下
            (x1, y1 + h * 0.3),            # 左上
        ]

        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

    def draw_soft_polygon(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """柔らかい多角形を描画 - 男性陣用"""
        x1, y1, x2, y2 = bbox
        
        # 角丸四角形として描画
        radius = min(x2 - x1, y2 - y1) // 6
        draw.rounded_rectangle(bbox, radius=radius, fill=style.fill_color, 
                               outline=style.outline_color, width=style.outline_width)

    def draw_oval(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """楕円形を描画 - モノローグ用"""
        draw.ellipse(bbox, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

    def draw_explosion(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle,
        spikes: int = 12
    ) -> None:
        """ギザギザ爆発型を描画 - ツッコミ用"""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        outer_rx = (x2 - x1) // 2
        outer_ry = (y2 - y1) // 2
        inner_rx = outer_rx * 0.7
        inner_ry = outer_ry * 0.7

        points = []
        for i in range(spikes * 2):
            angle = math.pi * i / spikes - math.pi / 2
            if i % 2 == 0:
                # 外側の頂点
                px = cx + outer_rx * math.cos(angle)
                py = cy + outer_ry * math.sin(angle)
            else:
                # 内側の頂点
                px = cx + inner_rx * math.cos(angle)
                py = cy + inner_ry * math.sin(angle)
            points.append((px, py))

        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

    def draw_cloud(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """雲型を描画 - 考え事用"""
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1

        # 複数の楕円を重ねて雲を表現
        circles = [
            (x1 + w * 0.2, y1 + h * 0.3, w * 0.35, h * 0.5),
            (x1 + w * 0.45, y1 + h * 0.15, w * 0.4, h * 0.55),
            (x1 + w * 0.7, y1 + h * 0.25, w * 0.35, h * 0.5),
            (x1 + w * 0.3, y1 + h * 0.5, w * 0.5, h * 0.45),
        ]

        for cx, cy, cw, ch in circles:
            draw.ellipse(
                (cx - cw/2, cy - ch/2, cx + cw/2, cy + ch/2),
                fill=style.fill_color,
                outline=style.outline_color,
                width=style.outline_width
            )

    def draw_bubble_shape(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """吹き出しの形状を描画"""
        shape_handlers = {
            BubbleShape.ANGULAR_POLYGON: self.draw_angular_polygon,
            BubbleShape.SOFT_POLYGON: self.draw_soft_polygon,
            BubbleShape.OVAL: self.draw_oval,
            BubbleShape.EXPLOSION: self.draw_explosion,
            BubbleShape.CLOUD: self.draw_cloud,
        }

        handler = shape_handlers.get(style.shape, self.draw_oval)
        handler(draw, bbox, style)

    def draw_tail(
        self, 
        draw: ImageDraw.Draw, 
        bubble_bbox: tuple[int, int, int, int],
        tail_point: tuple[int, int],
        style: BubbleStyle
    ) -> None:
        """吹き出しのしっぽ（三角形）を描画"""
        x1, y1, x2, y2 = bubble_bbox
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        tx, ty = tail_point

        # しっぽの付け根の幅
        tail_width = min(x2 - x1, y2 - y1) // 4

        # しっぽの方向を計算
        if ty > y2:  # 下向き
            base1 = (cx - tail_width // 2, y2)
            base2 = (cx + tail_width // 2, y2)
        elif ty < y1:  # 上向き
            base1 = (cx - tail_width // 2, y1)
            base2 = (cx + tail_width // 2, y1)
        elif tx > x2:  # 右向き
            base1 = (x2, cy - tail_width // 2)
            base2 = (x2, cy + tail_width // 2)
        else:  # 左向き
            base1 = (x1, cy - tail_width // 2)
            base2 = (x1, cy + tail_width // 2)

        triangle = [base1, base2, tail_point]
        draw.polygon(triangle, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

    def calculate_text_bbox(
        self, 
        draw: ImageDraw.Draw, 
        text: str, 
        font: ImageFont.FreeTypeFont
    ) -> tuple[int, int]:
        """テキストのバウンディングボックスを計算"""
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    # 縦書き用の句読点位置調整マップ
    VERTICAL_PUNCTUATION = {
        "。": (0.5, -0.3),   # 右上寄せ
        "、": (0.5, -0.3),
        "，": (0.5, -0.3),
        "．": (0.5, -0.3),
        "！": (0.0, 0.0),
        "？": (0.0, 0.0),
        "!": (0.0, 0.0),
        "?": (0.0, 0.0),
        "ー": (0.0, 0.0),    # 長音は回転が必要だが、そのまま描画
        "…": (0.0, 0.0),
        "─": (0.0, 0.0),
    }

    def calculate_vertical_layout(
        self, text: str, font_size: int, max_chars_per_col: int = 10
    ) -> tuple[list[str], int, int]:
        """縦書きレイアウトを計算し、必要な吹き出しサイズを返す
        
        Returns:
            (columns, bubble_width, bubble_height)
        """
        text_clean = text.replace("「", "").replace("」", "")
        
        char_h = font_size + 6      # 1文字の縦幅
        col_w = font_size + 10      # 1列の横幅
        padding = 20
        
        # テキストを列に分割
        columns = []
        current_col = ""
        for char in text_clean:
            if len(current_col) >= max_chars_per_col:
                columns.append(current_col)
                current_col = char
            else:
                current_col += char
        if current_col:
            columns.append(current_col)
        
        num_cols = len(columns)
        max_col_len = max(len(col) for col in columns) if columns else 1
        
        bubble_width = num_cols * col_w + padding * 2
        bubble_height = max_col_len * char_h + padding * 2
        
        # 最小サイズ保証
        bubble_width = max(bubble_width, 80)
        bubble_height = max(bubble_height, 100)
        
        return columns, bubble_width, bubble_height

    def draw_vertical_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: tuple[int, int, int, int],
        font_size: int = 28,
        fill: str = "#000000"
    ) -> None:
        """縦書きテキストを描画（右から左、上から下）"""
        font = self.get_font(font_size)
        x1, y1, x2, y2 = position
        
        text_clean = text.replace("「", "").replace("」", "")
        
        padding = 20
        char_h = font_size + 6
        col_w = font_size + 10
        
        # 利用可能エリア
        available_height = y2 - y1 - padding * 2
        max_chars_per_col = max(1, available_height // char_h)
        
        # テキストを列に分割
        columns = []
        current_col = ""
        for char in text_clean:
            if len(current_col) >= max_chars_per_col:
                columns.append(current_col)
                current_col = char
            else:
                current_col += char
        if current_col:
            columns.append(current_col)
        
        # テキスト全体の幅と高さ
        total_width = len(columns) * col_w
        max_col_chars = max(len(col) for col in columns) if columns else 0
        total_height = max_col_chars * char_h
        
        # 中央揃え
        start_x = x1 + (x2 - x1 + total_width) // 2 - col_w
        start_y = y1 + ((y2 - y1) - total_height) // 2
        
        # 右から左へ列を描画
        for col_idx, col in enumerate(columns):
            x = start_x - col_idx * col_w
            y = start_y
            
            for char in col:
                # 句読点の位置調整
                offset = self.VERTICAL_PUNCTUATION.get(char, (0.0, 0.0))
                dx = int(offset[0] * font_size)
                dy = int(offset[1] * font_size)
                
                draw.text((x + dx, y + dy), char, font=font, fill=fill)
                y += char_h

    def draw_text_with_emphasis(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: tuple[int, int],
        base_font_size: int = 28,
        keyword: Optional[str] = None,
        emphasis_scale: float = 1.4
    ) -> None:
        """テキストを描画（キーワード強調対応）"""
        font_standard = self.get_font(base_font_size)
        x, y = position

        if keyword and keyword in text:
            # キーワードを含む場合、分割して描画
            font_large = self.get_font(int(base_font_size * emphasis_scale))
            parts = text.split(keyword)

            for i, part in enumerate(parts):
                # 通常テキスト部分（黒・標準サイズ）
                if part:
                    draw.text((x, y), part, font=font_standard, fill=TEXT_COLOR_PRIMARY)
                    text_w, _ = self.calculate_text_bbox(draw, part, font_standard)
                    x += text_w

                # キーワード部分（赤・特大サイズ）
                if i < len(parts) - 1:
                    # 少し上にオフセット（大きい文字のベースライン調整）
                    y_offset = int(base_font_size * (emphasis_scale - 1) * 0.3)
                    draw.text((x, y - y_offset), keyword, font=font_large, fill=TEXT_COLOR_EMPHASIS)
                    kw_w, _ = self.calculate_text_bbox(draw, keyword, font_large)
                    x += kw_w
        else:
            # 通常テキストの描画
            draw.text(position, text, font=font_standard, fill=TEXT_COLOR_PRIMARY)

    def draw_caption(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: tuple[int, int, int, int],
        font_size: int = 20
    ) -> None:
        """
        紹介キャプション（四角い矩形）を描画
        
        Args:
            draw: ImageDraw オブジェクト
            text: キャプションテキスト
            position: キャプションの位置 (x1, y1, x2, y2)
            font_size: フォントサイズ
        """
        x1, y1, x2, y2 = position
        
        # 白い矩形を描画
        draw.rectangle(position, fill="#FFFFFF", outline="#000000", width=2)
        
        # テキストを中央に配置
        font = self.get_font(font_size)
        text_clean = text.replace("「", "").replace("」", "")
        text_bbox = draw.textbbox((0, 0), text_clean, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = x1 + (x2 - x1 - text_width) // 2
        text_y = y1 + (y2 - y1 - text_height) // 2
        
        draw.text((text_x, text_y), text_clean, font=font, fill="#000000")

    def draw_speech_bubble(
        self,
        draw: ImageDraw.Draw,
        character: str,
        text: str,
        position: tuple[int, int, int, int],
        tail_point: Optional[tuple[int, int]] = None,
        is_tsukkomi: bool = False,
        is_monologue: bool = False,
        is_thought: bool = False,
        is_caption: bool = False,
        keyword: Optional[str] = None,
        font_size: int = 28
    ) -> None:
        """
        吹き出しを描画するメイン関数

        Args:
            draw: ImageDraw オブジェクト
            character: キャラクター名（はな、さき、まさと、ともや、ようた）
            text: セリフテキスト
            position: 吹き出しの位置 (x1, y1, x2, y2)
            tail_point: しっぽの先端位置 (x, y)
            is_tsukkomi: ツッコミ（オチ）かどうか
            is_monologue: モノローグかどうか
            is_thought: 考え事かどうか
            is_caption: 紹介キャプションかどうか
            keyword: 強調するキーワード（ツッコミ時）
            font_size: 基本フォントサイズ
        """
        # キャプションの場合は専用メソッドで描画
        if is_caption:
            self.draw_caption(draw, text, position, font_size=18)
            return
        
        # 1. スタイルを決定
        style = self.get_bubble_style(character, is_tsukkomi, is_monologue, is_thought)

        # 2. 吹き出しの形状を描画
        self.draw_bubble_shape(draw, position, style)

        # 3. しっぽを描画（指定がある場合）
        if tail_point:
            self.draw_tail(draw, position, tail_point, style)

        # 4. テキストを縦書きで描画
        self.draw_vertical_text(draw, text, position, font_size=font_size, fill=TEXT_COLOR_PRIMARY)


def demo():
    """デモ: 各種吹き出しの描画例"""
    img = Image.new("RGB", (1200, 800), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    renderer = BubbleRenderer()

    # 1. はな（女性・黄色・角ばった多角形）
    renderer.draw_speech_bubble(
        draw, "はな", "なんで重い人\nばっかり！？",
        (50, 50, 300, 150),
        tail_point=(175, 180),
        font_size=24
    )

    # 2. さき（女性・黄色・角ばった多角形）
    renderer.draw_speech_bubble(
        draw, "さき", "プロフ見せて",
        (350, 50, 550, 130),
        tail_point=(450, 160),
        font_size=24
    )

    # 3. まさと（男性・パステルブルー）
    renderer.draw_speech_bubble(
        draw, "まさと", "今日も\nかわいいね",
        (600, 50, 850, 150),
        tail_point=(725, 180),
        font_size=24
    )

    # 4. モノローグ（白・楕円）
    renderer.draw_speech_bubble(
        draw, "はな", "（どうしよう…）",
        (900, 50, 1150, 130),
        is_monologue=True,
        font_size=22
    )

    # 5. ツッコミ（黄色・ギザギザ爆発型・キーワード強調）
    renderer.draw_speech_bubble(
        draw, "はな", "自分で募集してるし！",
        (50, 250, 400, 400),
        is_tsukkomi=True,
        keyword="募集",
        font_size=28
    )

    # 6. 考え事（雲型）
    renderer.draw_speech_bubble(
        draw, "はな", "もしかして…",
        (450, 250, 700, 380),
        is_thought=True,
        font_size=24
    )

    # 保存
    output_path = Path("bubble_demo.png")
    img.save(output_path)
    print(f"デモ画像を保存しました: {output_path}")


if __name__ == "__main__":
    demo()
