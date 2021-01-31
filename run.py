#!/usr/bin/python3
# -*- coding: utf-8 -*-
from lib import radiko, agqr, functions as f
from multiprocessing import Process
import signal
import time
import datetime as dt

saveroot = ""
T_BASELINE = dt.timedelta(seconds=60)
T_ZERO = dt.timedelta()
keywords = []
config = None


def main_radiko():
    global keywords
    print("call main_radiko")
    radiko_entity = radiko.Radiko()
    if len(keywords) == 0:
        keywords = f.load_configurations()["all"]["keywords"]
    radiko_entity.change_keywords(keywords)
    radiko_data = radiko_entity.search()
    while True:
        now = dt.datetime.now()
        # print(radiko_data)
        if bool(radiko_data):
            for data in radiko_data:
                tmp_time = data["DT_ft"] - now
                if tmp_time < T_ZERO:
                    # 放送開始が過去なら対象から除去
                    radiko_data.remove(data)
                elif tmp_time < T_BASELINE:
                    # 放送開始まで60秒を切っている
                    auth_token = radiko_entity.authorization()
                    p = Process(target=radiko_entity.rec,
                                args=([data, tmp_time.total_seconds(), auth_token, saveroot],))
                    p.start()
                    radiko_data.remove(data)
        # radikoは毎日6時に番組表を更新する
        if now.hour == 6 and now.minute <= 5 and radiko_entity.reload_date != dt.date.today():
            radiko_entity.reload_program()
            radiko_data = radiko_entity.search()
        time.sleep(60)


def main_agqr():
    global keywords
    print("call main_agqr")
    agqr_entity = agqr.Agqr()
    if len(keywords) == 0:
        keywords = f.load_configurations()["all"]["keywords"]
    agqr_entity.change_keywords(keywords)
    agqr_data = agqr_entity.search()
    # print(agqr_data)
    while True:
        now = dt.datetime.now()
        if bool(agqr_data):
            for data in agqr_data:
                tmp_time = data["DT_ft"] - now
                if tmp_time < T_ZERO:
                    # 放送開始が過去なら対象から除去
                    agqr_data.remove(data)
                elif tmp_time < T_BASELINE:
                    # 放送開始まで60秒を切っている
                    p = Process(target=agqr_entity.rec, args=([data, tmp_time.total_seconds(), saveroot],))
                    p.start() # 録音プロセス開始
                    agqr_data.remove(data)
        # A&Gは毎日0時に番組表を更新
        if now.hour == 0 and now.minute <= 5 and agqr_entity.reload_date != dt.date.today():
            agqr_entity.reload_program()
            agqr_data = agqr_entity.search()
        time.sleep(60)


# def main_onsen_hibiki():
#     Onsen = onsen.onsen(keywords, saveroot)
#     Hibiki = hibiki.hibiki(keywords, saveroot)
#     while(True):
#         now = dt.datetime.now()
#         if (now.hour == 7 and now.minute <= 5 and Onsen.reload_date != dt.date.today()):
#             titles = Onsen.rec()
#             titles.extend(Hibiki.rec())
#             if (bool(titles)):
#                 f.LINE.recording_successful_toline("、".join(titles))
#             else:
#                 print("in onsen, hibiki. there aren't new title.")
#         time.sleep(300)

def signal_handler(signal, handler):
    for i in ps:
        i.terminate()
    exit(0)


if __name__ == "__main__":
    config = f.load_configurations()
    saveroot = f.create_save_dir_path(config["all"]["savedir"])
    print("saveroot : " + saveroot)
    keywords = config["all"]["keywords"]
    print("config keywords :" + str(keywords))
    # ps = [
    #     Process(target=main_radiko),
    #     Process(target=main_agqr),
    #     Process(target=main_onsen_hibiki)
    # ]
    ps = [
        Process(target=main_radiko),
        Process(target=main_agqr)
    ]
    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    for i in ps:
        i.start()
    while True:
        time.sleep(1)
