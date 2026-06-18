@echo off
setlocal enabledelayedexpansion

:: ===== Configure paths (edit these) =====
set "input=C:\path\to\input"
set "processor=C:\path\to\JMAFileProcessor"
set "output=C:\path\to\output"
set "failed=C:\path\to\failed"

:: Make sure the output and failed folders exist
if not exist "%output%" mkdir "%output%"
if not exist "%failed%" mkdir "%failed%"

:: Copy all input files to the JMAFileProcessor folder
copy "%input%\*.PPD" "%processor%" >nul 2>&1
copy "%input%\*.ACD" "%processor%" >nul 2>&1
copy "%input%\*.PPB" "%processor%" >nul 2>&1
copy "%input%\*.ACS" "%processor%" >nul 2>&1

:: Move to the JMAFileProcessor directory
cd /d "%processor%"

:: Process each copied file
for %%a in (*.PPD *.ACD *.PPB *.ACS) do (

	:: Process file
	java -jar JMAFileProcessor.jar "%processor%\%%~nxa"

	:: Check that output files were created
	set cnt=0
	for %%c in (*.txt) do set /a cnt+=1
	if !cnt!==0 (
		:: Nothing produced - move the input file to the failed folder
		move "%%~nxa" "%failed%"
	) else (
		:: Move the produced outputs to the output folder, then drop the input
		move "*.txt" "%output%" >nul
		del "%%~nxa"
	)
)
