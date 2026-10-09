"""Prebuilt Gemini Live voice catalogue. No key or model change is needed.

Source: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/configure-language-voice
Verified 2026-10-07. Keep IDs exact; descriptions are style hints, not guarantees.
"""
DEFAULT_VOICE = 'Aoede'
PREVIEW_TEXT = 'Hi Charan.'
VOICES = tuple({'name': name, 'description': description} for name, description in (
    ('Aoede', 'Breezy'), ('Achernar', 'Soft'), ('Achird', 'Friendly'),
    ('Algenib', 'Gravelly'), ('Algieba', 'Smooth'), ('Alnilam', 'Firm'),
    ('Autonoe', 'Bright'), ('Callirrhoe', 'Easy-going'), ('Charon', 'Informative'),
    ('Despina', 'Smooth'), ('Enceladus', 'Breathy'), ('Erinome', 'Clear'),
    ('Fenrir', 'Excitable'), ('Gacrux', 'Mature'), ('Iapetus', 'Clear'),
    ('Kore', 'Firm'), ('Laomedeia', 'Upbeat'), ('Leda', 'Youthful'),
    ('Orus', 'Firm'), ('Puck', 'Upbeat'), ('Pulcherrima', 'Forward'),
    ('Rasalgethi', 'Informative'), ('Sadachbia', 'Lively'), ('Sadaltager', 'Knowledgeable'),
    ('Schedar', 'Even'), ('Sulafat', 'Warm'), ('Umbriel', 'Easy-going'),
    ('Vindemiatrix', 'Gentle'), ('Zephyr', 'Bright'), ('Zubenelgenubi', 'Casual'),
))
VOICE_NAMES = frozenset(voice['name'] for voice in VOICES)

def validate_voice(name):
    if not isinstance(name, str) or name not in VOICE_NAMES:
        raise ValueError('Choose a voice from the available list.')
    return name
