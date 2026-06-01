$StudyRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
python -X utf8 (Join-Path $StudyRoot "scripts\study_cli.py") @args
exit $LASTEXITCODE
