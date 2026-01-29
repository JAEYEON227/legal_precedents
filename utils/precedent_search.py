"""
Precedent Search Module
판례 검색 메인 로직
"""

from typing import List, Dict, Any
from .scoring import calculate_precedent_score, get_matched_fields


def search_precedent(
    query: str,
    data_kcs: List[Dict[str, Any]],
    data_moleg: List[Dict[str, Any]],
    top_k: int = 20,
    min_score: float = 30.0
) -> List[Dict[str, Any]]:
    """
    KCS 및 MOLEG 데이터에서 판례 검색

    Args:
        query: 사용자 검색어
        data_kcs: KCS 판례 데이터 리스트
        data_moleg: MOLEG 판례 데이터 리스트
        top_k: 반환할 최대 결과 수
        min_score: 최소 점수 (이 점수 미만은 제외)

    Returns:
        검색 결과 리스트 (점수 높은 순)
        [
            {
                'score': 95.0,
                'source': 'kcs' or 'moleg',
                'data': {원본 판례 데이터},
                'matched_fields': {'사건번호': 100.0, '선고일자': 90.0}
            },
            ...
        ]
    """
    results = []

    # KCS 데이터 검색
    for precedent in data_kcs:
        score = calculate_precedent_score(query, precedent, 'kcs')
        if score >= min_score:
            matched_fields = get_matched_fields(query, precedent, 'kcs')
            results.append({
                'score': score,
                'source': 'kcs',
                'data': precedent,
                'matched_fields': matched_fields
            })

    # MOLEG 데이터 검색
    for precedent in data_moleg:
        score = calculate_precedent_score(query, precedent, 'moleg')
        if score >= min_score:
            matched_fields = get_matched_fields(query, precedent, 'moleg')
            results.append({
                'score': score,
                'source': 'moleg',
                'data': precedent,
                'matched_fields': matched_fields
            })

    # 점수 높은 순으로 정렬
    results.sort(key=lambda x: x['score'], reverse=True)

    # 상위 k개만 반환
    return results[:top_k]


def format_precedent_title(result: Dict[str, Any]) -> str:
    """
    검색 결과를 제목 형식으로 포맷

    Args:
        result: 검색 결과 딕셔너리

    Returns:
        포맷된 제목 문자열
    """
    source = result['source']
    data = result['data']

    if source == 'kcs':
        case_number = data.get('사건번호', 'N/A')
        case_name = data.get('사건명', 'N/A')
        date = data.get('선고일자\n(종결일자)', 'N/A')
        return f"[{case_number}] {case_name} ({date})"
    else:  # moleg
        precedent_number = data.get('판례번호', 'N/A')
        title = data.get('제목', 'N/A')
        # 판례번호에서 대괄호 제거
        if precedent_number.startswith('[') and precedent_number.endswith(']'):
            precedent_number = precedent_number[1:-1]
        return f"[{precedent_number}] {title}"


def format_precedent_summary(result: Dict[str, Any]) -> str:
    """
    검색 결과를 요약 형식으로 포맷

    Args:
        result: 검색 결과 딕셔너리

    Returns:
        포맷된 요약 문자열
    """
    source = result['source']
    data = result['data']

    summary_lines = []

    if source == 'kcs':
        summary_lines.append(f"사건번호: {data.get('사건번호', 'N/A')}")
        summary_lines.append(f"사건명: {data.get('사건명', 'N/A')}")
        date_field = '선고일자\n(종결일자)'
        summary_lines.append(f"선고일자: {data.get(date_field, 'N/A')}")
        summary_lines.append(f"처분청: {data.get('처분청', 'N/A')}")
        summary_lines.append(f"결과: {data.get('결과', 'N/A')}")
    else:  # moleg
        summary_lines.append(f"판례번호: {data.get('판례번호', 'N/A')}")
        summary_lines.append(f"제목: {data.get('제목', 'N/A')}")
        summary_lines.append(f"법원명: {data.get('법원명', 'N/A')}")
        summary_lines.append(f"선고일자: {data.get('선고일자', 'N/A')}")
        summary_lines.append(f"사건유형: {data.get('사건유형', 'N/A')}")

        # 판결요지가 있으면 추가 (첫 200자만)
        if data.get('판결요지'):
            summary = data['판결요지'][:200]
            if len(data['판결요지']) > 200:
                summary += "..."
            summary_lines.append(f"\n판결요지: {summary}")

    return "\n".join(summary_lines)
