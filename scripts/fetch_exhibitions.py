# -*- coding: utf-8 -*-
"""
漫展数据抓取脚本 - 从B站会员购API获取漫展/展览信息
数据源: https://show.bilibili.com (B站会员购)
用途: 为「漫友搭子营」小程序提供漫展攻略数据

修复: 
  - API 分页问题：改用城市级别查询（省份查询分页失效）
  - pagesize 限制：固定使用 20
"""

import json
import time
import os
import sys
import re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

# ── B站会员购 API ──────────────────────────────────────────
CITY_API = "https://show.bilibili.com/api/ticket/city/list?channel=3"
SHOWS_API = "https://show.bilibili.com/api/ticket/project/listV2"
DETAIL_API = "https://show.bilibili.com/api/ticket/project/getV2"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 14; 114514YAJU Build/UKQ1.114514.001; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.6422.165 "
        "Mobile Safari/537.36 BiliApp/78102000 mobi_app/android isiNotchWindow/0 "
        "NotchHeight=34 mallVersion/78102000 mVersion/242 disable_rcmd/0 7.81.0 "
        "os/android model/114514YAJU mobi_app/android build/78102000 channel/bilih5 "
        "innerVer/7810210 osVer/14 network/2"
    ),
    "Referer": "https://show.bilibili.com/",
}

# 河南省省份ID
HENAN_PROVINCE_ID = 410000

# 河南省城市列表（用于提取城市名）
HENAN_CITIES = [
    "郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作",
    "濮阳", "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口",
    "驻马店", "济源", "兰考", "汝州", "滑县", "长垣", "邓州", "永城",
    "固始", "鹿邑", "新蔡", "项城", "沈丘", "罗山", "息县", "范县", "台前",
]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "crawler")


def extract_city(name):
    """从漫展名称提取城市名（格式：城市·漫展名）"""
    if "·" in name:
        city = name.split("·")[0]
        if city in HENAN_CITIES:
            return city
    for city in HENAN_CITIES:
        if city in name:
            return city
    return ""


def http_get(url, retries=3):
    """HTTP GET 请求"""
    for i in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            print(f"  [retry {i+1}/{retries}] {e}")
            if i < retries - 1:
                time.sleep(2)
    return None


def get_cities():
    """获取城市列表"""
    print("[1/4] Getting city list...")
    data = http_get(CITY_API)
    if not data or data.get("code") != 0:
        print(f"  FAILED: {data}")
        return {}
    
    # 返回 {城市名: {id, parent_id, num}} 格式
    cities = {}
    for region in data.get("data", {}).get("list", []):
        for city in region.get("city_list", []):
            cities[city["name"]] = {
                "id": city["id"],
                "parent_id": city.get("parent_id", 0),
                "num": city.get("num", 0)
            }
    print(f"  OK: {len(cities)} cities")
    return cities


def get_shows(area_id, page=1):
    """获取展览列表（pagesize 固定为 20）"""
    params = {
        "version": 133,
        "area": area_id,
        "page": page,
        "pagesize": 20,  # API 要求固定为 20
        "platform": "web",
        "style": 1,
    }
    url = SHOWS_API + "?" + urlencode(params)
    return http_get(url)


def get_show_detail(project_id):
    """获取展览详情"""
    params = {
        "id": project_id,
        "project_id": project_id,
        "requestSource": "neul-next",
    }
    url = DETAIL_API + "?" + urlencode(params)
    return http_get(url)


def convert_timestamp(ts):
    """时间戳 -> YYYY-MM-DD HH:MM"""
    if not ts or ts == 0:
        return ""
    if isinstance(ts, str):
        return ts
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, TypeError):
        return str(ts)


def process_show(item):
    """提取列表页关键字段"""
    price_low = item.get("price_low", 0) / 100
    price_high = item.get("price_high", 0) / 100
    district_name = item.get("district_name") or ""
    venue_name = item.get("venue_name") or ""

    guests_list = item.get("guests")
    guests = ""
    if guests_list:
        guests = "、".join(g["name"] for g in guests_list if g.get("name"))

    cover = item.get("cover", "")
    if cover and not cover.startswith("http"):
        cover = "https:" + cover

    start_unix = item.get("start_unix") or item.get("start_time", 0)
    start_time = convert_timestamp(start_unix)
    end_time = convert_timestamp(item.get("end_time", 0))

    project_name = item.get("project_name", "")
    city = extract_city(project_name)

    return {
        "projectId": item.get("project_id"),
        "name": project_name,
        "cover": cover,
        "startTime": start_time,
        "endTime": end_time,
        "startUnix": start_unix,
        "location": district_name + venue_name,
        "venueName": venue_name,
        "districtName": district_name,
        "city": city,
        "priceLow": price_low,
        "priceHigh": price_high,
        "saleFlag": item.get("sale_flag", ""),
        "wish": item.get("wish", 0),
        "guests": guests,
        "url": f"https://show.bilibili.com/platform/detail.html?id={item.get('project_id', '')}",
    }


def process_detail(detail_data):
    """提取详情页字段"""
    data = detail_data.get("data", {})

    # 票价
    ticket_info = []
    for screen in data.get("screen_list", []):
        for ticket in screen.get("ticket_list", []):
            ticket_info.append({
                "desc": ticket.get("desc", ""),
                "price": ticket.get("price", 0) / 100,
                "saleStart": convert_timestamp(ticket.get("saleStart", 0)),
                "saleEnd": convert_timestamp(ticket.get("saleEnd", 0)),
                "status": ticket.get("sale_flag", {}).get("display_name", ""),
                "screenName": ticket.get("screen_name"),
            })

    # 场馆
    venue_info = data.get("venue_info", {})
    venue_detail = venue_info.get("address_detail", "")

    # 主办方
    organizer = data.get("merchant", {}).get("company", "")

    # 嘉宾
    guests_list = data.get("guests")
    guests = ""
    if guests_list:
        guests = "、".join(g["name"] for g in guests_list if g.get("name"))

    # 活动介绍 (修复图片链接)
    desc_list = data.get("performance_desc", {}).get("list", [])
    details_html = ""
    for d in desc_list:
        if d.get("module") == "activity_content":
            details_html = d.get("details", "")
            break
    
    # 修复图片链接：//xxx -> https://xxx
    if details_html:
        details_html = re.sub(r'src="//', 'src="https://', details_html)

    banner = data.get("banner", "")
    if banner and not banner.startswith("http"):
        banner = "https:" + banner

    return {
        "venueDetail": venue_detail,
        "organizer": organizer,
        "ticketInfo": ticket_info,
        "guests": guests,
        "banner": banner,
        "detailsHtml": details_html,
        "isRefund": data.get("is_refund"),
        "hasEticket": data.get("has_eticket"),
    }


def fetch_all_exhibitions(cities):
    """按城市分别抓取展览"""
    all_shows = {}
    
    # 筛选河南省的城市
    henan_city_ids = []
    for city_name, info in cities.items():
        if info["parent_id"] == HENAN_PROVINCE_ID and info["num"] > 0:
            henan_city_ids.append((city_name, info["id"], info["num"]))
    
    print(f"[2/4] Fetching from {len(henan_city_ids)} cities in Henan...")
    
    for city_name, city_id, expected_num in sorted(henan_city_ids, key=lambda x: -x[2]):
        print(f"\n  >> {city_name} (id={city_id}, expected: {expected_num})")
        page = 1
        city_count = 0
        
        while page <= 5:  # 每个城市最多5页
            print(f"     page {page}...", end=" ")
            resp = get_shows(city_id, page=page)

            if not resp or resp.get("code") != 0:
                msg = resp.get("message", "no response") if resp else "no response"
                print(f"FAIL: {msg}")
                break

            result = resp.get("data", {}).get("result", [])
            if not result:
                print("no more data")
                break

            new_count = 0
            for item in result:
                pid = item.get("project_id")
                if pid and pid not in all_shows:
                    show = process_show(item)
                    show["province"] = "河南"
                    all_shows[pid] = show
                    new_count += 1
                    city_count += 1

            print(f"+{new_count} new (city: {city_count})")

            if len(result) < 20:
                break
            page += 1
            time.sleep(0.3)

    return list(all_shows.values())


def enrich_with_details(shows):
    """补充详情信息"""
    total = len(shows)
    print(f"\n[3/4] Enriching details ({total} exhibitions)...")
    
    for i, show in enumerate(shows):
        pid = show.get("projectId")
        if not pid:
            continue
        name_short = show["name"][:25] if len(show["name"]) > 25 else show["name"]
        print(f"  [{i+1}/{total}] {name_short}...", end=" ")

        detail_resp = get_show_detail(pid)
        if detail_resp and detail_resp.get("code") == 0:
            detail = process_detail(detail_resp)
            show.update(detail)
            print("OK")
        else:
            print("SKIP")

        time.sleep(0.3)

    return shows


def save_to_json(shows, filename="exhibitions.json"):
    """保存到 JSON"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    output = {
        "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalCount": len(shows),
        "exhibitions": shows,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[4/4] Saved {len(shows)} exhibitions to: {filepath}")
    return filepath


# ── Main ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  Exhibition Crawler - Bilibili Show API (City-based)")
    print("=" * 60)

    cities = get_cities()
    if not cities:
        print("FATAL: Cannot get city list")
        sys.exit(1)

    shows = fetch_all_exhibitions(cities)

    if not shows:
        print("FATAL: No exhibitions found")
        sys.exit(1)

    shows = enrich_with_details(shows)
    filepath = save_to_json(shows)

    # 摘要
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"  Total exhibitions: {len(shows)}")
    print(f"  Data file: {filepath}")
    if shows:
        print(f"\n  TOP 5:")
        for s in shows[:5]:
            price = f"{s['priceLow']}-{s['priceHigh']}" if s.get("priceHigh") else f"{s['priceLow']}+"
            print(f"  * {s['name']}")
            print(f"    {s['location']} | {price} yuan | {s['startTime']}")
