# Dell Outlet price monitor

Checks the supplied Dell Outlet inventory page every 10 minutes and emails
`gordon@bowser.net` when a listing at exactly **£3,024** appears. It remembers
active matches, so the same listing does not trigger an email every 10 minutes.

## 1. Configure the Hover password in PowerShell

The program already contains Hover's non-secret settings: `mail.hover.com`,
port `465`, SSL/TLS, and username/sender `gordon@bowser.net`. It deliberately
does not store the mailbox password.

The supplied launcher asks for the password before it starts. The password is
visible while it is typed, as requested. After entry, it sends a test email and
starts monitoring only if that succeeds.

To set the password manually instead, enter:

```powershell
$env:SMTP_PASSWORD = Read-Host "Hover email password"
```

The variable lasts for that PowerShell window. Do not put the password in this
README, the Python file, a batch file, or source control.

These values follow Hover's mail-client documentation: use the complete email
address as the username and SMTP on port 465 with SSL/TLS.

## 2. Test one check

From the repository root:

```powershell
.\.venv\Scripts\python.exe ".\Dell Outlet Monitor\dell_outlet_monitor.py" --once --dry-run
```

The first Selenium run may download the matching Chrome driver. Chrome must be
installed. Remove `--dry-run` to test a real alert if a matching listing is
currently present.

## 3. Run continuously

```powershell
& ".\Dell Outlet Monitor\start_monitor.ps1"
```

Keep that process running. For unattended monitoring, create a Windows Task
Scheduler task that starts the command at logon and restarts it after failure.

Useful options:

```text
--once                 check once and exit
--dry-run              never send email or change alert state
--interval 600         polling interval in seconds
--recipient ADDRESS    alert recipient
--price 3024           exact whole-pound target
```

The file `monitor_state.json` is created beside the script after a successful
non-dry-run check. Delete it if you deliberately want the current listing to
trigger another alert.
