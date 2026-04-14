#!/usr/bin/env python3
"""
吹き出し自動描画モジュール

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
    RADIATION = "radiation"                  # 放射線型（内心用）
    DOTTED_OVAL = "dotted_oval"              # 点線楕円（内心語用）


@dataclass
class BubbleStyle:
    """吹き出しのスタイル定義"""
    fill_color: str
    outline_color: str
    shape: BubbleShape
    outline_width: int = 4


# キャラクター別吹き出しスタイル定義（参考画像準拠: 角丸四角形）
CHARACTER_BUBBLE_STYLES = {
    # 女性陣：高彩度黄色、角丸四角形
    "はな": BubbleStyle("#FFE800", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),
    "さき": BubbleStyle("#FFE800", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),
    "なおみ": BubbleStyle("#FFE800", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),

    # 男性陣：パステルブルー、角丸四角形
    "まさと": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),
    "ともや": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),
    "ようた": BubbleStyle("#D4E8FF", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6),
}

# 特殊吹き出しスタイル
MONOLOGUE_STYLE = BubbleStyle("#FFFFFF", "#000000", BubbleShape.SOFT_POLYGON, outline_width=6)
TSUKKOMI_STYLE = BubbleStyle("#FFE800", "#000000", BubbleShape.RADIATION, outline_width=7)
THOUGHT_STYLE = BubbleStyle("#E8E8E8", "#666666", BubbleShape.DOTTED_OVAL, outline_width=3)
CAPTION_STYLE = BubbleStyle("#FFFFFF", "#000000", BubbleShape.SOFT_POLYGON, outline_width=4)

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
        style: BubbleStyle,
        clip_edges: Optional[set] = None
    ) -> None:
        """手描き風の有機的な吹き出しを描画。clip_edgesに含まれる辺は直線でパネル外に拡張。"""
        import random
        import hashlib

        if clip_edges is None:
            clip_edges = set()
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        ow = style.outline_width

        # clip辺の拡張量
        ext = ow + 20
        ex1 = x1 - ext if "left" in clip_edges else x1
        ey1 = y1 - ext if "top" in clip_edges else y1
        ex2 = x2 + ext if "right" in clip_edges else x2
        ey2 = y2 + ext if "bottom" in clip_edges else y2

        ew, eh = ex2 - ex1, ey2 - ey1
        cx, cy = ex1 + ew / 2, ey1 + eh / 2
        rx, ry = ew / 2, eh / 2

        # テキストベースで再現可能なシード
        seed = int(hashlib.md5(f"{x1}{y1}{x2}{y2}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # 有機的な形状: スーパー楕円（角丸寄り）+ 低周波不規則変位
        num_points = 120
        n_power = 4.5  # スーパー楕円の指数（大きいほど角丸四角形に近い）

        # ランダムな低周波成分を生成（控えめにして膨らみを抑制）
        num_harmonics = 4
        harmonics = []
        for _ in range(num_harmonics):
            freq = rng.randint(3, 7)
            amp_ratio = rng.uniform(0.005, 0.018)
            phase = rng.uniform(0, 2 * math.pi)
            harmonics.append((freq, amp_ratio, phase))

        points = []
        for i in range(num_points):
            t = i / num_points
            angle = t * 2 * math.pi

            # スーパー楕円（角丸四角形ベース）
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            exp = 2.0 / n_power
            sx = abs(cos_a) ** exp * (1 if cos_a >= 0 else -1)
            sy = abs(sin_a) ** exp * (1 if sin_a >= 0 else -1)
            px = cx + rx * sx
            py = cy + ry * sy

            # 不規則な変位（法線方向に）
            displacement = 0
            for freq, amp_ratio, phase in harmonics:
                displacement += amp_ratio * math.sin(freq * angle + phase)

            min_r = min(rx, ry)
            disp_px = displacement * min_r

            # clip辺に近い部分は変位を抑制
            suppress = 1.0
            if "right" in clip_edges and cos_a > 0.3:
                suppress *= max(0, 1 - (cos_a - 0.3) / 0.7)
            if "left" in clip_edges and cos_a < -0.3:
                suppress *= max(0, 1 - (-cos_a - 0.3) / 0.7)
            if "bottom" in clip_edges and sin_a > 0.3:
                suppress *= max(0, 1 - (sin_a - 0.3) / 0.7)
            if "top" in clip_edges and sin_a < -0.3:
                suppress *= max(0, 1 - (-sin_a - 0.3) / 0.7)

            # 法線方向に変位
            norm_len = math.sqrt(cos_a**2 + sin_a**2)
            if norm_len > 0:
                nx = cos_a / norm_len
                ny = sin_a / norm_len
            else:
                nx, ny = 0, 0
            px += nx * disp_px * suppress
            py += ny * disp_px * suppress

            points.append((px, py))

        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=ow)

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
        spikes: int = 20,
        clip_edges: Optional[set] = None
    ) -> None:
        """ギザギザ爆発型を描画 - ツッコミ用"""
        if clip_edges is None:
            clip_edges = set()

        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        outer_rx = (x2 - x1) // 2
        outer_ry = (y2 - y1) // 2
        inner_rx = outer_rx * 0.88
        inner_ry = outer_ry * 0.88

        points = []
        for i in range(spikes * 2):
            angle = math.pi * i / spikes - math.pi / 2
            if i % 2 == 0:
                px = cx + outer_rx * math.cos(angle)
                py = cy + outer_ry * math.sin(angle)
            else:
                px = cx + inner_rx * math.cos(angle)
                py = cy + inner_ry * math.sin(angle)
            points.append((px, py))

        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

        # パネル端に接する辺を直線化
        spike_depth_x = int(outer_rx * 0.15) + 2
        spike_depth_y = int(outer_ry * 0.15) + 2
        ow = style.outline_width
        if "top" in clip_edges:
            draw.rectangle([x1, y1 - 2, x2, y1 + spike_depth_y], fill=style.fill_color)
            draw.line([x1, y1, x2, y1], fill=style.outline_color, width=ow)
        if "bottom" in clip_edges:
            draw.rectangle([x1, y2 - spike_depth_y, x2, y2 + 2], fill=style.fill_color)
            draw.line([x1, y2, x2, y2], fill=style.outline_color, width=ow)
        if "right" in clip_edges:
            draw.rectangle([x2 - spike_depth_x, y1, x2 + 2, y2], fill=style.fill_color)
            draw.line([x2, y1, x2, y2], fill=style.outline_color, width=ow)
        if "left" in clip_edges:
            draw.rectangle([x1 - 2, y1, x1 + spike_depth_x, y2], fill=style.fill_color)
            draw.line([x1, y1, x1, y2], fill=style.outline_color, width=ow)

    def draw_cloud(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """雲型を描画 - 内心語用（もこもこした輪郭）"""
        import math
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w // 2, y1 + h // 2
        
        # もこもこの数
        num_bumps = 12
        points = []
        
        for i in range(num_bumps * 2):
            angle = (2 * math.pi * i) / (num_bumps * 2)
            # 偶数=外側（もこ）、奇数=内側（くぼみ）
            if i % 2 == 0:
                r_x = w * 0.50
                r_y = h * 0.50
            else:
                r_x = w * 0.44
                r_y = h * 0.44
            
            px = cx + r_x * math.cos(angle)
            py = cy + r_y * math.sin(angle)
            points.append((px, py))
        
        # 塗りつぶし
        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)
        
        # 内側を白で塗りつぶして文字領域を確保
        inner_points = []
        for i in range(num_bumps * 2):
            angle = (2 * math.pi * i) / (num_bumps * 2)
            r_x = w * 0.38
            r_y = h * 0.38
            px = cx + r_x * math.cos(angle)
            py = cy + r_y * math.sin(angle)
            inner_points.append((px, py))
        draw.polygon(inner_points, fill=style.fill_color)

    def draw_radiation(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """放射線型を描画 - 内心/驚き用（縦フラッシュ/ウニフラ）"""
        import random
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        
        spike_depth = min(w * 0.3, 42)
        inner_left = x1 + spike_depth
        inner_right = x2 - spike_depth
        num_spikes = max(10, int(h / 12))
        points = []
        rng = random.Random(x1 + y1)
        
        points.append((inner_left, y1))
        points.append((inner_right, y1))
        
        for i in range(1, num_spikes + 1):
            py_outer = y1 + (h / num_spikes) * (i - 0.5)
            px_outer = x2 - rng.uniform(0, spike_depth * 0.2)
            points.append((px_outer, py_outer))
            
            py_inner = y1 + (h / num_spikes) * i
            if i == num_spikes:
                points.append((inner_right, y2))
            else:
                px_inner = inner_right - rng.uniform(0, spike_depth * 0.3)
                points.append((px_inner, py_inner))
                
        points.append((inner_left, y2))
        
        for i in range(1, num_spikes + 1):
            py_outer = y2 - (h / num_spikes) * (i - 0.5)
            px_outer = x1 + rng.uniform(0, spike_depth * 0.2)
            points.append((px_outer, py_outer))
            
            py_inner = y2 - (h / num_spikes) * i
            if i == num_spikes:
                points.append((inner_left, y1))
            else:
                px_inner = inner_left + rng.uniform(0, spike_depth * 0.3)
                points.append((px_inner, py_inner))
                
        draw.polygon(points, fill=style.fill_color, outline=style.outline_color, width=style.outline_width)

    def draw_dotted_oval(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle
    ) -> None:
        """点線の楕円を描画 - 内心語用"""
        import math
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w // 2, y1 + h // 2
        rx, ry = w // 2 - 5, h // 2 - 5
        
        # 白で塗りつぶし
        draw.ellipse([x1 + 5, y1 + 5, x2 - 5, y2 - 5], fill=style.fill_color)
        
        # 点線で輪郭を描画
        num_dots = 60
        dot_length = 0.6  # 点の長さ（角度比率）
        for i in range(num_dots):
            if i % 2 == 0:  # 点を描画（偶数のみ）
                angle_start = (2 * math.pi * i) / num_dots
                angle_end = angle_start + (2 * math.pi * dot_length) / num_dots
                
                # 点の始点と終点
                for j in range(5):
                    angle = angle_start + (angle_end - angle_start) * j / 4
                    px = cx + rx * math.cos(angle)
                    py = cy + ry * math.sin(angle)
                    # 小さな円で点を描画
                    draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=style.outline_color)

    def draw_bubble_shape(
        self, 
        draw: ImageDraw.Draw, 
        bbox: tuple[int, int, int, int],
        style: BubbleStyle,
        clip_edges: Optional[set] = None
    ) -> None:
        """吹き出しの形状を描画"""
        if style.shape == BubbleShape.EXPLOSION:
            self.draw_explosion(draw, bbox, style, clip_edges=clip_edges)
            return

        if style.shape == BubbleShape.SOFT_POLYGON:
            self.draw_soft_polygon(draw, bbox, style, clip_edges=clip_edges)
            return

        shape_handlers = {
            BubbleShape.ANGULAR_POLYGON: self.draw_angular_polygon,
            BubbleShape.OVAL: self.draw_oval,
            BubbleShape.CLOUD: self.draw_cloud,
            BubbleShape.RADIATION: self.draw_radiation,
            BubbleShape.DOTTED_OVAL: self.draw_dotted_oval,
        }

        handler = shape_handlers.get(style.shape, self.draw_oval)
        handler(draw, bbox, style)

    def calculate_text_bbox(
        self, 
        draw: ImageDraw.Draw, 
        text: str, 
        font: ImageFont.FreeTypeFont
    ) -> tuple[int, int]:
        """テキストのバウンディングボックスを計算"""
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    VERTICAL_PUNCTUATION = {
        "。": (0.5, -0.3), "、": (0.5, -0.3), "，": (0.5, -0.3), "．": (0.5, -0.3),
        "！": (0.0, 0.0), "？": (0.0, 0.0), "!": (0.0, 0.0), "?": (0.0, 0.0),
        "…": (0.0, 0.0), "─": (0.0, 0.0),
        "っ": (0.12, -0.08), "ゃ": (0.12, -0.08), "ゅ": (0.12, -0.08), "ょ": (0.12, -0.08),
        "ッ": (0.12, -0.08), "ャ": (0.12, -0.08), "ュ": (0.12, -0.08), "ョ": (0.12, -0.08),
        "ぁ": (0.12, -0.08), "ぃ": (0.12, -0.08), "ぅ": (0.12, -0.08), "ぇ": (0.12, -0.08), "ぉ": (0.12, -0.08),
        "ァ": (0.12, -0.08), "ィ": (0.12, -0.08), "ゥ": (0.12, -0.08), "ェ": (0.12, -0.08), "ォ": (0.12, -0.08),
        "ゎ": (0.12, -0.08), "ヮ": (0.12, -0.08),
    }

    ROTATE_CHARS = {"ー", "〜", "～", "─", "—", "―"}

    VERTICAL_BRACKETS = {
        "「": "﹁", "」": "﹂",
        "『": "﹃", "』": "﹄",
        "(": "︵", ")": "︶",
        "（": "︵", "）": "︶",
        "…": "︙",  # 三点リーダーを縦書き用に変換
    }

    def _draw_rotated_char(
        self,
        draw: ImageDraw.Draw,
        img: Image.Image,
        char: str,
        x: int, y: int,
        font: ImageFont.FreeTypeFont,
        font_size: int,
        fill: str
    ) -> None:
        """文字を90°回転して描画（ー、〜など横長文字用）"""
        col_w = font_size + 16
        char_h = font_size + 4
        canvas_size = int(font_size * 2)
        char_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        char_draw = ImageDraw.Draw(char_img)
        bbox = char_draw.textbbox((0, 0), char, font=font)
        cw = bbox[2] - bbox[0]
        ch = bbox[3] - bbox[1]
        cx = (canvas_size - cw) // 2 - bbox[0]
        cy = (canvas_size - ch) // 2 - bbox[1]
        char_draw.text((cx, cy), char, font=font, fill=fill)
        rotated = char_img.rotate(-90, resample=Image.BICUBIC, expand=False)
        rot_bbox = rotated.getbbox()
        if rot_bbox:
            rx1, ry1, rx2, ry2 = rot_bbox
            rot_cw = rx2 - rx1
            rot_ch = ry2 - ry1
            paste_x = x + (col_w - rot_cw) // 2 - rx1
            paste_y = y + (char_h - rot_ch) // 2 - ry1
        else:
            paste_x = x + (col_w - canvas_size) // 2
            paste_y = y + (char_h - canvas_size) // 2
        img.paste(rotated, (paste_x, paste_y), rotated)

    def calculate_vertical_layout(
        self, text: str, font_size: int, max_chars_per_col: int = 6
    ) -> tuple[list[str], int, int]:
        """縦書きレイアウトを計算し、必要な吹き出しサイズを返す"""
        char_h = font_size + 4
        col_w = font_size + 16
        padding = 30
        
        text = text.replace('！！', '‼').replace('!!', '‼')
        OPEN_PARENS = set('(（')
        CLOSE_PARENS = set(')）')
        columns = []
        current_col = ""
        paren_depth = 0
        for char in text:
            if char == '\n':
                columns.append(current_col)
                current_col = ""
                paren_depth = 0
            elif len(current_col) >= max_chars_per_col and paren_depth == 0:
                columns.append(current_col)
                current_col = char
                if char in OPEN_PARENS:
                    paren_depth += 1
            else:
                current_col += char
                if char in OPEN_PARENS:
                    paren_depth += 1
                elif char in CLOSE_PARENS:
                    paren_depth = max(0, paren_depth - 1)
        if current_col:
            columns.append(current_col)
        
        num_cols = len(columns)
        max_col_len = max(len(col) for col in columns) if columns else 1
        
        bubble_width = num_cols * col_w + padding * 2
        bubble_height = max_col_len * char_h + padding * 2
        
        bubble_width = max(bubble_width, 100)
        bubble_height = max(bubble_height, 150)
        
        return columns, bubble_width, bubble_height

    def draw_vertical_text(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: tuple[int, int, int, int],
        font_size: int = 36,
        fill: str = "#000000",
        img: Optional[Image.Image] = None,
        keyword: Optional[str] = None
    ) -> None:
        """縦書きテキストを描画"""
        font = self.get_font(font_size)
        emphasis_fs = int(font_size * 1.2)
        emphasis_font = self.get_font(emphasis_fs)
        text = text.replace('！！', '‼').replace('!!', '‼')
        text_no_nl = text.replace('\n', '')
        
        highlight_indices = set()
        if keyword and keyword in text_no_nl:
            start = 0
            while True:
                idx = text_no_nl.find(keyword, start)
                if idx == -1:
                    break
                for i in range(idx, idx + len(keyword)):
                    highlight_indices.add(i)
                if idx > 0 and text_no_nl[idx - 1] == '『':
                    highlight_indices.add(idx - 1)
                end_idx = idx + len(keyword)
                if end_idx < len(text_no_nl) and text_no_nl[end_idx] == '』':
                    highlight_indices.add(end_idx)
                start = idx + 1
        x1, y1, x2, y2 = position
        
        padding = 30
        char_h = font_size + 4
        col_w = font_size + 16
        
        available_height = y2 - y1 - padding * 2
        max_chars_per_col = max(1, available_height // char_h)
        
        OPEN_PARENS = set('(（')
        CLOSE_PARENS = set(')）')
        columns = []
        current_col = ""
        paren_depth = 0
        for char in text:
            if char == '\n':
                columns.append(current_col)
                current_col = ""
                paren_depth = 0
            elif len(current_col) >= max_chars_per_col and paren_depth == 0:
                columns.append(current_col)
                current_col = char
                if char in OPEN_PARENS:
                    paren_depth += 1
            else:
                current_col += char
                if char in OPEN_PARENS:
                    paren_depth += 1
                elif char in CLOSE_PARENS:
                    paren_depth = max(0, paren_depth - 1)
        if current_col:
            columns.append(current_col)
        
        total_width = len(columns) * col_w
        max_col_chars = max(len(col) for col in columns) if columns else 0
        total_height = max_col_chars * char_h
        
        start_x = x1 + (x2 - x1 + total_width) // 2 - col_w
        start_y = y1 + ((y2 - y1) - total_height) // 2
        min_y = max(y1 + padding // 2, 12)
        if start_y < min_y:
            start_y = min_y
        
        char_global_idx = 0
        for col_idx, col in enumerate(columns):
            x = start_x - col_idx * col_w
            y = start_y
            
            for char in col:
                char_fill = TEXT_COLOR_EMPHASIS if char_global_idx in highlight_indices else fill
                char_global_idx += 1

                if char in self.ROTATE_CHARS and img is not None:
                    self._draw_rotated_char(draw, img, char, x, y, font, font_size, char_fill)
                    y += char_h
                    continue
                
                if char in self.VERTICAL_BRACKETS:
                    v_char = self.VERTICAL_BRACKETS[char]
                    bbox = draw.textbbox((0, 0), v_char, font=font)
                    cw = bbox[2] - bbox[0]
                    cx = x + (col_w - cw) // 2 - bbox[0]
                    draw.text((cx, y), v_char, font=font, fill=char_fill)
                    y += char_h
                    continue
                
                if char == '‼':
                    small_fs = font_size
                    small_font = font
                    excl = '!'
                    eb = draw.textbbox((0, 0), excl, font=small_font)
                    ew = eb[2] - eb[0]
                    eh = eb[3] - eb[1]
                    gap = -2
                    total_w = ew * 2 + gap
                    bx = x + (col_w - total_w) // 2 - eb[0]
                    by = y + (char_h - eh) // 2 - eb[1]
                    draw.text((bx, by), excl, font=small_font, fill=char_fill)
                    draw.text((bx + ew + gap, by), excl, font=small_font, fill=char_fill)
                    y += char_h
                    continue

                is_emphasis = (char_fill == TEXT_COLOR_EMPHASIS and char not in ('『', '』'))
                cur_font = emphasis_font if is_emphasis else font
                cur_fs = emphasis_fs if is_emphasis else font_size

                offset = self.VERTICAL_PUNCTUATION.get(char, (0.0, 0.0))
                dx = int(offset[0] * cur_fs)
                dy = int(offset[1] * cur_fs)
                
                bbox = draw.textbbox((0, 0), char, font=cur_font)
                cw = bbox[2] - bbox[0]
                ch_actual = bbox[3] - bbox[1]
                cx = x + (col_w - cw) // 2 - bbox[0] + dx
                cy_offset = (char_h - ch_actual) // 2 - bbox[1] if is_emphasis else 0
                draw.text((cx, y + dy + cy_offset), char, font=cur_font, fill=char_fill)
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
            font_large = self.get_font(int(base_font_size * emphasis_scale))
            parts = text.split(keyword)

            for i, part in enumerate(parts):
                if part:
                    draw.text((x, y), part, font=font_standard, fill=TEXT_COLOR_PRIMARY)
                    text_w, _ = self.calculate_text_bbox(draw, part, font_standard)
                    x += text_w

                if i < len(parts) - 1:
                    y_offset = int(base_font_size * (emphasis_scale - 1) * 0.3)
                    draw.text((x, y - y_offset), keyword, font=font_large, fill=TEXT_COLOR_EMPHASIS)
                    kw_w, _ = self.calculate_text_bbox(draw, keyword, font_large)
                    x += kw_w
        else:
            draw.text(position, text, font=font_standard, fill=TEXT_COLOR_PRIMARY)

    def draw_caption(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: tuple[int, int, int, int],
        font_size: int = 28
    ) -> None:
        """紹介キャプション（四角い矩形）を描画"""
        x1, y1, x2, y2 = position
        
        draw.rectangle(position, fill="#FFFFFF", outline="#000000", width=2)
        
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
        is_tsukkomi: bool = False,
        is_monologue: bool = False,
        is_thought: bool = False,
        is_caption: bool = False,
        keyword: Optional[str] = None,
        font_size: int = 28,
        clip_edges: Optional[set] = None,
        img: Optional[Image.Image] = None
    ) -> None:
        """吹き出しを描画するメイン関数"""
        if text.startswith("「") and text.endswith("」"):
            text = text[1:-1]

        if is_caption:
            self.draw_caption(draw, text, position, font_size=28)
            return
        
        # 1. スタイルを決定
        style = self.get_bubble_style(character, is_tsukkomi, is_monologue, is_thought)
        
        # 2. 吹き出し本体を描画（しっぽ描画は廃止）
        self.draw_bubble_shape(draw, position, style, clip_edges=clip_edges)

        # 3. テキストを縦書きで描画
        self.draw_vertical_text(draw, text, position, font_size=font_size, fill=TEXT_COLOR_PRIMARY, img=img, keyword=keyword)


def demo():
    """デモ: 各種吹き出しの描画例"""
    img = Image.new("RGB", (1200, 800), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    renderer = BubbleRenderer()

    # 1. はな（女性・黄色・角ばった多角形）
    renderer.draw_speech_bubble(
        draw, "はな", "なんで重い人\nばっかり！？",
        (50, 50, 300, 150),
        font_size=24
    )

    # 2. さき（女性・黄色・角ばった多角形）
    renderer.draw_speech_bubble(
        draw, "さき", "プロフ見せて",
        (350, 50, 550, 130),
        font_size=24
    )

    # 3. まさと（男性・パステルブルー）
    renderer.draw_speech_bubble(
        draw, "まさと", "今日も\nかわいいね",
        (600, 50, 850, 150),
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