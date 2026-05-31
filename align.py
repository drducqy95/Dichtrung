import json
import math
from pathlib import Path

def gale_church_align(source_lengths, target_lengths, mean=-0.04, variance=0.068):
    # Simplified Gale-Church alignment
    # We want to find the minimum cost path.
    # Allowed alignments: (1,1), (1,0), (0,1), (2,1), (1,2), (2,2)
    c = 1.0
    
    n = len(source_lengths)
    m = len(target_lengths)
    
    # dp[i][j] = min cost to align source[:i] and target[:j]
    dp = [[float('inf')] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    
    pointers = [[None] * (m + 1) for _ in range(n + 1)]
    
    moves = [
        (1, 1), # 1-to-1
        (2, 1), # 2-to-1
        (1, 2), # 1-to-2
        (0, 1), # 0-to-1 (insertion)
        (1, 0), # 1-to-0 (deletion)
        (2, 2)  # 2-to-2
    ]
    
    def cost(s_len, t_len):
        if s_len == 0 and t_len == 0: return 0
        if s_len == 0 or t_len == 0: return 1000 # High penalty for 1-to-0 or 0-to-1
        
        # Expected target length given source length
        expected_t_len = s_len * c
        # The cost is based on the difference
        diff = (t_len - expected_t_len) / math.sqrt(s_len * variance) if s_len > 0 else 0
        return abs(diff) * 10
        
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
                
            best_cost = float('inf')
            best_move = None
            
            for di, dj in moves:
                prev_i, prev_j = i - di, j - dj
                if prev_i >= 0 and prev_j >= 0:
                    s_len = sum(source_lengths[prev_i:i])
                    t_len = sum(target_lengths[prev_j:j])
                    
                    # Compute match cost
                    match_cost = cost(s_len, t_len)
                    
                    # Penalty for non 1-to-1
                    penalty = 0
                    if (di, dj) == (2, 1) or (di, dj) == (1, 2): penalty = 200
                    elif (di, dj) == (2, 2): penalty = 400
                    
                    total_cost = dp[prev_i][prev_j] + match_cost + penalty
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_move = (prev_i, prev_j)
            
            dp[i][j] = best_cost
            pointers[i][j] = best_move
            
    # Backtrack
    alignments = []
    curr_i, curr_j = n, m
    while curr_i > 0 or curr_j > 0:
        prev_i, prev_j = pointers[curr_i][curr_j]
        alignments.append((prev_i, curr_i, prev_j, curr_j))
        curr_i, curr_j = prev_i, prev_j
        
    return alignments[::-1]

def process_chapter(branch, chapter):
    branch_dir = Path("Output") / branch
    pack_file = branch_dir / "runtime" / "context_packs" / f"chapter_{chapter:04d}.context_pack.json"
    trans_file = branch_dir / "runtime" / f"chapter_{chapter:04d}.translation_result.json"
    analysis_file = branch_dir / "runtime" / "analysis" / f"chapter_{chapter:04d}.analysis_result.json"
    
    with open(pack_file, encoding='utf-8') as f:
        source_text = json.load(f)['chapter']['source_text']
    with open(trans_file, encoding='utf-8') as f:
        target_text = json.load(f)['translated_text']
        
    source_paras = [p.strip() for p in source_text.split('\n') if p.strip()]
    target_paras = [p.strip() for p in target_text.split('\n') if p.strip()]
    
    s_lengths = [len(p) for p in source_paras]
    t_lengths = [len(p) for p in target_paras]
    
    alignments = gale_church_align(s_lengths, t_lengths)
    
    aligned_segments = []
    seg_idx = 1
    for (si, ei, sj, ej) in alignments:
        src = "\n".join(source_paras[si:ei])
        tgt = "\n".join(target_paras[sj:ej])
        
        # Determine alignment type
        di = ei - si
        dj = ej - sj
        atype = "1-to-1"
        if di > 1 and dj == 1: atype = "many-to-1"
        elif di == 1 and dj > 1: atype = "1-to-many"
        elif di == 0 or dj == 0: continue
        
        aligned_segments.append({
            "seg_id": f"seg_{seg_idx:04d}",
            "source": src,
            "target": tgt,
            "alignment_type": atype,
            "narrative_type": "narration"
        })
        seg_idx += 1
        
    with open(analysis_file, encoding='utf-8') as f:
        analysis = json.load(f)
        
    analysis['aligned_segments'] = aligned_segments
    
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
        
    print(f"Chapter {chapter}: Aligned {len(source_paras)} src to {len(target_paras)} tgt into {len(aligned_segments)} segments.")

for ch in range(23, 34):
    process_chapter('Tu Chan Bon Van Nam_Ngoa Nguu Chan Nhan', ch)
