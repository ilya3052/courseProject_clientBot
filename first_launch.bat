@echo on

python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo @echo on > run.bat
echo call .venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat

del "%~f0"