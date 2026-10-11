$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -X utf8 launch.py @args
