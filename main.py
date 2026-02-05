import sys
import re
import time
import random

class NagataChoInterpreter:
    def __init__(self):
        self.variables = {}
        self.renho_mode = False
        self.nonomura_mode = False
        self.koizumi_mode = False
        self.constants = {
            "KakugiKettei": True,
            "Gojin": False,
            "None": None
        }

    def execute(self, code_lines):
        print("--- 国会審議開始 (Session Start) ---")
        pc = 0
        total_lines = len(code_lines)
        loop_stack = [] 

        while pc < total_lines:
            line = code_lines[pc].strip()
            if not line or line.startswith("//"):
                pc += 1
                continue

            try:
                # 1. Sakiokuri (Whileループ)
                if line.startswith("Sakiokuri"):
                    condition_str = re.search(r'Sakiokuri\s*\((.*)\)', line)
                    if condition_str:
                        # 条件判定時は蓮舫モード無効（1が2にならないように）
                        cond = self.evaluate(condition_str.group(1), ignore_renho=True)
                        if cond:
                            loop_stack.append(pc)
                            pc += 1
                        else:
                            pc = self.find_matching_brace(code_lines, pc) + 1
                        continue

                # 2. ループ終了 '}'
                if line == "}":
                    if loop_stack:
                        pc = loop_stack.pop()
                        continue
                    else:
                        pc += 1
                        continue

                # 3. Zensho (If文)
                if line.startswith("Zensho"):
                    parts = re.search(r'Zensho\s*\((.*)\)\s*->\s*(.*)', line)
                    if parts:
                        cond = self.evaluate(parts.group(1), ignore_renho=True)
                        if cond:
                            self.parse_line(parts.group(2))
                        pc += 1
                        continue

                self.parse_line(line)
                pc += 1

            except Exception as e:
                if self.nonomura_mode:
                    self.trigger_nonomura_panic()
                    break 
                else:
                    print(f"[野党のヤジ] Error: {e}")
                    pc += 1

    def find_matching_brace(self, lines, start_index):
        count = 0
        for i in range(start_index, len(lines)):
            if "{" in lines[i]: count += 1
            if "}" in lines[i]: count -= 1
            if count == 0: return i
        return len(lines)

    def parse_line(self, line):
        line = line.strip()

        # import
        if line == "import Koizumi":
            self.koizumi_mode = True
            print("[System] 小泉環境相が入閣しました（セクシーモードON）")
            return

        # Jinin
        if line.startswith("Jinin"):
            target = line.split()[1]
            if target == "Koizumi":
                self.koizumi_mode = False
                print("[System] 小泉環境相が辞任しました（セクシーモードOFF）")
            return

        if line.startswith("Kentou"):
            print("[Kentou] ...（前向きに検討中ですが、何もしません）")
            return

        if line.startswith("Habatsu"):
            parts = line.split()
            habatsu_name = parts[1]
            if "Riritou" in line or "extends" in line:
                old_party = parts[3] if len(parts) > 3 else "Jiminto"
                print(f"[System] {old_party} を離党し、派閥「{habatsu_name}」を設立しました。")
            else:
                print(f"[System] 派閥「{habatsu_name}」が結成されました。")
            return

        if "PublicComment()" in line:
            parts = line.split("=")
            var_name = parts[0].replace("Touben", "").replace("Yosan", "").replace("string", "").strip()
            print(f"[PublicComment] 意見を入力してください ({var_name}):")
            user_input = input(">> ")
            if random.random() < 0.2:
                print("[System] (その意見はシュレッダーにかけられました)")
                self.variables[var_name] = "Gojin"
            else:
                self.variables[var_name] = user_input
            return

        if " = " in line and not line.startswith("Zensho"):
            clean_line = line.replace("Sexy", "").replace("Yosan", "").replace("Touben", "").replace("int", "").replace("string", "").strip()
            parts = clean_line.split("=")
            var_name = parts[0].strip()
            expr = parts[1].strip()
            val = self.evaluate(expr)
            self.variables[var_name] = val
            return

        if line.startswith("KishaKaiken"):
            content_match = re.search(r'KishaKaiken\((.*)\)', line)
            if content_match:
                raw_val = content_match.group(1)
                val = self.evaluate(raw_val)
                if self.koizumi_mode:
                    val = self.koizumi_translator(str(val))
                print(f"[答弁] {val}")
            return

        if line == "SoExcited":
            print("[安倍氏] 「そんなに興奮しないでください...」（3秒停止）")
            time.sleep(3)
            return

        if line == "#pragma Renho":
            self.renho_mode = True
            print("[Renho] 蓮舫氏「事業仕分けを開始します。」")
            return

        if line == "RyutaroCatch":
            self.nonomura_mode = True
            raise Exception("SeimuKatsudohi error")

        if "++" in line:
            var_name = line.replace("++", "").strip()
            if var_name in self.variables: self.variables[var_name] += 1
            return
        if "--" in line:
            var_name = line.replace("--", "").strip()
            if var_name in self.variables: self.variables[var_name] -= 1
            return

    def evaluate(self, expr, ignore_renho=False):
        """式の評価（ここを修正しました）"""
        
        # 実行コンテキスト（変数と定数）
        context = {**self.variables, **self.constants}

        try:
            # 1. まずは素直に計算してみる
            # Pythonのevalは優秀なので "Hello" も 1+1 も計算できます
            result = eval(expr, {}, context)
            
            # 蓮舫チェック (1位なら2位にする)
            if not ignore_renho and self.renho_mode and type(result) is int and result == 1:
                print("  [Renho] 「二位じゃダメなんですか」（1を2に変更）")
                return 2
            return result

        except TypeError:
            # 2. 文字列と数値を足そうとして失敗した場合
            # (例: "Rank: " + 1)
            # 変数をすべて文字列化して再計算する
            try:
                str_context = {k: str(v) for k, v in self.variables.items()}
                str_context.update(self.constants)
                return eval(expr, {}, str_context)
            except:
                # それでもダメなら引用符を取って返す
                return expr.strip('"')

        except Exception:
            # 3. そもそも計算式じゃない場合（ただの単語など）
            return expr.strip('"')

    def koizumi_translator(self, text):
        return f"今のままではいけないと思います。だからこそ、{text}。"

    def trigger_nonomura_panic(self):
        screams = ["うわああああん！", "この世の中を！ ガエダイ！", "やっと議員になったんです！", "アハァーン！", "命がけでッヘッヘエエ！"]
        print("\n[Ryutaro Exception Thrown]")
        for _ in range(5):
            print(f"[Ryutaro] {random.choice(screams)}")
            time.sleep(0.3)
        print("（会見場から退出しました）")

if __name__ == "__main__":
    filename = "test.ncp"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            code = f.readlines()
        interpreter = NagataChoInterpreter()
        interpreter.execute(code)
    except FileNotFoundError:
        print(f"[System] 法案ファイル '{filename}' が提出されていません。")