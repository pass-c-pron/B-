# -*- coding: utf-8 -*-
"""测试完整同步流程（不写数据库，只打印结果）"""
import sys, os, json, time, re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError

APPID = 'wx1b940e41e6a54afd'
SECRET = '899faede77c0b025c9b1f5e5f59f4ae9'
CLOUD_ENV = 'dev-1grdm6tp754371fa'
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; 114514YAJU Build/UKQ1.114514.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.6422.165 Mobile Safari/537.36 BiliApp/78102000",
    "Referer": "https://show.bilibili.com/",
}

HENAN_PROVINCE_ID = 410000
HENAN_CITIES = ["郑州","开封","洛阳","平顶山","安阳","鹤壁","新乡","焦作","濮阳","许昌","漯河","三门峡","南阳","商丘","信阳","周口","驻马店","济源","兰考","汝州","滑县","长垣","邓州","永城","固始","鹿邑","新蔡","项城","沈丘","罗山","息县","范县","台前"]

def http_get(url, retries=2):
    for i in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if i < retries - 1:
                time.sleep(1)
    return None

def convert_ts(ts):
    if not ts: return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except:
        return str(ts)

def extract_city(name):
    if "·" in name:
        c = name.split("·")[0]
        if c in HENAN_CITIES: return c
    for c in HENAN_CITIES:
        if c in name: return c
    return ""

def process_show(item):
    cover = item.get("cover", "")
    if cover and not cover.startswith("http"):
        cover = "https:" + cover
    start_unix = item.get("start_unix") or item.get("start_time", 0)
    guests_list = item.get("guests") or []
    guests = "、".join(g.get("name","") for g in guests_list if g.get("name"))
    return {
        "projectId": item.get("project_id"),
        "name": item.get("project_name", ""),
        "city": extract_city(item.get("project_name", "")),
        "cover": cover,
        "startTime": convert_ts(start_unix),
        "endTime": convert_ts(item.get("end_time")),
        "startUnix": start_unix,
        "location": (item.get("district_name") or "") + (item.get("venue_name") or ""),
        "venueName": item.get("venue_name") or "",
        "districtName": item.get("district_name") or "",
        "province": "河南",
        "priceLow": (item.get("price_low") or 0) / 100,
        "priceHigh": (item.get("price_high") or 0) / 100,
        "saleFlag": item.get("sale_flag") or "",
        "wish": item.get("wish") or 0,
        "guests": guests,
        "url": f"https://show.bilibili.com/platform/detail.html?id={item.get('project_id')}",
    }

def process_detail(detail_data):
    data = detail_data.get("data", {})
    ticket_info = []
    for screen in data.get("screen_list", []):
        for ticket in screen.get("ticket_list", []):
            ticket_info.append({
                "desc": ticket.get("desc", ""),
                "price": (ticket.get("price") or 0) / 100,
                "saleStart": convert_ts(ticket.get("saleStart")),
                "saleEnd": convert_ts(ticket.get("saleEnd")),
                "status": ticket.get("sale_flag", {}).get("display_name", ""),
                "screenName": ticket.get("screen_name"),
            })
    venue_info = data.get("venue_info", {})
    guests_list = data.get("guests") or []
    guests = "、".join(g.get("name","") for g in guests_list if g.get("name"))
    details_html = ""
    for d in data.get("performance_desc", {}).get("list", []):
        if d.get("module") == "activity_content":
            details_html = d.get("details", "") or ""
            break
    if details_html:
        details_html = re.sub(r'src="//', 'src="https://', details_html)
    banner = data.get("banner") or ""
    if banner and not banner.startswith("http"):
        banner = "https:" + banner
    return {
        "venueDetail": venue_info.get("address_detail") or "",
        "organizer": data.get("merchant", {}).get("company") or "",
        "ticketInfo": ticket_info,
        "guests": guests,
        "banner": banner,
        "detailsHtml": details_html,
        "isRefund": data.get("is_refund"),
        "hasEticket": data.get("has_eticket"),
    }

def get_shows(area_id, page=1):
    params = urlencode({
        "version": 133, "area": area_id, "page": page,
        "pagesize": 20, "platform": "web", "style": 1,
    })
    return http_get(f"https://show.bilibili.com/api/ticket/project/listV2?{params}")

def get_detail(project_id):
    params = urlencode({"id": project_id, "project_id": project_id, "requestSource": "neul-next"})
    return http_get(f"https://show.bilibili.com/api/ticket/project/getV2?{params}")

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={SECRET}"
    with urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    return data.get("access_token", "")

def write_to_cloud(shows, token):
    base_url = f"https://api.weixin.qq.com/tcb"
    hdrs = {"Content-Type": "application/json"}

    # Get existing IDs
    query_url = f"{base_url}/databasequery?access_token={token}"
    query_payload = json.dumps({"env": CLOUD_ENV, "query": "db.collection('exhibitions').limit(1000).field({projectId:true}).get()"}, ensure_ascii=False)
    try:
        req = Request(query_url, data=query_payload.encode(), headers=hdrs)
        with urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        existing = set()
        for item in result.get("data", []):
            rec = json.loads(item) if isinstance(item, str) else item
            if "projectId" in rec: existing.add(rec["projectId"])
        print(f"  Cloud DB existing: {len(existing)} records")
    except Exception as e:
        print(f"  Query existing failed: {e}")
        existing = set()

    inserted = upserted = 0
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for show in shows:
        pid = show.get("projectId")
        if not pid: continue
        rec = dict(show)
        rec["updateTime"] = now

        if pid in existing:
            url = f"{base_url}/databaseupdate?access_token={token}"
            payload = json.dumps({"env": CLOUD_ENV, "query": f"db.collection('exhibitions').where({{projectId:{pid}}}).update({{data:{json.dumps(rec, ensure_ascii=False)}}})"}, ensure_ascii=False)
            upserted += 1
        else:
            url = f"{base_url}/databaseadd?access_token={token}"
            rec["createTime"] = now
            payload = json.dumps({"env": CLOUD_ENV, "query": f"db.collection('exhibitions').add({{data:{json.dumps(rec, ensure_ascii=False)}}})"}, ensure_ascii=False)
            inserted += 1

        try:
            req = Request(url, data=payload.encode(), headers=hdrs)
            with urlopen(req, timeout=10) as r:
                res = json.loads(r.read())
            if res.get("errcode") not in (0, None):
                print(f"  WARN {pid}: {res.get('errmsg')}")
        except Exception as e:
            print(f"  ERR {pid}: {e}")
        time.sleep(0.1)

    return inserted, upserted

def main():
    print("=" * 50)
    print("漫展数据同步测试")
    print("=" * 50)

    # Get city list
    city_data = http_get("https://show.bilibili.com/api/ticket/city/list?channel=3")
    if not city_data or city_data.get("code") != 0:
        print("FAIL: Cannot get city list")
        sys.exit(1)

    cities = {}
    for region in city_data.get("data", {}).get("list", []):
        for city in region.get("city_list", []):
            cities[city["name"]] = {"id": city["id"], "parent_id": city.get("parent_id", 0), "num": city.get("num", 0)}

    henan = [(n, c["id"], c["num"]) for n, c in cities.items() if c["parent_id"] == HENAN_PROVINCE_ID and c["num"] > 0]
    print(f"Henan cities with data: {len(henan)}")

    all_shows = {}
    for city_name, city_id, expected in sorted(henan, key=lambda x: -x[2]):
        page = 1
        city_count = 0
        while page <= 5:
            resp = get_shows(city_id, page)
            if not resp or resp.get("code") != 0: break
            result = resp.get("data", {}).get("result", [])
            if not result: break
            for item in result:
                pid = item.get("project_id")
                if pid and pid not in all_shows:
                    all_shows[pid] = process_show(item)
                    city_count += 1
            if len(result) < 20: break
            page += 1
            time.sleep(0.3)
        print(f"  {city_name} ({city_id}): got {city_count} (expected {expected})")

    shows = list(all_shows.values())
    print(f"\nTotal fetched: {len(shows)} exhibitions")

    # Get token and write
    token = get_token()
    if not token:
        print("FAIL: Cannot get access token")
        sys.exit(1)
    print("Token OK")

    ins, upd = write_to_cloud(shows, token)
    print(f"\nCloud write: +{ins} new, ~{upd} updated")
    print(f"Total in cloud: {len(shows)} exhibitions")

if __name__ == "__main__":
    main()
