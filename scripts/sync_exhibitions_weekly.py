# -*- coding: utf-8 -*-
"""
漫展数据自动同步脚本
- 定时任务调用此脚本，抓取全部 89 条河南省漫展
- 通过腾讯云 API 直接写入微信云开发数据库
- 输出简洁日志，供 cron 任务捕获通知用户
"""
import json
import time
import sys
import os
import re
import logging
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

# ── 配置 ──────────────────────────────────────────────
APP_ID = "wx1b940e41e6a54afd"      # 微信小程序 appid（从 project.config.json）
CLOUD_ENV = "coser-helper-9g0b9mzp3f2a2a8b"  # 云开发环境 ID（需确认）
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

HENAN_PROVINCE_ID = 410000

HENAN_CITIES = [
    "郑州", "开封", "洛阳", "平顶山", "安阳", "鹤壁", "新乡", "焦作",
    "濮阳", "许昌", "漯河", "三门峡", "南阳", "商丘", "信阳", "周口",
    "驻马店", "济源", "兰考", "汝州", "滑县", "长垣", "邓州", "永城",
    "固始", "鹿邑", "新蔡", "项城", "沈丘", "罗山", "息县", "范县", "台前",
]

# ── 日志配置 ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("exhibition_sync")


# ── 工具函数 ────────────────────────────────────────────

def extract_city(name):
    if "·" in name:
        city = name.split("·")[0]
        if city in HENAN_CITIES:
            return city
    for city in HENAN_CITIES:
        if city in name:
            return city
    return ""


def http_get(url, retries=3):
    for i in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            log.warning(f"  [retry {i+1}/{retries}] {e}")
            if i < retries - 1:
                time.sleep(2)
    return None


def convert_timestamp(ts):
    if not ts or ts == 0:
        return ""
    if isinstance(ts, str):
        return ts
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, TypeError):
        return str(ts)


# ── B站 API ─────────────────────────────────────────────

def get_cities():
    data = http_get(CITY_API)
    if not data or data.get("code") != 0:
        log.error(f"获取城市列表失败: {data}")
        return {}
    cities = {}
    for region in data.get("data", {}).get("list", []):
        for city in region.get("city_list", []):
            cities[city["name"]] = {
                "id": city["id"],
                "parent_id": city.get("parent_id", 0),
                "num": city.get("num", 0),
            }
    return cities


def get_shows(area_id, page=1):
    params = {
        "version": 133,
        "area": area_id,
        "page": page,
        "pagesize": 20,
        "platform": "web",
        "style": 1,
    }
    url = SHOWS_API + "?" + urlencode(params)
    return http_get(url)


def get_show_detail(project_id):
    params = {"id": project_id, "project_id": project_id, "requestSource": "neul-next"}
    url = DETAIL_API + "?" + urlencode(params)
    return http_get(url)


def process_show(item):
    price_low = item.get("price_low", 0) / 100
    price_high = item.get("price_high", 0) / 100
    district_name = item.get("district_name") or ""
    venue_name = item.get("venue_name") or ""
    cover = item.get("cover", "")
    if cover and not cover.startswith("http"):
        cover = "https:" + cover
    start_unix = item.get("start_unix") or item.get("start_time", 0)
    project_name = item.get("project_name", "")
    guests_list = item.get("guests") or []
    guests = "、".join(g["name"] for g in guests_list if g.get("name"))

    return {
        "projectId": item.get("project_id"),
        "name": project_name,
        "city": extract_city(project_name),
        "cover": cover,
        "startTime": convert_timestamp(start_unix),
        "endTime": convert_timestamp(item.get("end_time")),
        "startUnix": start_unix,
        "location": district_name + venue_name,
        "venueName": venue_name,
        "districtName": district_name,
        "province": "河南",
        "priceLow": price_low,
        "priceHigh": price_high,
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
                "price": ticket.get("price", 0) / 100,
                "saleStart": convert_timestamp(ticket.get("saleStart", 0)),
                "saleEnd": convert_timestamp(ticket.get("saleEnd", 0)),
                "status": ticket.get("sale_flag", {}).get("display_name", ""),
                "screenName": ticket.get("screen_name"),
            })
    venue_info = data.get("venue_info", {})
    guests_list = data.get("guests") or []
    guests = "、".join(g["name"] for g in guests_list if g.get("name"))
    desc_list = data.get("performance_desc", {}).get("list", [])
    details_html = ""
    for d in desc_list:
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


# ── 抓取主流程 ──────────────────────────────────────────

def fetch_all():
    """抓取全部河南省漫展（按城市分页）"""
    cities = get_cities()
    if not cities:
        log.error("无法获取城市列表，退出")
        sys.exit(1)

    all_shows = {}
    henan_cities = [
        (name, info["id"], info["num"])
        for name, info in cities.items()
        if info["parent_id"] == HENAN_PROVINCE_ID and info["num"] > 0
    ]

    log.info(f"抓取河南省 {len(henan_cities)} 个城市的漫展...")

    for city_name, city_id, expected in sorted(henan_cities, key=lambda x: -x[2]):
        page = 1
        while page <= 5:
            resp = get_shows(city_id, page)
            if not resp or resp.get("code") != 0:
                break
            result = resp.get("data", {}).get("result", [])
            if not result:
                break
            for item in result:
                pid = item.get("project_id")
                if pid and pid not in all_shows:
                    all_shows[pid] = process_show(item)
            if len(result) < 20:
                break
            page += 1
            time.sleep(0.3)

    shows = list(all_shows.values())
    log.info(f"抓取到 {len(shows)} 条漫展，开始补充详情...")

    for i, show in enumerate(shows):
        pid = show.get("projectId")
        if not pid:
            continue
        detail = get_show_detail(pid)
        if detail and detail.get("code") == 0:
            d = process_detail(detail)
            show.update(d)
        time.sleep(0.3)
        if (i + 1) % 20 == 0:
            log.info(f"  详情进度 {i+1}/{len(shows)}...")

    return shows


# ── 写入云数据库 ────────────────────────────────────────

def get_access_token():
    """从腾讯云获取 access_token（需在腾讯云控制台配置密钥）"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            if line.strip().startswith("WECHAT_ACCESS_TOKEN="):
                return line.split("=", 1)[1].strip()

    # 备用：检查环境变量
    token = os.environ.get("WECHAT_ACCESS_TOKEN")
    if token:
        return token

    log.error("未找到 WECHAT_ACCESS_TOKEN，请在 .env 文件或环境变量中配置")
    log.error("获取方式：微信公众平台 -> 开发管理 -> 接口调用 -> 获取 access_token")
    return None


def get_collection_token():
    """通过云开发 API 获取 access_token（需 appid + secret）"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    appid = APP_ID
    secret = None
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            if line.strip().startswith("WECHAT_SECRET="):
                secret = line.split("=", 1)[1].strip()

    if not secret:
        secret = os.environ.get("WECHAT_SECRET")

    if not secret:
        log.error("未找到 WECHAT_SECRET，请在 .env 文件中配置 WECHAT_SECRET=<你的密钥>")
        return None

    url = (
        f"https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={appid}&secret={secret}"
    )
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "access_token" in data:
            return data["access_token"]
        else:
            log.error(f"获取 access_token 失败: {data}")
            return None
    except Exception as e:
        log.error(f"获取 access_token 异常: {e}")
        return None


def write_to_cloud(shows):
    """通过云开发数据库 API 写入数据"""
    token = get_collection_token()
    if not token:
        log.error("无法获取 access_token，跳过云端写入")
        return 0, 0

    base_url = f"https://api.weixin.qq.com/tcb/databasecollection?access_token={token}"
    coll_url = f"https://api.weixin.qq.com/tcb/databasequery?access_token={token}"
    add_url = f"https://api.weixin.qq.com/tcb/databaseadd?access_token={token}"
    update_url = f"https://api.weixin.qq.com/tcb/databaseupdate?access_token={token}"

    # 确保 exhibitions 集合存在
    try:
        req = Request(base_url + f"&env={CLOUD_ENV}&action=createCollection&name=exhibitions",
                      method="POST")
        with urlopen(req, timeout=10) as resp:
            json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass  # 集合可能已存在

    # 查询现有数据
    query_payload = json.dumps({"env": CLOUD_ENV, "query": "db.collection('exhibitions').limit(1000).field({projectId:true}).get()"})
    try:
        req = Request(coll_url, data=query_payload.encode(), headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        existing_ids = set()
        for item in data.get("data", []):
            record = json.loads(item) if isinstance(item, str) else item
            if "projectId" in record:
                existing_ids.add(record["projectId"])
    except Exception as e:
        log.warning(f"查询现有数据失败: {e}，全部作为新增处理")
        existing_ids = set()

    log.info(f"云数据库已有 {len(existing_ids)} 条记录")
    inserted = 0
    upserted = 0

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for show in shows:
        pid = show.get("projectId")
        if not pid:
            continue
        record = dict(show)
        record["updateTime"] = now

        if pid in existing_ids:
            # 更新
            payload = json.dumps({
                "env": CLOUD_ENV,
                "query": f"db.collection('exhibitions').where({{projectId:'{pid}'}}).update({{data:{json.dumps(record, ensure_ascii=False)}}})"
            }, ensure_ascii=False)
            url = update_url
        else:
            # 新增
            record["createTime"] = now
            payload = json.dumps({
                "env": CLOUD_ENV,
                "query": f"db.collection('exhibitions').add({{data:{json.dumps(record, ensure_ascii=False)}}})"
            }, ensure_ascii=False)
            url = add_url

        try:
            req = Request(url, data=payload.encode(), headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            if result.get("errcode") == 0:
                if pid in existing_ids:
                    upserted += 1
                else:
                    inserted += 1
            else:
                log.warning(f"写入失败 {pid}: {result}")
        except Exception as e:
            log.warning(f"写入异常 {pid}: {e}")

    return inserted, upserted


# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 50)
    log.info("漫展数据同步任务开始")
    log.info("=" * 50)

    shows = fetch_all()

    if not shows:
        log.error("抓取失败，无数据")
        sys.exit(1)

    log.info(f"抓取完成：{len(shows)} 条漫展")

    inserted, upserted = write_to_cloud(shows)
    log.info(f"云端写入完成：新增 {inserted} 条，更新 {upserted} 条")

    # 输出摘要（供通知用）
    summary = f"✅ 漫展同步完成！本周新增 {inserted} 条，更新 {upserted} 条，共 {len(shows)} 条漫展数据已更新到云数据库。"
    print("\n" + summary)

    # 同时保存本地备份
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "crawler")
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, "exhibitions_latest.json")
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump({"updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "totalCount": len(shows), "exhibitions": shows}, f, ensure_ascii=False, indent=2)
    log.info(f"本地备份已保存: {backup_file}")
