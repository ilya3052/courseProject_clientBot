@echo on

python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt

mkdir logs

echo @echo on > run.bat
echo call .venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat

if not exist ".env" (
    copy .env.example .env 2>nul || echo Заполните .env на основе .env.example!
)

del "%~f0"