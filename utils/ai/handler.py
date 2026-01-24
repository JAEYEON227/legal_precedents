"""
Gemini API Handler with Fallback Support
"""

import logging
import time
from google.genai import types

def generate_with_fallback(client, models, contents, config=None):
    """
    여러 모델에 대해 순차적으로 fallback을 시도하며 콘텐츠를 생성합니다.

    Args:
        client: Gemini API 클라이언트
        models (list): 시도할 모델 이름 리스트 (우선순위 순서)
        contents: 프롬프트 내용
        config: 생성 설정 (선택 사항)

    Returns:
        response: 생성된 응답 객체

    Raises:
        Exception: 모든 모델 시도 실패 시 마지막 예외 발생
    """
    last_exception = None

    for i, model in enumerate(models):
        try:
            logging.info(f"모델 시도: {model}")
            
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # 성공 시 즉시 반환
            return response

        except Exception as e:
            last_exception = e
            error_msg = str(e)
            
            # 429 (Resource Exhausted) 또는 기타 에러 발생 시 로그 기록
            logging.warning(f"모델 {model} 실패: {error_msg}")

            # 마지막 모델이 아니면 잠시 대기 후 다음 모델 시도
            if i < len(models) - 1:
                wait_time = 2  # 2초 대기
                logging.info(f"{wait_time}초 대기 후 다음 모델({models[i+1]}) 시도...")
                time.sleep(wait_time)
            
    # 모든 모델 실패 시
    logging.error("모든 fallback 모델 시도 실패")
    if last_exception:
        raise last_exception
    else:
        raise Exception("Unknown error in generate_with_fallback")
