"""채널 + AppsFlyer CSV 로드 및 조인 로직 (streamlit 의존성 없음)."""
import glob
import os
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent

# channel.csv의 `채널` 값 → appsflyer.csv의 `미디어소스` 값.
# 새 채널 추가 시 여기 한 줄.
CHANNEL_TO_MEDIA = {
    "구글": "googleadwords_int",
    "메타": "Facebook Ads",
    "네이버": "naver_search",
}

JOIN_KEYS = ["일", "미디어소스", "캠페인", "그룹", "소재"]


CHANNEL_DIR    = DATA_DIR / "data" / "channel"
APPSFLYER_DIR  = DATA_DIR / "data" / "appsflyer"


def files_signature(pattern: str) -> tuple:
    paths = sorted(glob.glob(str(DATA_DIR / pattern)))
    return tuple((p, os.path.getmtime(p)) for p in paths)


def channel_signature() -> tuple:
    paths = sorted(glob.glob(str(CHANNEL_DIR / "*_channel.csv")))
    return tuple((p, os.path.getmtime(p)) for p in paths)


def appsflyer_signature() -> tuple:
    paths = sorted(glob.glob(str(APPSFLYER_DIR / "*_appsflyer*.csv")))
    return tuple((p, os.path.getmtime(p)) for p in paths)


def load_channel(signature: tuple) -> pd.DataFrame:
    paths = [p for p, _ in signature]
    if not paths:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["일"] = pd.to_datetime(df["일"])
    df["미디어소스"] = df["채널"].map(CHANNEL_TO_MEDIA).fillna(df["채널"])
    return df


def load_appsflyer(signature: tuple) -> pd.DataFrame:
    paths = [p for p, _ in signature]
    if not paths:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["일"] = pd.to_datetime(df["일"])
    return df


def join_data(ch: pd.DataFrame, af: pd.DataFrame) -> pd.DataFrame:
    if ch.empty:
        return af
    if af.empty:
        return ch

    af_renamed = af.rename(columns={
        "클릭": "클릭_af",
        "회원가입": "회원가입_af",
        "구매": "구매_af",
        "구매매출": "구매매출_af",
    })

    merged = ch.merge(af_renamed, on=JOIN_KEYS, how="outer")

    merged["CTR"] = (merged["클릭"] / merged["노출"]).round(4)
    merged["CPC"] = (merged["비용"] / merged["클릭"]).round(0)
    merged["CPM"] = (merged["비용"] / merged["노출"] * 1000).round(0)
    merged["ROAS"] = (merged["구매매출"] / merged["비용"]).round(2)
    return merged
