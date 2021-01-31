# -*- coding: utf-8 -*-
import requests
import xml.etree.ElementTree as Et
import re
import base64
import datetime as dt
import time
import subprocess
from . import functions as f


class Radiko:
    RADIKO_URL = "http://radiko.jp/v3/program/today/JP13.xml"

    def __init__(self):
        tmpconf = f.load_configurations()
        # TODO: 正規表現で https:// から始まる文字列ならに変更する
        if tmpconf["all"].get("Radiko_URL") is not None:
            self.RADIKO_URL = tmpconf["all"].get("Radiko_URL")
        self.reload_program()
        self.isKeyword = False

    def reload_program(self):
        print("radiko - reload_program")
        res = requests.get(self.RADIKO_URL)
        res.encoding = "utf-8"
        self.program_radiko = Et.fromstring(res.text)
        self.reload_date = dt.date.today()
        print("radilp programs : " + str(self.program_radiko))
        print("radiko reload_date : " + str(self.reload_date))

    def change_keywords(self, keywords):
        if bool(keywords):
            print("radiko - change_keywords")
            word = "("
            for keyword in keywords:
                word += keyword
                word += "|"
            word = word.rstrip("|")
            word += ")"
            self.isKeyword = True
            self.keyword = re.compile(word)
        else:
            print("radiko - not_change_keywords")
            self.isKeyword = False

    def delete_keywords(self):
        print("radiko - delete_keywords")
        self.change_keywords([])

    def search(self):
        # print("radiko - search")
        if self.isKeyword is False:
            return []
        res = []
        for station in self.program_radiko.findall("stations/station"):
            for prog in station.findall("./progs/prog"):
                ck = False
                title = prog.find("title").text
                info = prog.find("info").text
                desc = prog.find("desc").text
                pfm = prog.find("pfm").text
                if self.keyword.search(title):
                    ck = True
                if (ck is False) and (info is not None):
                    if self.keyword.search(info):
                        ck = True
                if (ck is False) and (pfm is not None):
                    if self.keyword.search(pfm):
                        ck = True
                if (ck is False) and (desc is not None):
                    if self.keyword.search(desc):
                        ck = True
                if ck:
                    pfm = pfm or ""
                    print("radiko - rec_target : station:{0}, title:{1}, ft:{2}, to:{3}, ftl:{4}, tol:{5}, dur:{6}, pfm:{7}, info:{8}".format(
                        station.get("id"), title, prog.get("ft"), prog.get("to"), prog.get("ftl"), prog.get("tol"), prog.get("dur"), "", info))
                    res.append({
                        "station": station.get("id"),
                        "title": title.replace(" ", "_"),
                        "ft": prog.get("ft"),
                        "DT_ft": dt.datetime.strptime(prog.get("ft"), "%Y%m%d%H%M%S"),
                        "to": prog.get("to"),
                        "ftl": prog.get("ftl"),
                        "tol": prog.get("tol"),
                        "dur": int(prog.get("dur")),
                        # "pfm": pfm.replace("，", ","),
                        "pfm": "",
                        "info": info
                    })
        if bool(res):
            print("radiko - search result : " + str(res))
            return res
        else:
            print("radiko - search result : nothing")
            return []

    @staticmethod
    def authorization():
        print("radiko - authorization")
        auth1_url = "https://radiko.jp/v2/api/auth1"
        auth2_url = "https://radiko.jp/v2/api/auth2"
        auth_key = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
        headers = {
            "X-Radiko-App": "pc_html5",
            "X-Radiko-App-Version": "0.0.1",
            "X-Radiko-User": "sunyryr",
            "X-Radiko-Device": "pc"
        }
        res = requests.get(auth1_url, headers=headers)
        if res.status_code != 200:
            print("Authorization1 Failed")
            return None
        # print(res.headers)
        auth_token = res.headers["X-RADIKO-AUTHTOKEN"]
        key_length = int(res.headers["X-Radiko-KeyLength"])
        key_offset = int(res.headers["X-Radiko-KeyOffset"])
        tmp_authkey = auth_key[key_offset:key_offset+key_length]
        auth_key = base64.b64encode(tmp_authkey.encode('utf-8')).decode('utf-8')
        # print(AuthKey)
        headers = {
            "X-Radiko-AuthToken": auth_token,
            "X-Radiko-PartialKey": auth_key,
            "X-Radiko-User": "sunyryr",
            "X-Radiko-Device": "pc"
        }
        res = requests.get(auth2_url, headers=headers)
        if res.status_code == 200:
            # print("----------")
            # print(res.headers)
            return auth_token
        else:
            print("Authorization2 Failed")
            return None

    def rec(self, data):
        print("radiko - rec")
        program_data = data[0]
        wait_start_time = data[1]
        auth_token = data[2]
        saveroot = data[3]
        # タイトルを表示
        print(program_data["title"])
        # ディレクトリの作成
        dir_name = f.delete_serial(program_data["title"].replace(" ", "_").replace("　", "_"))
        dir_path = saveroot + "/" + dir_name
        f.create_save_dir(dir_path)
        # 保存先パスの作成
        file_path = dir_path + "/" + program_data["title"]+"_"+program_data["ft"][:12]
        file_path = file_path.replace(" ", "_")

        f.LINE.nortification_start_rec_agqr(program_data["title"])

        # stream urlの取得
        url = 'http://f-radiko.smartstream.ne.jp/%s/_definst_/simul-stream.stream/playlist.m3u8' \
              % program_data["station"]
        m3u8 = self.gen_temp_chunk_m3u8_url(url, auth_token)
        # コマンドの実行
        time.sleep(wait_start_time)
        # 音声エンコードについての参考
        # http://tech.ckme.co.jp/ffmpeg_acodec.shtml
        cwd = ('ffmpeg -loglevel error -headers "X-Radiko-AuthToken: %s" -i "%s" -acodec libmp3lame "%s.mp3"'
               % (auth_token, m3u8, file_path))
        p1 = subprocess.Popen(cwd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, shell=True)
        print("Radiko: sleep for " + str(program_data["dur"]-10))
        time.sleep(program_data["dur"]-10)
        print("STOP SIGNAL......")
        p1.communicate(b'q')
        time.sleep(10)
        if f.is_recording_succeeded(file_path):
            f.LINE.recording_successful_toline(program_data["title"])
            # dropbox
            # fs = open(file_path+".m4a", "rb")
            # f.DropBox.upload(program_data["title"], program_data["ft"], fs.read())
            # fs.close()

            # rclone
            # f.Rclone.upload(dir_path, dir_name)
            # object storage
            # url = f.Swift.upload_file(filePath=file_path + ".m4a")
            #f.Mysql.insert(
            #    title=program_data["title"].replace(" ", "_"),
            #    pfm=program_data["pfm"],
            #    timestamp=program_data["ft"],
            #    station=program_data["station"],
            #    uri=url,
            #    info=program_data["info"]
            #)
            #if f.Swift.hadInit:
            #    cmd = 'rm "%s"' % (file_path + ".m4a")
            #    subprocess.run(cmd, shell=True)
        else:
            f.LINE.recording_failure_toline(program_data["title"])

    @staticmethod
    def gen_temp_chunk_m3u8_url(url, auth_token):
        print("radiko - gen_temp_chuck_m3u8_url")
        headers = {
            "X-Radiko-AuthToken": auth_token,
        }
        res = requests.get(url, headers=headers)
        res.encoding = "utf-8"
        if res.status_code != 200:
            print(res.text)
        body = res.text
        lines = re.findall('^https?://.+m3u8$', body, flags=re.MULTILINE)
        if len(lines) <= 0:
            print("Radiko: no m3u8 in the response.")
            return ""
        return lines[0]
