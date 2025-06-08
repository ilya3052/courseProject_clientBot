@echo off
chcp 65001

python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt

mkdir logs

echo @echo off > run.bat
echo chcp 65001 >> run.bat
echo call .venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat
echo pause >> run.bat

if not exist ".env" (
    copy .env.example .env 2>nul
    echo Заполните .env файл своими значениями!
)

del .env.example
timeout /t 1 >nul  && del "%~f0"