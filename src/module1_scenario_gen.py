#!/usr/bin/env python3
"""
モジュール1：シナリオ・プロット生成（Gemini API）

PlotTwist_plain.txtのルールを学習し、「正体の転換」または「存在の転換」に基づく
起承転結のシナリオを生成する。
"""

import argparse
import json
import os
import random
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

# PlotTwistの10パターン
PLOT_TWIST_PATTERNS = {
    "identity_transformation": [
        "ドラキュラ2世",      # D→D'（継承）
        "ドラキュラの影",     # D→D'（誤認）
        "ドラウルフ",         # D→W
        "ドラフランケン",     # D→F
        "ウルフドラキュラ",   # W→D
        "ウルフフランケン",   # W→F
        "フランケンドラキュラ", # F→D
        "フランケンウルフ",   # F→W
    ],
    "existence_transformation": [
        "ゾンビ",             # ∅→○
        "ドラゴンの卵",       # 遠→近
    ]
}

# 固定キャラクター
CHARACTERS = {
    "protagonist": {"name": "はな", "age": 25, "gender": "女性", "role": "主人公"},
    "boyfriend": {"name": "まさと", "age": 28, "gender": "男性", "role": "彼氏"},
    "friend_female": {"name": "さき", "age": 25, "gender": "女性", "role": "友人"},
    "friend_male": {"name": "ともや", "age": 25, "gender": "男性", "role": "友人"},
    "brother": {"name": "ようた", "age": 20, "gender": "男性", "role": "弟"},
}

# 禁止キャラクター名（セリフに固有名詞を含めない）
PROHIBITED_NAMES = []


def load_plot_twist_rules(config_path: str) -> str:
    """PlotTwist_plain.txtを読み込む"""
    with open(config_path, "r", encoding="utf-8") as f:
        return f.read()


def select_random_pattern() -> tuple[str, str]:
    """ランダムにどんでん返しパターンを選択"""
    category = random.choice(list(PLOT_TWIST_PATTERNS.keys()))
    pattern = random.choice(PLOT_TWIST_PATTERNS[category])
    return category, pattern


def generate_scenario(api_key: str, plot_twist_rules: str, pattern: str, 
                       title: str = "", theme: str = "", detail: str = "") -> dict:
    """Gemini APIを使用してシナリオを生成"""
    client = genai.Client(api_key=api_key)

    # テーマ指定がある場合は追加
    theme_section = ""
    if theme:
        theme_section = f"""
## 今回のテーマ・指示
{theme}
"""

    # 詳細シナリオ指定がある場合は追加
    detail_section = ""
    if detail:
        detail_section = f"""
## 詳細シナリオ（この内容に従って生成すること）
{detail}
"""

    # タイトル指定
    title_instruction = f'タイトルは「{title}」を使用すること' if title else 'タイトルは内容に合わせて生成すること'

    prompt = f"""
あなたは4コマ漫画のシナリオライターです。
以下のルールに従って、マッチングアプリをテーマにした4コマ漫画のシナリオを生成してください。

## どんでん返しパターン
今回使用するパターン: {pattern}
{theme_section}
{detail_section}
## PlotTwistルール
{plot_twist_rules}

## キャラクター設定
- 主人公: はな（25歳女性）
- 彼氏: まさと（28歳男性）
- 友人: さき（25歳女性）
- 友人: ともや（25歳男性）
- 弟: ようた（20歳男性）

## 制約条件
1. セリフにキャラクターの固有名詞（はな、さき、まさと等）を含めない
2. 心理描写ではなく「実際の行動」ベースで描写する
3. 主人公の目的・戦い・変化の3つのストーリーラインが交錯する瞬間にオチを発生させる
4. 4コマ目は必ずツッコミ（オチ）で終わる
5. {title_instruction}

## 出力形式（JSON）
{{
  "title": "タイトル",
  "plot_twist_pattern": "{pattern}",
  "panels": [
    {{
      "number": 1,
      "name": "起",
      "description": "シーンの説明",
      "characters": ["登場キャラクター"],
      "dialogue": [
        {{"character": "キャラ名", "text": "セリフ", "bubble_type": "normal/monologue/tsukkomi"}}
      ],
      "background": "背景の説明",
      "effects": ["効果"]
    }},
    // 2〜4コマ目も同様
  ],
  "instagram_hook": "SNS用の共感フック文"
}}
"""

    response = client.models.generate_content(
        model="gemini-1.5-flash-latest",
        contents=prompt
    )
    
    # JSONを抽出
    response_text = response.text
    json_start = response_text.find("{")
    json_end = response_text.rfind("}") + 1
    json_str = response_text[json_start:json_end]
    
    return json.loads(json_str)


def validate_scenario(scenario: dict) -> list[str]:
    """シナリオの基本検証"""
    errors = []
    
    # 禁止名のチェック
    scenario_str = json.dumps(scenario, ensure_ascii=False)
    for name in PROHIBITED_NAMES:
        if name in scenario_str:
            errors.append(f"禁止キャラクター名「{name}」が含まれています")
    
    # パネル数チェック
    if len(scenario.get("panels", [])) != 4:
        errors.append("パネル数が4ではありません")
    
    return errors


def parse_pattern_input(pattern_input: str) -> str:
    """入力されたパターン文字列からパターン名を抽出"""
    if not pattern_input or pattern_input == "おまかせ（自動選択）":
        return ""
    # "ドラフランケン (D→F)" のような形式からパターン名を抽出
    pattern_name = pattern_input.split(" (")[0].strip()
    return pattern_name


def main():
    parser = argparse.ArgumentParser(description="4コマ漫画シナリオ生成")
    parser.add_argument("--config", required=True, help="PlotTwist_plain.txtのパス")
    parser.add_argument("--output", required=True, help="出力JSONファイルのパス")
    parser.add_argument("--title", default="", help="漫画のタイトル")
    parser.add_argument("--theme", default="", help="テーマやシナリオ指示")
    parser.add_argument("--pattern", default="", help="どんでん返しパターン")
    parser.add_argument("--detail", default="", help="詳細シナリオ（起承転結を直接指定）")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    # PlotTwistルールを読み込み
    plot_twist_rules = load_plot_twist_rules(args.config)

    # パターン選択
    pattern_name = parse_pattern_input(args.pattern)
    if pattern_name:
        pattern = pattern_name
        category = "manual"
    else:
        category, pattern = select_random_pattern()

    print(f"[Module1] 選択パターン: {pattern} ({category})")
    if args.title:
        print(f"[Module1] タイトル: {args.title}")
    if args.theme:
        print(f"[Module1] テーマ: {args.theme}")

    # シナリオ生成
    scenario = generate_scenario(
        api_key, plot_twist_rules, pattern,
        title=args.title, theme=args.theme, detail=args.detail
    )

    # 検証
    errors = validate_scenario(scenario)
    if errors:
        print(f"[Module1] 警告: {errors}")

    # メタデータ追加
    scenario["metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "pattern_category": category,
        "pattern_name": pattern,
        "validation_errors": errors,
    }

    # 出力
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenario, f, ensure_ascii=False, indent=2)

    print(f"[Module1] シナリオ生成完了: {output_path}")


if __name__ == "__main__":
    main()
