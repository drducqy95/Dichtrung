#!/usr/bin/env python3
"""
Retroactive AI Aligner - Uses Gemini API to generate perfect 1-to-1 semantic mapping 
between source_text and translated_text for existing chapters.
"""

import argparse
import sys
import os
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("Vui lòng cài đặt thư viện: pip install google-generativeai")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.io import load_json, save_json_atomic, resolve_branch_dir, get_logger

LOGGER = get_logger("retroactive_align")

PROMPT_TEMPLATE = """Bạn là một chuyên gia đối chiếu ngôn ngữ Trung-Việt.
Dưới đây là một đoạn văn bản gốc tiếng Trung (Source Text) và bản dịch tiếng Việt của nó (Translated Text).
Nhiệm vụ của bạn là ánh xạ từng đoạn/câu của văn bản gốc với bản dịch tương ứng của nó.

Yêu cầu ĐẦU RA (Output) PHẢI LÀ MỘT MẢNG JSON HỢP LỆ (chỉ chứa mảng JSON, không bọc trong markdown code block nếu không cần thiết, hoặc nếu có thì tôi sẽ tự parse).
Cấu trúc mỗi item trong mảng:
{
  "source": "câu tiếng trung gốc",
  "target": "câu dịch tiếng việt tương ứng",
  "narrative_type": "narration" | "dialogue" | "inner_thought" | "description"
}

QUY TẮC QUAN TRỌNG:
1. Bạn không được tự ý sửa đổi bản dịch. Bạn PHẢI trích xuất chính xác từng chữ từ bản dịch đã cung cấp.
2. Không được bỏ sót bất kỳ câu nào trong văn bản gốc. Toàn bộ văn bản gốc phải được chia thành các segments.
3. Nếu 2 câu gốc được gộp thành 1 câu dịch, hãy ghép 2 câu gốc lại vào trường "source" và để "target" là câu dịch. Đảm bảo mapping sát nghĩa nhất.

SOURCE TEXT:
{source}

TRANSLATED TEXT:
{target}
"""

def run_alignment(branch_name: str, start: int, end: int):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        LOGGER.error("LỖI: Không tìm thấy GEMINI_API_KEY trong biến môi trường.")
        LOGGER.info("Hãy set biến môi trường: set GEMINI_API_KEY=your_key")
        return

    genai.configure(api_key=api_key)
    # Cấu hình model (sử dụng gemini-2.5-flash vì context dài và tốc độ cao)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    branch_dir = resolve_branch_dir(branch_name)
    
    for chapter in range(start, end + 1):
        context_pack_file = branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
        translation_result_file = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
        
        if not context_pack_file.exists() or not translation_result_file.exists():
            LOGGER.warning(f"Chương {chapter} không có đủ data để align. Bỏ qua.")
            continue
            
        LOGGER.info(f"Đang xử lý Chương {chapter}...")
        
        pack = load_json(context_pack_file)
        result = load_json(translation_result_file)
        
        source_text = pack.get("chapter", {}).get("source_text", "")
        translated_text = result.get("translated_text", "")
        
        if not source_text or not translated_text:
            LOGGER.warning(f"Chương {chapter} thiếu text.")
            continue
            
        prompt = PROMPT_TEMPLATE.format(source=source_text, target=translated_text)
        
        try:
            LOGGER.info("Gửi request lên Gemini API...")
            response = model.generate_content(prompt)
            # Response expects a JSON array directly because of response_mime_type = application/json
            
            import json
            aligned_segments = json.loads(response.text)
            
            # Ghi vào analysis_result.json
            analysis_out_path = branch_dir / "runtime" / "analysis" / f"chapter_{chapter:04d}.analysis_result.json"
            
            # Đọc lại cái cũ nếu có để giữ lại quality_audit v.v.
            analysis_data = load_json(analysis_out_path) or {}
            analysis_data["schema_version"] = "1.0"
            analysis_data["branch"] = branch_name
            analysis_data["chapter"] = chapter
            analysis_data["aligned_segments"] = aligned_segments
            
            save_json_atomic(analysis_out_path, analysis_data)
            LOGGER.info(f"Đã lưu analysis_result.json cho chương {chapter}.")
            
            # Chạy lại validate và update state
            from update_analysis_state import update_analysis_state
            update_analysis_state(branch_name, chapter)
            
        except Exception as e:
            LOGGER.error(f"Lỗi khi xử lý chương {chapter}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    
    run_alignment(args.branch, args.start, args.end)
