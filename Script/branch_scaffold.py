from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "Output"
GLOBAL_CONFIG_PATH = ROOT / "Global State" / "global_config.json"
HOME_CATALOG_PATH = ROOT / "home.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DISPLAY_FILENAME_PATTERN = "Chương {chapter:04d}: {title}.md"
FILESYSTEM_FILENAME_PATTERN = "Chương {chapter:04d} - {title}.md"
FILESYSTEM_NOTE = "Windows không cho phép ký tự ':' trong tên file, vì vậy pattern lưu trên đĩa dùng dấu gạch ngang."
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
GENRE_LABELS = {
    "eastern_fiction": "Đông phương",
    "western_fiction": "Tây phương",
    "xianxia": "Tiên hiệp",
    "wizardry": "Phù thủy",
    "fantasy": "Fantasy",
    "horror": "Kinh dị",
    "unlimited_flow": "Vô hạn lưu",
    "evolution_scifi": "Tiến hóa khoa huyễn",
    "fanfic": "Fanfic",
    "system": "Hệ thống",
    "infinite_worlds": "Đa thế giới",
}

BRANCH_OVERRIDES: dict[str, dict[str, Any]] = {
    "Ac Linh Quoc Gia": {
        "backdrop": "Đô thị hiện đại bị xâm thực bởi các sự kiện siêu nhiên, nơi hợp đồng việc làm lương cao thực chất là cánh cửa dẫn vào chuỗi nhiệm vụ linh dị và sinh tử.",
        "summary": "Hạ Thiên Kì từ một sinh viên bình thường bị cuốn vào công ty bí ẩn chuyên xử lý các sự kiện quỷ dị. Càng tiến sâu, anh càng nhận ra công việc ấy là trò chơi sinh tồn được xây bằng sợ hãi, mưu tính và cái giá phải trả để còn sống.",
        "style_tags": ["đô thị", "kinh dị", "đen hài", "căng thẳng"],
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Ác Linh Quốc Gia' is written in LARGE, distorted, and blood-stained typography perfectly centered. The author name 'Đạn Chỉ Nhất Tiếu Gian 0' is written in smaller, weathered bone-white text neatly placed near the title. Typography style: Gothic horror serif with dripping blood effects and cracks. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a pale young man (Hạ Thiên Kỳ) with one eye glowing a terrifying demonic red (Tà Linh Nhãn), holding a modern smartphone that displays a cursed red eye icon. His expression is one of cold terror. [BỐ CẢNH NỀN]: The background is a long, dark, and decaying apartment corridor with peeling wallpaper and flickering overhead lights, where shadowy, distorted ghost hands reach out from the walls. [NGÔN NGỮ NỀN]: Subtly integrated into the shadows and the walls are glowing red Ancient Chinese spirit-warding charms and digital glitch characters. [SẮC THÁI]: Mood is dread-filled and terrifying, lighting is a mix of clinical flickering white and a deep, bloody red glow from the protagonist's eye.",
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
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Chủ Thần Đại Đạo' is written in LARGE, massive typography perfectly centered. The author name 'Cổ Nguyệt Cư Sĩ' is written in smaller, elegant text neatly placed near the title. Typography style: Modern bold serif font with glowing golden outlines and white inner glow. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a young, calm man (Triệu Kỳ) with a divine aura, his eyes glowing with wisdom, holding a radiant crystalline seed (The Seed) that emits pulses of light. [BỐ CẢNH NỀN]: The background is a juxtaposition of a modern city street at dusk and multiple overlapping mystical realms, including floating jade palaces and gothic cathedrals, appearing through circular portals. [NGÔN NGỮ NỀN]: Subtly integrated into the air are floating golden Hán tự (Ancient Chinese characters) and translucent blue digital UI hologram codes. [SẮC THÁI]: Mood is divine, epic, and awe-inspiring, lighting is brilliant golden rays piercing through the twilight city clouds.",
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
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Hồng Hoang Lịch' is written in LARGE, massive typography perfectly centered. The author name 'Zhttty' is written in smaller, elegant text neatly placed near the title. Typography style: Ancient calligraphic brush font in cinnabar red and golden ink, weathered and powerful. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a young scholar-mage (Ngô Minh) in flowing taoist robes integrated with subtle mechanical armor, eyes focused, holding a floating silver orb (Master God Space) that radiates immense power. [BỐ CẢNH NỀN]: The background features a vast primordial valley with giant prehistoric beasts in the distance, overshadowed by a massive, high-tech floating fortress (Huyền Hoàng Battleship) and a glowing Magic Tower. [NGÔN NGỮ NỀN]: Subtly integrated into the sky and floating around the battleship are carved golden Ancient Chinese characters and complex geometric magic circles. [SẮC THÁI]: Mood is epic, historical, and grand, lighting is dramatic sunset rays with high contrast between deep shadows and bright magical glows.",
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
    "Pham Nhan Bat Dau Doat Xa Mac Cu Nhan_Tieu Tran Tu": {
        "backdrop": "Fanfiction đặt trên nền Phàm Nhân Tu Tiên, nơi một linh hồn dị thế nhập vào thân xác Mặc Cư Nhân và cố viết lại vận mệnh bi kịch đã định của mình.",
        "summary": "Từ vị trí vốn là một nhân vật bi kịch ở đầu truyện gốc, Mặc Cư Nhân nay có thêm ký ức của kẻ biết trước cốt truyện và quyết tâm thoát khỏi kết cục cũ bằng tính toán, huyết mạch và hiểu biết nguyên tác.",
        "style_tags": ["fanfic", "tiên hiệp", "đoạt xá", "đổi mệnh"],
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Phàm Nhân Bắt Đầu Đoạt Xá Mặc Cư Nhân' is written in LARGE, sharp, elegant typography perfectly centered. The author name 'Tiêu Trần Tử' is written in smaller, refined text neatly placed near the title. Typography style: Classic serif with sharp edges, deep emerald green color with a dark shadow effect. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on an older, dignified man with a sharp, calculating gaze (Mặc Cư Nhân), dressed in dark scholarly robes, sitting before a heavy, ancient bronze furnace (Bloodline Furnace) that emits a subtle green glow. A faint, ghostly green python (Bích Lân Mãng) is coiled around the furnace. [BỐ CẢNH NỀN]: The background is a misty, secluded valley (Thần Thủ Cốc) at dusk, with ancient pine trees and wooden shelves filled with glass vials and dried herbs. [NGÔN NGỮ NỀN]: Subtly integrated into the background mist and the furnace texture are faint diagrams of meridians and traditional Chinese herbal names. [SẮC THÁI]: Mood is dark, mysterious, and intellectual, lighting is dominated by the eerie green glow from the furnace contrasting with the deep blue twilight of the valley.",
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
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Phi Phàm Hồng Hoang' is written in LARGE, massive typography perfectly centered. The author name 'Ngã Tự Phi Phàm' is written in smaller, elegant text neatly placed near the title. Typography style: Ancient Seal-script calligraphy in solid gold and emerald jade texture, appearing to be carved into stone. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a tall, long-haired immortal (La Phàm) sitting in meditation on a flat rock at the very edge of a sky-piercing mountain peak, surrounded by a faint, eternal golden aura (Immortal Light). [BỐ CẢNH NỀN]: The background features the massive pillar of Mount Buzhou (Bất Chu Sơn) disappearing into the swirling primordial chaos and thick white clouds below, with a giant silver moon and a distant red sun shining simultaneously in the sky. [NGÔN NGỮ NỀN]: Subtly integrated into the rock textures and the clouds are glowing ancient seals and primordial runes of the creation era. [SẮC THÁI]: Mood is eternal, solitary, and transcendent, lighting is a serene blend of cool moonbeams and warm primordial dawn.",
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
    "Ta Trong Binh Vu Tru_Tam Bach Can Dich Vi Tieu": {
        "backdrop": "Thế giới vi mô nằm trong một phòng thí nghiệm của 'bệnh nhân tâm thần' Lý Khanh, nơi các nền văn minh đơn bào phát triển và diệt vong dưới sự quan sát của Ngoại Thần.",
        "summary": "Lý Khanh phát hiện mình có khả năng 'Thức tỉnh' vi sinh vật. Anh bắt đầu thí nghiệm trong một bình thủy tinh, tạo ra nền văn minh Atabia. Câu chuyện là cuộc đấu trí giữa các 'phàm nhân' kiến tí và vị 'Ngoại Thần' nắm giữ quyền sinh sát tối thượng.",
        "style_tags": ["sáng thế", "vi mô", "sử thi", "khoa học viễn tưởng"],
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Ta Trong Bình Vũ Trụ' is written in LARGE, futurist neon-blue typography perfectly centered. The author name 'Tam Bách Cân Đích Vi Tiếu' is written in smaller, sleek white text neatly placed near the title. Typography style: Bold sans-serif font with a glowing digital glitches and cybernetic patterns. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a young, calm man in a modern white doctor's coat (Lý Khanh), holding a glowing glass bottle that contains a miniature, rotating galaxy and tiny, intricate cities. His eyes reflect a vast cosmic wisdom. [BỐ CẢNH NỀN]: The background is a fusion of a dark modern laboratory and a deep space nebula, with translucent DNA helixes and binary code strings (0101) floating like stardust. [NGÔN NGỮ NỀN]: Subtly integrated into the cosmic clouds are glowing DNA sequences (A, T, C, G) and microscopic cell diagrams. [SẮC THÁI]: Mood is surreal, scientific, and awe-inspiring, lighting is a contrast between sharp laboratory white and the deep violet and blue of a distant nebula.",
        "sample_chapter": 25,
        "sample_summary": "Hoàng đế Atabia (Möbius) ngã xuống, cơ thể ông hóa thành cây Thế Giới để cung cấp oxy cho thần dân sau Ngày phán xét. Một thời đại mới bắt đầu từ sự hy sinh của vị vua tiên phong.",
        "sample_characters": ["Lý Khanh", "Möbius (Atabia)"],
        "sample_entities": ["Thế Giới Thụ", "Tháp Babel", "Ngày phán xét", "Gen băng hội"],
        "sample_tone_tags": ["bi tráng", "sử thi", "hy vọng", "khai thiên"],
        "sample_illustration": "Cảnh tượng Tinh Linh vương Atabia dần thụ hóa, lớp vỏ cây bao phủ cơ thể khổng lồ khi ánh hoàng hôn chiếu qua vách ngăn pha lê, tạo nên bức tượng sáp vĩ đại của thời viễn cổ.",
        "signature_style_name": "Sáng thế sử thi",
        "signature_style_purpose": "Làm nổi bật sự tương phản giữa góc nhìn vĩ mô của Ngoại Thần và sự bi tráng của phàm nhân vi mô.",
        "signature_style_tail": "Khoảnh khắc này không chỉ là cái chết, mà là sự khởi đầu của một thế giới mới trên xác của vị vua cũ.",
    },
    "Sieu Duy Thuat Si_Muc Ho": {
        "backdrop": "Fantasy phương Tây pha huyền bí và siêu duy, mở ra từ các thị trấn hẻo lánh, gia tộc quyền lực và cánh cửa bước vào nền văn minh phù thủy.",
        "summary": "Từ nhịp mở đầu ở thị trấn Gelu, truyện dựng bầu không khí rất mạnh: xa trung tâm nhưng luôn bị ảnh hưởng bởi các gia tộc và thế lực lớn. Đây là kiểu tác phẩm đưa người đọc từ tín hiệu quyền lực đầu tiên đến thế giới phù thủy rộng lớn hơn.",
        "style_tags": ["fantasy", "phù thủy", "mystery", "adventure"],
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Siêu Duy Thuật Sĩ' is written in LARGE, premium gold-leaf typography perfectly centered. The author name 'Mục Hồ' is written in smaller, elegant white text neatly placed near the title. Typography style: Modern classical Latin-style serif with intricate filigree details. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a refined young man (Anger) with golden hair and intelligent eyes, wearing a dark blue noble coat with silver embroidery, holding a translucent, glowing blue geometric magic pattern (Rolling Waves) that rotates between his fingers. [BỐ CẢNH NỀN]: The background is a grand, high-ceilinged wizard library with floating books and glowing crystals, with a large arched window showing a night sky filled with multiple moons and a distant floating island (White Coral Island). [NGÔN NGỮ NỀN]: Subtly etched into the wooden shelves and floating in the air are glowing Latin-style magic runes and mathematical diagrams. [SẮC THÁI]: Mood is academic, mysterious, and high-fantasy, lighting is a warm study glow contrasted with cool, brilliant magical blue light.",
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
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Theo Tử Thần Bắt Đầu Đánh Xuyên Qua Tổng Mạn Vô Hạn' is written in LARGE, sharp Anime-style typography perfectly centered. The author name 'Khuyết danh' is written in smaller, bold text neatly placed near the title. Typography style: Aggressive brush-stroke font with white inner color and thick black outlines, resembling classic Shonen manga titles. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a young man in a black Shinigami kimono (Shihakusho), holding a long, black katana (Zanpakuto) that emits spiritual blue energy. He has a determined expression, eyes glowing with power. [BỐ CẢNH NỀN]: The background is a chaotic dimensional rift with floating shards of glass reflecting iconic anime landscapes: a Japanese pagoda, a modern cityscape, and a desert. [NGÔN NGỮ NỀN]: Subtly integrated into the energy waves and dimensional shards are floating white Japanese Kanji and Katakana characters (e.g., 卍, 死神). [SẮC THÁI]: Mood is action-packed and epic, lighting is dominated by brilliant blue energy sparks and high-contrast dramatic shadows.",
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
    "Linh Hon Negary_Hu Minh": {
        "backdrop": "Thế giới kỳ huyễn phương Tây, nơi các mầm bệnh và linh hồn là nguồn gốc của sức mạnh và sự kinh hoàng.",
        "summary": "Vương Uyên xuyên không trở thành một linh hồn tàn khuyết mang tên Negary. Trong thế giới đầy rẫy sự lừa dối và nguy hiểm của Thần Ân giáo và các vương quốc, hắn từng bước thôn phệ, tiến hóa và trở thành nỗi khiếp sợ thực sự - kẻ chi phối vạn vật từ trong bóng tối.",
        "style_tags": ["dark fantasy", "linh hồn", "tiến hóa", "mưu lược"],
        "cover_prompt": "Vertical book cover ratio 6:9. Cinematic composition, hyper-detailed, 8k resolution. [BỐ CỤC CHỮ]: The title 'Linh Hồn Negary' is written in LARGE, sharp Gothic-style typography perfectly centered. The author name 'Hư Minh' is written in smaller, elegant bone-white text neatly placed near the title. Typography style: Dark Gothic font with silver stroke and a subtle greenish necrotic glow. [NHÂN VẬT & ĐIỂM NHẤN]: Centered focus on a majestic, ethereal being made of grey-blue soul mist (Negary) sitting on a massive throne made of white dragon bones. His eyes are hollow but emit a piercing light, and his hands are covered in black 'Crows' and 'Germs' (Black Crow and Germs) that flow like silk threads. [BỐ CẢNH NỀN]: The background is a dark, infinite void (The Void) with distant, decaying medieval castle silhouettes and a swarm of black crows flying around the throne. [NGÔN NGỮ NỀN]: Subtly integrated into the soul mist and the crows are glowing ancient Latin runes and necrotic symbols. [SẮC THÁI]: Mood is dark, oppressive, and majestic Gothic fantasy, lighting is a mix of eerie cold blue soul light and deep, pitch-black shadows.",
        "sample_chapter": 42,
        "sample_summary": "Chris Modo truyền thụ Hô hấp pháp cho Nala, phát hiện thiên phú kinh người của cô bé, đồng thời chuẩn bị cho cuộc tấn công cuối cùng vào cấm địa của Negary.",
        "sample_characters": ["Chris Modo", "Nala"],
        "sample_entities": ["Hô hấp pháp", "Rhythm", "Thần Ân giáo"],
        "sample_tone_tags": ["kỳ bí", "hy vọng", "chuẩn bị"],
        "sample_illustration": "Chris Modo đặt tay lên vai Nala, ánh sáng vàng rực rỡ lóe lên trong mắt cô bé khi nhịp thở (Rhythm) của hai người đồng bộ hoàn hảo.",
        "signature_style_name": "Kỳ huyễn u ám",
        "signature_style_purpose": "Giữ vững bầu không khí căng thẳng, bí ẩn của thế giới Negary.",
        "signature_style_tail": "Sức mạnh của linh hồn trong cảnh này không chỉ là năng lượng, mà còn là sự rung cảm lạnh lẽo của định mệnh.",
    },
}


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    text = text.lstrip('\ufeff')
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
    match = re.match(r"^Chương\s*(\d{1,4})\s*-\s*(.+?)(?:\.md)?$", filename, re.IGNORECASE)
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


def is_project_branch(branch_dir: Path) -> bool:
    return (
        branch_dir.is_dir()
        and (branch_dir / "translation_config.json").exists()
        and (branch_dir / "progress.json").exists()
    )


def first_text(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def unique_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        items = values
    else:
        items = re.split(r"[,;/|]+", str(values))
    return unique_list([str(item).strip() for item in items if str(item).strip()])


def compact_text(text: str, limit: int = 420) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(normalized) <= limit:
        return normalized
    clipped = normalized[: limit - 3].rsplit(" ", 1)[0].strip()
    return f"{clipped or normalized[: limit - 3]}..."


def humanize_tag(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if token in GENRE_LABELS:
        return GENRE_LABELS[token]
    token = token.replace("_", " ").replace("-", " ")
    return token[:1].upper() + token[1:] if token else ""


def parse_branch_readme(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("Branch nội bộ:", "Quy ước output:", "Ebook:", "Converter DB:")):
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("`")
    return {
        "name": fields.get("Tên Truyện", ""),
        "author": fields.get("Tác Giả", ""),
        "backdrop": fields.get("Bối cảnh", ""),
        "summary": fields.get("Tóm tắt nội dung", ""),
    }


def infer_style_tags(cfg: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for value in [cfg.get("genre"), *normalize_text_list(cfg.get("sub_genre"))]:
        label = humanize_tag(value).strip().lower()
        if label:
            tags.append(label)
    notes = str(cfg.get("notes") or "")
    if re.search(r"\bfanfic|fanfiction\b", notes, re.IGNORECASE):
        tags.append("fanfic")
    return unique_list(tags)[:4] or ["dịch thuật"]


def infer_backdrop(title: str, cfg: dict[str, Any], style_tags: list[str]) -> str:
    notes = first_text(cfg.get("notes"))
    if notes:
        return compact_text(notes, limit=280)
    genre = humanize_tag(cfg.get("genre")).lower()
    tone = ", ".join(unique_list(style_tags)[:3])
    if genre and tone:
        return f"Tác phẩm {genre} mang màu sắc {tone}, đang được chuẩn hóa dữ liệu dịch và ebook trong repo Dichtrung."
    if tone:
        return f"Tác phẩm mang màu sắc {tone}, đang được chuẩn hóa dữ liệu dịch và ebook trong repo Dichtrung."
    return f"Tác phẩm {title} đang được chuẩn hóa dữ liệu dịch và ebook trong repo Dichtrung."


def infer_summary(title: str, cfg: dict[str, Any], sample: dict[str, Any] | None) -> str:
    excerpt = compact_text((sample or {}).get("excerpt", ""), limit=360)
    if excerpt:
        return excerpt
    notes = compact_text(cfg.get("notes", ""), limit=280)
    if notes:
        return notes
    return f"{title} đang được tiếp tục hoàn thiện metadata, mục lục và ebook từ dữ liệu dịch hiện có."


def resolve_branch_profile(
    branch_dir: Path,
    cfg: dict[str, Any],
    records: list[dict[str, Any]],
    title: str,
    author: str,
    readme: dict[str, str],
) -> dict[str, Any]:
    branch = branch_dir.name
    override = BRANCH_OVERRIDES.get(branch, {})
    preferred_chapter = override.get("sample_chapter")
    if not isinstance(preferred_chapter, int) or preferred_chapter <= 0:
        preferred_chapter = 1
    sample = sample_record(records, preferred_chapter)
    style_tags = normalize_text_list(override.get("style_tags")) or infer_style_tags(cfg)
    backdrop = first_text(
        override.get("backdrop"),
        readme.get("backdrop"),
        infer_backdrop(title, cfg, style_tags),
    )
    summary = first_text(
        override.get("summary"),
        readme.get("summary"),
        infer_summary(title, cfg, sample),
    )
    sample_chapter = override.get("sample_chapter")
    if not isinstance(sample_chapter, int) or sample_chapter <= 0:
        sample_chapter = (sample or {}).get("chapter_number") or 1
    return {
        "backdrop": backdrop,
        "summary": summary,
        "style_tags": style_tags or ["dịch thuật"],
        "cover_prompt": first_text(
            override.get("cover_prompt"),
            f"Bìa dọc 6x9 cho truyện {title} của {author}, ưu tiên sắc thái {', '.join(style_tags[:3] or ['dịch thuật'])}. Bối cảnh: {backdrop}",
        ),
        "sample_chapter": sample_chapter,
        "sample_summary": first_text(
            override.get("sample_summary"),
            compact_text((sample or {}).get("excerpt", ""), limit=320),
            summary,
        ),
        "sample_characters": normalize_text_list(override.get("sample_characters")) or ["nhân vật chính"],
        "sample_entities": normalize_text_list(override.get("sample_entities")) or [
            title,
            humanize_tag(cfg.get("sub_genre")) or humanize_tag(cfg.get("genre")) or "mạch truyện",
        ],
        "sample_tone_tags": normalize_text_list(override.get("sample_tone_tags")) or style_tags or ["dịch thuật"],
        "sample_illustration": first_text(
            override.get("sample_illustration"),
            f"Cảnh minh họa đại diện cho {title}, bám theo bối cảnh: {backdrop}",
        ),
        "signature_style_name": first_text(override.get("signature_style_name"), "Giọng chuẩn hóa"),
        "signature_style_purpose": first_text(
            override.get("signature_style_purpose"),
            "Giữ giọng kể ổn định và bám sát metadata của branch.",
        ),
        "signature_style_tail": first_text(
            override.get("signature_style_tail"),
            "Đoạn văn nên giữ nhịp rõ ràng và thống nhất với dữ liệu branch.",
        ),
    }


def slugify(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "misc"


def int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_cover_slots(branch: str) -> list[str]:
    base = f"Output/{branch}/illustrations/cover"
    return [
        f"{base}/cover.jpg",
        f"{base}/cover.png",
        f"{base}/cover.webp",
        f"{base}/cover.jpeg",
    ]


def format_progress(completed: int | None, total: int | None) -> str:
    if completed is None and total is None:
        return ""
    if total:
        return f"{completed or 0}/{total} chương"
    return f"{completed or 0} chương"


def normalize_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status in {"done", "complete", "completed", "finished"}:
        return "completed"
    if status in {"paused", "on_hold", "hold"}:
        return "paused"
    return "in_progress"


def status_label(value: Any) -> str:
    mapping = {
        "completed": "Hoàn thành",
        "paused": "Tạm dừng",
        "in_progress": "Đang ra",
    }
    return mapping[normalize_status(value)]


def read_optional_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def category_entry(prefix: str, token: Any, title: str | None = None) -> dict[str, str] | None:
    raw_token = str(token or "").strip()
    label = first_text(title, humanize_tag(raw_token))
    if not raw_token or not label:
        return None
    key_token = label if prefix == "tag" else raw_token
    return {
        "key": f"{prefix}:{slugify(key_token)}",
        "token": raw_token,
        "title": label,
    }


def build_book_categories(metadata: dict[str, Any]) -> list[dict[str, str]]:
    categories: list[dict[str, str]] = []
    genre_entry = category_entry("genre", metadata.get("genre"))
    if genre_entry:
        categories.append(genre_entry)

    for token in normalize_text_list(metadata.get("sub_genre")):
        entry = category_entry("tag", token)
        if entry:
            categories.append(entry)

    for token in normalize_text_list(metadata.get("style_tags"))[:4]:
        entry = category_entry("tag", token)
        if entry:
            categories.append(entry)

    unique: dict[str, dict[str, str]] = {}
    for entry in categories:
        unique.setdefault(entry["key"], entry)
    return list(unique.values())


def build_catalog_tabs(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {
        "all": {"key": "all", "title": "Tất cả", "count": len(books), "priority": 0}
    }
    for book in books:
        for entry in book.get("categories", []):
            item = counts.setdefault(
                entry["key"],
                {
                    "key": entry["key"],
                    "title": entry["title"],
                    "count": 0,
                    "priority": 1 if entry["key"].startswith("genre:") else 2,
                },
            )
            item["count"] += 1

    tabs = list(counts.values())
    tabs.sort(key=lambda item: (item["priority"], -item["count"], item["title"].casefold()))
    trimmed = [tabs[0]]
    trimmed.extend(item for item in tabs[1:] if item["count"] > 1 or item["priority"] == 1)
    return [{"key": item["key"], "title": item["title"], "count": item["count"]} for item in trimmed[:10]]


def build_book_catalog_entry(branch_dir: Path) -> dict[str, Any]:
    branch = branch_dir.name
    metadata = read_json(branch_dir / "converter_db" / "metadata.json")
    progress = read_json(branch_dir / "progress.json")
    readme = parse_branch_readme(branch_dir / "README.md")
    manifest = read_optional_json(branch_dir / "ebook" / "illustration_manifest.json") or {}
    toc = read_optional_json(branch_dir / "toc.json") or []

    completed = int_or_none(progress.get("completed_chapters"))
    if completed is None:
        completed = int_or_none(metadata.get("completed_chapters"))
    total = int_or_none(progress.get("total_chapters"))
    if total is None:
        total = int_or_none(metadata.get("total_chapters"))
    latest_chapter = ""
    if isinstance(toc, list) and toc:
        latest_chapter = str((toc[-1] or {}).get("title") or "").strip()

    cover_data = manifest.get("cover", {}) if isinstance(manifest, dict) else {}
    cover_candidates = [
        str(item).strip()
        for item in cover_data.get("asset_candidates", [])
        if str(item).strip()
    ]
    cover_slots = build_cover_slots(branch)
    categories = build_book_categories(metadata)
    status = normalize_status(
        first_text(progress.get("status"), (progress.get("meta") or {}).get("status"))
    )
    progress_text = format_progress(completed, total)
    detail_bits = [
        first_text(readme.get("backdrop"), metadata.get("backdrop")),
        f"Tiến độ: {progress_text}" if progress_text else "",
        f"Mới nhất: {latest_chapter}" if latest_chapter else "",
    ]

    return {
        "branch": branch,
        "title": first_text(readme.get("name"), metadata.get("display_title"), metadata.get("project_name"), branch),
        "author": first_text(readme.get("author"), metadata.get("author"), "Khuyết danh"),
        "summary": first_text(readme.get("summary"), metadata.get("summary")),
        "backdrop": first_text(readme.get("backdrop"), metadata.get("backdrop")),
        "description": first_text(readme.get("summary"), metadata.get("summary")),
        "detail": " | ".join(bit for bit in detail_bits if bit),
        "status": status,
        "status_label": status_label(status),
        "ongoing": status != "completed",
        "completed_chapters": completed,
        "total_chapters": total,
        "latest_chapter": latest_chapter,
        "genre": metadata.get("genre"),
        "sub_genre": metadata.get("sub_genre"),
        "style_tags": metadata.get("style_tags") or [],
        "categories": categories,
        "cover_candidates": cover_candidates,
        "cover_slots": cover_slots,
        "cover_prompt": first_text(cover_data.get("prompt")),
        "cover_relative_path": cover_candidates[0] if cover_candidates else "",
        "readme_path": f"Output/{branch}/README.md",
        "toc_path": f"Output/{branch}/toc.json",
        "updated_at": first_text(progress.get("last_updated"), metadata.get("generated_at")),
    }


def build_home_payload(branch_dirs: list[Path]) -> dict[str, Any]:
    books = [build_book_catalog_entry(branch_dir) for branch_dir in branch_dirs if is_project_branch(branch_dir)]
    books.sort(key=lambda item: item["title"].casefold())
    return {
        "metadata": {
            "generated_at": now_iso(),
            "total_books": len(books),
            "source": "Dichtrung/Output",
        },
        "tabs": build_catalog_tabs(books),
        "books": books,
    }


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
    cfg_path = branch_dir / "translation_config.json"
    progress_path = branch_dir / "progress.json"
    cfg = read_json(cfg_path)
    progress = read_json(progress_path)
    records = output_records(branch_dir, progress)
    readme = parse_branch_readme(branch_dir / "README.md")
    title, author = title_from_source(
        (cfg.get("source_ref") or {}).get("full"),
        cfg.get("display_title") or cfg.get("project_name", branch),
    )
    title = first_text(readme.get("name"), cfg.get("display_title"), title, cfg.get("project_name"), branch)
    author = first_text(readme.get("author"), cfg.get("display_author"), author)
    override = resolve_branch_profile(branch_dir, cfg, records, title, author, readme)
    sample = sample_record(records, override["sample_chapter"])
    variants = generate_style_variants(
        sample or {"excerpt": override["sample_summary"], "display_name": None, "relative_path": None},
        override,
    )

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

    cfg.setdefault("source_ref", {})
    cfg["project_branch"] = branch
    cfg["source_ref"]["split"] = f"Source/Source split/{branch}/"
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
            "title": f"Chương {record['chapter_number']}: {record['title']}",
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
            "cover": {
                "status": "asset_ready" if assets["cover"] else "prompt_ready",
                "asset_candidates": assets["cover"],
                "slot_paths": build_cover_slots(branch),
                "preferred_slot": build_cover_slots(branch)[0],
                "prompt": override["cover_prompt"],
            },
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
    all_project_branches = [path for path in sorted(OUTPUT_ROOT.iterdir()) if is_project_branch(path)]
    branches = (
        [path for path in sorted(OUTPUT_ROOT.iterdir()) if is_project_branch(path)]
        if args.all
        else [OUTPUT_ROOT / args.branch]
    )
    for branch_dir in branches:
        if not is_project_branch(branch_dir):
            print(f"[SKIP] {branch_dir.name}: thiếu translation_config.json hoặc progress.json")
            continue
        scaffold_branch(branch_dir)
        print(f"[OK] {branch_dir.name}")
    write_json(HOME_CATALOG_PATH, build_home_payload(all_project_branches))
    print(f"[OK] {HOME_CATALOG_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
