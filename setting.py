qiandao_url = "https://api.live.bilibili.com/sign/doSign"
livezhibo = 'https://api.live.bilibili.com/relation/v1/Feed/getList?_=1541700619773'
ROOM_INIT_URL = 'https://api.live.bilibili.com/room/v1/Room/room_init'
WEBSOCKET_URL = 'wss://broadcastlv.chat.bilibili.com:2245/sub'
header = {
    "authority": "data.bilibili.com",
    "method": "GET",
    "path": "/log/web?0005161540830761927page|1.5.8|346|395443|true|kfb7yf8j-8NtK-4jPD-nrAb-BPM3GPNp9JHr|0|0|https://js.live-play.acgvideo.com/live-js/525575/live_34396410_8521406.flv?wsSecret=8b63de3b49c6949e3215ab4464ff4f07&wsTime=1540833625&trid=3a67fa4f719f44a29b3e3163fe2e608e|60|0",
    "scheme": "https",
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "cookie": '',
    "origin": "https://live.bilibili.com",
    "pragma": "no-cache",
    "referer": "https://live.bilibili.com/1206?visit_id=2wnza6jxepu0",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
}
roomid_name_dict = {}
online = {}
