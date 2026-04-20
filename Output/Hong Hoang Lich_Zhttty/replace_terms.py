# -*- coding: utf-8 -*-
import os
import re

output_dir = r"d:\Dichtrung\Output\Hong Hoang Lich_Zhttty\output"

replacements = {
    "Ác Ma tiểu đội": "Tiểu đội Ác Ma",
    "Hồng Hoang Thiên Đình": "Thiên Đình Hồng Hoang",
    "Tâm Linh Chi Quang": "Ánh sáng Tâm Linh",
    "Vô Đáy Thâm Uyên": "Thâm Uyên Không Đáy",
    "Ma Pháp Tháp": "Tháp Ma Pháp",
    "Thành phố Tây Lan": "Thành phố Zion", 
    "Tây Lan": "Zion",
    "Đại Y Vạn": "Tsar Bomba",
    "Trung Châu đội": "Đội Trung Châu",
    "La Lỵ": "Lori",
    "Dưỡng thực giả tiểu đội": "Tiểu đội Dưỡng Thực Giả",
    "Nhân lang": "Người Sói",
    "Điroc hải": "Biển Dirac",
    "Giả Tâm Linh Chi Quang": "Ánh Sáng Tâm Linh (Giả)",
    "Thiểm Hoa Thất Kỵ Sĩ": "Bảy Kỵ Sĩ Thiểm Hoa",
    "Truyền kỳ chiến dịch": "Chiến dịch Truyền Kỳ",
    "Địa tinh tộc": "tộc Gnome",
    "Hồng Hoang Thế Giới": "Thế Giới Hồng Hoang",
    "Huyền Hoàng hạm": "Hạm Huyền Hoàng",
    "Thái Thanh học phủ": "Học phủ Thái Thanh",
    "Ngọc Thanh học phủ": "Học phủ Ngọc Thanh",
    "Thượng Thanh học phủ": "Học phủ Thượng Thanh",
    "Thanh hôi cự lang": "Sói xám xanh",
    "Cô lang": "Sói cô độc",
    "Quang Huy Chi Chiến": "Chiến dịch Quang Huy",
    "Chi tuyến kịch tình": "Cốt truyện phụ",
    "Hậu Địa Tinh Huyết tộc": "Huyết tộc Địa tinh cao cấp",
    "Hậu Địa Tinh": "Địa Tinh Cao Cấp",
    "Xỉ Thiên Sứ trưởng": "Thiên Sứ Trưởng",
    "Huyết Phí chiến sĩ": "Chiến sĩ Huyết Phí",
    "Tử ma pháp trường": "Pháp trường Tử Ma",
    "Huyết tộc mục trường": "Trang trại Huyết tộc",
    "Thiết Sơn thành": "Thành phố Thiết Sơn",
    "Mệnh vận chi tử": "Con của Định Mệnh",
    "Trí chi tử địa nhi hậu sinh": "Đặt mình vào chỗ chết rồi mới sống",
    "Cảnh đốc": "Cảnh sát trưởng",
    "Nhân mã tộc": "tộc Nhân mã",
    "Thực phong lãnh địa": "Lãnh địa thực phong",
    "Hư phong lãnh địa": "Lãnh địa hư phong",
    "Trực hạt lãnh địa": "Lãnh địa trực hạt",
    "Đạo vận phản ứng đôi": "Lò phản ứng Đạo vận/Đạo Vận Phản Ứng Đồ",
    "Càn Khôn tiếp thụ khí": "Máy thu Càn Khôn/Càn Khôn Tiếp Thu Khí",
    "Vạn Tượng Thiên Dẫn nghi": "Máy dẫn Vạn Tượng/Vạn Tượng Thiên Dẫn Nghi",
    "Bát quái phù văn cố hóa thiết bị": "Thiết bị cố định Bát quái phù văn",
    "Thiên Đô Tử Hỏa lô": "Lò Tử Hỏa Thiên Đô/Thiên Đô Tử Hỏa Lô",
    "Huyền Hoàng Thanh Hỏa lô": "Lò Thanh Hỏa Huyền Hoàng/Huyền Hoàng Thanh Hỏa Lô",
    "Hoang Cổ Hoàng Hỏa lô": "Lò Hoàng Hỏa Hoang Cổ/Hoang Cổ Hoàng Hỏa Lô",
    "Pháo Thiên Địa Huyền Hoàng": "Pháo Thiên Địa Huyền Hoàng/Thiên Địa Huyền Hoàng Pháo",
    "Đa Pháo Tháp Thần giáo": "Giáo phái Đa Pháo Tháp",
    "Gen Tỏa": "Khóa Gen",
    "Gnome tộc / Địa Linh tộc": "tộc Gnome",
    "Gnome tộc": "tộc Gnome",
    "Địa Linh tộc": "tộc Gnome",
    "Thiên Xà tộc": "tộc Thiên Xà",
    "Thương Bạch chi địa": "Vùng đất Thương Bạch",
    "Thương Bạch chi Địa": "Vùng đất Thương Bạch",
    "Bất Chu Sơn": "Bất Chu Sơn/núi Bất Chu",
    "Ô Bối Lợi Tư Khắc chi Cự Thần Binh": "Cự Thần Binh Obelisk",
    "Thiên Khải Tứ Kỵ Sĩ": "Bốn Kỵ Sĩ Khải Huyền",
    "U Minh Kỵ Sĩ": "Kỵ Sĩ U Minh",
    "Lược Đoạt Giả Liên Minh": "Liên minh Lược Đoạt Giả",
    "Thụ tinh Huyết tộc": "Huyết tộc Thụ Tinh cao cấp",
    "Miêu nhĩ Huyết tộc": "Huyết tộc Miêu Nhân",
}

keys = sorted(replacements.keys(), key=len, reverse=True)

print("Starting term replacement in:", output_dir)
changed_files = 0

for file in os.listdir(output_dir):
    if file.endswith(".md"):
        filepath = os.path.join(output_dir, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        orig_content = content
        for k in keys:
            v = replacements[k]
            if v == k: continue
            
            # case sensitive replace with lookahead to prevent infinite expansion on matching substring
            # for exact uppercase mapping:
            if k in v:
                suffix = v[len(k):]
                pattern = re.escape(k) + r'(?!' + re.escape(suffix) + r')'
                content = re.sub(pattern, lambda _: v, content) # lambda used to prevent \ escape errors in v
            else:
                content = content.replace(k, v)
                
            # lowercase mapping replace
            kl = k.lower()
            vl = v.lower()
            if kl in vl:
                suffix = vl[len(kl):]
                pattern = re.escape(kl) + r'(?!' + re.escape(suffix) + r')'
                content = re.sub(pattern, lambda _: vl, content)
            else:
                content = content.replace(kl, vl)
                
        if content != orig_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            changed_files += 1

print("Replacement done. Updated files.")
