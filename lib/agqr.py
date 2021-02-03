# -*- coding: utf-8 -*-
import requests
from requests import Response
import json
import re
import datetime as dt
from pathlib import Path
import time
import subprocess
import os
from . import functions as f
from typing import Final, Dict, List


class Agqr:
    AGQR_URL: Final[str] = "https://agqr.sun-yryr.com/api/today"

    def __init__(self):
        self.reload_program()
        self.isKeyword: bool = False

    def reload_program(self) -> None:
        print("AGQR - reload_program")
        res: Response = requests.get(self.AGQR_URL)
        res.encoding = "utf-8"
        self.program_agqr: Dict = json.loads(res.text)
        self.reload_date: dt.date = dt.date.today()
        print(f"AGQR programs : {str(self.program_agqr)}")
        print(f"AGQR update reload_date : {str(self.reload_date)}")

    def change_keywords(self, keywords: List) -> None:
        if bool(keywords):
            print("AGQR - change_keywords")
            word: str = "("
            for keyword in keywords:
                # print(keyword)
                word += keyword
                word += "|"
            word = word.rstrip("|")  # 文字列末尾の「|」を除去
            word += ")"
            self.isKeyword: bool = True
            self.keyword: re.Pattern = re.compile(word)
            # print(self.keyword)
        else:
            print("AGQR - not_change_keywords")
            self.isKeyword = False

    def delete_keywords(self) -> None:
        print("AGQR - delete_keywords")
        self.change_keywords(list())

    def search(self) -> List:
        # print("AGQR - search")
        if self.isKeyword is False:
            return list()
        res: List = list()
        for prog in self.program_agqr:
            ck: bool = False
            title: str = prog.get("title")
            pfm: str = prog.get("pfm")
            if self.keyword.search(title):
                ck = True
            if (ck is False) and (pfm is not None):
                if self.keyword.search(pfm):
                    ck = True
            if ck:
                print(f"AGQR - rec_target : {str(prog)}")
                res.append(
                    {
                        "title": title.replace(" ", "_"),
                        "ft": prog.get("ft"),
                        "DT_ft": dt.datetime.strptime(prog.get("ft"), "%Y%m%d%H%M"),
                        "to": prog.get("to"),
                        "dur": int(prog.get("dur")),
                        "pfm": pfm,
                    }
                )
        if bool(res):
            print(f"AGQR - search result : {str(res)}")
            return res
        else:
            print("AGQR - search result : nothing")
            return list()

    @staticmethod
    def get_valid_url() -> str:
        for i in range(1, 10, 1):
            ret_url = f"https://fms2.uniqueradio.jp/agqr10/aandg{str(i)}.m3u8"
            print(ret_url)
            res: Response = requests.get(ret_url, verify=False)
            if res.status_code == 200:
                print(f"valid url : {ret_url}")
                return ret_url

    @staticmethod
    def rec(data: List):
        print("AGQR - rec")
        program_data: Dict = data[0]
        wait_start_time = data[1]
        saveroot: str = data[2]

        dir_name = program_data["title"].replace(" ", "_")
        dir_path: Path = Path(saveroot) / dir_name
        f.create_save_dir(str(dir_path))

        file_path: Path = (
            dir_path
            / f'{program_data["title"].replace(" ", "_")}_{program_data["ft"][:12]}'
        )

        f.LINE.nortification_start_rec_agqr(program_data["title"])

        # 2020-11-12 A&GのFlash終了のため、rtmpによる録音は不可になった。
        # 新配信方式はHLSになったのでffmpegで直接mp3化する
        # url = 'https://fms2.uniqueradio.jp/agqr10/aandg1.m3u8'
        url = Agqr.get_valid_url()
        duration = str(program_data["dur"] * 60)
        cwd3 = f"ffmpeg -i {url} -movflags faststart -t {duration} {str(file_path)}.mp3"
        result = subprocess.run(cwd3, shell=True)

        # time.sleep(program_data["dur"] * 60)

        print("AGQR: finished!")
        if result.returncode == 0 and f.is_recording_succeeded(str(file_path)):
            # LINE通知
            f.LINE.recording_successful_toline(title=program_data["title"])
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
            f.LINE.recording_failure_toline(
                title=program_data["title"], result_code=result.returncode
            )
        # flvファイルは作成しなくなったので、コメントアウトする
        # os.remove(file_path + ".flv")


if __name__ == "__main__":
    agqr: Agqr = Agqr()
    agqr.reload_program()
    agqr.rec([{"title": "test-program", "dur": 3}, 1, "."])
