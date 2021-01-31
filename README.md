# How to Setup
1. install "pipenv"
    ```
   $ pip install pipenv --user
   ```
2. install ffmpeg, rtmpdump
    ```
    $ sudo apt install -y ffmpeg rtmpdump
    ```
3. install requirement libralies
    ```
    $ cd recRadio
    $ pipenv install # read from "Pipfile"
   ```
4. generate config.json
    ```
     $ pipenv run python Setup.py
    ```
5. append "Keywords" to config.json
    ```
     $ vim conf/config.json
     > "keywords": []
    ```
   
6. fix rec_radio.service to exec env
    - User : your machine's username.
    - WorkingDirectory : abstoract project path (ex: /User/admin/project/recRadio)
    - ExecStart: the path which '$ which pipenv' + "run start"

7. append systemd
    ```
    $ sudo mv ./rec_radio.service /etc/systemd/system/
    $ sudo systemctl daemon-reload
    $ systemctl enable rec_radio.service
   ```
    
