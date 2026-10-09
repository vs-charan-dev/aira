"""Interactive local configuration. Reads bot setup only; sends no messages."""
import getpass
import re
from app.config import ROOT,settings
from app.services.telegram_notification import bot_request,valid_token,valid_chat

def save_config(path,token,chat):
    if not valid_token(token) or not valid_chat(chat): raise ValueError('Invalid Telegram configuration.')
    if path.is_symlink(): raise ValueError('Linked environment files are not supported.')
    original=path.read_text(encoding='utf-8') if path.exists() else ''
    text=original
    for key,value in {'AIRA_TELEGRAM_ENABLED':'true','AIRA_TELEGRAM_BOT_TOKEN':token,'AIRA_TELEGRAM_CHAT_ID':chat}.items():
        pattern=r'^'+key+r'=[^\r\n]*'
        if re.search(pattern,text,re.M):text=re.sub(pattern,lambda match:key+'='+value,text,flags=re.M)
        else:text=text.rstrip('\r\n')+'\n'+key+'='+value+'\n'
    temporary=path.with_name('.env.telegram.tmp')
    if temporary.exists():raise ValueError('A temporary environment file exists. Inspect it before retrying.')
    if path.exists() and path.read_text(encoding='utf-8')!=original:raise ValueError('Environment changed. Retry setup.')
    created=False
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            created=True
            stream.write(text)
        temporary.replace(path)
    finally:
        if created and temporary.exists():temporary.unlink()

def main():
    print('Create a new bot with @BotFather /newbot first. Your token is entered privately here.')
    token=getpass.getpass('Bot token (hidden; Enter keeps the configured token): ').strip() or settings.aira_telegram_bot_token.get_secret_value().strip()
    if not valid_token(token):raise ValueError('Enter a valid BotFather token.')
    me=bot_request(token,'getMe',{})
    if not isinstance(me,dict) or me.get('is_bot') is not True:raise ValueError('This token was not verified as a bot.')
    username=me.get('username','')
    if not isinstance(username,str) or not re.fullmatch(r'[A-Za-z0-9_]{5,32}',username):raise ValueError('Bot username unavailable.')
    print('Open @'+username+' in Telegram and send /start from your own account.')
    input('Press Enter here after sending /start: ')
    updates=bot_request(token,'getUpdates',{'limit':100,'timeout':0})
    chats=sorted({str(message['chat']['id']) for update in updates if isinstance(update,dict)
        for message in [update.get('message')] if isinstance(message,dict) and message.get('chat',{}).get('type')=='private'
        and type(message['chat'].get('id')) is int and message['chat']['id']>0}) if isinstance(updates,list) else []
    if not chats:raise ValueError('No private chat found. Send /start to the bot, then rerun setup. Use a new bot without another polling service/webhook.')
    if len(chats)==1:chat=chats[0]
    else:
        print('Private chat IDs seen by this bot: '+', '.join(chats))
        chat=input('Enter your own chat ID from this list: ').strip()
        if chat not in chats:raise ValueError('Choose one of the observed private chat IDs.')
    save_config(ROOT/'.env',token,chat)
    print('Telegram notifications configured. Restart AIRA to load them. No message was sent by setup.')

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nSetup cancelled.')
    except Exception:
        # API/HTTP exception text can contain the secret URL. Never echo it.
        print('Setup could not complete. Check the token, internet connection and /start message; see docs/TELEGRAM.md.')
        raise SystemExit(1)
