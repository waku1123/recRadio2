# -*- coding: utf-8 -*-
import requests
import json
import re
import datetime as dt
import time
import subprocess
import os
from . import functions as f


class Agqr:
    AGQR_URL = "https://agqr.sun-yryr.com/api/today"

    def __init__(self):
        self.reload_program()
        self.isKeyword = False

    def reload_program(self):
        print("AGQR - reload_program")
        res = requests.get(self.AGQR_URL)
        res.encoding = "utf-8"
        self.program_agqr = json.loads(res.text)
        self.reload_date = dt.date.today()
        print("AGQR programs : " + str(self.program_agqr))
        print("AGQR update reload_date : " + str(self.reload_date))

    def change_keywords(self, keywords):
        if bool(keywords):
            print("AGQR - change_keywords")
            word = "("
            for keyword in keywords:
                # print(keyword)
                word += keyword
                word += "|"
            word = word.rstrip("|")  # 文字列末尾の「|」を除去
            word += ")"
            self.isKeyword = True
            self.keyword = re.compile(word)
            # print(self.keyword)
        else:
            print("AGQR - not_change_keywords")
            self.isKeyword = False

    def delete_keywords(self):
        print("AGQR - delete_keywords")
        self.change_keywords([])

    def search(self):
        # print("AGQR - search")
        if self.isKeyword is False:
            return []
        res = []
        for prog in self.program_agqr:
            ck = False
            title = prog.get("title")
            pfm = prog.get("pfm")
            if self.keyword.search(title):
                ck = True
            if (ck is False) and (pfm is not None):
                if self.keyword.search(pfm):
                    ck = True
            if ck:
                print("AGQR - rec_target : " + str(prog))
                res.append({
                    "title": title.replace(" ", "_"),
                    "ft": prog.get("ft"),
                    "DT_ft": dt.datetime.strptime(prog.get("ft"), "%Y%m%d%H%M"),
                    "to": prog.get("to"),
                    "dur": int(prog.get("dur")),
                    "pfm": pfm
                })
        if bool(res):
            print("AGQR - search result : " + str(res))
            return res
        else:
            print("AGQR - search result : nothing")
            return []

    @staticmethod
    def get_valid_url():
        for i in range(1, 10, 1):
            ret_url = 'https://fms2.uniqueradio.jp/agqr10/aandg{0}.m3u8'.format(str(i))
            print(ret_url)
            res = requests.get(ret_url, verify=False)
            if res.status_code == 200:
                print("valid url :" + ret_url)
                return ret_url

    @staticmethod
    def rec(data):
        print("AGQR - rec")
        program_data = data[0]
        wait_start_time = data[1]
        saveroot = data[2]

        dir_name = program_data["title"].replace(" ", "_")
        dir_path = saveroot + "/" + dir_name
        f.create_save_dir(dir_path)

        file_path = dir_path + "/" + program_data["title"].replace(" ", "_") + "_" + program_data["ft"][:12]

        f.LINE.nortification_start_rec_agqr(program_data["title"])

        # 2020-11-12 A&GのFlash終了のため、rtmpによる録音は不可になった。
        # 新配信方式はHLSになったのでffmpegで直接mp3化する
        # url = 'https://fms2.uniqueradio.jp/agqr10/aandg1.m3u8'
        url = Agqr.get_valid_url()
        duration = str(program_data["dur"] * 60)
        cwd3 = (f'ffmpeg -i {url} -movflags faststart -t {duration} {file_path}.mp3')
        result = subprocess.run(cwd3, shell=True)

        # time.sleep(program_data["dur"] * 60)

        print("AGQR: finished!")
        if result.returncode == 0 and f.is_recording_succeeded(file_path):
            # LINE通知
            f.LINE.recording_successful_toline(title=program_data['title'])
            # メール通知とか

            # rclone
            # f.Rclone.upload(dir_path, dir_name)
            # object storage
            # url = f.Swift.upload_file(filePath=file_path+".mp3")
            # f.Mysql.insert(
            #     title=program_data["title"].replace(" ", "_"),
            #     pfm=program_data["pfm"],
            #     timestamp=program_data["ft"] + "00",
            #     station="AGQR",
            #     uri=url
            # )
            # if f.Swift.hadInit:
            #     cmd = 'rm "%s"' % (file_path + ".mp3")
            #     subprocess.run(cmd, shell=True)
        else:
            f.LINE.recording_failure_toline(title=program_data["title"], result_code=result.returncode)
        # flvファイルは作成しなくなったので、コメントアウトする
        # os.remove(file_path + ".flv")


if __name__ == "__main__":
    agqr = Agqr()
    agqr.reload_program()
    agqr.rec([{"title": "test-program", "dur": 3}, 1, "."])