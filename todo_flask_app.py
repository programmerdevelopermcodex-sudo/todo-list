"""
Simple TODO web app in a single Python file using Flask + SQLite.

Features:
- List todos
- Add todo (title + optional description)
- Edit todo
- Toggle complete / incomplete
- Delete todo
- Persistent storage with SQLite (file: todos.db)

How to run:
1. Create a virtualenv (recommended) and install Flask:
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   pip install Flask
2. Save this file as todo_flask_app.py and run:
   python todo_flask_app.py
3. Open http://127.0.0.1:5000 in your browser.

"""
from flask import Flask, g, render_template_string, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

DATABASE = os.path.join(os.path.dirname(__file__), 'todos.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-this-with-a-secret-if-deploying'

# ---------- Database helpers ----------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    db.commit()

# Initialize DB when app starts
with app.app_context():
    init_db()

# ---------- Templates ----------
BASE_HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>تودو ليست</title>
  <style>
    body{font-family: Arial, Helvetica, sans-serif; max-width:900px;margin:20px auto;padding:10px}
    .card{background:#f9f9f9;border-radius:8px;padding:12px;margin:8px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
    form.inline{display:inline}
    input, textarea{width:100%;padding:8px;margin:6px 0;border:1px solid #ddd;border-radius:6px}
    button{padding:8px 12px;border-radius:6px;border:0;background:#2b7cff;color:white;cursor:pointer}
    .muted{color:#666;font-size:0.9em}
    .done{opacity:0.6;text-decoration:line-through}
    .actions{display:flex;gap:8px;flex-wrap:wrap}
    .small{padding:6px 10px;font-size:0.9em}
  </style>
</head>
<body>
  <h1>قائمة المهام (تودو ليست)</h1>
  {% block content %}{% endblock %}
</body>
</html>
"""

INDEX_HTML = """
{% extends base %}
{% block content %}
<div class="card">
  <h3>أضف مهمة جديدة</h3>
  <form method="post" action="{{ url_for('add') }}">
    <input name="title" placeholder="عنوان المهمة" required>
    <textarea name="description" placeholder="وصف (اختياري)" rows="3"></textarea>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button type="submit">أضف</button>
    </div>
  </form>
</div>

<div class="card">
  <h3>المهمات</h3>
  {% if todos | length == 0 %}
    <p class="muted">لا توجد مهام بعد.</p>
  {% else %}
    {% for t in todos %}
      <div class="card {% if t.done %}done{% endif %}">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <strong>{{ t.title }}</strong>
            <div class="muted">{{ t.created_at }}</div>
          </div>
          <div class="actions">
            <form class="inline" method="post" action="{{ url_for('toggle', todo_id=t.id) }}">
              <button class="small" type="submit">{% if t.done %}إلغاء علامة منجزة{% else %}تم{% endif %}</button>
            </form>
            <a class="small" href="{{ url_for('edit', todo_id=t.id) }}">تعديل</a>
            <form class="inline" method="post" action="{{ url_for('delete', todo_id=t.id) }}" onsubmit="return confirm('حذف المهمة؟');">
              <button class="small" type="submit">حذف</button>
            </form>
          </div>
        </div>
        {% if t.description %}
          <div style="margin-top:8px">{{ t.description }}</div>
        {% endif %}
      </div>
    {% endfor %}
  {% endif %}
</div>
{% endblock %}
"""

EDIT_HTML = """
{% extends base %}
{% block content %}
<div class="card">
  <h3>تعديل المهمة</h3>
  <form method="post" action="{{ url_for('edit', todo_id=todo.id) }}">
    <input name="title" value="{{ todo.title }}" required>
    <textarea name="description" rows="4">{{ todo.description }}</textarea>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button type="submit">حفظ التعديلات</button>
      <a href="{{ url_for('index') }}" class="small">إلغاء</a>
    </div>
  </form>
</div>
{% endblock %}
"""

# ---------- Routes ----------
@app.route('/')
def index():
    db = get_db()
    cur = db.execute('SELECT id, title, description, done, created_at FROM todos ORDER BY created_at DESC')
    todos = cur.fetchall()
    return render_template_string(INDEX_HTML, base=BASE_HTML, todos=todos)

@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not title:
        return redirect(url_for('index'))
    db = get_db()
    db.execute('INSERT INTO todos (title, description, created_at) VALUES (?, ?, ?)',
               (title, description, datetime.utcnow().isoformat()))
    db.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:todo_id>', methods=['GET', 'POST'])
def edit(todo_id):
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        if title:
            db.execute('UPDATE todos SET title = ?, description = ? WHERE id = ?', (title, description, todo_id))
            db.commit()
        return redirect(url_for('index'))
    cur = db.execute('SELECT id, title, description, done, created_at FROM todos WHERE id = ?', (todo_id,))
    todo = cur.fetchone()
    if todo is None:
        return redirect(url_for('index'))
    return render_template_string(EDIT_HTML, base=BASE_HTML, todo=todo)

@app.route('/toggle/<int:todo_id>', methods=['POST'])
def toggle(todo_id):
    db = get_db()
    cur = db.execute('SELECT done FROM todos WHERE id = ?', (todo_id,))
    row = cur.fetchone()
    if row:
        new = 0 if row['done'] else 1
        db.execute('UPDATE todos SET done = ? WHERE id = ?', (new, todo_id))
        db.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:todo_id>', methods=['POST'])
def delete(todo_id):
    db = get_db()
    db.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
    db.commit()
    return redirect(url_for('index'))

# Run
if __name__ == '__main__':
    app.run(debug=True)
