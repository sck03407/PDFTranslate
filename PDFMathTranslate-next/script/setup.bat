@echo off
setlocal enabledelayedexpansion

set PYTHON_URL=https://www.python.org/ftp/python/3.13.3/python-3.13.3-embed-amd64.zip
set PIP_URL=https://bootstrap.pypa.io/get-pip.py
set HF_ENDPOINT=https://hf-mirror.com
set PIP_MIRROR=https://mirrors.aliyun.com/pypi/simple

if not exist pdf2zh_dist/python.exe (
    powershell -Command "& {Invoke-WebRequest -Uri !PYTHON_URL! -OutFile python.zip}"
    powershell -Command "& {Expand-Archive -Path python.zip -DestinationPath pdf2zh_dist -Force}"
    del python.zip
    for %%F in (pdf2zh_dist\python*._pth) do echo import site >> "%%F"
)
cd pdf2zh_dist

if not exist Scripts/pip.exe (
    powershell -Command "& {Invoke-WebRequest -Uri !PIP_URL! -OutFile get-pip.py}"
    python get-pip.py
)
path Scripts

pip install --no-warn-script-location --upgrade setuptools -i !PIP_MIRROR!
pip install --no-warn-script-location --upgrade pdf2zh -i !PIP_MIRROR!
pdf2zh -i

pause
