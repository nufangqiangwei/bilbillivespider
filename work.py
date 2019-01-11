from asyncio import run_coroutine_threadsafe, new_event_loop, set_event_loop
import sys
import os
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
import time
import schedule
from threading import Thread

from setting import online, header, qiandao_url, livezhibo
from billive import BLiveClient


class Worken(object):
    def __init__(self):
        self.OKDATA = {"code": 0, "msg": "OK", "message": "OK",
                       "data": {"text": "3000用户经验值,2辣条", "specialText": "", "allDays": 31,
                                "hadSignDays": 18, "isBonusDay": 0}}
        self.twodata = {"code": -500, "msg": "今天已签到过", "message": "今天已签到过", "data": []}
        self.baddata = {'message': '请先登录', 'data': [], 'code': -401, 'msg': '请先登录'}
        self.header = header
        self.onlive = {}
        self.file = open("bilbillog.txt", "w")
        self.time_file = open("live_time.txt", "w")
        self.rqfile = open('riqi.txt', 'w')

    def get_data(self, url):
        try:
            return requests.get(url, headers=self.header)
        except Exception as e:
            with open('qqcw.txt', 'w') as file:
                file.write(str(e))
            return 1

    def qiandao(self):
        response = self.get_data(qiandao_url)
        if response == 1:
            return
        data = json.loads(response.text)
        mes = data.get("message", "None")
        if mes == "OK":
            ti = time.strftime("%Y/%m/%d  %H:%M:%S")
            self.rqfile.write(ti + "签到成功" + str(data))
            self.rqfile.flush()
        elif mes == "今天已签到过":
            pass
        elif mes == '请先登录':
            baddats = str(response.request.headers) + response.text
            self.send_mail(baddats)
        else:
            baddats = str(response.request.headers) + response.text
            self.send_mail(baddats)

    def zhibolive(self):
        response = self.get_data(livezhibo)
        if response == 1:
            return
        data = json.loads(response.text)
        if data['code'] == 0:
            lida = self.line_or_noline(data)
            self.shangxiaxian(lida)
        elif data['code'] == 401:
            self.send_mail("掉线了，请更新cookie")
        else:
            sta = "不明原因请看消息" + str(data)
            self.file.write(sta)
            self.file.flush()
            self.send_mail(sta)

    def line_or_noline(self, data):
        interim_dict = {}
        time_dict = {}
        for dit in data['data']['rooms']:
            interim_dict[dit['room_id']] = dit['uname']
            time_dict[dit['room_id']] = dit["live_time"]
        shangxiand = interim_dict.keys() - self.onlive.keys()  # 上线的主播
        xiaxiand = self.onlive.keys() - interim_dict.keys()  # 下线的主播
        self.onlive = interim_dict
        return shangxiand, xiaxiand, time_dict

    def shangxiaxian(self, room_list):
        """
        上线的主播开启一个线程去记录，下线的主播发送退出消息
        消息格式 {房间id：True/False} True代表正在直播False代表以下播
        :param room_list: 开播的房间id [(id,kaiboshijian),[id]]
        :return:
        消息格式 {房间id：True/False} True代表正在直播False代表以下播
        :param room_list: 开播和下播的房间id [(id,kaiboshijian),[id]]
        :return:
        """
        times = room_list[2]
        time_star = time.time()
        try:
            for i in room_list[0]:
                ti1 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_star - times[i]))
                estr = "{}-id{}房间开播时间{}\n".format(self.onlive[i], i, ti1)
                self.time_file.write(estr)
                online[self.onlive[i]] = True
                token = BLiveClient(i, self.onlive[i])
                run_handel(token)
        except Exception as e:
            self.file.write(str(e))
            self.file.write(str(room_list[0]))
            self.file.flush()

        try:
            for i in room_list[1]:
                ti1 = time.strftime("%Y-%m-%d %H:%M:%S")
                estr = '{}房间下播时间{}\n'.format(i, ti1)
                self.time_file.write(estr)
                online[self.onlive[i]] = False  # i是房间的id self.onlive[i]取出up的名字 online[]是将检验退出的值改为false
        except Exception as e:
            self.file.write(str(e))
            self.file.write(str(room_list[1]))
            self.file.flush()

        self.time_file.flush()

    def shchu(self):
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def token(self):
        print(self.shchu())
        # 每天0点签到
        # 0点到八点不查询是否有新开播,其他时间每十分钟查询一次
        schedule.every().day.at("00:00").do(chongqi)
        schedule.every().day.at("00:01").do(self.zhibolive)
        schedule.every().day.at("00:02").do(self.qiandao)
        schedule.every(10).minutes.do(self.zhibolive)
        schedule.every(1).hours.do(chakan, self)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def send_mail(self, text):
        try:
            msg = MIMEText(text, 'plain', 'utf-8')
            msg['From'] = formataddr(["525372869@qq.com", "525372869@qq.com"])
            msg['To'] = formataddr(["b站签到", "407640432@qq.com"])
            msg['Subject'] = Header("b站爬虫", "utf-8")
            server = smtplib.SMTP("smtp.qq.com", 25)
            server.login("525372869@qq.com", "rlfkvgwxmlzqcbab")
            server.sendmail("525372869@qq.com", ["407640432@qq.com", ], msg.as_string())
            server.quit()
        except Exception as e:
            self.file.write(text)
            self.file.write(str(e))
            self.file.flush()

    def __del__(self):
        self.file.close()
        self.time_file.close()
        self.rqfile.close()


def chakan(self):
    with open("online.txt", "a")as fi:
        fi.write(str(online))
        fi.write(str(self.onlive))
        fi.write("\n")


def chongqi():
    python = sys.executable
    os.execl(python, 'python3', 'work.py')


def run_handel(new_room):
    run_coroutine_threadsafe(new_room._message_loop(), new_loop)
    run_coroutine_threadsafe(new_room._heartbeat_loop(), new_loop)
    # new_loop.call_soon_threadsafe(new_room._message_loop())
    # new_loop.call_soon_threadsafe(new_room._heartbeat_loop())


def start_loop(loop):
    set_event_loop(loop)
    loop.run_forever()


if __name__ == '__main__':
    new_loop = new_event_loop()
    TH = Thread(target=start_loop, args=(new_loop,))
    TH.daemon = True
    TH.start()

    q = Worken()
    q.token()
    # q.onlive[1314277] = 'yimeng'
    # q.onlive[4092369] = 'luohan'
    # q.shangxiaxian(({1314277, 4092369}, set(), {4092369: 4061, 1314277: 6048}))

    # q.zhibolive()
