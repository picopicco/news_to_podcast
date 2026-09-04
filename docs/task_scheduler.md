# Windows Task Scheduler setup

`run_pipeline.py` is meant to be run once a day, at 5:00 AM local time,
by Windows Task Scheduler. It loads credentials from `.env` in the repo
root, so no secrets need to be passed on the command line.

## Automated setup

The task was created with:

```powershell
$action = New-ScheduledTaskAction -Execute "<python.exe>" -Argument "run_pipeline.py" -WorkingDirectory "<repo root>"
$trigger = New-ScheduledTaskTrigger -Daily -At 5:00AM
Register-ScheduledTask -TaskName "news_to_podcast" -Action $action -Trigger $trigger -Description "Daily Instapaper -> podcast pipeline"
```

## Requirements

- The PC must be powered on (not asleep/hibernating) at 5:00 AM for the
  task to run. Windows Task Scheduler has a "wake the computer to run
  this task" option under the trigger's advanced settings if needed.
- `.env` must exist in the repo root with all required values filled in
  (see `config.example.env`).

## Checking / managing the task

```powershell
Get-ScheduledTask -TaskName "news_to_podcast"
Get-ScheduledTaskInfo -TaskName "news_to_podcast"   # last/next run time, last result
Start-ScheduledTask -TaskName "news_to_podcast"     # run it now, manually
Unregister-ScheduledTask -TaskName "news_to_podcast" -Confirm:$false  # remove it
```

Task Scheduler doesn't capture stdout/stderr by default. To debug a
failed run, run `python run_pipeline.py` directly from a terminal in the
repo root.
