# -*- coding: utf-8 -*-
import os
import json
import requests
from requests import Response

# import dropbox
import mysql.connector as sql
from bs4 import BeautifulSoup as Bs
import hashlib
import subprocess
import time
import re
from typing import Dict, List, Union, Generator, Optional


def load_configurations() -> Dict:
    root = __file__.replace("/lib/functions.py", "")
    if root == __file__:
        root = root.replace("functions.py", "..")
    path = root + "/conf/config.json"
    if os.path.isfile(path) is False:
        print("config file is not found")
        exit(1)
    with open(path, "r", encoding="utf-8") as f:
        tmp = json.load(f)
        return tmp


def create_save_dir_path(path: str = "") -> str:
    root = __file__.replace("/lib/functions.py", "")
    if root == __file__:
        root = root.replace("functions.py", ".")
    if path == "":
        path = root + "/savefile"
    else:
        path = path
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def create_save_dir(path: str) -> None:
    if os.path.isdir(path) is False:
        os.makedirs(path)


def is_recording_succeeded(path: str) -> bool:
    m4a_path: str = path + ".mp3"
    if os.path.isfile(m4a_path):
        size: int = os.path.getsize(m4a_path)
        return True if size >= 1024 else False
    return False


class LineController:
    # hadInit: bool = False

    def __init__(self):
        tmpconf: Dict = load_configurations()
        if (tmpconf.get("all") is None) or (tmpconf["all"].get("line_token") is None):
            return
        self.token = tmpconf["all"]["line_token"]
        self.hadInit = True

    def recording_successful_toline(self, title: str) -> None:
        if not self.hadInit:
            return
        headers: Dict = {"Authorization": f"Bearer {self.token}"}
        payload: Dict = {"message": f"\n {title} の録音に成功しました"}
        requests.post(
            url="https://notify-api.line.me/api/notify", headers=headers, data=payload
        )

    def recording_failure_toline(self, title: str, result_code: int = None) -> None:
        if not self.hadInit:
            return
        headers = {"Authorization": "Bearer %s" % self.token}
        if result_code is None:
            payload: Dict = {"message": f"\n {title} の録音に失敗しました"}
        else:
            payload: Dict = {
                "message": f"\n {title} の録音に失敗しました。code: {str(result_code)}"
            }
        requests.post(
            url="https://notify-api.line.me/api/notify", headers=headers, data=payload
        )

    def nortification_start_rec_agqr(self, title: str) -> None:
        if not self.hadInit:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"message": f"\n {title} の録音を開始します..."}
        requests.post(
            url="https://notify-api.line.me/api/notify", headers=headers, data=payload
        )


LINE = LineController()


def did_record_prog(file_path: str, title: str, timestamp) -> bool:
    if Mysql.hadInit:
        # DBあり
        res = Mysql.check(title, timestamp)
        return len(res) != 0
    else:
        # DBなし
        return os.path.exists(file_path)


# delete serial number words
def delete_serial(path: str) -> str:
    drm_regex = re.compile(r"（.*?）|［.*?］|第.*?回")
    rtn_message = drm_regex.sub("", path)
    return rtn_message.rstrip("_ ")


class DBXController:
    # hadInit = False

    def __init__(self):
        tmpconf: Dict = load_configurations()
        if (tmpconf.get("all") is None) or (tmpconf["all"].get("dbx_token") is None):
            return
        self.dbx = dropbox.Dropbox(tmpconf["all"]["dbx_token"])
        self.dbx.users_get_current_account()
        res = self.dbx.files_list_folder("")
        db_list = [d.name for d in res.entries]
        if "radio" not in db_list:
            self.dbx.files_create_folder("radio")
        self.hadInit = True

    def upload(self, title: str, ft: str, file_data) -> None:
        if not self.hadInit:
            return
        dbx_path: str = f"/radio/{title}"
        # dropboxにフォルダを作成する
        res = self.dbx.files_list_folder("/radio")
        db_list: List = [d.name for d in res.entries]
        if title not in db_list:
            self.dbx.files_create_folder(dbx_path)
        dbx_path += f"/{title}_{ft[:12]}.m4a"
        self.dbx.files_upload(file_data, dbx_path)

    def upload_onsen(self, title: str, count: str, file_data):
        if not self.hadInit:
            return
        dbx_path: str = f"/radio/{title}"
        # dropboxにフォルダを作成する
        res = self.dbx.files_list_folder("/radio")
        db_list: List = [d.name for d in res.entries]
        if title not in db_list:
            self.dbx.files_create_folder(dbx_path)
        dbx_path += f"/{title}#{count}.mp3"
        self.dbx.files_upload(file_data, dbx_path)


DropBox = DBXController()


# rclone


class RcloneController:
    # hadInit = False

    def __init__(self):
        tmpconf: Dict = load_configurations()
        if tmpconf.get("rclone") is None:
            return
        self.rcl = tmpconf["rclone"]["method"]
        self.outdir = tmpconf["rclone"]["outdir"]
        self.rclop = tmpconf["rclone"]["options"]

        self.hadInit: bool = True

    def upload(self, save_dir, dist_dir) -> None:
        if not self.hadInit:
            return
        time.sleep(5)
        cwd = f"rclone {self.rcl} {save_dir} {self.outdir}{dist_dir}/ {self.rclop}"
        p1 = subprocess.run(cwd.split())


Rclone = RcloneController()


class SwiftController:
    # hadInit = False
    containerName: str = "radio"

    def __init__(self):
        tmpconf: Dict = load_configurations()
        if (tmpconf is None) or (tmpconf.get("swift") is None):
            return
        self.username = tmpconf["swift"]["username"]
        self.password = tmpconf["swift"]["password"]
        self.tenantid = tmpconf["swift"]["tenantid"]
        self.identityUrl = tmpconf["swift"]["identityUrl"]
        self.objectStorageUrl = tmpconf["swift"]["objectStorageUrl"]
        # エラーがあったら初期化中止
        if not self.renewal_token():
            # print("Swift login failed")
            return
        self.hadInit: bool = True
        self.create_container(self.containerName)

    def renewal_token(self) -> bool:
        data: Dict = {
            "auth": {
                "passwordCredentials": {
                    "username": self.username,
                    "password": self.password,
                },
                "tenantId": self.tenantid,
            }
        }
        try:
            res: Response = requests.post(
                url=f"{self.identityUrl}/tokens",
                headers={"Content-Type": "application/json"},
                data=json.dumps(data),
            )
            res_data: Dict = json.loads(res.text)
            if "error" in res_data.keys():
                return False
            self.token: str = res_data["access"]["token"]["id"]
        except (HTTPError, Exception):
            return False
        return True

    def create_container(
        self, container_name: str, is_renew_token: bool = False
    ) -> bool:
        if not self.hadInit:
            return False
        if is_renew_token:
            self.renewal_token()
        res: Response = requests.put(
            url=f"{self.objectStorageUrl}/{container_name}",
            headers={
                "Content-Type": "application/json",
                "X-Auth-Token": self.token,
                "X-Container-Read": ".r:*",
            },
        )
        if res.status_code in [200, 201, 204]:
            return True
        else:
            return False

    def upload_file(self, file_path: str) -> Union[bool, str]:
        if not self.hadInit:
            return False
        self.renewal_token()
        # create mp3 file
        root, ext = os.path.splitext(file_path)
        if ext == ".m4a":
            cmd = f'ffmpeg -loglevel error -i "{file_path}" -vn -c:a libmp3lame "{file_path.replace(".m4a", ".mp3")}"'
            subprocess.run(cmd, shell=True)
        # stationとdatetimeでObjectNameを生成する。md5
        hash_path: str = hashlib.md5(file_path.encode("utf-8")).hexdigest()
        path: str = f"{self.objectStorageUrl}/{self.containerName}/{hash_path}"
        with open(file_path.replace(".m4a", ".mp3"), "rb") as f
            res: Response = requests.put(
                url=path,
                headers={
                    "Content-Type": "audio/mpeg",  # ここで送信するデータ形式を決める
                    "X-Auth-Token": self.token,
                },
                data=f.read(),
            )
            print(res.status_code)
        # delete mp3 file
        if ext == ".m4a":
            cmd = 'rm "%s"' % (file_path.replace(".m4a", ".mp3"))
            subprocess.run(cmd, shell=True)
        return path


Swift = SwiftController()


class DBController:
    # hadInit = False

    def __init__(self):
        tmpconf: Dict = load_configurations()
        if tmpconf.get("mysql") is None:
            return
        try:
            self.conn = sql.connect(
                host=tmpconf["mysql"]["hostname"] or "localhost",
                port=tmpconf["mysql"]["port"] or "3306",
                user=tmpconf["mysql"]["username"],
                password=tmpconf["mysql"]["password"],
                database=tmpconf["mysql"]["database"],
            )
            self.hadInit = True
        except:
            # print("Mysql login failed")
            pass

    def insert(self, title: str, pfm: str, timestamp: str, station: str, uri: str, info: str = "") -> None:
        if not self.hadInit:
            return
        self.conn.ping(reconnect=True)
        cur = self.conn.cursor()
        quey_str = "INSERT INTO Programs (`title`, `pfm`, `rec-timestamp`, `station`, `uri`, `info`) VALUES ( %s, %s, %s, %s, %s, %s)"
        cur.execute(
            quey_str, (title, pfm, timestamp, station, uri, self.escape_html(info))
        )
        self.conn.commit()
        cur.close()

    @staticmethod
    def escape_html(html) -> str:
        soup = Bs(html, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        # get text
        text: str = soup.get_text()
        # break into lines and remove leading and trailing space on each
        lines: Generator = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks: Generator = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text

    def check(self, title, timestamp) -> Optional[List]:
        if not self.hadInit:
            return
        self.conn.ping(reconnect=True)
        cur = self.conn.cursor()
        query_str = (
            "SELECT id FROM Programs WHERE `title` = %s AND `rec-timestamp` = %s"
        )
        cur.execute(query_str, (title, timestamp))
        return cur.fetchall()


Mysql = DBController()

if __name__ == "__main__":
    s = "hoge"  # "<img src='http://www.joqr.co.jp/qr_img/detail/20150928195756.jpg' style=\"max-width: 200px;\"> <br /><br /><br />番組メールアドレス：<br /><a href=\"mailto:mar@joqr.net\">mar@joqr.net</a><br />番組Webページ：<br /><a href=\"http://portal.million-arthurs.com/kairi/radio/\">http://portal.million-arthurs.com/kairi/radio/</a><br /><br />パーソナリティは盗賊アーサーを演じる『佐倉綾音』さん、歌姫アーサーを演じる『内田真礼』さん、そして期待の新人『鈴木亜理沙』さん。<br />番組では「乖離性ミリオンアーサー」の最新情報はもちろん、パーソナリティのここだけでしか聞けない話、ゲストをお招きしてのトークなど盛りだくさんでお送りします。<br /><br />初回＆2回目放送は内田真礼さん＆鈴木亜理沙さんのコンビで、その次の2週を佐倉綾音さん＆鈴木亜理沙さんのコンビで2週毎にパーソナリティがローテーションしていく今までにない斬新な番組となります。<br /><br /><br />twitterハッシュタグは「<a href=\"http://twitter.com/search?q=%23millionradio\">#millionradio</a>」<br />twitterアカウントは「<a href=\"http://twitter.com/joqrpr\">@joqrpr</a>」<br />facebookページは「<a href='http://www.facebook.com/1134joqr'>http://www.facebook.com/1134joqr</a>」<br />"
    # print(Mysql.escape_html(s))
# test.insert()
