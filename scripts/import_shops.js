// 在微信开发者工具 Console 中执行以下代码批量导入店铺数据
// 请确保云开发已连接且 shops 集合已创建
// 操作：打开开发者工具 → 点击 Console 标签 → 粘贴以下代码 → 回车

const db = wx.cloud.database();

const shops = [
  { name: "三分妄想", desc: "三分妄想 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i3/85470570/O1CN01DMBJS11G56mpC24h8_!!85470570.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop61937106.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 1 },
  { name: "初兽猫Cosplay", desc: "初兽猫Cosplay - 优质C服店铺", coverUrl: "https://gw.alicdn.com/tfs//9c/ce/TB1_vIESXXXXXbuapXXSutbFXXX.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop33922676.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 2 },
  { name: "米悠塔cos服饰", desc: "米悠塔cos服饰 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i1/3367393061/O1CN01PlmUbM1YTz7FwPVV8_!!3367393061-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop462960039.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 3 },
  { name: "万花筒cos服", desc: "万花筒cos服 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i4/2201296224018/O1CN01mokhVp1fYI8FeHVZq_!!2201296224018-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop169565770.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 4 },
  { name: "喵屋小铺", desc: "喵屋小铺 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i1/77937585/O1CN01yCT30225tyzdyqN8H_!!77937585-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop35126367.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 5 },
  { name: "次元宇宙cos服", desc: "次元宇宙cos服 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i3/3408565042/O1CN01CEqCf21n7I2YMRsZC_!!3408565042.png_320x320q75.jpg_.webp", taobaoUrl: "https://shop221546415.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 6 },
  { name: "雾都动漫店", desc: "雾都动漫店 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i4/98340989/O1CN01ODTDu41JB0oa6In2e~crop,60,54,425,425~_!!98340989.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop35785629.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 7 },
  { name: "Uwowo悠窝窝", desc: "Uwowo悠窝窝 - 优质C服店铺", coverUrl: "https://gw.alicdn.com/tfs//42/ff/TB1VjapewDqK1RjSZSySuuxEVXa.jpg", taobaoUrl: "", wechat: "", location: "", tags: ["C服"], status: 1, order: 8 },
  { name: "次元电台 cosplayfm", desc: "次元电台 cosplayfm - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i2/6000000003666/O1CN01dxbUhj1cx4g1BX6ym_!!6000000003666-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop111045008.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 9 },
  { name: "漫囧cos店", desc: "漫囧cos店 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i2/2784021642/O1CN01BMNE1W1O05FStYKoM_!!2784021642-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop148523923.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 10 },
  { name: "糖霜COS服", desc: "糖霜COS服 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i2/2200684062490/O1CN01nAHXRa1UGT6jEqPdR_!!2200684062490-0-shopmanager.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop316833944.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 11 },
  { name: "次元依品牌店", desc: "次元依品牌店 - 优质C服店铺", coverUrl: "https://img.alicdn.com/imgextra/i3/1062141336/O1CN01KdsgZE1Ljw6K2C8TZ_!!1062141336.png_320x320q75.jpg_.webp", taobaoUrl: "https://shop379347003.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 12 },
  { name: "ICOS二次元品牌店", desc: "ICOS二次元品牌店 - 优质C服店铺", coverUrl: "https://gw.alicdn.com/tfs//2c/b9/TB11B3meBiE3KVjSZFMSuvQhVXa.jpg_320x320q75.jpg_.webp", taobaoUrl: "https://shop131200896.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 13 },
  { name: "三里空山COSPLAY工作室", desc: "三里空山COSPLAY工作室 - 优质C服店铺", coverUrl: "https://gw.alicdn.com/tfs//ed/be/TB1X3Pena6qK1RjSZFmwu00PFXa.png_320x320q75.jpg_.webp", taobaoUrl: "https://shop151000219.taobao.com/", wechat: "", location: "", tags: ["C服"], status: 1, order: 14 }
];

async function importShops() {
  let success = 0, fail = 0;
  for (const shop of shops) {
    try {
      await db.collection("shops").add({ data: { ...shop, createTime: db.serverDate() } });
      console.log("✅ 已添加:", shop.name);
      success++;
    } catch (err) {
      console.error("❌ 失败:", shop.name, err);
      fail++;
    }
  }
  console.log(`🎉 导入完成！成功 ${success} 家，失败 ${fail} 家`);
}

importShops();
