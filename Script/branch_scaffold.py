from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "Output"
GLOBAL_CONFIG_PATH = ROOT / "Global State" / "global_config.json"

DISPLAY_FILENAME_PATTERN = "Chương {chapter:04d}: {title}.md"
FILESYSTEM_FILENAME_PATTERN = "Chương {chapter:04d} - {title}.md"
FILESYSTEM_NOTE = "Windows không cho phép ký tự ':' trong tên file, vì vậy pattern lưu trên đĩa dùng dấu gạch ngang."
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

BRANCH_OVERRIDES: dict[str, dict[str, Any]] = {
    "Ac Linh Quoc Gia": {
        "backdrop": "Đô thị hiện đại bị xâm thực bởi các sự kiện siêu nhiên, nơi hợp đồng việc làm lương cao thực chất là cánh cửa dẫn vào chuỗi nhiệm vụ linh dị và sinh tử.",
        "summary": "Hạ Thiên Kì từ một sinh viên bình thường bị cuốn vào công ty bí ẩn chuyên xử lý các sự kiện quỷ dị. Càng tiến sâu, anh càng nhận ra công việc ấy là trò chơi sinh tồn được xây bằng sợ hãi, mưu tính và cái giá phải trả để còn sống.",
        "style_tags": ["đô thị", "kinh dị", "đen hài", "căng thẳng"],
        "cover_prompt": "Bìa dọc 6x9, đô thị mưa đêm xanh chì, tòa nhà văn phòng tối om, nam chính trẻ đứng cạnh sedan hạng sang nhưng bóng đổ sau lưng méo mó như ác linh, cinematic horror, chi tiết cao.",
        "sample_chapter": 1,
        "sample_summary": "Hạ Thiên Kì vừa ký được hợp đồng thử việc lương cao đến mức phi lý, nhưng niềm vui ấy lập tức pha lẫn bất an khi anh bị đưa thẳng đến công việc thật sự.",
        "sample_characters": ["Hạ Thiên Kì", "người đàn ông trung niên đưa đón"],
        "sample_entities": ["công ty bí ẩn", "hợp đồng thử việc", "Audi A6"],
        "sample_tone_tags": ["horror công sở", "bất an", "mồi nhử", "đổi vận"],
        "sample_illustration": "Khoảnh khắc Hạ Thiên Kì ngồi trong chiếc Audi A6, vẻ mừng rỡ trên mặt còn chưa tan nhưng ánh sáng ngoài kính xe lạnh bất thường, như đang lao tới một nơi không nên đặt chân.",
        "signature_style_name": "U ám đen hài",
        "signature_style_purpose": "Giữ chút trào phúng mỏng ở bề mặt rồi lật sang cảm giác rợn người.",
        "signature_style_tail": "Niềm vui trong cảnh này vì thế không hề sáng sủa; nó giống mồi câu hơn là phần thưởng.",
    },
    "Chu Than Dai Dao_Co Nguyet Cu Si": {
        "backdrop": "Hiện đại đô thị giao cắt với con đường thành thần và vô hạn thế giới, nơi cơ duyên siêu hình có thể xé toạc nhịp sống bình thường chỉ trong một khoảnh khắc.",
        "summary": "Triệu Kỳ từ một người bình thường bỗng chạm vào cơ duyên vượt khỏi nhận thức, từ đó bước lên hành trình thành thần, kiến tạo thế giới và can dự vào những cục diện lớn hơn rất nhiều so với đời sống phàm tục.",
        "style_tags": ["vô hạn lưu", "thành thần", "đại cục", "huyền ảo"],
        "cover_prompt": "Bìa dọc 6x9, thanh niên đứng giữa phố hiện đại nhưng sau lưng mở ra nhiều vòng sáng như cổng thế giới chồng lớp, tông vàng lam, cảm giác thần tính giáng lâm.",
        "sample_chapter": 1,
        "sample_summary": "Triệu Kỳ bất ngờ chịu đựng cơn đau đầu như bị vô số ý niệm xâm nhập, mở ra dấu hiệu đầu tiên cho cơ duyên vượt khỏi đời thường.",
        "sample_characters": ["Triệu Kỳ", "ông lão bên đường"],
        "sample_entities": ["dị tượng trong não", "cơ duyên thành thần", "tiếng nói hỗn loạn"],
        "sample_tone_tags": ["khai mở", "siêu hình", "choáng váng", "tiền định"],
        "sample_illustration": "Triệu Kỳ quỵ giữa phố, đám đông thường dân vây quanh nhưng phía sau đầu hắn mơ hồ chồng lên vô số bóng mờ và quầng sáng như cả thế giới đang ép xuống.",
        "signature_style_name": "Thần tính đại cục",
        "signature_style_purpose": "Kéo giọng kể gần hơn với cảm giác thiên mệnh và con đường thành thần.",
        "signature_style_tail": "Điều thay đổi ở đây không chỉ là số phận của một người, mà còn là góc nhìn về cả trật tự thế giới.",
    },
    "Hong Hoang Lich_Zhttty": {
        "backdrop": "Một biên niên sử hồng hoang nơi bóng tối, sinh tồn, ma pháp, công nghệ và tu luyện cùng lúc tồn tại, khiến mỗi bước tiến cá nhân đều chạm tới vận mệnh của cả văn minh.",
        "summary": "Tác phẩm dẫn người đọc từ cảnh sinh tồn trong hỗn loạn sang những cột mốc liên quan đến Chủ Thần, công pháp và quá trình xây dựng lực lượng. Nhịp truyện rộng, nhiều tuyến và thiên về quy mô đại cục.",
        "style_tags": ["hồng hoang", "sử thi", "sinh tồn", "đa văn minh"],
        "cover_prompt": "Bìa dọc 6x9, vùng đất hồng hoang nửa là đêm bất tận nửa là quang mang linh lực, phía xa có thành trì, robot cháy dở và tháp ma pháp cùng xuất hiện trong một đường chân trời.",
        "sample_chapter": 10,
        "sample_summary": "Sau biến cố sống còn, nhiều tuyến nhân vật ở các khu vực khác nhau cùng nhận ra giá trị thật sự của công pháp và tia hy vọng mới để đối đầu với thời đại hỗn loạn.",
        "sample_characters": ["Từ Văn", "Vương Vũ", "Pháp Nhĩ Ai", "Ngô Minh"],
        "sample_entities": ["Chủ Thần", "Thượng Thanh Tru Tiên Công", "đại quân robot", "Vô Tận Lục Hải"],
        "sample_tone_tags": ["sử thi", "hỗn loạn", "hy vọng", "bước ngoặt"],
        "sample_illustration": "Một montage đa lớp: Từ Văn quỳ bên thi thể vợ trong đêm, Vương Vũ hút năng lượng từ PDA trong tầng hầm, và Pháp Nhĩ Ai run lên vì phát hiện đột phá trong phòng thí nghiệm ma pháp.",
        "signature_style_name": "Hồng hoang sử thi",
        "signature_style_purpose": "Làm nổi bật cảm giác đại thế đang chuyển động trên quy mô nhiều văn minh.",
        "signature_style_tail": "Từ những cảnh tưởng như rời rạc, nhịp điệu của một thời đại mới bắt đầu ghép lại thành sử thi chung.",
    },
    "Pham Nhan Bat au oat Xa Mac Cu Nhan_Tieu Tran Tu": {
        "backdrop": "Fanfiction đặt trên nền Phàm Nhân Tu Tiên, nơi một linh hồn dị thế nhập vào thân xác Mặc Cư Nhân và cố viết lại vận mệnh bi kịch đã định của mình.",
        "summary": "Từ vị trí vốn là một nhân vật bi kịch ở đầu truyện gốc, Mặc Cư Nhân nay có thêm ký ức của kẻ biết trước cốt truyện và quyết tâm thoát khỏi kết cục cũ bằng tính toán, huyết mạch và hiểu biết nguyên tác.",
        "style_tags": ["fanfic", "tiên hiệp", "đoạt xá", "đổi mệnh"],
        "cover_prompt": "Bìa dọc 6x9, một lão y sư áo xanh đứng giữa Thần Thủ cốc, nửa gương mặt già nua nửa là bóng linh hồn trẻ hơn phản chiếu, tông xanh ngọc và nâu trầm, tiên hiệp nhưng hiểm ác.",
        "sample_chapter": 1,
        "sample_summary": "Linh hồn dị thế tỉnh dậy trong thân xác Mặc Cư Nhân, ngay lập tức ý thức rõ bi kịch nguyên bản của nhân vật này và bắt đầu suy tính đường thoát cho mình.",
        "sample_characters": ["Mặc Cư Nhân", "Dư Tử Đồng"],
        "sample_entities": ["Thần Thủ cốc", "huyết mạch chuyển hóa", "Kinh Giao hội"],
        "sample_tone_tags": ["tiên hiệp", "bi kịch", "tính toán", "đổi mệnh"],
        "sample_illustration": "Mặc Cư Nhân đứng trên sườn núi của Thần Thủ cốc, gương mặt già nua ngước lên trời, trong mắt vừa có vẻ bất lực vừa có toán tính của kẻ biết trước số mệnh.",
        "signature_style_name": "Tiên hiệp lão luyện",
        "signature_style_purpose": "Đẩy giọng văn gần hơn với sắc thái cổ phong mực thước của tiên hiệp.",
        "signature_style_tail": "Cảnh này vì thế không chỉ là xuyên qua, mà còn là khoảnh khắc một quân cờ quyết định tự sửa lại bàn cờ.",
    },
    "Phi Pham Hong Hoang_Nga Tu Phi Pham": {
        "backdrop": "Thiên địa sơ khai của thế giới Hồng Hoang, nơi núi chống trời, dị thú và quy luật nguyên thủy còn mạnh hơn mọi khái niệm văn minh.",
        "summary": "La Phàm tỉnh dậy giữa một thế giới hoàn toàn không còn dấu vết Trái Đất, từ đó bước vào hành trình nhận thức lại bản thân, huyết mạch và đại đạo trong môi trường nguyên sơ nhất của hồng hoang.",
        "style_tags": ["hồng hoang", "khai thiên", "cổ phong", "đại đạo"],
        "cover_prompt": "Bìa dọc 6x9, dị thú khổng lồ nhìn về ngọn núi chống trời xuyên mây trong buổi sơ khai, tông đất đỏ, vàng cổ và lam nhạt, cảm giác thiên địa mới mở.",
        "sample_chapter": 1,
        "sample_summary": "La Phàm tỉnh lại trong thân thể và hoàn cảnh hoàn toàn xa lạ, vừa kinh ngạc trước thiên địa hồng hoang vừa phải chịu đựng dòng ký ức và thông tin khổng lồ tràn vào đầu.",
        "sample_characters": ["La Phàm"],
        "sample_entities": ["núi chống trời", "thiên địa sơ khai", "dị thú", "hồng hoang"],
        "sample_tone_tags": ["sơ khai", "choáng ngợp", "cô độc", "sử thi"],
        "sample_illustration": "La Phàm trong thân hình dị thú vừa tỉnh giấc, trước mặt là một ngọn núi chống trời cắm thẳng lên mây, khiến sự tồn tại của hắn trở nên nhỏ bé trước thiên địa sơ khai.",
        "signature_style_name": "Cổ phong khai thiên",
        "signature_style_purpose": "Tăng cảm giác huyền cổ và thiên địa sơ lập của Hồng Hoang.",
        "signature_style_tail": "Chính vì vậy cảnh mở đầu mang hơi thở của một lần khai nhãn giữa càn khôn mới dựng.",
    },
    "Sieu Duy Thuat Si_Muc Ho": {
        "backdrop": "Fantasy phương Tây pha huyền bí và siêu duy, mở ra từ các thị trấn hẻo lánh, gia tộc quyền lực và cánh cửa bước vào nền văn minh phù thủy.",
        "summary": "Từ nhịp mở đầu ở thị trấn Gelu, truyện dựng bầu không khí rất mạnh: xa trung tâm nhưng luôn bị ảnh hưởng bởi các gia tộc và thế lực lớn. Đây là kiểu tác phẩm đưa người đọc từ tín hiệu quyền lực đầu tiên đến thế giới phù thủy rộng lớn hơn.",
        "style_tags": ["fantasy", "phù thủy", "mystery", "adventure"],
        "cover_prompt": "Bìa dọc 6x9, thị trấn châu Âu cổ nhỏ dưới bầu trời xám, đoàn kỵ binh giáp bạc tiến vào, lá cờ gia tộc Morn tung bay, xa xa là ánh sáng ma pháp mờ ảo.",
        "sample_chapter": 1,
        "sample_summary": "Sự xuất hiện đột ngột của đoàn kỵ binh gia tộc Morn khiến cả thị trấn Gelu chấn động, báo hiệu một biến cố có thể kéo những con người nhỏ bé vào phạm vi ảnh hưởng của quyền lực lớn.",
        "sample_characters": ["Parcia", "Dim", "Angel", "gia tộc Morn"],
        "sample_entities": ["hành tỉnh Yamei", "thị trấn Gelu", "Đế quốc Jinque", "huy hiệu Morn"],
        "sample_tone_tags": ["fantasy", "quyền lực", "dự báo biến cố", "bí ẩn"],
        "sample_illustration": "Đoàn kỵ binh giáp bạc tiến qua cổng thị trấn Gelu, dân làng kinh hãi nhìn lá cờ gia tộc Morn, trong khi Parcia và Dim phản ứng theo hai cách hoàn toàn khác nhau.",
        "signature_style_name": "Fantasy cổ điển",
        "signature_style_purpose": "Đưa giọng văn gần hơn với chất truyện phương Tây cổ điển, giàu cảm giác điềm báo.",
        "signature_style_tail": "Ở các miền đất xa kinh thành, đôi khi chỉ một lá cờ đã đủ trở thành điềm báo cho vận mệnh đổi chiều.",
    },
    "Theo Tu Than Bat Dau Danh Xuyen Qua Tong Man Vo Han": {
        "backdrop": "Fanfic đa thế giới khởi đầu bằng bối cảnh giam cầm kiểu sci-fi, rồi mở rộng sang nhiều thế giới quen thuộc với hệ thống, xuyên qua và chiến đấu liên chuỗi IP.",
        "summary": "Lục Ly bước vào truyện từ thế cực kỳ bị động: bị giam, chờ tử hình và bị thẩm vấn. Từ trạng thái ấy, câu chuyện dần lật mở quá khứ, năng lực và các tầng thế giới mà anh sẽ đi qua.",
        "style_tags": ["fanfic", "đa thế giới", "sci-fi", "hệ thống"],
        "cover_prompt": "Bìa dọc 6x9, phòng thẩm vấn tương lai với màn hình hologram xanh tím, nam chính bị trói trong áo cưỡng chế nhìn thẳng về phía trước, phía sau là những cánh cổng thế giới chồng lớp, sci-fi noir.",
        "sample_chapter": 1,
        "sample_summary": "Lục Ly bị thẩm vấn trước giờ hành quyết trong một nhà tù công ty tương lai, qua đó hé lộ khí chất và bầu không khí lạnh lẽo của thế giới anh đang mắc kẹt.",
        "sample_characters": ["Lục Ly", "Nifeier"],
        "sample_entities": ["nhà tù của công ty", "màn hình 3D", "giáp trợ lực", "hồ sơ tử hình"],
        "sample_tone_tags": ["sci-fi noir", "thẩm vấn", "lạnh", "đa thế giới"],
        "sample_illustration": "Phòng thẩm vấn ánh xanh tím lạnh, Lục Ly bị trói trong áo cưỡng chế nhưng vẫn ngẩng đầu mỉm cười mỉa mai, trước mặt là Nifeier và hologram hồ sơ lơ lửng trong không khí.",
        "signature_style_name": "Kỹ thuật cao sắc cạnh",
        "signature_style_purpose": "Tạo exemplar sci-fi noir với chất kim loại lạnh và dữ liệu bao quanh.",
        "signature_style_tail": "Công nghệ trong cảnh này vận hành trơn tru, nhưng bầu không khí lại sắc lạnh như kim loại mới mài.",
    },
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def title_from_source(source_full: str | None, fallback: str) -> tuple[str, str]:
    if not source_full:
        return fallback, "Khuyết danh"
    stem = Path(source_full).stem
    if "_" not in stem:
        return stem, "Khuyết danh"
    title, author = stem.rsplit("_", 1)
    return title.strip(), author.strip()


def safe_title(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or "Khong tieu de"


def extract_heading(text: str) -> tuple[int | None, str | None]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^#+\s*Chương\s+(\d+)\s*[:\-]\s*(.+?)\s*$", stripped, re.IGNORECASE)
        if match:
            return int(match.group(1)), match.group(2).strip()
        break
    return None, None


def extract_filename_info(filename: str) -> tuple[int | None, str | None]:
    match = re.search(r"chapter_(\d{1,4})", filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), None
    match = re.match(r"^(\d{1,4})\s*-\s*Chương\s*\d+\s*-\s*(.+?)(?:\.md)?$", filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), match.group(2).strip()
    match = re.match(r"^(\d{1,4})\s*-\s*(.+?)(?:\.md)?$", filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), match.group(2).strip()
    return None, None


def extract_excerpt(text: str, limit: int = 900) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    if not lines:
        return ""
    excerpt = "\n\n".join(lines[:2]).strip()
    return excerpt[:limit]


def chapter_lookup(progress: dict[str, Any]) -> dict[int, dict[str, Any]]:
    lookup: dict[int, dict[str, Any]] = {}
    for item in progress.get("chapters", []):
        chapter_number = item.get("chapter_number") or item.get("chapter") or item.get("number")
        if isinstance(chapter_number, int):
            lookup[chapter_number] = item
    return lookup


def output_records(branch_dir: Path, progress: dict[str, Any]) -> list[dict[str, Any]]:
    out_dir = branch_dir / "output"
    lookup = chapter_lookup(progress)
    records: list[dict[str, Any]] = []
    if not out_dir.exists():
        return records
    for path in sorted(p for p in out_dir.iterdir() if p.is_file()):
        text = path.read_text(encoding="utf-8", errors="ignore")
        heading_number, heading_title = extract_heading(text)
        file_number, file_title = extract_filename_info(path.name)
        chapter_number = heading_number or file_number
        progress_title = lookup.get(chapter_number or -1, {}).get("title")
        title = (heading_title or file_title or progress_title or "Chưa đặt tiêu đề").strip()
        display_name = None
        filesystem_name = None
        if chapter_number is not None:
            display_name = DISPLAY_FILENAME_PATTERN.format(chapter=chapter_number, title=title)
            filesystem_name = FILESYSTEM_FILENAME_PATTERN.format(chapter=chapter_number, title=safe_title(title))
        records.append(
            {
                "path": path,
                "relative_path": path.relative_to(branch_dir).as_posix(),
                "chapter_number": chapter_number,
                "title": title,
                "size": path.stat().st_size,
                "excerpt": extract_excerpt(text),
                "display_name": display_name,
                "filesystem_name": filesystem_name,
            }
        )
    return sorted(records, key=lambda item: (item["chapter_number"] is None, item["chapter_number"] or 0, item["path"].name.lower()))


def sample_record(records: list[dict[str, Any]], preferred_chapter: int) -> dict[str, Any] | None:
    for record in records:
        if record["chapter_number"] == preferred_chapter and (record["excerpt"] or record["size"] > 0):
            return record
    for record in reversed(records):
        if record["excerpt"] or record["size"] > 0:
            return record
    return records[0] if records else None


def scan_images(branch_dir: Path) -> dict[str, list[str]]:
    illustrations_dir = branch_dir / "illustrations"
    buckets: dict[str, list[str]] = {}
    for folder in ["cover", "chapters", "maps", "characters", "diagrams"]:
        current_dir = illustrations_dir / folder
        assets = []
        if current_dir.exists():
            for path in sorted(current_dir.iterdir()):
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                    assets.append(path.relative_to(branch_dir).as_posix())
        buckets[folder] = assets
    return buckets


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", text.replace("\n", " ").strip())
    return [part.strip() for part in parts if part.strip()]


def generate_style_variants(record: dict[str, Any], override: dict[str, Any]) -> list[dict[str, str]]:
    excerpt = record["excerpt"] or override["sample_summary"]
    sentences = split_sentences(excerpt)
    first = sentences[0] if sentences else override["sample_summary"]
    second = sentences[1] if len(sentences) > 1 else override["sample_summary"]
    protagonist = override["sample_characters"][0]
    cinematic = " ".join(sentences[:3]) or excerpt
    cold = (
        f"{protagonist} không còn đứng ngoài biến cố ấy nữa. {first} {second} "
        f"Không khí lạnh và khép lại, đúng với tông {', '.join(override['sample_tone_tags'][:2])} mà chương này cần giữ."
    ).strip()
    signature = (
        f"{override['sample_summary']} {first} {override['signature_style_tail']}"
    ).strip()
    return [
        {
            "style_id": "smooth_standard",
            "style_name": "Mượt tiêu chuẩn",
            "purpose": "Giữ nghĩa và nhịp kể tự nhiên, phù hợp làm bản chuẩn đối chiếu.",
            "rewrite": excerpt,
        },
        {
            "style_id": "cinematic_fast",
            "style_name": "Điện ảnh nhịp nhanh",
            "purpose": "Ưu tiên nhịp cắt cảnh nhanh, câu ngắn và độ bật của tình huống.",
            "rewrite": cinematic,
        },
        {
            "style_id": "cold_interior",
            "style_name": "Sắc lạnh nội tâm",
            "purpose": "Kéo tiêu điểm vào cảm giác bị dồn ép hoặc nhận thức lạnh đi của nhân vật.",
            "rewrite": cold,
        },
        {
            "style_id": "signature_branch",
            "style_name": override["signature_style_name"],
            "purpose": override["signature_style_purpose"],
            "rewrite": signature,
        },
    ]


def render_branch_readme(branch: str, title: str, author: str, override: dict[str, Any], progress: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Tên Truyện: {title}",
            f"Tác Giả: {author}",
            f"Bối cảnh: {override['backdrop']}",
            f"Tóm tắt nội dung: {override['summary']}",
            "",
            f"Branch nội bộ: `{branch}`",
            f"Tiến độ hiện tại: `{progress.get('completed_chapters', 0)}/{progress.get('total_chapters', 0)}` chương",
            "",
            "Quy ước output:",
            f"- Hiển thị mong muốn: `{DISPLAY_FILENAME_PATTERN}`",
            f"- Lưu file trên Windows: `{FILESYSTEM_FILENAME_PATTERN}`",
            f"- Ghi chú: {FILESYSTEM_NOTE}",
            "",
            "Ebook:",
            "- Phải có `ebook/toc.md`.",
            "- Phải có `ebook/illustration_manifest.json` để chuẩn bị đường vào ảnh bìa và ảnh chương.",
            "",
            "Converter DB:",
            "- Dữ liệu bổ trợ nằm trong `converter_db/`.",
            "- Mỗi chương mới nên có chapter card, style variants và prompt minh họa tương ứng.",
            "",
        ]
    )


def render_converter_readme(branch: str, title: str) -> str:
    return "\n".join(
        [
            f"# Converter DB - {title}",
            "",
            "Thư mục này chứa dữ liệu bổ trợ để tái sử dụng trong `D:\\Converter by DrDuc`.",
            "",
            "Thành phần chính:",
            "- `metadata.json`: metadata chuẩn hóa của branch.",
            "- `style_variants.json` và `style_variants/`: ngân hàng đoạn dịch nhiều văn phong.",
            "- `chapter_cards/`: thẻ chương dùng cho continuity và entity tracking.",
            "- `exports/`: các file JSONL để đưa sang converter hoặc pipeline downstream.",
            "",
            f"Branch nguồn: `{branch}`",
            "",
        ]
    )


def render_simple_readme(title: str, bullets: list[str]) -> str:
    lines = [f"# {title}", ""]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.append("")
    return "\n".join(lines)


def render_style_markdown(title: str, record: dict[str, Any], style_tags: list[str], variants: list[dict[str, str]]) -> str:
    lines = [
        f"# Style Variants - {title}",
        "",
        f"Chương mẫu: `{record.get('display_name') or record.get('relative_path') or 'Khong xac dinh'}`",
        f"Tags nền: {', '.join(style_tags)}",
        "",
        "## Đoạn gốc đã dịch",
        "",
        record["excerpt"] or "_Chưa có excerpt đủ dài từ output hiện tại._",
        "",
    ]
    for variant in variants:
        lines.extend([f"## {variant['style_name']}", "", f"Mục đích: {variant['purpose']}", "", variant["rewrite"], ""])
    return "\n".join(lines)


def build_toc(title: str, records: list[dict[str, Any]]) -> str:
    lines = [f"# Mục lục - {title}", ""]
    if not records:
        lines.extend(["_Chưa có chapter output để lập mục lục._", ""])
        return "\n".join(lines)
    for record in records:
        entry = record["display_name"] or record["relative_path"]
        if entry.endswith(".md"):
            entry = entry[:-3]
        lines.append(f"- {entry}")
    lines.append("")
    return "\n".join(lines)


def update_global_config() -> None:
    global_config = read_json(GLOBAL_CONFIG_PATH)
    global_config.setdefault("workflow_defaults", {})
    global_config["workflow_defaults"].update(
        {
            "require_branch_readme": True,
            "require_converter_db": True,
            "require_ebook_toc": True,
            "require_ebook_illustrations": True,
            "output_filename_pattern_display": DISPLAY_FILENAME_PATTERN,
            "output_filename_pattern_filesystem": FILESYSTEM_FILENAME_PATTERN,
            "output_filename_constraint_note": FILESYSTEM_NOTE,
            "branch_scaffold_script": "Script/branch_scaffold.py",
        }
    )
    global_config["metadata"]["last_updated"] = now_iso()
    write_json(GLOBAL_CONFIG_PATH, global_config)


def scaffold_branch(branch_dir: Path) -> None:
    branch = branch_dir.name
    override = BRANCH_OVERRIDES[branch]
    cfg_path = branch_dir / "translation_config.json"
    progress_path = branch_dir / "progress.json"
    cfg = read_json(cfg_path)
    progress = read_json(progress_path)
    title, author = title_from_source((cfg.get("source_ref") or {}).get("full"), cfg.get("project_name", branch))
    records = output_records(branch_dir, progress)
    sample = sample_record(records, override["sample_chapter"])
    variants = generate_style_variants(sample or {"excerpt": override["sample_summary"], "display_name": None, "relative_path": None}, override)

    for path in [
        branch_dir / "converter_db",
        branch_dir / "converter_db" / "style_variants",
        branch_dir / "converter_db" / "chapter_cards",
        branch_dir / "converter_db" / "exports",
        branch_dir / "ebook",
        branch_dir / "illustrations" / "characters",
        branch_dir / "illustrations" / "diagrams",
        branch_dir / "illustrations" / "maps",
        branch_dir / "illustrations" / "chapters",
        branch_dir / "illustrations" / "cover",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    cfg["display_title"] = title
    cfg["display_author"] = author
    cfg["output_filename_pattern_display"] = DISPLAY_FILENAME_PATTERN
    cfg["output_filename_pattern_filesystem"] = FILESYSTEM_FILENAME_PATTERN
    cfg["output_filename_constraint_note"] = FILESYSTEM_NOTE
    cfg["database_support"] = {
        "enabled": True,
        "converter_root": f"Output/{branch}/converter_db/",
        "metadata_file": f"Output/{branch}/converter_db/metadata.json",
        "style_variants_index": f"Output/{branch}/converter_db/style_variants.json",
        "style_variants_dir": f"Output/{branch}/converter_db/style_variants/",
        "chapter_cards_dir": f"Output/{branch}/converter_db/chapter_cards/",
        "exports_dir": f"Output/{branch}/converter_db/exports/",
    }
    cfg["ebook_requirements"] = {
        "toc_required": True,
        "illustrations_required": True,
        "toc_file": f"Output/{branch}/ebook/toc.md",
        "illustration_manifest_file": f"Output/{branch}/ebook/illustration_manifest.json",
    }
    cfg["readme_path"] = f"Output/{branch}/README.md"
    cfg["last_updated"] = now_iso()
    write_json(cfg_path, cfg)

    progress.setdefault("workflow_artifacts", {})
    progress["workflow_artifacts"].update(
        {
            "branch_readme": "README.md",
            "converter_db_ready": True,
            "ebook_toc": "ebook/toc.md",
            "illustration_manifest": "ebook/illustration_manifest.json",
        }
    )
    progress["last_updated"] = now_iso()
    write_json(progress_path, progress)

    write_text(branch_dir / "README.md", render_branch_readme(branch, title, author, override, progress))
    write_text(branch_dir / "converter_db" / "README.md", render_converter_readme(branch, title))
    write_text(branch_dir / "converter_db" / "style_variants" / "README.md", render_simple_readme("Style Variants", ["Mỗi file lưu một mẫu chapter với nhiều biến thể văn phong.", "Dùng kèm `style_variants.json` để lấy metadata tổng hợp."]))
    write_text(branch_dir / "converter_db" / "chapter_cards" / "README.md", render_simple_readme("Chapter Cards", ["Mỗi file lưu thẻ chương ngắn gọn để kiểm continuity.", "Giữ số chương, tóm tắt, nhân vật, entity và tone tags."]))
    write_text(branch_dir / "converter_db" / "exports" / "README.md", render_simple_readme("Exports", ["`style_bank.jsonl` cho style memory.", "`scene_tone_exemplars.jsonl` cho truy vấn theo tone và ngữ cảnh."]))
    write_json(
        branch_dir / "converter_db" / "chapter_cards" / "index.json",
        {
            "branch": branch,
            "generated_at": now_iso(),
            "chapters": [
                {
                    "chapter_number": record["chapter_number"],
                    "chapter_title": record["title"],
                    "source_output_file": record["relative_path"],
                    "display_output_filename": record["display_name"],
                    "filesystem_output_filename": record["filesystem_name"],
                    "has_content": bool(record["size"]),
                }
                for record in records
            ],
        },
    )

    metadata = {
        "branch": branch,
        "project_name": cfg.get("project_name"),
        "display_title": title,
        "author": author,
        "genre": cfg.get("genre"),
        "sub_genre": cfg.get("sub_genre"),
        "backdrop": override["backdrop"],
        "summary": override["summary"],
        "notes": cfg.get("notes"),
        "source_ref": cfg.get("source_ref", {}),
        "completed_chapters": progress.get("completed_chapters"),
        "total_chapters": progress.get("total_chapters"),
        "output_filename_pattern_display": DISPLAY_FILENAME_PATTERN,
        "output_filename_pattern_filesystem": FILESYSTEM_FILENAME_PATTERN,
        "output_filename_constraint_note": FILESYSTEM_NOTE,
        "style_tags": override["style_tags"],
        "generated_at": now_iso(),
    }
    write_json(branch_dir / "converter_db" / "metadata.json", metadata)

    sample_payload = {
        "metadata": {"branch": branch, "project_title": title, "generated_at": now_iso()},
        "sample": {
            "chapter_number": sample["chapter_number"] if sample else None,
            "chapter_title": sample["title"] if sample else None,
            "source_output_file": sample["relative_path"] if sample else None,
            "display_output_filename": sample["display_name"] if sample else None,
            "filesystem_output_filename": sample["filesystem_name"] if sample else None,
            "base_excerpt": sample["excerpt"] if sample else override["sample_summary"],
            "style_tags": override["style_tags"],
        },
        "variants": variants,
    }
    write_json(branch_dir / "converter_db" / "style_variants.json", sample_payload)
    write_text(branch_dir / "converter_db" / "style_variants.md", render_style_markdown(title, sample or sample_payload["sample"], override["style_tags"], variants))
    if sample and sample["chapter_number"] is not None:
        write_json(branch_dir / "converter_db" / "style_variants" / f"chuong_{sample['chapter_number']:04d}.json", sample_payload)
        write_json(
            branch_dir / "converter_db" / "chapter_cards" / f"chuong_{sample['chapter_number']:04d}.json",
            {
                "chapter_number": sample["chapter_number"],
                "chapter_title": sample["title"],
                "source_output_file": sample["relative_path"],
                "display_output_filename": sample["display_name"],
                "filesystem_output_filename": sample["filesystem_name"],
                "summary": override["sample_summary"],
                "appearing_characters": override["sample_characters"],
                "new_entities_or_focus": override["sample_entities"],
                "tone_tags": override["sample_tone_tags"],
                "illustration_focus": override["sample_illustration"],
            },
        )

    style_bank_lines = []
    tone_lines = []
    for variant in variants:
        style_bank_lines.append(json.dumps({"branch": branch, "chapter_number": sample_payload["sample"]["chapter_number"], "chapter_title": sample_payload["sample"]["chapter_title"], "style_id": variant["style_id"], "style_name": variant["style_name"], "purpose": variant["purpose"], "base_excerpt": sample_payload["sample"]["base_excerpt"], "rewrite": variant["rewrite"]}, ensure_ascii=False))
        tone_lines.append(json.dumps({"branch": branch, "tone_tags": override["sample_tone_tags"], "style_name": variant["style_name"], "excerpt": variant["rewrite"], "application": "converter_style_memory"}, ensure_ascii=False))
    write_text(branch_dir / "converter_db" / "exports" / "style_bank.jsonl", "\n".join(style_bank_lines))
    write_text(branch_dir / "converter_db" / "exports" / "scene_tone_exemplars.jsonl", "\n".join(tone_lines))

    write_text(branch_dir / "ebook" / "toc.md", build_toc(title, records))
    
    toc_json_payload = [
        {
            "chapter_number": record["chapter_number"],
            "title": record["title"],
            "relative_path": record["relative_path"]
        }
        for record in records
    ]
    write_json(branch_dir / "toc.json", toc_json_payload)
    
    assets = scan_images(branch_dir)
    write_json(
        branch_dir / "ebook" / "illustration_manifest.json",
        {
            "metadata": {"project_title": title, "generated_at": now_iso()},
            "requirements": {"toc_required": True, "illustrations_required": True},
            "cover": {"status": "asset_ready" if assets["cover"] else "prompt_ready", "asset_candidates": assets["cover"], "prompt": override["cover_prompt"]},
            "sample_chapter": {"chapter_number": sample_payload["sample"]["chapter_number"], "chapter_title": sample_payload["sample"]["chapter_title"], "prompt": override["sample_illustration"], "asset_candidates": assets["chapters"]},
            "supplementary_assets": {"maps": assets["maps"], "characters": assets["characters"], "diagrams": assets["diagrams"]},
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold README, converter_db and ebook artifacts for Dichtrung branches.")
    parser.add_argument("--branch", help="Tên project branch trong Output/")
    parser.add_argument("--all", action="store_true", help="Scaffold toàn bộ branch hiện có trong Output/")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.branch and not args.all:
        raise SystemExit("Cần truyền --branch [Tên] hoặc --all")
    update_global_config()
    branches = [path for path in sorted(OUTPUT_ROOT.iterdir()) if path.is_dir()] if args.all else [OUTPUT_ROOT / args.branch]
    for branch_dir in branches:
        if not branch_dir.exists() or branch_dir.name not in BRANCH_OVERRIDES:
            continue
        scaffold_branch(branch_dir)
        print(f"[OK] {branch_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
