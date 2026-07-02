# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, sys

TOKEN = '103_036xO8SHeaTetnLcZxxxxxxxxxxxxx'  # placeholder
CLOUD_ENV = 'dev-1grdm6tp754371fa'

def load_token():
    with open(r'D:\coser_helper\.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('WECHAT_ACCESS_TOKEN='):
                return line.split('=', 1)[1].strip()
    return None

def call_api(url, payload):
    token = load_token()
    full_url = url.replace('{TOKEN}', token)
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(full_url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {'errcode': -1, 'errmsg': str(e)}

# 1. 查询现有数据量
query_payload = {
    "env": CLOUD_ENV,
    "query": "db.collection('exhibitions').count()"
}
result = call_api(
    'https://api.weixin.qq.com/tcb/databasequery?access_token={TOKEN}',
    query_payload
)
print('=== exhibitions 集合统计 ===')
print(json.dumps(result, ensure_ascii=False))

# 2. 查询最近3条数据
list_payload = {
    "env": CLOUD_ENV,
    "query": "db.collection('exhibitions').limit(3).field({projectId:true,name:true,city:true,province:true}).get()"
}
result2 = call_api(
    'https://api.weixin.qq.com/tcb/databasequery?access_token={TOKEN}',
    list_payload
)
print('\n=== 最近3条数据 ===')
for item in result2.get('data', []):
    print(json.loads(item) if isinstance(item, str) else item)

# 3. 尝试查询所有城市列表
print('\n=== 云开发环境信息 ===')
info = call_api(
    'https://api.weixin.qq.com/tcb/envinfo?access_token={TOKEN}',
    {"env": CLOUD_ENV, "limit": 1}
)
print(json.dumps(info, ensure_ascii=False))
