# -*- coding: utf-8 -*-
import requests
from requests import Response
import xml.etree.ElementTree as Et
import re
from re import Pattern
import base64
import datetime as dt
from pathlib import Path
import time
import subprocess
from . import functions as f
from typing import Final, List, Dict, Optional


class Radiko:
    RADIKO_URL: Final[str] = "http://radiko.jp/v3/program/today/JP13.xml"

    def __init__(self):
        tmpconf: Dict = f.load_configurations()
        # TODO: 正規表現で https:// から始まる文字列ならに変更する
        if tmpconf["all"].get("Radiko_URL") is not None:
            self.RADIKO_URL: str = tmpconf["all"].get("Radiko_URL")
        self.reload_program()
        self.isKeyword: bool = False

    def reload_program(self) -> None:
        print("radiko - reload_program")
        res: Response = requests.get(self.RADIKO_URL)
        res.encoding = "utf-8"
        self.program_radiko: Et.Element = Et.fromstring(res.text)
        self.reload_date: dt.date = dt.date.today()
        print("radilp programs : " + str(self.program_radiko))
        print("radiko reload_date : " + str(self.reload_date))

    def change_keywords(self, keywords: List) -> None:
        if bool(keywords):
            print("radiko - change_keywords")
            word: str = "("
            for keyword in keywords:
                word += keyword
                word += "|"
            word = word.rstrip("|")
            word += ")"
            self.isKeyword = True
            self.keyword: Pattern = re.compile(word)
        else:
            print("radiko - not_change_keywords")
            self.isKeyword = False

    def delete_keywords(self) -> None:
        print("radiko - delete_keywords")
        self.change_keywords(list())

    def search(self) -> List:
        # print("radiko - search")
        if self.isKeyword is False:
            return list()
        res: List = list()
        for station in self.program_radiko.findall("stations/station"):
            for prog in station.findall("./progs/prog"):
                ck: bool = False
                title: str = prog.find("title").text
                info: str = prog.find("info").text
                desc: str = prog.find("desc").text
                pfm: str = prog.find("pfm").text
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
                    # pfm = pfm or ""
                    print(
                        f"radiko - rec_target : station:{station.get('id')}, title:{title}, ft:{prog.get('ft')}, to:{prog.get('to')}, ftl:{prog.get('ftl')}, tol:{prog.get('tol')}, dur:{prog.get('dur')}, pfm:{''}, info:{info}"
                    )
                    res.append(
                        {
                            "station": station.get("id"),
                            "title": title.replace(" ", "_"),
                            "ft": prog.get("ft"),
                            "DT_ft": dt.datetime.strptime(
                                prog.get("ft"), "%Y%m%d%H%M%S"
                            ),
                            "to": prog.get("to"),
                            "ftl": prog.get("ftl"),
                            "tol": prog.get("tol"),
                            "dur": int(prog.get("dur")),
                            # "pfm": pfm.replace("，", ","),
                            "pfm": "",
                            "info": info,
                        }
                    )
        if bool(res):
            print("radiko - search result : " + str(res))
            return res
        else:
            print("radiko - search result : nothing")
            return list()

    @staticmethod
    def authorization() -> Optional[str]:
        print("radiko - authorization")
        auth1_url: str = "https://radiko.jp/v2/api/auth1"
        auth2_url: str = "https://radiko.jp/v2/api/auth2"
        auth_key: str = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
        headers: Dict = {
            "X-Radiko-App": "pc_html5",
            "X-Radiko-App-Version": "0.0.1",
            "X-Radiko-User": "sunyryr",
            "X-Radiko-Device": "pc",
        }
        res: Response = requests.get(auth1_url, headers=headers)
        if res.status_code != 200:
            print("Authorization1 Failed")
            return None
        # print(res.headers)
        auth_token: str = res.headers["X-RADIKO-AUTHTOKEN"]
        key_length: int = int(res.headers["X-Radiko-KeyLength"])
        key_offset: int = int(res.headers["X-Radiko-KeyOffset"])
        tmp_authkey: str = auth_key[key_offset : key_offset + key_length]
        auth_key: str = base64.b64encode(tmp_authkey.encode("utf-8")).decode("utf-8")
        # print(AuthKey)
        headers: Dict = {
            "X-Radiko-AuthToken": auth_token,
            "X-Radiko-PartialKey": auth_key,
            "X-Radiko-User": "sunyryr",
            "X-Radiko-Device": "pc",
        }
        res: Response = requests.get(auth2_url, headers=headers)
        if res.status_code == 200:
            # print("----------")
            # print(res.headers)
            return auth_token
        else:
            print("Authorization2 Failed")
            return None

    def rec(self, data: List) -> None:
        print("radiko - rec")
        program_data: Dict = data[0]
        wait_start_time = data[1]
        auth_token: str = data[2]
        saveroot: str = data[3]
        # タイトルを表示
        print(program_data["title"])
        # ディレクトリの作成
        dir_name: str = f.delete_serial(
            program_data["title"].replace(" ", "_").replace("　", "_")
        )
        dir_path: Path = Path(saveroot + "/" + dir_name)
        f.create_save_dir(dir_path)
        # 保存先パスの作成
        file_path: str = str(
            dir_path / program_data["title"] + "_" + program_data["ft"][:12]
        )
        file_path = file_path.replace(" ", "_")

        f.LINE.nortification_start_rec_agqr(program_data["title"])

        # stream urlの取得
        url: str = f"http://f-radiko.smartstream.ne.jp/{program_data['station']}/_definst_/simul-stream.stream/playlist.m3u8"
        m3u8: str = self.gen_temp_chunk_m3u8_url(url, auth_token)
        # コマンドの実行
        time.sleep(wait_start_time)
        # 音声エンコードについての参考
        # http://tech.ckme.co.jp/ffmpeg_acodec.shtml
        cwd = f'ffmpeg -loglevel error -headers "X-Radiko-AuthToken: {auth_token}" -i "{m3u8}" -acodec libmp3lame "{file_path}.mp3"'
        p1 = subprocess.Popen(
            cwd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, shell=True
        )
        print("Radiko: sleep for " + str(program_data["dur"] - 10))
        time.sleep(program_data["dur"] - 10)
        print("STOP SIGNAL......")
        p1.communicate(b"q")
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
            # f.Mysql.insert(
            #    title=program_data["title"].replace(" ", "_"),
            #    pfm=program_data["pfm"],
            #    timestamp=program_data["ft"],
            #    station=program_data["station"],
            #    uri=url,
            #    info=program_data["info"]
            # )
            # if f.Swift.hadInit:
            #    cmd = 'rm "%s"' % (file_path + ".m4a")
            #    subprocess.run(cmd, shell=True)
        else:
            f.LINE.recording_failure_toline(program_data["title"])

    @staticmethod
    def gen_temp_chunk_m3u8_url(url: str, auth_token: str) -> str:
        print("radiko - gen_temp_chuck_m3u8_url")
        headers: Dict = {
            "X-Radiko-AuthToken": auth_token,
        }
        res: Response = requests.get(url, headers=headers)
        res.encoding = "utf-8"
        if res.status_code != 200:
            print(res.text)
        body: str = res.text
        lines: List[str] = re.findall("^https?://.+m3u8$", body, flags=re.MULTILINE)
        if len(lines) <= 0:
            print("Radiko: no m3u8 in the response.")
            return ""
        return lines[0]
