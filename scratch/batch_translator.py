#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Insert ROOT in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import google.generativeai as genai
except ImportError:
    print("Vui lòng cài đặt google-generativeai: pip install google-generativeai")
    sys.exit(1)

from Script.strict_engine.utils.io import load_json, save_json_atomic, resolve_branch_dir, get_logger

LOGGER = get_logger("batch_translator")

PROMPT_TEMPLATE = """Bạn là một AI dịch thuật cao cấp, chuyên dịch tiểu thuyết võ hiệp/tiên hiệp/khoa huyễn Trung-Việt, đặc biệt là tác phẩm "Tu Chân Bốn Vạn Năm" (修真四万年).
Nhiệm vụ của bạn là dịch các phân đoạn nguồn (source_segments) trong context pack sang tiếng Việt và thực hiện phân tích chương học chi tiết theo đúng cấu trúc Schema V2.0.

QUY TẮC QUAN TRỌNG:
1. KHÔNG được chứa bất kỳ ký tự Trung Quốc (CJK) nào trong các phần dịch mục tiêu (target) và các trường phân tích tiếng Việt.
2. Tuân thủ tuyệt đối các thuật ngữ bị khóa (locked_terms) có trong context pack. Ví dụ: "晶脑" bắt buộc dịch thành "Tinh não", "修真" dịch thành "tu chân", v.v.
3. Mỗi phân đoạn nguồn (source_segment) phải có đúng một phần dịch tương ứng với segment_id chính xác. Không bỏ sót, không tự gộp hay chia lại segment nếu không được yêu cầu.
4. "narrative_type" của mỗi phân đoạn dịch phải là một trong: "narration", "dialogue", "inner_thought", "description".
5. Thực hiện phân tích ngữ cảnh để tìm các term mới phát hiện (new_terms_discovered), nhân vật mới phát hiện (new_characters_discovered), worldbuilding cập nhật (locations, items, factions, techniques, cultivation_resources), và tóm tắt chương cũng như timeline chi tiết.
6. Trong phân tích candidates (analysis_candidates):
   - Đảm bảo tham chiếu chính xác đến segment_id dạng "chapter_XXXX:seg_XXXX".
   - Nếu không tìm thấy bằng chứng cho một phân mục (ví dụ: grammar_rule_candidates), PHẢI ghi status là "no_evidence", evidence_count là 0, và items là mảng rỗng []. KHÔNG được bỏ trống hay để status là "ok" nếu không có items.
   - Thống kê các term xuất hiện, thực thể, tên nhân vật tìm thấy có trong văn bản nguồn.
7. ĐẦU RA PHẢI LÀ MỘT ĐỐI TƯỢNG JSON HỢP LỆ khớp hoàn toàn với JSON Schema V2.

Dưới đây là Context Pack dữ liệu của chương cần dịch:
{context_pack_json}
"""

def run_cmd(args: list[str]) -> bool:
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        LOGGER.error(f"Lệnh thất bại: {' '.join(args)}")
        LOGGER.error(f"STDOUT: {res.stdout}")
        LOGGER.error(f"STDERR: {res.stderr}")
        return False
    return True

def translate_chapter(branch_name: str, chapter: int, model_name: str = "gemini-2.5-flash") -> bool:
    LOGGER.info(f"=== Bắt đầu dịch Chương {chapter} ===")
    
    # 1. Chạy Preflight
    preflight_cmd = [
        sys.executable,
        "Script/strict_engine/translation_runner.py",
        "preflight",
        "--branch", branch_name,
        "--chapter", str(chapter)
    ]
    LOGGER.info(f"Đang chạy preflight...")
    if not run_cmd(preflight_cmd):
        LOGGER.error(f"Preflight thất bại cho chương {chapter}")
        return False
        
    branch_dir = resolve_branch_dir(branch_name)
    context_pack_path = branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
    if not context_pack_path.exists():
        LOGGER.error(f"Không tìm thấy file context pack: {context_pack_path}")
        return False
        
    pack = load_json(context_pack_path)
    
    # 2. Gọi Gemini API
    prompt = PROMPT_TEMPLATE.format(context_pack_json=json.dumps(pack, ensure_ascii=False, indent=2))
    
    LOGGER.info(f"Đang gửi request dịch lên Gemini API (model={model_name})...")
    model = genai.GenerativeModel(
        model_name,
        generation_config={"response_mime_type": "application/json"}
    )
    
    # Thử gọi API với cơ chế retry đơn giản
    for attempt in range(1, 4):
        try:
            response = model.generate_content(prompt)
            result = json.loads(response.text)
            
            # Ghi nhận kết quả thô
            result_path = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
            save_json_atomic(result_path, result)
            LOGGER.info(f"Đã lưu kết quả dịch thô tại {result_path}")
            break
        except Exception as e:
            LOGGER.warning(f"Lỗi gọi API lần thử {attempt}: {e}")
            if attempt == 3:
                LOGGER.error("Thử lại thất bại sau 3 lần.")
                return False
            time.sleep(5)
            
    # 3. Chạy Postflight để kiểm tra các gate, tạo markdown, phân tích và cập nhật trạng thái
    postflight_cmd = [
        sys.executable,
        "Script/strict_engine/translation_runner.py",
        "postflight",
        "--branch", branch_name,
        "--chapter", str(chapter)
    ]
    LOGGER.info(f"Đang chạy postflight...")
    if not run_cmd(postflight_cmd):
        LOGGER.error(f"Postflight thất bại cho chương {chapter}. Vui lòng kiểm tra báo cáo lỗi trong runtime/gates/")
        return False
        
    LOGGER.info(f"=== Đã hoàn thành dịch và duyệt Chương {chapter} thành công! ===")
    return True

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("LỖI: Chưa cấu hình GEMINI_API_KEY trong biến môi trường.")
        sys.exit(1)
        
    genai.configure(api_key=api_key)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", default="Tu Chan Bon Van Nam_Ngoa Nguu Chan Nhan")
    parser.add_argument("--start", type=int, default=40)
    parser.add_argument("--end", type=int, default=100)
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()
    
    failed_chapters = []
    for chap in range(args.start, args.end + 1):
        try:
            success = translate_chapter(args.branch, chap, args.model)
            if not success:
                failed_chapters.append(chap)
                LOGGER.error(f"Dừng dịch do lỗi ở Chương {chap}.")
                break
        except Exception as e:
            failed_chapters.append(chap)
            LOGGER.error(f"Lỗi ngoại lệ khi xử lý Chương {chap}: {e}")
            break
            
    if failed_chapters:
        print(f"Quá trình dịch dừng lại. Các chương thất bại/chưa dịch hết: {failed_chapters}")
        sys.exit(1)
    else:
        print(f"Chúc mừng! Đã dịch thành công tất cả các chương từ {args.start} đến {args.end}!")

if __name__ == "__main__":
    main()
