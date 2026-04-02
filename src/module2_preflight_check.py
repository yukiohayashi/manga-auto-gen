#!/usr/bin/env python3
"""
モジュール2：プリフライト検証＆テキスト補正

画像生成前にシナリオを検証し、仕様違反やAI特有のエラーを自動検知・修正する。
"""

import argparse
import json
import re
from pathlib import Path

import yaml


class PreflightChecker:
    """プリフライト検証クラス"""

    # 必須チェック項目
    REQUIRED_CANVAS_SIZE = "1000px × 1000px 正方形"
    REQUIRED_FONTS = ["Noto Sans JP Black", "M PLUS Rounded 1c ExtraBold"]
    
    # 吹き出し色仕様
    BUBBLE_COLORS = {
        "female": {"hex": "#FFE800", "characters": ["はな", "さき"]},
        "male": {"hex": "#D4E8FF", "characters": ["まさと", "ともや", "ようた"]},
        "monologue": {"hex": "#FFFFFF", "characters": ["all"]},
    }
    
    # 禁止キャラクター名
    PROHIBITED_NAMES = ["あや"]
    
    # セリフ内で禁止される固有名詞
    PROHIBITED_IN_DIALOGUE = ["はな", "さき", "まさと", "ともや", "ようた"]

    def __init__(self, spec_path: str):
        """manga_spec.ymlを読み込み"""
        with open(spec_path, "r", encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)
        self.errors = []
        self.warnings = []
        self.corrections = []

    def check_prohibited_names(self, scenario: dict) -> None:
        """禁止キャラクター名のチェック"""
        scenario_str = json.dumps(scenario, ensure_ascii=False)
        for name in self.PROHIBITED_NAMES:
            if name in scenario_str:
                self.errors.append(f"禁止キャラクター名「{name}」が含まれています")

    def check_dialogue_names(self, scenario: dict) -> None:
        """セリフ内の固有名詞チェック"""
        for panel in scenario.get("panels", []):
            for dialogue in panel.get("dialogue", []):
                text = dialogue.get("text", "")
                for name in self.PROHIBITED_IN_DIALOGUE:
                    if name in text:
                        self.errors.append(
                            f"パネル{panel['number']}のセリフに固有名詞「{name}」が含まれています: {text}"
                        )

    def check_panel_count(self, scenario: dict) -> None:
        """パネル数チェック"""
        panels = scenario.get("panels", [])
        if len(panels) != 4:
            self.errors.append(f"パネル数が4ではありません（現在: {len(panels)}）")

    def fix_duplicate_text(self, scenario: dict) -> dict:
        """連続重複テキストの自動修正"""
        for panel in scenario.get("panels", []):
            for dialogue in panel.get("dialogue", []):
                original_text = dialogue.get("text", "")
                
                # 連続重複パターンを検出（例: "全部覚えて全部覚えて" → "全部覚えて"）
                # 2〜10文字の繰り返しを検出
                for length in range(2, 11):
                    pattern = rf"(.{{{length}}})\1+"
                    match = re.search(pattern, original_text)
                    if match:
                        fixed_text = re.sub(pattern, r"\1", original_text)
                        if fixed_text != original_text:
                            self.corrections.append({
                                "panel": panel["number"],
                                "original": original_text,
                                "fixed": fixed_text,
                                "type": "consecutive_duplicate"
                            })
                            dialogue["text"] = fixed_text
                
                # 非連続重複の警告（同じフレーズが離れた場所に2回以上出現）
                words = re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", dialogue.get("text", ""))
                word_counts = {}
                for word in words:
                    if len(word) >= 3:
                        word_counts[word] = word_counts.get(word, 0) + 1
                for word, count in word_counts.items():
                    if count >= 2:
                        self.warnings.append(
                            f"パネル{panel['number']}で「{word}」が{count}回出現しています"
                        )
        
        return scenario

    def check_bubble_types(self, scenario: dict) -> None:
        """吹き出しタイプのチェック"""
        for panel in scenario.get("panels", []):
            for dialogue in panel.get("dialogue", []):
                bubble_type = dialogue.get("bubble_type", "normal")
                if bubble_type not in ["normal", "monologue", "tsukkomi", "shout"]:
                    self.warnings.append(
                        f"パネル{panel['number']}で不明な吹き出しタイプ: {bubble_type}"
                    )

    def check_tsukkomi_in_panel4(self, scenario: dict) -> None:
        """4コマ目にツッコミがあるかチェック"""
        panels = scenario.get("panels", [])
        if len(panels) >= 4:
            panel4 = panels[3]
            has_tsukkomi = any(
                d.get("bubble_type") == "tsukkomi" 
                for d in panel4.get("dialogue", [])
            )
            if not has_tsukkomi:
                self.warnings.append("4コマ目にツッコミ（tsukkomi）タイプの吹き出しがありません")

    def run_all_checks(self, scenario: dict) -> dict:
        """全チェックを実行"""
        self.errors = []
        self.warnings = []
        self.corrections = []

        # 各チェック実行
        self.check_prohibited_names(scenario)
        self.check_dialogue_names(scenario)
        self.check_panel_count(scenario)
        self.check_bubble_types(scenario)
        self.check_tsukkomi_in_panel4(scenario)
        
        # 自動修正
        scenario = self.fix_duplicate_text(scenario)

        # 検証結果をシナリオに追加
        scenario["preflight_result"] = {
            "passed": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "corrections": self.corrections,
        }

        return scenario


def main():
    parser = argparse.ArgumentParser(description="プリフライト検証")
    parser.add_argument("--scenario", required=True, help="入力シナリオJSONファイル")
    parser.add_argument("--spec", required=True, help="manga_spec.ymlのパス")
    parser.add_argument("--output", required=True, help="出力JSONファイルのパス")
    args = parser.parse_args()

    # シナリオ読み込み
    with open(args.scenario, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    # 検証実行
    checker = PreflightChecker(args.spec)
    validated_scenario = checker.run_all_checks(scenario)

    # 結果出力
    result = validated_scenario["preflight_result"]
    print(f"[Module2] 検証結果: {'PASS' if result['passed'] else 'FAIL'}")
    
    if result["errors"]:
        print(f"[Module2] エラー ({len(result['errors'])}件):")
        for err in result["errors"]:
            print(f"  - {err}")
    
    if result["warnings"]:
        print(f"[Module2] 警告 ({len(result['warnings'])}件):")
        for warn in result["warnings"]:
            print(f"  - {warn}")
    
    if result["corrections"]:
        print(f"[Module2] 自動修正 ({len(result['corrections'])}件):")
        for corr in result["corrections"]:
            print(f"  - パネル{corr['panel']}: {corr['original']} → {corr['fixed']}")

    # 出力
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(validated_scenario, f, ensure_ascii=False, indent=2)

    print(f"[Module2] 検証済みシナリオ出力: {output_path}")

    # エラーがある場合は終了コード1
    if not result["passed"]:
        exit(1)


if __name__ == "__main__":
    main()
