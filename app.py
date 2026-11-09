# ============================================================
# app.py  -  amader Flask app (shob page er route ekhane)
# Chalate:  python app.py
# ============================================================
import os
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, session, flash, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from db import fetch_all, fetch_one, execute
import helpers

app = Flask(__name__)
app.secret_key = 'ei-ta-pore-bodle-nio'      # session (login) er jonno lage

# Upload kora file egulo "uploads" folder e jabe (nijei toiri hobe). Maximum 10 MB.
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
BLOCKED_EXTENSIONS = ('exe', 'bat', 'cmd', 'msi', 'com', 'scr', 'vbs')

# HTML e helper function use korar jonno:  {{ name|initials }}
app.jinja_env.filters['initials'] = helpers.initials
app.jinja_env.filters['first_name'] = helpers.first_name
app.jinja_env.filters['avatar'] = helpers.avatar
app.jinja_env.filters['time_ago'] = helpers.time_ago


# ------------------------------------------------------------
#  Login check
# ------------------------------------------------------------

# Ke login kore ache? (na thakle None)
def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return fetch_one(
        "SELECT u.id, u.name, u.email, p.role "
        "FROM users u JOIN profiles p ON p.user_id = u.id WHERE u.id = %s",
        (user_id,),
    )


# Je page e login lagbe, tar upore @login_required likhbo
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect('/login')
        return view(*args, **kwargs)
    return wrapper


# Shob HTML page e "user" variable pawa jabe
@app.context_processor
def inject_user():
    return {'user': current_user()}


# ------------------------------------------------------------
#  Home / Login / Register / Logout
# ------------------------------------------------------------

@app.route('/')
def home():
    if current_user():
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user():
        return redirect('/dashboard')

    error = None
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        # database e ei email er user ache kina
        found = fetch_one("SELECT * FROM users WHERE email = %s", (email,))

        if found and check_password_hash(found['password'], password):
            session['user_id'] = found['id']       # login holo
            return redirect('/dashboard')
        error = 'Email ba password thik nai. Abar try koro.'

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user():
        return redirect('/dashboard')

    error = None
    form = {'role': 'student', 'full_name': '', 'email': ''}

    if request.method == 'POST':
        form['role'] = request.form.get('role', 'student')
        form['full_name'] = request.form['full_name'].strip()
        form['email'] = request.form['email'].strip()
        password1 = request.form['password1']
        password2 = request.form['password2']

        if form['role'] not in ('student', 'teacher'):
            error = 'Role thik nai.'
        elif len(password1) < 6:
            error = 'Password kom pokkhe 6 character hote hobe.'
        elif password1 != password2:
            error = 'Duto password mile nai.'
        elif fetch_one("SELECT id FROM users WHERE email = %s", (form['email'],)):
            error = 'Ei email diye age account khola hoyeche.'
        else:
            # notun user + profile database e rakhi
            user_id = execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (form['full_name'], form['email'], generate_password_hash(password1)),
            )
            execute("INSERT INTO profiles (user_id, role) VALUES (%s, %s)", (user_id, form['role']))

            session['user_id'] = user_id           # sathe sathe login
            flash('Account toiri hoyeche. Welcome!', 'success')
            return redirect('/dashboard')

    return render_template('register.html', error=error, form=form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ------------------------------------------------------------
#  Project / Task er info ber korar function
# ------------------------------------------------------------

# Project dict er sathe progress, member, comment sonkha jure dei
def add_project_info(project):
    counts = fetch_one(
        "SELECT COUNT(*) AS total, SUM(status = 'done') AS done FROM tasks WHERE project_id = %s",
        (project['id'],),
    )
    total = counts['total']
    done = int(counts['done'] or 0)

    project['total'] = total
    project['done'] = done
    project['progress'] = int(done / total * 100) if total else 0
    completed = total > 0 and done == total

    project['status'] = helpers.project_status(project['deadline'], completed)
    project['tone'] = helpers.deadline_tone(project['deadline'], completed)
    project['deadline_text'] = helpers.deadline_text(project['deadline'], completed)

    project['members'] = fetch_all(
        "SELECT u.id, u.name FROM project_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.project_id = %s ORDER BY u.id",
        (project['id'],),
    )
    project['comment_count'] = fetch_one(
        "SELECT COUNT(*) AS c FROM comments WHERE project_id = %s", (project['id'],)
    )['c']
    return project


# Student: nijer project. Teacher: shob project.
def get_projects(user):
    if user['role'] == 'teacher':
        rows = fetch_all("SELECT * FROM projects ORDER BY created_at DESC, id DESC")
    else:
        rows = fetch_all(
            "SELECT p.* FROM projects p JOIN project_members m ON m.project_id = p.id "
            "WHERE m.user_id = %s ORDER BY p.created_at DESC, p.id DESC",
            (user['id'],),
        )
    return [add_project_info(p) for p in rows]


# Task dict e overdue, label jure dei
def add_task_info(task):
    task['overdue'] = (
        task['status'] != 'done' and task['due_date'] is not None and task['due_date'] < date.today()
    )
    task['priority_label'] = helpers.PRIORITY_LABELS[task['priority']]
    task['status_label'] = helpers.STATUS_LABELS[task['status']]
    return task


# ------------------------------------------------------------
#  Dashboard
# ------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()

    # Teacher dashboard pore banabo
    if user['role'] == 'teacher':
        return render_template('coming_soon.html', title='Teacher Dashboard')

    projects = get_projects(user)

    # amar task gulo (pending = done na)
    pending = fetch_all(
        "SELECT t.*, p.title AS project_title FROM tasks t JOIN projects p ON p.id = t.project_id "
        "WHERE t.assigned_to = %s AND t.status != 'done' "
        "ORDER BY t.due_date IS NULL, t.due_date LIMIT 6",
        (user['id'],),
    )
    counts = fetch_one(
        "SELECT SUM(status != 'done') AS pending, SUM(status = 'done') AS done "
        "FROM tasks WHERE assigned_to = %s",
        (user['id'],),
    )
    pending_count = int(counts['pending'] or 0)
    completed_count = int(counts['done'] or 0)
    all_count = pending_count + completed_count

    return render_template(
        'dashboard.html',
        total_projects=len(projects),
        pending_count=pending_count,
        completed_count=completed_count,
        completion_rate=int(completed_count / all_count * 100) if all_count else 0,
        projects=projects[:5],
        my_tasks=[add_task_info(t) for t in pending],
    )


# ------------------------------------------------------------
#  Projects list  ar  My Tasks
# ------------------------------------------------------------

@app.route('/projects')
@login_required
def project_list():
    user = current_user()
    return render_template('projects.html', projects=get_projects(user))


@app.route('/my-tasks')
@login_required
def my_tasks():
    user = current_user()
    if user['role'] == 'teacher':              # teacher er My Tasks nai
        return redirect('/dashboard')

    status = request.args.get('status', '')    # URL er ?status=todo theke ashe

    sql = ("SELECT t.*, p.title AS project_title FROM tasks t JOIN projects p ON p.id = t.project_id "
           "WHERE t.assigned_to = %s ")
    params = [user['id']]
    if status in helpers.STATUS_LABELS:        # todo / doing / done
        sql += "AND t.status = %s "
        params.append(status)
    sql += "ORDER BY t.due_date IS NULL, t.due_date"

    tasks = [add_task_info(t) for t in fetch_all(sql, params)]
    return render_template(
        'my_tasks.html',
        tasks=tasks,
        status=status,
        status_choices=helpers.STATUS_LABELS.items(),
    )


# ------------------------------------------------------------
#  Notun Project banano
# ------------------------------------------------------------

# Project ta ei user dekhte pare kina (teacher shob dekhe, student shudhu nijer)
def get_project_or_404(user, project_id):
    project = fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if project is None:
        abort(404)
    if user['role'] == 'student' and not is_member(user, project_id):
        abort(404)
    return project


# User ei project er member kina
def is_member(user, project_id):
    row = fetch_one(
        "SELECT 1 AS ok FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, user['id']),
    )
    return row is not None


@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def project_new():
    user = current_user()
    if user['role'] != 'student':
        flash('Shudhu student project banate pare.', 'error')
        return redirect('/projects')

    # member hishebe jader add kora jabe (nijeke chara baki student)
    students = fetch_all(
        "SELECT u.id, u.name, u.email FROM users u JOIN profiles p ON p.user_id = u.id "
        "WHERE p.role = 'student' AND u.id != %s ORDER BY u.name",
        (user['id'],),
    )

    error = None
    form = {'title': '', 'description': '', 'deadline': '', 'members': []}

    if request.method == 'POST':
        form['title'] = request.form['title'].strip()
        form['description'] = request.form['description'].strip()
        form['deadline'] = request.form['deadline']
        form['members'] = [int(i) for i in request.form.getlist('members')]   # tick kora member id

        if not form['title'] or not form['description'] or not form['deadline']:
            error = 'Title, description ar deadline dite hobe.'
        else:
            # 1) project table e save
            project_id = execute(
                "INSERT INTO projects (title, description, deadline, created_by) VALUES (%s, %s, %s, %s)",
                (form['title'], form['description'], form['deadline'], user['id']),
            )
            # 2) member der save (nije auto member)
            execute("INSERT INTO project_members (project_id, user_id) VALUES (%s, %s)", (project_id, user['id']))
            valid_ids = [s['id'] for s in students]
            for member_id in form['members']:
                if member_id in valid_ids:
                    execute("INSERT INTO project_members (project_id, user_id) VALUES (%s, %s)", (project_id, member_id))

            flash('Project toiri hoyeche.', 'success')
            return redirect('/projects')

    return render_template('project_form.html', form=form, students=students, error=error,
                           editing=False, project=None)


# ------------------------------------------------------------
#  Notun Task banano
# ------------------------------------------------------------

@app.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def task_new(project_id):
    user = current_user()
    project = get_project_or_404(user, project_id)
    if user['role'] != 'student':
        abort(403)

    # task kake deya jabe: ei project er member ra
    members = fetch_all(
        "SELECT u.id, u.name, u.email FROM project_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.project_id = %s ORDER BY u.name",
        (project_id,),
    )

    error = None
    form = {
        'title': '', 'description': '', 'assigned_to': '',
        'status': request.args.get('status', 'todo'),     # ?status=doing hole oita select thakbe
        'priority': 'medium', 'due_date': '',
    }
    if form['status'] not in helpers.STATUS_LABELS:
        form['status'] = 'todo'

    if request.method == 'POST':
        form['title'] = request.form['title'].strip()
        form['description'] = request.form['description'].strip()
        form['assigned_to'] = request.form['assigned_to']
        form['status'] = request.form['status']
        form['priority'] = request.form['priority']
        form['due_date'] = request.form['due_date']

        if not form['title']:
            error = 'Task title dite hobe.'
        else:
            # khali hole NULL (kichu na) save hobe
            assigned_to = int(form['assigned_to']) if form['assigned_to'] else None
            due_date = form['due_date'] or None

            execute(
                "INSERT INTO tasks (project_id, title, description, priority, status, due_date, assigned_to) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (project_id, form['title'], form['description'], form['priority'],
                 form['status'], due_date, assigned_to),
            )
            flash('Task toiri hoyeche.', 'success')
            return redirect('/projects')

    return render_template('task_form.html', form=form, members=members, project=project,
                           error=error, editing=False)


# ------------------------------------------------------------
#  Server chalu
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)