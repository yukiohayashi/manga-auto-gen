#!/usr/bin/env python3
"""
吹き出し描画のみテスト（Gemini API不要）
ダミー画像に吹き出しを描画して出力する
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PIL import Image, ImageDraw
from bubble_renderer import BubbleRenderer

PANEL_SIZE = (1000, 1000)
BORDER_WIDTH = 10  # ボーダーの太さ（参考画像準拠）
BORDER_COLOR = "#1A1A1A"  # ほぼ黒

def test_panel(panel: dict, output_path: str, is_final: bool = False):
    """1パネル分の吹き出し描画テスト"""
    # ダミー背景（薄いグレー）
    img = Image.new("RGB", PANEL_SIZE, "#FFFFFF")
    draw = ImageDraw.Draw(img)
    # グリッド線（位置確認用）
    for x in range(0, PANEL_SIZE[0], 100):
        draw.line([(x, 0), (x, PANEL_SIZE[1])], fill="#EEEEEE", width=1)
    for y in range(0, PANEL_SIZE[1], 100):
        draw.line([(0, y), (PANEL_SIZE[0], y)], fill="#EEEEEE", width=1)

    # module3と同じロジックで吹き出しを描画
    renderer = BubbleRenderer()
    dialogues = panel.get("dialogue", [])
    if not dialogues:
        # ボーダー枠だけ描画
        draw.rectangle([0, 0, PANEL_SIZE[0]-1, PANEL_SIZE[1]-1], outline=BORDER_COLOR, width=BORDER_WIDTH)
        img.save(output_path)
        return

    panel_w, panel_h = PANEL_SIZE
    font_size = 52
    # ボーダー内側に収めるためのmargin（ボーダー幅 + 十分な余白）
    margin = BORDER_WIDTH + 10

    speech_items = []
    caption_items = []
    for d in dialogues:
        bt = d.get("type", d.get("bubble_type", "normal"))
        if bt == "caption":
            caption_items.append(d)
        else:
            speech_items.append(d)

    num_speech = len(speech_items)
    if num_speech <= 2:
        available_h = panel_h - margin * 2
    else:
        available_h = (panel_h - margin * 3) // 2

    max_bw = int(panel_w * 0.50)
    bubble_infos = []

    for d in speech_items:
        text = d.get("text", "")
        text_len = len(text)
        fs = font_size
        while fs >= 24:
            ch = fs + 4
            cw = fs + 10
            pd = 50
            max_chars_col = max(1, (available_h - pd * 2) // ch)
            num_cols = max(1, -(-text_len // max_chars_col))
            bw = num_cols * cw + pd * 2 + 10
            if bw <= max_bw:
                break
            fs -= 2

        ch = fs + 4
        cw = fs + 10
        pd = 50
        max_chars_col = max(1, (available_h - pd * 2) // ch)
        num_cols = max(1, -(-text_len // max_chars_col))
        chars_per_col = min(max_chars_col, -(-text_len // num_cols))
        bh = min(available_h, max(chars_per_col * ch + pd * 2, 200))
        bw = num_cols * cw + pd * 2 + 10
        bw = min(bw, max_bw)

        bubble_infos.append({
            "dialogue": d, "width": bw, "height": bh,
            "is_caption": False, "font_size": fs,
        })
        print(f"  [{d.get('character','')}] fs={fs} cols={num_cols} bw={bw} bh={bh} text_len={text_len}")

    for d in caption_items:
        text_clean = d.get("text", "").replace("「", "").replace("」", "")
        caption_fs = 28
        bw = len(text_clean) * caption_fs + 40
        bh = caption_fs + 24
        bubble_infos.append({
            "dialogue": d, "width": bw, "height": bh,
            "is_caption": True, "font_size": caption_fs,
        })

    if num_speech == 1:
        positions = [("right", "top")]
    elif num_speech == 2:
        positions = [("right", "top"), ("left", "bottom")]
    elif num_speech == 3:
        positions = [("right", "top"), ("left", "top"), ("left", "bottom")]
    else:
        positions = [("right", "top"), ("left", "top"), ("left", "bottom"), ("right", "bottom")]

    speech_idx = 0
    for info in bubble_infos:
        d = info["dialogue"]
        character = d.get("character", "")
        text = d.get("text", "")
        bt = d.get("type", d.get("bubble_type", "normal"))
        keyword = d.get("highlight", d.get("keyword", ""))
        bw, bh = info["width"], info["height"]
        is_caption = info["is_caption"]
        bubble_fs = info["font_size"]

        if is_caption:
            x1 = (panel_w - bw) // 2
            y1 = panel_h - bh - margin - 30
        else:
            pos = positions[speech_idx % len(positions)]
            h_pos, v_pos = pos
            # ボーダーにスナップ: right/topはボーダー端に配置
            x1 = panel_w - bw if h_pos == "right" else margin
            y1 = 0 if v_pos == "top" else panel_h - bh
            speech_idx += 1

        x1 = max(0, min(x1, panel_w - bw))
        y1 = max(0, min(y1, panel_h - bh))
        x2, y2 = x1 + bw, y1 + bh

        is_tsukkomi = bt in ["tsukkomi", "shout"] or (is_final and speech_idx == num_speech)
        is_monologue = bt == "monologue"
        is_thought = bt == "thought"

        # ボーダー接触判定
        border_threshold = BORDER_WIDTH + 2
        clip_edges = set()
        if y1 <= border_threshold: clip_edges.add("top")
        if y2 >= panel_h - border_threshold: clip_edges.add("bottom")
        if x2 >= panel_w - border_threshold: clip_edges.add("right")
        if x1 <= border_threshold: clip_edges.add("left")

        tail_x, tail_y = None, None
        if not is_caption:
            if "bottom" not in clip_edges and "top" in clip_edges:
                tail_x, tail_y = x1 + bw // 3, y2 + 20
            elif "top" not in clip_edges and "bottom" in clip_edges:
                tail_x, tail_y = x1 + bw // 3, y1 - 20

        renderer.draw_speech_bubble(
            draw=draw, character=character, text=text,
            position=(x1, y1, x2, y2),
            tail_point=(tail_x, tail_y) if tail_x else None,
            is_tsukkomi=is_tsukkomi, is_monologue=is_monologue,
            is_thought=is_thought, is_caption=is_caption,
            keyword=keyword or None,
            font_size=bubble_fs, clip_edges=clip_edges, img=img,
        )

    # ボーダー枠を最前面に描画（吹き出しの上に乗る）
    draw.rectangle([0, 0, panel_w - 1, panel_h - 1], outline=BORDER_COLOR, width=BORDER_WIDTH)

    # manga_spec準拠: 白い余白で中央配置
    white_margin = 20
    padded = Image.new("RGB", (panel_w + white_margin * 2, panel_h + white_margin * 2), "#FFFFFF")
    padded.paste(img, (white_margin, white_margin))
    padded.save(output_path)
    print(f"  => {output_path}")


def main():
    scenario_path = Path(__file__).parent / "test_scenario.json"
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    panels = scenario.get("panels", [])
    for i, panel in enumerate(panels):
        print(f"パネル{i+1}: {panel.get('structure', '')}")
        out = str(output_dir / f"bubble_test_panel_{i+1:02d}.png")
        test_panel(panel, out, is_final=(i == len(panels) - 1))

    print(f"\n完了！{output_dir} を確認してください")


if __name__ == "__main__":
    main()
