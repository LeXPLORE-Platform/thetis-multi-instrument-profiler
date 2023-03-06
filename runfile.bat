@echo off
setlocal enabledelayedexpansion

:: Ensure correct location
cd "C:\Users\Seatronic 1147\Documents\Data_Lexplore\git\thetis-profiler"

:: Ensure repo up to date
:: git stash
:: git pull

:: Load input parameters
call "scripts\input_batch.bat"

:: Backup files
md %backup%
md %failed%
robocopy %in% %backup% /NFL /NDL /NJH /NJS /nc /ns /np

:: Process .PPD and .ACD files
for %%a in (%in%"\*.PPD", %in%"\*.ACD", %in%"\*.PPB", %in%"\*.ACS") do (

	:: Copy file to JMAFileProcessor folder
	move "%%a" %processor%

	:: Move to JMAFileProcessor Directory
	cd %processor%

	:: Process file
	java -jar JMAFileProcessor.jar %processor%\%%~nxa

	:: Check that output files were created
	SET cnt=0
	for %%c in (*.txt) do SET /a cnt+=1
	if !cnt!==0 (move %%~nxa %failed%) else (del %%~nxa)
)

:: Process thetis data
%pythonenv% %script% --directory %processor%

:: Move all output files to Level 0 folder
for %%b in (%processor%"\*.txt") do (
    move "%%b" %Level0%
)


:: Remove debugging files
del %in%"\*.DBG"

:: Move remaining files to failed
move %in%"\*" %failed%

:: Move back summaries file
move %failed%"\*.xml" %in%

:: Push changes to remote repository
git add --all
git commit -m "Auto upload"
git push
