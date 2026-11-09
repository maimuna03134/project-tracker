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
        flash('Project toiri hoyeche.', 'success')
        return redirect('/projects/%d' % project_id)

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
                    error = check_task_form(form, members)
        if not error:
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
            return redirect('/projects/%d#tasks' % project_id)

    return render_template('task_form.html', form=form, members=members, project=project,
                           error=error, editing=False)

# ------------------------------------------------------------
#  Step 4: Project Details page
# ------------------------------------------------------------

# Task form e vul ache kina dekhi (thik hole None return kore)
def check_task_form(form, members):
    if not form['title']:
        return 'Task title dite hobe.'
    if form['status'] not in helpers.STATUS_LABELS or form['priority'] not in helpers.PRIORITY_LABELS:
        return 'Status ba priority thik nai.'
    if form['assigned_to'] and form['assigned_to'] not in [str(m['id']) for m in members]:
        return 'Ei member ei project e nai.'
    return None


# Kaj korar permission: shudhu student (je ei project er member)
def get_project_for_work(user, project_id):
    project = get_project_or_404(user, project_id)
    if user['role'] != 'student':
        abort(403)
    return project


# Task ta ana + user ei project dekhte pare kina check
def get_task_or_404(user, task_id):
    task = fetch_one("SELECT * FROM tasks WHERE id = %s", (task_id,))
    if task is None:
        abort(404)
    get_project_or_404(user, task['project_id'])
    return task


# Upload kora file ta disk e kothay ache (id_naam.ext)
def attachment_path(att):
    safe_name = secure_filename(att['file_name']) or 'file'
    return os.path.join(UPLOAD_FOLDER, '%d_%s' % (att['id'], safe_name))


@app.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    user = current_user()
    project = add_project_info(get_project_or_404(user, project_id))
    project['lead'] = fetch_one("SELECT id, name, email FROM users WHERE id = %s", (project['created_by'],))

    # Task gulo 3 column e bhag kore (To Do / In Progress / Done)
    rows = fetch_all(
        "SELECT t.*, u.name AS assignee_name FROM tasks t LEFT JOIN users u ON u.id = t.assigned_to "
        "WHERE t.project_id = %s ORDER BY t.due_date IS NULL, t.due_date, t.id",
        (project_id,),
    )
    columns = {'todo': [], 'doing': [], 'done': []}
    for row in rows:
        columns[row['status']].append(add_task_info(row))

    comments = fetch_all(
        "SELECT c.*, u.name, p.role FROM comments c JOIN users u ON u.id = c.user_id "
        "JOIN profiles p ON p.user_id = u.id WHERE c.project_id = %s ORDER BY c.created_at DESC, c.id DESC",
        (project_id,),
    )

    attachments = fetch_all(
        "SELECT a.*, u.name AS uploader FROM attachments a JOIN users u ON u.id = a.uploaded_by "
        "WHERE a.project_id = %s ORDER BY a.uploaded_at DESC, a.id DESC",
        (project_id,),
    )
    for a in attachments:
        a['icon'] = helpers.file_icon(a['file_name'])
        a['size'] = helpers.file_size(attachment_path(a))
        a['can_delete'] = user['role'] == 'student' and user['id'] in (a['uploaded_by'], project['created_by'])

    feedbacks = fetch_all(
        "SELECT f.*, u.name AS teacher_name FROM feedbacks f JOIN users u ON u.id = f.teacher_id "
        "WHERE f.project_id = %s ORDER BY f.created_at DESC, f.id DESC",
        (project_id,),
    )

    return render_template(
        'project_detail.html',
        project=project,
        todo_tasks=columns['todo'],
        doing_tasks=columns['doing'],
        done_tasks=columns['done'],
        comments=comments,
        attachments=attachments,
        feedbacks=feedbacks,
        can_work=user['role'] == 'student',                                   # student member
        is_owner=user['role'] == 'student' and user['id'] == project['created_by'],
        status_choices=helpers.STATUS_LABELS.items(),
    )


# ------------------------------------------------------------
#  Project edit / delete
# ------------------------------------------------------------

@app.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def project_edit(project_id):
    user = current_user()
    project = get_project_for_work(user, project_id)
    if project['created_by'] != user['id']:          # shudhu je banaise
        abort(403)

    error = None
    form = {'title': project['title'], 'description': project['description'],
            'deadline': project['deadline'].isoformat(), 'members': []}

    if request.method == 'POST':
        form['title'] = request.form['title'].strip()
        form['description'] = request.form['description'].strip()
        form['deadline'] = request.form['deadline']

        if not form['title'] or not form['description'] or not form['deadline']:
            error = 'Title, description ar deadline dite hobe.'
        else:
            execute(
                "UPDATE projects SET title = %s, description = %s, deadline = %s WHERE id = %s",
                (form['title'], form['description'], form['deadline'], project_id),
            )
            flash('Project update hoyeche.', 'success')
            return redirect('/projects/%d' % project_id)

    return render_template('project_form.html', form=form, students=[], error=error,
                           editing=True, project=project)


@app.route('/projects/<int:project_id>/delete', methods=['GET', 'POST'])
@login_required
def project_delete(project_id):
    user = current_user()
    project = get_project_for_work(user, project_id)
    if project['created_by'] != user['id']:
        abort(403)

    if request.method == 'POST':
        execute("DELETE FROM projects WHERE id = %s", (project_id,))   # task, comment shob sathe muche jay
        flash('Project delete hoyeche.', 'success')
        return redirect('/projects')

    # GET: "Nishchit?" page dekhai
    return render_template(
        'confirm_delete.html',
        heading='Delete project?',
        message='"%s" project ta, tar shob task, comment ar file shompurno muche jabe. Eta ar ferot ana jabe na.' % project['title'],
        action='/projects/%d/delete' % project_id,
        back='/projects/%d' % project_id,
    )


# ------------------------------------------------------------
#  Member add / remove
# ------------------------------------------------------------

@app.route('/projects/<int:project_id>/members/add', methods=['POST'])
@login_required
def member_add(project_id):
    user = current_user()
    get_project_for_work(user, project_id)
    email = request.form['email'].strip()

    student = fetch_one(
        "SELECT u.id, u.name FROM users u JOIN profiles p ON p.user_id = u.id "
        "WHERE u.email = %s AND p.role = 'student'",
        (email,),
    )
    if student is None:
        flash('Ei email e kono student account nai.', 'error')
    elif is_member(student, project_id):
        flash('%s age thekei member.' % student['name'], 'error')
    else:
        execute("INSERT INTO project_members (project_id, user_id) VALUES (%s, %s)", (project_id, student['id']))
        flash('%s ke member kora hoyeche.' % student['name'], 'success')
    return redirect('/projects/%d' % project_id)


@app.route('/projects/<int:project_id>/members/<int:member_id>/remove', methods=['POST'])
@login_required
def member_remove(project_id, member_id):
    user = current_user()
    project = get_project_for_work(user, project_id)
    if project['created_by'] != user['id']:          # shudhu project lead remove korte pare
        abort(403)
    if member_id == project['created_by']:
        flash('Project lead ke remove kora jay na.', 'error')
    else:
        execute("DELETE FROM project_members WHERE project_id = %s AND user_id = %s", (project_id, member_id))
        # oi member er task gulo "Unassigned" hoye jabe
        execute("UPDATE tasks SET assigned_to = NULL WHERE project_id = %s AND assigned_to = %s",
                (project_id, member_id))
        flash('Member remove kora hoyeche.', 'success')
    return redirect('/projects/%d' % project_id)


# ------------------------------------------------------------
#  Task edit / delete / status change
# ------------------------------------------------------------

@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def task_edit(task_id):
    user = current_user()
    task = get_task_or_404(user, task_id)
    project = get_project_for_work(user, task['project_id'])

    members = fetch_all(
        "SELECT u.id, u.name, u.email FROM project_members m JOIN users u ON u.id = m.user_id "
        "WHERE m.project_id = %s ORDER BY u.name",
        (project['id'],),
    )

    error = None
    form = {
        'title': task['title'], 'description': task['description'] or '',
        'assigned_to': str(task['assigned_to']) if task['assigned_to'] else '',
        'status': task['status'], 'priority': task['priority'],
        'due_date': task['due_date'].isoformat() if task['due_date'] else '',
    }

    if request.method == 'POST':
        form['title'] = request.form['title'].strip()
        form['description'] = request.form['description'].strip()
        form['assigned_to'] = request.form['assigned_to']
        form['status'] = request.form['status']
        form['priority'] = request.form['priority']
        form['due_date'] = request.form['due_date']

        error = check_task_form(form, members)
        if not error:
            execute(
                "UPDATE tasks SET title = %s, description = %s, priority = %s, status = %s, "
                "due_date = %s, assigned_to = %s WHERE id = %s",
                (form['title'], form['description'], form['priority'], form['status'],
                 form['due_date'] or None,
                 int(form['assigned_to']) if form['assigned_to'] else None,
                 task_id),
            )
            flash('Task update hoyeche.', 'success')
            return redirect('/projects/%d#tasks' % project['id'])

    return render_template('task_form.html', form=form, members=members, project=project,
                           error=error, editing=True)


@app.route('/tasks/<int:task_id>/delete', methods=['GET', 'POST'])
@login_required
def task_delete(task_id):
    user = current_user()
    task = get_task_or_404(user, task_id)
    get_project_for_work(user, task['project_id'])
    back = '/projects/%d#tasks' % task['project_id']

    if request.method == 'POST':
        execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        flash('Task delete hoyeche.', 'success')
        return redirect(back)

    return render_template(
        'confirm_delete.html',
        heading='Delete task?',
        message='"%s" task ta muche jabe.' % task['title'],
        action='/tasks/%d/delete' % task_id,
        back=back,
    )


@app.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def task_status(task_id):
    user = current_user()
    task = get_task_or_404(user, task_id)
    get_project_for_work(user, task['project_id'])

    status = request.form.get('status', '')
    if status in helpers.STATUS_LABELS:
        execute("UPDATE tasks SET status = %s WHERE id = %s", (status, task_id))
    return redirect('/projects/%d#tasks' % task['project_id'])


# ------------------------------------------------------------
#  Comment
# ------------------------------------------------------------

@app.route('/projects/<int:project_id>/comments', methods=['POST'])
@login_required
def comment_add(project_id):
    user = current_user()
    get_project_or_404(user, project_id)             # student (member) ar teacher duijon-i comment korte pare
    text = request.form['text'].strip()

    if not text:
        flash('Comment khali rakha jay na.', 'error')
    else:
        execute("INSERT INTO comments (project_id, user_id, text) VALUES (%s, %s, %s)",
                (project_id, user['id'], text))
    return redirect('/projects/%d#discussion' % project_id)


# ------------------------------------------------------------
#  File upload / download / delete
# ------------------------------------------------------------

@app.route('/projects/<int:project_id>/files', methods=['POST'])
@login_required
def file_upload(project_id):
    user = current_user()
    get_project_for_work(user, project_id)
    back = '/projects/%d#files' % project_id

    file = request.files.get('file')
    if file is None or file.filename == '':
        flash('Age ekta file select koro.', 'error')
        return redirect(back)

    original_name = os.path.basename(file.filename.replace('\\', '/'))[:255]
    extension = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if extension in BLOCKED_EXTENSIONS:
        flash('Ei dhoroner file upload kora jabe na.', 'error')
        return redirect(back)

    # age database e naam rakhi (id pai), tarpor file ta disk e save
    att_id = execute(
        "INSERT INTO attachments (project_id, file_name, uploaded_by) VALUES (%s, %s, %s)",
        (project_id, original_name, user['id']),
    )
    file.save(attachment_path({'id': att_id, 'file_name': original_name}))
    flash('File upload hoyeche.', 'success')
    return redirect(back)


@app.route('/files/<int:file_id>')
@login_required
def file_download(file_id):
    user = current_user()
    att = fetch_one("SELECT * FROM attachments WHERE id = %s", (file_id,))
    if att is None:
        abort(404)
    get_project_or_404(user, att['project_id'])
    path = attachment_path(att)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=att['file_name'])


@app.route('/files/<int:file_id>/delete', methods=['GET', 'POST'])
@login_required
def file_delete(file_id):
    user = current_user()
    att = fetch_one("SELECT * FROM attachments WHERE id = %s", (file_id,))
    if att is None:
        abort(404)
    project = get_project_for_work(user, att['project_id'])
    if user['id'] not in (att['uploaded_by'], project['created_by']):    # uploader ba project lead
        abort(403)
    back = '/projects/%d#files' % project['id']

    if request.method == 'POST':
        execute("DELETE FROM attachments WHERE id = %s", (file_id,))
        path = attachment_path(att)
        if os.path.exists(path):
            os.remove(path)
        flash('File delete hoyeche.', 'success')
        return redirect(back)

    return render_template(
        'confirm_delete.html',
        heading='Delete file?',
        message='"%s" file ta muche jabe.' % att['file_name'],
        action='/files/%d/delete' % file_id,
        back=back,
    )


# File 10 MB er beshi boro hole
@app.errorhandler(413)
def file_too_large(error):
    flash('File ta 10 MB er beshi boro. Chhoto file dao.', 'error')
    return redirect(request.referrer or '/projects')


# ------------------------------------------------------------
#  Server chalu
# ------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)