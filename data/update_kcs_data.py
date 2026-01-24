#!/usr/bin/env python3
"""
KCS Data Update and Merge Script

This script processes newly crawled KCS data by:
1. Cleaning the temporary data using clean_kcs.py
2. Merging cleaned data with existing data_kcs.json
3. Removing duplicates to maintain data integrity

Usage:
    python update_kcs_data.py
"""

import json
import os
import sys
from datetime import datetime
import pandas as pd
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

def load_json(file_path):
    """JSON 파일 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON 파일 파싱 오류 ({file_path}): {e}")
        return []

def save_json(data, file_path):
    """JSON 파일 저장"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"파일 저장 오류 ({file_path}): {e}")
        return False

def clean_temp_data():
    """clean_kcs.py를 사용하여 임시 데이터 정리"""
    print("1. 임시 데이터 정리 중...")

    try:
        # clean_kcs.py 모듈 임포트
        from clean_kcs import KCSDataCleaner

        # 임시 파일 확인
        temp_file = PROJECT_ROOT / 'data_kcs_temp.json'
        if not temp_file.exists():
            print(f"오류: {temp_file} 파일이 없습니다.")
            return None

        # 임시 데이터 로드 및 기본 정리
        temp_data = load_json(str(temp_file))

        # 기본적인 데이터 정리 수행 (빈 데이터 제거)
        cleaned_data = []
        for entry in temp_data:
            # 주요 필드가 있는지 확인
            key_fields = ['판결주문', '청구취지', '판결이유']
            has_content = False

            for field in key_fields:
                content = str(entry.get(field, '')).strip()
                if content and len(content) > 5:  # 최소 5자 이상
                    has_content = True
                    break

            if has_content and entry.get('사건번호', '').strip():
                cleaned_data.append(entry)

        if cleaned_data:
            print(f"   - 정리 완료: {len(cleaned_data)}건의 데이터")
            return cleaned_data
        else:
            print("   - 정리된 데이터가 없습니다.")
            return []

    except ImportError as e:
        print(f"오류: clean_kcs.py 모듈을 찾을 수 없습니다: {e}")
        return None
    except Exception as e:
        print(f"데이터 정리 중 오류 발생: {e}")
        return None

def merge_data(new_data, existing_file=None):
    """새 데이터를 기존 데이터와 병합하고 중복 제거"""
    print("2. 데이터 병합 및 중복 제거 중...")

    # 기존 데이터 로드
    if existing_file is None:
        existing_file = str(PROJECT_ROOT / 'data_kcs.json')
    existing_data = load_json(existing_file)

    # 데이터 병합
    combined_data = existing_data + new_data

    if not combined_data:
        print("   - 병합할 데이터가 없습니다.")
        return []

    # 중복 제거를 위해 DataFrame 사용
    try:
        df = pd.DataFrame(combined_data)

        # 전체 필드를 기준으로 중복 제거 (더 정확한 중복 탐지)
        df_unique = df.drop_duplicates(keep='first')

        unique_data = df_unique.to_dict(orient='records')

        print(f"   - 병합 전 데이터: {len(combined_data)}건")
        print(f"   - 기존 데이터: {len(existing_data)}건")
        print(f"   - 새 데이터: {len(new_data)}건")
        print(f"   - 중복 제거 후: {len(unique_data)}건")
        print(f"   - 새로 추가된 데이터: {len(unique_data) - len(existing_data)}건")

        return unique_data

    except Exception as e:
        print(f"데이터 병합 중 오류 발생: {e}")
        return combined_data

def main():
    """메인 실행 함수"""
    print("=== KCS 데이터 업데이트 시작 ===")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. 임시 데이터 정리
    cleaned_data = clean_temp_data()
    if cleaned_data is None:
        print("데이터 정리에 실패했습니다. 종료합니다.")
        sys.exit(1)

    if not cleaned_data:
        print("정리된 데이터가 없습니다. 종료합니다.")
        sys.exit(0)

    # 2. 데이터 병합 및 중복 제거
    merged_data = merge_data(cleaned_data)

    if not merged_data:
        print("병합할 데이터가 없습니다.")
        return

    # 3. 백업 생성
    backup_file = PROJECT_ROOT / "data_kcs_backup.json"
    main_file = PROJECT_ROOT / 'data_kcs.json'
    if main_file.exists():
        try:
            original_data = load_json(str(main_file))
            save_json(original_data, str(backup_file))
            print(f"3. 기존 데이터 백업 완료: {backup_file}")
        except Exception as e:
            print(f"백업 생성 실패: {e}")

    # 4. 업데이트된 데이터 저장
    if save_json(merged_data, str(main_file)):
        print(f"4. 업데이트 완료: {main_file}")
    else:
        print("4. 데이터 저장 실패")
        return

    # 5. 임시 파일 유지 (삭제하지 않음)
    temp_file = PROJECT_ROOT / 'data_kcs_temp.json'
    if temp_file.exists():
        print(f"5. 임시 파일 유지: {temp_file}")

    print(f"\n=== 업데이트 완료 ===")
    print(f"최종 데이터: {len(merged_data)}건")
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()