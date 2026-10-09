# Telegram completion messages

AIRA can message your private Telegram chat after a coding fix succeeds with
passing, nonempty local tests and changed files. For Invoice Studio, the visible
VS Code terminal verification must also succeed. An already-correct invoice,
investigation, failed repair, cancelled job, or opening an application does not
send a completion message.

## One-time setup

1. Open the official [@BotFather](https://t.me/BotFather) in Telegram. Send
   `/newbot`, choose a name and username, and copy the token it gives you. Use a
   new bot dedicated to AIRA. See [Telegram's bot tutorial](https://core.telegram.org/bots/tutorial).
2. Double-click **Configure-Telegram.cmd** in `E:\Havetobuild\AIRA`.
3. Paste the token into the hidden terminal prompt. No characters appear while
   entering it. Setup checks the bot identity using Telegram's API.
4. Open the bot username shown by setup in Telegram and send `/start` from your
   own account. Then press Enter in the setup terminal. Setup discovers a private
   chat; if it finds multiple private chats, select your own chat ID.
5. Quit AIRA from its tray, then launch **Restart-AIRA-Desktop.cmd** to load the
   saved configuration. Existing conversations disconnect during restart.

Setup sends no Telegram message. It privately updates only these three values
in the existing root `.env`, preserving other configuration:

```dotenv
AIRA_TELEGRAM_ENABLED=true
AIRA_TELEGRAM_BOT_TOKEN=<your BotFather token>
AIRA_TELEGRAM_CHAT_ID=<your numeric private chat ID>
```

Do not paste the token into a chat, screenshot, commit, or demo recording. It is
stored locally in `.env`, which is ignored by Git. To disable messages, set
`AIRA_TELEGRAM_ENABLED=false` and restart AIRA.

## Rehearsal

Create the known invoice fault with **Create-Fault.cmd**, show the invoice demo,
and ask AIRA to fix the invoice error. After repair, all eight tests and the
return to the localhost Chrome tab succeed, you should receive:

```text
AIRA
Invoice error fixed and verified.
All 8 selected tests passed.
Task: <task ID> · run 1
```

The message deliberately contains the result and task ID, without project paths,
code, raw test logs, prompts or API credentials. General verified coding fixes
use the same completion hook. Each completed run gets at most one send attempt;
reopening AIRA or viewing the task board does not replay old messages. Enabling
Telegram does not send notifications for historical fixes.

## Delivery status and limitations

The task board shows Telegram delivery separately from the code result:

| Status | Meaning |
| --- | --- |
| Sending notification | The completed fix is saved; delivery is in progress. |
| Message sent | Telegram returned a message ID for your configured chat. This does not prove you read it. |
| Delivery unconfirmed | A timeout, connection error or unexpected response prevented confirmation. Inspect Telegram; AIRA does not automatically retry. |
| Message rejected | Telegram returned a rejection. Check the token and chat configuration. |
| Run Configure-Telegram.cmd | Notifications were enabled with incomplete or invalid configuration. |

A failed Telegram delivery does not change the fix result, rerun tests or repeat
code changes. The spoken completion happens before the bounded Telegram attempt.
An interrupted send can still reach Telegram; AIRA marks it unconfirmed and does
not resend. A backend crash during sending can leave the historical status at
"sending"; it is not retried after restart.

The backend must be running and have internet access when the fix finishes.
There is no public server, webhook, cloud database, new Gemini call or additional
LLM key. Telegram receives the short notification through its HTTPS
[`sendMessage` API](https://core.telegram.org/bots/api#sendmessage). Setup uses
[`getUpdates`](https://core.telegram.org/bots/api#getupdates) once to discover
your private chat; an existing bot served by another polling process or webhook
may not work with this helper. Use a new bot in that case.

Offline regression checks mock Telegram and use isolated data on E:. A real bot
setup and one real repair notification remain the user's acceptance check.
