@echo off
setlocal

REM 必要ならこれをON（まずはOFFで試してOK）
REM set PYTHONPATH=.

.\.venv\Scripts\python.exe -m src.simulation %*

endlocal
