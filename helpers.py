# ============================================================
# helpers.py  -  chhoto chhoto kaj (date, naam, rong)
# ============================================================
from datetime import date

# Avatar circle er rong (Stitch er color)
AVATAR_COLORS = [
    'bg-primary text-on-primary',
    'bg-secondary text-on-secondary',
    'bg-tertiary text-on-tertiary',
    'bg-primary-container text-on-primary',
    'bg-tertiary-container text-on-tertiary',
]


# 'Maimuna Akter' -> 'Maimuna'
def first_name(name):
    return name.split()[0]


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