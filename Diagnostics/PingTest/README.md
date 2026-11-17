# Ping test

Run from the PythonScripts repository root:

```powershell
powershell.exe -NoProfile -File .\Diagnostics\PingTest\PingTest.ps1 -Target 192.168.1.36
```

The script logs each ping immediately to CSV. Stop early with Ctrl+C.
The defaults are a 5-second interval and 2-hour duration. New CSVs go to
`D:\Dropbox\Public Documents\UCLAN\MSc Research\Diagnostics\PingTest`.
Use `-Target`, `-OutputFolder`, `-IntervalSeconds`, `-DurationHours` and
`-TimeoutMilliseconds` to change these. Moving the script did not move existing
ping logs or perform any network tests.
