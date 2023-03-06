SET mypath=%~dp0
start javaw.exe -Xmx1024m -Duser.language=en -Duser.country=US -jar "%mypath%JMAFileProcessor.jar" -config "%mypath%config.xml" %*