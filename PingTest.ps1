# Run with: powershell.exe -NoProfile -File .\PingTest.ps1
# Stop early with Ctrl+C. Each result is saved immediately.
[CmdletBinding()]
param(
    [string]$Target = '192.168.1.36',
    [string]$OutputFolder = 'E:\PingTest',
    [ValidateRange(1, 86400)]
    [double]$IntervalSeconds = 5,
    [ValidateRange(0.0001, 168)]
    [double]$DurationHours = 2,
    [ValidateRange(1, 60000)]
    [int]$TimeoutMilliseconds = 4000
)

$ErrorActionPreference = 'Stop'
if ($TimeoutMilliseconds -ge ($IntervalSeconds * 1000)) {
    throw 'TimeoutMilliseconds must be less than IntervalSeconds.'
}

New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
$fileName = 'ping_{0}_{1}_{2}.csv' -f ($Target -replace '[^a-zA-Z0-9.-]', '_'), (Get-Date -Format 'yyyyMMdd_HHmmss_fff'), $PID
$csvPath = Join-Path $OutputFolder $fileName
$ping = New-Object System.Net.NetworkInformation.Ping
$payload = New-Object byte[] 32
$options = New-Object System.Net.NetworkInformation.PingOptions
$options.Ttl = 128
$options.DontFragment = $true
$clock = [System.Diagnostics.Stopwatch]::StartNew()
$durationSeconds = $DurationHours * 3600
$nextSeconds = 0.0
$sent = 0
$received = 0
$previousRtt = $null

Write-Host "Logging $Target to $csvPath"
Write-Host "Duration: $DurationHours hours; interval: $IntervalSeconds seconds. Press Ctrl+C to stop."

try {
    while ($clock.Elapsed.TotalSeconds -lt $durationSeconds) {
        $waitSeconds = $nextSeconds - $clock.Elapsed.TotalSeconds
        if ($waitSeconds -gt 0) {
            Start-Sleep -Milliseconds ([int][Math]::Ceiling($waitSeconds * 1000))
        }
        if ($clock.Elapsed.TotalSeconds -ge $durationSeconds) { break }

        $timestamp = [DateTimeOffset]::Now
        $elapsedSeconds = $clock.Elapsed.TotalSeconds
        $sent++
        $rtt = $null
        $rttChange = $null
        $replyAddress = ''
        $replyTtl = $null
        $replyBytes = $null
        $errorText = ''
        try {
            $reply = $ping.Send($Target, $TimeoutMilliseconds, $payload, $options)
            $status = $reply.Status.ToString()
            if ($reply.Status -eq [System.Net.NetworkInformation.IPStatus]::Success) {
                $received++
                $rtt = $reply.RoundtripTime
                $replyAddress = $reply.Address.ToString()
                $replyBytes = $reply.Buffer.Length
                if ($null -ne $reply.Options) { $replyTtl = $reply.Options.Ttl }
                if ($null -ne $previousRtt) {
                    $rttChange = [Math]::Abs($rtt - $previousRtt)
                }
                $previousRtt = $rtt
            }
        }
        catch {
            $status = 'Error'
            $errorText = $_.Exception.GetBaseException().Message
        }

        [pscustomobject][ordered]@{
            Timestamp = $timestamp.ToString('o')
            Date = $timestamp.ToString('yyyy-MM-dd')
            Time = $timestamp.ToString('HH:mm:ss.fff')
            ElapsedSeconds = [Math]::Round($elapsedSeconds, 3)
            Sequence = $sent
            Target = $Target
            Status = $status
            RoundTripTimeMs = $rtt
            RttChangeSinceLastSuccessMs = $rttChange
            ReplyAddress = $replyAddress
            ReplyTtl = $replyTtl
            RequestPayloadBytes = $payload.Length
            ReplyPayloadBytes = $replyBytes
            TimeoutMs = $TimeoutMilliseconds
            TotalSent = $sent
            TotalReceived = $received
            TotalLost = $sent - $received
            CumulativeLossPercent = [Math]::Round(100.0 * ($sent - $received) / $sent, 3)
            Error = $errorText
        } | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Append -Encoding UTF8

        Write-Host ('{0}  #{1}  {2}  RTT={3} ms  Lost={4}/{1}' -f $timestamp.ToString('HH:mm:ss'), $sent, $status, $rtt, ($sent - $received))

        # Keep a steady schedule; skip missed slots instead of sending a burst.
        $nextSeconds += $IntervalSeconds
        while ($nextSeconds -lt $clock.Elapsed.TotalSeconds) {
            $nextSeconds += $IntervalSeconds
        }
    }
}
finally {
    $clock.Stop()
    $ping.Dispose()
    Write-Host "CSV saved to: $csvPath"
}
