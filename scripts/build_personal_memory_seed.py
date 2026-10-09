"""One-time, deterministic conversion of the supplied brief into atomic records.

The original brief stays in docs/memory-palace/seed-source.txt for provenance.
Runtime imports the reviewed JSON, never reparses or overwrites corrections.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS = [
    ('IDENTITY', 'Lobby / Identity', '🏛', 'museum'),
    ('ACADEMIC', 'Academic Room', '🎓', 'library'),
    ('CAREER', 'Career Room', '💼', 'studio'),
    ('PROJECT', 'Projects Lab', '🧪', 'lab'),
    ('DECISION', 'Decision Vault', '🔐', 'workshop'),
    ('PERSON', 'People Room', '👥', 'gallery'),
    ('DEV', 'Developer Workspace', '💻', 'workshop'),
    ('PREFERENCE', 'AI Preferences', '🤖', 'dojo'),
    ('GOAL', 'Goals Observatory', '🎯', 'observatory'),
    ('COMMITMENT', 'Commitments Room', '📅', 'library'),
    ('ROUTINE', 'Routine Room', '⏰', 'garden'),
    ('PERSONAL', 'Personal Room', '❤️', 'sanctuary'),
    ('PLACE', 'Places Room', '🗺', 'gallery'),
    ('LEARNING', 'Learning Library', '📚', 'library'),
    ('TIMELINE', 'Timeline Archive', '📜', 'museum'),
]

# A list of (short title, independent assertion), indexed by source Q number.
# Combined answers are split without inventing facts or dates.
SPLITS = {
 'IDENTITY': {
  8: [('Introversion', 'I am introverted, but friendly.'), ('Laptop time', 'I spend a large amount of my time working in front of my laptop.')],
  9: [('Software development', 'I love developing software.'), ('Building projects', 'I love building different projects.'), ('Technology experiments', 'I love experimenting with technology.'), ('AI passion', 'AI is a field that I am particularly passionate about.')],
  10: [('Health priority', 'Improve my health and get into good physical shape.'), ('Income priority', 'Increase my streams of income.'), ('Impactful projects priority', 'Build ambitious projects that can create meaningful impact, especially in AI.')],
  11: [('Friendly personality', 'I am friendly.'), ('Technical curiosity', 'I am technically curious.'), ('Ambition', 'I am ambitious.'), ('Explanation preference', 'I prefer concepts to be explained clearly, visually and using simple words.')],
  12: [('Health value', 'I fundamentally value health.'), ('Wealth value', 'I fundamentally value wealth.'), ('Relationships value', 'I fundamentally value relationships.')],
 },
 'ACADEMIC': {3: [('Learning DevOps', 'I am studying DevOps even though it is not part of my core Mechanical Engineering curriculum.'), ('Learning MLOps', 'I am studying MLOps even though it is not part of my core Mechanical Engineering curriculum.')],
  7: [('Internship placement', 'I have already secured an internship.'), ('Current internship', 'I am currently working at my internship.')],
  10: [('Current CGPA', 'My CGPA is approximately 8.8.'), ('CGPA goal', 'I want to increase my CGPA to above 9.0 in the next six months.')],
 },
 'CAREER': {5: [('Hands-on career stage', 'Initially I expect to be hands-on and do technical work.'), ('Leadership career direction', 'As I gain experience, I want to move toward leadership, management and consulting roles where I can manage projects and people in addition to understanding the technical work.')],
  6: [('Learning DevOps production', 'I am currently learning how DevOps works.'), ('Production integration', 'I am learning how applications and AI systems are integrated into real production environments.')],
 },
 'PERSON': {1: [(name, f'{name} is among my close friends and best friends.') for name in ['Hrullekh', 'Ronith', 'Sheetal']],
  2: [(name, f'{name} is a close friend whom I consider like a sister, and has also been my teammate in different hackathons.') for name in ['Srinitya', 'Priya']],
  5: [('School physics teacher', 'My physics teacher during school had a significant impact on me.'), ('School mathematics teacher', 'My mathematics teacher during school had a significant impact on me.')],
  6: [('Rajwant Sir', 'Rajwant Sir had a significant influence on me during my 11th and 12th studies.'), ('Sachin Sir', 'Sachin Sir had a significant influence on me during my 11th and 12th studies.')],
 },
 'DEV': {2: [('Laptop processor', 'My laptop has an Intel Core i5 11th-generation processor.'), ('Laptop RAM', 'My laptop has 16 GB RAM.'), ('Laptop storage', 'My laptop has a 512 GB SSD.'), ('Laptop graphics', 'My laptop has Intel Iris Xe graphics.')],
  5: [('PowerShell', 'I use PowerShell for terminal/project workflows.'), ('Herder', 'I use a tool I refer to as Herder for terminal/project workflows.')],
  6: [('Claude Code', 'Claude Code is one of my preferred coding agents.'), ('Codex', 'Codex is one of my preferred coding agents.')],
  8: [('Gamma', 'I sometimes use Gamma for content generation.'), ('Google / Gemini media', "I sometimes use Google's/Gemini's tools for image, video and music generation.")],
  11: [('Product-driven development', 'I like product-driven development depending on the project.'), ('Test-driven development', 'I like test-driven development depending on the project.')],
 },
 'GOAL': {2: [('Delhi trip this month', 'I have a Delhi trip planned this month.'), ('Projects this month', 'I have approximately two projects that I want to complete this month.')],
  4: [('Stable income streams', 'I want stable income streams.'), ('Financial independence', 'I would like to reach a point where my financial stability does not depend completely on having a traditional job.')],
  6: [('Health priority', 'Improve my health and physical condition.'), ('Income priority', 'Increase my income streams.'), ('AI project priority', 'Build ambitious and impactful AI projects.')],
 },
 'COMMITMENT': {1: [('Hackathons this week', 'Two hackathons are planned for this week.'), ('Delhi trip', 'A Delhi trip is planned.'), ('Projects this month', 'Two projects need to be completed this month.'), ('Unfinished major project', 'A final-year major project remains unfinished.'), ('November examinations', 'Important academic examinations are expected during November; exact dates are not stored.')],},
 'ROUTINE': {3: [('Sleep and productivity', 'Good sleep helps create my most productive days.'), ('Light food and productivity', 'Relatively light food helps create my most productive days.'), ('Night phone use', 'Avoiding excessive phone use at night helps create my most productive days.')],},
 'PERSONAL': {8: [('Introverted but friendly', 'I am introverted but friendly.'), ('Ambition', 'I am ambitious.'), ('Technology interest', 'I am highly interested in technology.'), ('Humour', 'I enjoy humour.')],
  9: [('Health value', 'I fundamentally value health.'), ('Wealth value', 'I fundamentally value wealth.'), ('Relationships value', 'I fundamentally value relationships.')],},
 'LEARNING': {1: [('Learning DevOps', 'I am currently learning DevOps.'), ('Learning MLOps', 'I am currently learning MLOps.')],
  3: [('Teach DevOps', 'I would like AIRA to help teach me DevOps.'), ('Teach MLOps', 'I would like AIRA to help teach me MLOps.')],},
}

TITLES = {
 'IDENTITY': ['Full name', 'Nickname', 'Home', 'Student', 'College', 'Branch', 'Final year', 'Personality', 'Passions', 'Priorities', 'Personality and explanations', 'Values'],
 'ACADEMIC': ['Degree', 'SPJP', 'Outside curriculum', 'November examinations', 'GATE preparation', 'Government examinations', 'Placement', 'Aptitude and CRT', 'Unfinished major project', 'CGPA', 'CGPA motivation'],
 'CAREER': ['Target role', 'Preferred work city', 'Target package', 'Entire career coding', 'Career evolution', 'Production learning', 'Target companies', 'Career uncertainty', 'Software salary opportunities', 'Multidisciplinary potential'],
 'PROJECT': ['AIRA', 'AI observability', 'PLC automation', 'Australian grocery product', 'Self-improving agent', 'LLM weights unchanged', 'Proudest project', 'Confidential projects', 'Confidentiality principle'],
 'DECISION': ['Cloudflare Workers decision', 'Hackathon lesson', 'Presentation mistake', 'Product vs presentation belief', 'Team presentations', 'Complexity lesson', 'Simple architectures', 'Why simplicity matters', 'Overengineering reminder'],
 'PERSON': ['Closest friends', 'Friends like sisters', 'Vinay', 'Client count', 'School teachers', '11th and 12th teachers', 'Virat Kohli inspiration', 'Why Kohli inspires me', 'AI problem solving'],
 'DEV': ['Operating system', 'Laptop specifications', 'Phone', 'Editor', 'Terminal tools', 'Coding agents', 'ChatGPT', 'Content tools', 'GitHub', 'Remote development', 'Development approaches', 'Languages and frameworks unknown'],
 'PREFERENCE': ['Technical explanations', 'One step at a time', 'Answer length', 'AI frustrations', 'Low-risk autonomy', 'Autonomous code changes', 'High-impact permission', 'Permission examples', 'Autonomy principle'],
 'GOAL': ['Hackathons this week', 'This month', 'Passive income product', 'Financial objective', 'One-year plans', 'Current priorities', 'AI career goal', 'Salary goal', 'Work city'],
 'COMMITMENT': ['Current commitments', 'Exact dates unknown'],
 'ROUTINE': ['Wake-up time', 'Sleep time', 'Productivity conditions', 'Afternoon slump', 'Productive hours', 'College hours', 'Sunday free', 'Saturday holidays', 'Social interruptions', 'Replanning support'],
 'PERSONAL': ['Friendly conversation', 'Long explanations', 'Humour style', 'Challenge unrealistic plans', 'Motivation', 'Procrastination', 'Flexible planning', 'Personality', 'Values'],
 'PLACE': ['College city', 'Work city', 'Delhi visits', 'Upcoming Delhi trip', 'Microsoft event', 'Agra association'],
 'LEARNING': ['Currently learning', 'Production databases', 'Teaching support', 'Learning format', 'Visual learner'],
}

# Repeated assertions share a key so future corrections can surface conflicts.
def semantic_key(title, text, prefix, index):
    pairs = {
        'work_city': ['preferred work city', 'work city'],
        'salary_target': ['target package', 'salary goal'],
        'cgpa_current': ['current cgpa'],
        'health_priority': ['health priority'],
        'income_priority': ['income priority'],
        'delhi_trip': ['delhi trip', 'delhi trip this month', 'upcoming delhi trip'],
        'hackathons_week': ['hackathons this week'],
        'projects_month': ['projects this month'],
        'major_project': ['unfinished major project'],
        'exams_november': ['november examinations'],
    }
    for key, titles in pairs.items():
        if title.lower() in titles:
            return key
    return f'{prefix.lower()}_{index:03}'

def main():
    source = ROOT / 'docs/memory-palace/seed-source.txt'
    content = source.read_text(encoding='utf-8-sig')
    headings = list(re.finditer(r'^ROOM (\d+) .+$', content, re.M))
    rooms, memories = [], []
    for i, (prefix, name, icon, style) in enumerate(ROOMS):
        start = headings[i].end()
        end = headings[i + 1].start() if i + 1 < len(headings) else content.index('MEMORY RETRIEVAL RULES')
        body = content[start:end]
        room_id = 'room_personal_' + prefix.lower()
        rooms.append(dict(id=room_id, prefix=prefix, name=name, icon=icon, style=style))
        items = []
        if prefix == 'TIMELINE':
            for match in re.finditer(r'^- (.+)$', body, re.M):
                items.append((match.group(1).strip().rstrip('.'), match.group(1).strip(), 'Timeline event', start + match.start()))
        else:
            qa = list(re.finditer(r'^Q: (.+)\r?\nA:([\s\S]*?)(?=\r?\nQ:|\r?\n={10,}|\Z)', body, re.M))
            for qi, match in enumerate(qa, 1):
                question, answer = match.group(1).strip(), match.group(2).strip()
                answer = re.sub(r'\s+', ' ', answer)
                parts = SPLITS.get(prefix, {}).get(qi, [(TITLES[prefix][qi - 1], answer)])
                for title, assertion in parts:
                    items.append((title, assertion, question, start + match.start()))
        for n, (title, assertion, question, offset) in enumerate(items, 1):
            # The question supplies essential meaning for short answers like "No".
            if assertion in {'No.', 'Yes.', 'Hyderabad.', 'Windows.', 'VS Code.', 'Motorola Edge 60 Fusion.', 'Virat Kohli.', 'Friendly.', 'Sunday.', 'Around 7:00 AM.', 'Around 11:00 PM.'}:
                assertion = f'{question} {assertion}'
            unknown = ('not yet been specifically stored' in assertion or title == 'Exact dates unknown')
            tags = sorted(set([prefix.lower(), *re.findall(r'[a-z0-9]+', title.lower())]))
            if prefix == 'DECISION' and n >= 2:
                tags += ['hackathons', 'lessons', 'presentation']
            if (prefix == 'LEARNING' and title in {'Learning format', 'Visual learner'}) or (prefix == 'PREFERENCE' and title in {'Technical explanations', 'Answer length', 'One step at a time'}):
                tags += ['technical', 'concepts', 'explanations']
            memories.append(dict(
                id=f'{prefix}-{n:03}', room=name, room_id=room_id,
                category=prefix.lower(), title=title, memory=assertion,
                importance='high' if prefix in {'CAREER', 'DECISION', 'GOAL', 'COMMITMENT', 'PREFERENCE'} else 'medium',
                tags=sorted(set(tags)),
                source='Memory Palace Seed', source_file='docs/memory-palace/seed-source.txt',
                source_line=content[:offset].count('\n') + 1, question=question,
                created_at='2026-10-09', as_of='2026-10-09', event_date=None,
                kind='unknown' if unknown else 'fact', status='active', version=1, history=[],
                semantic_key=semantic_key(title, assertion, prefix, n),
            ))
    target = ROOT / 'backend/app/data/personal_memory_seed.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(schema_version=1, rooms=rooms, memories=memories), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(rooms)} rooms, {len(memories)} atomic memories -> {target}')

if __name__ == '__main__':
    main()
