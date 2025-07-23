@echo off 
chcp 65001 
echo Для завершения программы нажмите Ctrl+C 
call .venv\Scripts\activate.bat 
python main.py 
pause 
