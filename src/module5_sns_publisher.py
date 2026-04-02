#!/usr/bin/env python3
"""
モジュール5：Instagram投稿文＆メタデータ生成（Gemini API）

完成した4コマ漫画のSNS拡散用キャプションを自動生成する。
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import google.generativeai as genai


class SNSPublisher:
    """SNS投稿文生成クラス"""

    # デフォルトハッシュタグ
    DEFAULT_HASHTAGS = [
        "#4コマ漫画",
        "#恋愛漫画",
        "#恋愛悩み",
        "#マッチングアプリ",
        "#マッチングアプリあるある",
        "#恋愛あるある",
        "#漫画好きと繋がりたい",
        "#イラスト",
        "#創作漫画",
    ]

    def __init__(self, api_key: str, strategy_path: str = None):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        
        self.strategy = ""
        if strategy_path and Path(strategy_path).exists():
            with open(strategy_path, "r", encoding="utf-8") as f:
                self.strategy = f.read()

    def generate_caption(self, scenario: dict) -> dict:
        """Instagram投稿文を生成"""
        title = scenario.get("title", "無題")
        instagram_hook = scenario.get("instagram_hook", "")
        panels = scenario.get("panels", [])
        
        # パネル情報を要約
        panel_summaries = []
        for panel in panels:
            panel_summaries.append(f"- {panel.get('name', '')}: {panel.get('description', '')}")
        panels_text = "\n".join(panel_summaries)

        prompt = f"""
あなたはInstagramのSNSマーケターです。
以下の4コマ漫画の投稿文を作成してください。

## 漫画情報
タイトル: {title}
フック: {instagram_hook}

## ストーリー概要
{panels_text}

## 投稿文の要件
1. 1行目: 読者の共感を呼ぶフック（絵文字を含む）
2. 2-3行目: 漫画のあらすじ（オチのネタバレは絶対禁止）
3. 4行目: コメントを促すCTA（2択質問や絵文字など）
4. 5行目: プロフィール誘導文
5. 最後: ハッシュタグ

## マーケティング戦略
{self.strategy if self.strategy else "なし"}

## 出力形式（JSON）
{{
  "hook": "共感フック（1行目）",
  "summary": "あらすじ（オチなし）",
  "cta": "コメント促進CTA",
  "profile_link": "プロフィール誘導文",
  "hashtags": ["#ハッシュタグ1", "#ハッシュタグ2", ...],
  "full_caption": "完成した投稿文全体"
}}
"""

        response = self.model.generate_content(prompt)
        
        # JSONを抽出
        response_text = response.text
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        json_str = response_text[json_start:json_end]
        
        result = json.loads(json_str)
        
        # デフォルトハッシュタグを追加
        existing_hashtags = set(result.get("hashtags", []))
        for tag in self.DEFAULT_HASHTAGS:
            existing_hashtags.add(tag)
        result["hashtags"] = list(existing_hashtags)
        
        return result

    def format_caption(self, caption_data: dict) -> str:
        """投稿文をフォーマット"""
        lines = [
            caption_data.get("hook", ""),
            "",
            caption_data.get("summary", ""),
            "",
            caption_data.get("cta", ""),
            "",
            caption_data.get("profile_link", ""),
            "",
            " ".join(caption_data.get("hashtags", [])),
        ]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Instagram投稿文生成")
    parser.add_argument("--scenario", required=True, help="検証済みシナリオJSON")
    parser.add_argument("--strategy", help="instagram_marketing_strategy.mdのパス")
    parser.add_argument("--output", required=True, help="出力ファイルパス")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    # シナリオ読み込み
    with open(args.scenario, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    # 投稿文生成
    publisher = SNSPublisher(api_key, args.strategy)
    caption_data = publisher.generate_caption(scenario)
    
    # フォーマット
    formatted_caption = publisher.format_caption(caption_data)

    # 出力
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # テキストファイル出力
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(formatted_caption)
    
    # JSONも出力
    json_output_path = output_path.with_suffix(".json")
    caption_data["formatted_caption"] = formatted_caption
    caption_data["generated_at"] = datetime.now().isoformat()
    caption_data["scenario_title"] = scenario.get("title", "無題")
    
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(caption_data, f, ensure_ascii=False, indent=2)

    print(f"[Module5] 投稿文生成完了")
    print(f"[Module5] テキスト出力: {output_path}")
    print(f"[Module5] JSON出力: {json_output_path}")
    print(f"[Module5] ハッシュタグ数: {len(caption_data.get('hashtags', []))}")
    print("\n--- 生成された投稿文 ---")
    print(formatted_caption)


if __name__ == "__main__":
    main()
