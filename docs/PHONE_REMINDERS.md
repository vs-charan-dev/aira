# Phone reminders with Twilio

AIRA can save a timed reminder and call one personal phone number when due.
For upgraded accounts, the call says “Hi, this is AIRA” followed by the saved
reminder, then hangs up. Trial accounts ring using Twilio's text-to-speech demo
template and play demo audio instead of the reminder text.
This first version is a spoken notification; it does not support a conversation
over the telephone and does not record the call.

## Set up and rehearse

1. Launch AIRA and open **More → Settings → Phone reminders**.
2. Enter your Twilio **Account SID**, **Auth Token**, voice-capable calling
   number, and your receiving phone number. Use full international format
   (`+` and country code). The calling number must be authorized by Twilio.
3. Save the calling setup. The Auth Token is never returned to the browser or
   voice model. Settings are encrypted with Windows DPAPI in
   `data/secrets/twilio.dpapi`, for the Windows account running the backend.
4. Under **Try a reminder**, leave the delay at one minute and choose
   **Schedule phone call**. This schedules a real call and can use Twilio credit.
5. Leave the backend terminal running, keep the computer awake and online,
   and answer your phone. Watch the status under Settings or **Tasks → Phone
   reminders**. Check Twilio Console Voice logs if the call fails.
6. Rehearse a spoken command: **“Call me in one minute to head out.”**
   Stop the voice session after AIRA confirms; the reminder remains active.
7. For the demo say **“Call me in five minutes to remind me to head out”** or
   **“Call me at 9:05 PM to head out.”** Confirm AIRA reports the intended time.

The local scheduler uses IST (`Asia/Kolkata`, UTC+05:30), independently of the
Windows host timezone. AIRA fetches the actual current clock before handling a
spoken clock-time request. It should clarify ambiguous AM/PM or dates. A time
without a date means today; a past time is rejected instead of silently scheduling
tomorrow. Relative delays range from ten seconds to seven days. The manual form
uses whole minutes. No phone number can be supplied through a voice tool;
all reminders use the receiving number saved in Settings when scheduled.

## Twilio account requirements

- AIRA checks the account type before each dispatch. New trial accounts reject
  inline `Twiml` and extra call parameters, even `Record=false`, with an HTTP 400
  parameter-access error. For trials AIRA sends only `To`, `From` and the supported
  Twilio text-to-speech template `Url`. This rings with demo audio. Upgrade for the
  saved reminder to be spoken; AIRA detects the upgrade automatically.
- A trial account restricts recipients and geography. Verify the receiving
  number and test the exact account before the demo.
- Enable the intended destination in Twilio **Voice Geographic Permissions**
  and ensure the account has sufficient credit.
- For calls into India, use a non-Indian calling number. Your phone will display
  that international caller ID.
- These settings are separate from the Gemini key. Gemini is used for spoken
  command interpretation; Twilio reads the saved message over the telephone.
  This does not use the selected Gemini conversation voice.

Official references: [Call resource](https://www.twilio.com/docs/voice/api/call-resource),
[Voice trial](https://www.twilio.com/docs/usage/trials/try-out-voice),
[India Voice guidelines](https://www.twilio.com/en-us/guidelines/in/voice).

## Scheduling and failure behavior

- Reminders are stored in `data/db/call-reminders.sqlite3`, separate from
  desktop/coding jobs. Disconnecting the browser, ending Gemini Live, or
  closing the companion does not cancel a saved phone reminder.
- The backend checks due reminders approximately every two seconds. It asks
  Twilio to call when due; carrier/queue delay means ringing can start later.
- Pending reminders survive backend restarts. A reminder overdue by up to two
  minutes can still dispatch. Older reminders become **missed**, without a
  surprise late call. AIRA cannot call while the computer/backend is off.
- SQLite atomically claims each reminder before contacting Twilio. Browser
  submission IDs and actual Gemini function-call IDs deduplicate retries.
  A reminder left **dispatching** after a crash becomes **uncertain**, never
  automatically replays. A timeout/lost API response can mean Twilio accepted
  the call: check Voice logs before requesting another. There are no automatic
  redials for busy/no-answer/rejected calls either.
- **Cancel reminder** cancels a pending call. After dispatch, cancellation is
  rejected and does not claim to undo the phone call. Removing calling setup
  deletes the credentials and cancels pending reminders; dispatched calls
  may continue. Ordinary “stop conversation” and desktop “stop all tasks” do
  not cancel independent phone reminders; explicitly ask to cancel the reminder.
- Upgraded accounts receive inline TwiML; trials use a Twilio-hosted template.
  Neither requires a tunnel or public inbound endpoint. The backend polls known
  Call SIDs for status and records whether demo audio was used. **Completed** describes
  the call lifecycle; it does not prove a person heard the reminder (voicemail
  can answer too).
- Rejections include the HTTP status and Twilio's diagnosis, with account IDs,
  credentials and phone numbers redacted. An account lookup failure prevents a
  call request. AIRA never retries a POST to switch call modes.
- Changing the receiving number affects future reminders. Existing reminders
  keep their original recipient. Changing the account/calling number stops
  pending reminders from dispatching with a different account; create new
  reminders with the new setup.

## Validation

Offline checks with fake Twilio requests, isolated local storage and fake time:

```powershell
Set-Location E:\Havetobuild\AIRA\backend
..\.venv\Scripts\python.exe -m unittest tests.test_call_reminders -v
Set-Location E:\Havetobuild\AIRA\frontend
npm.cmd run build
```

Tests cover scheduling, IST/date parsing, early/due/missed behavior, atomic
claims, cancellation, restart persistence, crash/timeout duplicate prevention,
recipient binding, encrypted credentials, HTTP payload/TwiML escaping,
authentication and origin checks. Real phone delivery and Gemini interpreting
the demo command require a configured account and device rehearsal.
