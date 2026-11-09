# ============================================================
# helpers.py  -  chhoto chhoto kaj (date, naam, rong)
# ============================================================
import os
from datetime import date, datetime

# Avatar circle er rong (Stitch er color)
AVATAR_COLORS = [
    'bg-primary text-on-primary',
    'bg-secondary text-on-secondary',
    'bg-tertiary text-on-tertiary',
    'bg-primary-container text-on-primary',
    'bg-tertiary-container text-on-tertiary',
]


# 'Maimuna Akter' -> 'Maimuna'   ('Dr. Aris Thorne' -> 'Aris')
def first_name(name):
    words = name.replace('Dr. ', '').split()
    return words[0] if words else name


# 'Maimuna Akter' -> 'MA'
def initials(name):
    words = name.replace('Dr. ', '').split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper()


# user id onujayi ekta fixed rong
def avatar(user_id):
    return AVATAR_COLORS[user_id % len(AVATAR_COLORS)]


# Deadline e ar koy din baki (minus mane deadline pass)
def days_left(deadline):
    return (deadline - date.today()).days


# "Due in 4 days" / "Due today" / "Overdue by 2 days" / "Completed"
def deadline_text(deadline, completed):
    if completed:
        return 'Completed'
    d = days_left(deadline)
    if d < 0:
        return 'Overdue by %d day%s' % (-d, '' if d == -1 else 's')
    if d == 0:
        return 'Due today'
    return 'Due in %d day%s' % (d, '' if d == 1 else 's')


# 'done' (shobuj) / 'error' (lal) / 'normal' (dhushor)
def deadline_tone(deadline, completed):
    if completed:
        return 'done'
    if days_left(deadline) <= 7:
        return 'error'
    return 'normal'


# 'Completed' / 'Overdue' / 'In Progress'
def project_status(deadline, completed):
    if completed:
        return 'Completed'
    if days_left(deadline) < 0:
        return 'Overdue'
    return 'In Progress'


PRIORITY_LABELS = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}
STATUS_LABELS = {'todo': 'To Do', 'doing': 'In Progress', 'done': 'Done'}

# ---------- Step 4: file, somoy ----------

# "just now" / "5 min ago" / "2 hours ago" / "3 days ago"
def time_ago(dt):
    seconds = max(0, int((datetime.now() - dt).total_seconds()))
    if seconds < 60:
        return 'just now'
    minutes = seconds // 60
    if minutes < 60:
        return '%d min ago' % minutes
    hours = minutes // 60
    if hours < 24:
        return '%d hour%s ago' % (hours, '' if hours == 1 else 's')
    days = hours // 24
    if days < 30:
        return '%d day%s ago' % (days, '' if days == 1 else 's')
    return dt.strftime('%b %d, %Y')


# File er type onujayi (icon, rong)
def file_icon(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'pdf':
        return ('picture_as_pdf', 'bg-error-container text-error')
    if ext in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
        return ('image', 'bg-tertiary-fixed text-tertiary')
    if ext in ('zip', 'rar', '7z'):
        return ('folder_zip', 'bg-secondary-fixed text-secondary')
    if ext in ('doc', 'docx', 'txt', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'):
        return ('description', 'bg-primary-fixed text-primary')
    return ('draft', 'bg-surface-container-highest text-on-surface-variant')


# File er size ("2.4 MB"). File na thakle khali.
def file_size(path):
    if not os.path.exists(path):
        return ''
    size = os.path.getsize(path)
    if size < 1024:
        return '%d B' % size
    if size < 1024 * 1024:
        return '%.0f KB' % (size / 1024)
    return '%.1f MB' % (size / 1024 / 1024)