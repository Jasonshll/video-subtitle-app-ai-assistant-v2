from typing import Dict, Tuple, List, Optional


def script_counts(text: str) -> Dict[str, int]:
    counts = {"zh": 0, "ja": 0, "ko": 0, "en": 0}
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7AF:
            counts["ko"] += 1
        elif 0x3040 <= code <= 0x30FF:
            counts["ja"] += 1
        elif 0x4E00 <= code <= 0x9FFF:
            counts["zh"] += 1
        elif ("a" <= ch.lower() <= "z"):
            counts["en"] += 1
    return counts


def detect_language(text: str) -> str:
    counts = script_counts(text)
    total = sum(counts.values())
    if total == 0:
        return "unknown"

    if counts["ja"] > 0:
        return "ja"

    dominant = max(counts.items(), key=lambda x: x[1])[0]
    second = sorted(counts.values(), reverse=True)[1]
    if counts[dominant] == 0:
        return "unknown"
    if second / max(1, counts[dominant]) > 0.5:
        return "mixed"
    return dominant


def mismatch_score(expected: str, text: str) -> float:
    counts = script_counts(text)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    expected_count = counts.get(expected, 0)
    return 1.0 - (expected_count / total)


def normalize_with_map(text: str) -> Tuple[str, List[int]]:
    normalized_chars: List[str] = []
    index_map: List[int] = []
    for i, ch in enumerate(text):
        if ch.isalnum():
            normalized_chars.append(ch.lower())
            index_map.append(i)
    return "".join(normalized_chars), index_map


def extract_between_neighbors(
    combined_text: str, prev_text: str, next_text: str
) -> Optional[str]:
    combined_norm, combined_map = normalize_with_map(combined_text)
    prev_norm, _ = normalize_with_map(prev_text)
    next_norm, _ = normalize_with_map(next_text)

    if not prev_norm or not next_norm:
        return None

    prev_pos = combined_norm.find(prev_norm)
    if prev_pos < 0:
        return None

    next_pos = combined_norm.find(next_norm, prev_pos + len(prev_norm))
    if next_pos < 0:
        return None

    start_norm = prev_pos + len(prev_norm)
    end_norm = next_pos
    if start_norm >= end_norm:
        return None

    if start_norm >= len(combined_map) or end_norm >= len(combined_map):
        return None

    start_orig = combined_map[start_norm]
    end_orig = combined_map[end_norm]
    if start_orig >= end_orig:
        return None

    return combined_text[start_orig:end_orig].strip()
