import sys
import os
import unittest

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from src.agents.seeker_file_upload_agent import extract_ncs_level, extract_rcs_level, extract_talent_type

class TestRegexParsing(unittest.TestCase):
    def test_ncs_level_parsing(self):
        cases = [
            ("- **NCS Level:** **Lv. 3**", "Lv. 3"),  # Standard (Double Bold)
            ("- **NCS Level:** Lv. 3", "Lv. 3"),      # Single Bold (Key only)
            ("- **NCS Level:** **Lv.3**", "Lv.3"),    # No space in value
            ("- **NCS Level:** Lv.3", "Lv.3"),        # No space, no bold value
            ("- **NCS Level:** **Lv. 3** (High)", "Lv. 3"), # With parenthesis
            ("- **NCS Level:** Lv. 3 (High)", "Lv. 3"),     # With parenthesis, no bold
        ]
        
        print("\n[Testing NCS Level Parsing]")
        for text, expected in cases:
            result = extract_ncs_level(text)
            print(f"Input: '{text}' -> Output: '{result}' (Expected: '{expected}')")
            self.assertEqual(result, expected)

    def test_rcs_level_parsing(self):
        cases = [
            ("- **RCS Level:** **Lv. 4**", "Lv. 4"),
            ("- **RCS Level:** Lv. 4", "Lv. 4"),
            ("- **RCS Level:** **Lv.4**", "Lv.4"),
            ("- **RCS Level:** Lv.4", "Lv.4"),
        ]
        
        print("\n[Testing RCS Level Parsing]")
        for text, expected in cases:
            result = extract_rcs_level(text)
            print(f"Input: '{text}' -> Output: '{result}' (Expected: '{expected}')")
            self.assertEqual(result, expected)

    def test_talent_type_parsing(self):
        cases = [
            ("- **Talent Type:** **PROVEN_ACE**", "PROVEN_ACE"),
            ("- **Talent Type:** PROVEN_ACE", "PROVEN_ACE"),
            ("- **Talent Type:** **HIDDEN_GEM**", "HIDDEN_GEM"),
            ("- **Talent Type:** LEARNER", "LEARNER"),
        ]
        
        print("\n[Testing Talent Type Parsing]")
        for text, expected in cases:
            result = extract_talent_type(text)
            print(f"Input: '{text}' -> Output: '{result}' (Expected: '{expected}')")
            self.assertEqual(result, expected)
            
    def test_full_markdown_context(self):
        markdown_text = """
        ## [Step 3: Final Analysis Summary]
        
        - **Name:** 홍길동
        - **NCS Level:** **Lv. 3** (Derived from project A)
        - **RCS Level:** Lv. 4
        - **Talent Type:** **PROVEN_ACE**
        - **Summary:** "Good candidate"
        """
        
        print("\n[Testing Full Markdown Context]")
        
        ncs = extract_ncs_level(markdown_text)
        rcs = extract_rcs_level(markdown_text)
        talent = extract_talent_type(markdown_text)
        
        print(f"NCS: {ncs}")
        print(f"RCS: {rcs}")
        print(f"Talent: {talent}")
        
        self.assertEqual(ncs, "Lv. 3")
        self.assertEqual(rcs, "Lv. 4")
        self.assertEqual(talent, "PROVEN_ACE")

if __name__ == '__main__':
    unittest.main()
