import re

def extract_heading(text: str):
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^#+\s*Chương\s+(\d+)\s*[:\-]\s*(.+?)\s*$", stripped, re.IGNORECASE)
        if match:
            return int(match.group(1)), "MATCH"
        else:
            return None, "NO MATCH"
    return None, None

text1 = "# Chương 1: Title"
print(f"Text 1: {extract_heading(text1)}")

text32 = "# Chương 0032: Title"
print(f"Text 32: {extract_heading(text32)}")
