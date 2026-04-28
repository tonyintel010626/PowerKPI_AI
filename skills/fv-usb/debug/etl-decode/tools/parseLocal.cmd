@echo off
setlocal

call parseEtl.cmd TbtLog.etl "%cd%" detailed

endlocal
