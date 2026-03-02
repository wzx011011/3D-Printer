@echo off
if [%1] == [] (
	set PWD=%CD%
) else (
	set PWD=%1
)
REM 设置下载URL和目标文件路径
REM Release包从 GitHub Releases 下载（tag: deps-prebuilt-latest）
REM 若需更新预编译包，请触发 .github/workflows/release_deps.yml 工作流
set "url=https://github.com/wzx011011/3D-Printer/releases/download/deps-prebuilt-latest/OrcaDepsLib.zip"
set "zipfile=%PWD%\OrcaDepsLib.zip"
set "unzipdir=%PWD%"
if [%2] == [Debug] (
	REM TODO: Debug预编译包尚未上传至GitHub Releases，暂时仍使用内网服务器
	REM       如需从GitHub获取，请在release_deps.yml中添加Debug构建步骤后更新此URL
	set "url=http://172.20.180.14/soft/OrcaDepsLib_Debug.zip"
	set "zipfile=%PWD%\OrcaDepsLib_Debug.zip"
)
REM 1. download zip file
echo downloading... %zipfile%
powershell -Command "(New-Object Net.WebClient).DownloadFile('%url%', '%zipfile%')"
REM 2. check download result
echo %zipfile%
if not exist "%zipfile%" (
    echo download failed！
    exit /b 1
)

REM 3. mkdir destdir
mkdir "%unzipdir%"

REM 4. unzip
echo unziping...
powershell -Command "Expand-Archive -LiteralPath '%zipfile%' -DestinationPath '%unzipdir%' -Force"

REM 5. check unzip result
if errorlevel 1 (
    echo unzip failed！
    exit /b 1
)
del "%zipfile%"
echo done.
