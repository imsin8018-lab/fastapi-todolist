from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import sqlite3

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key="shinwoochul-todo-secret-key",
    max_age=60 * 60 * 24
)

templates = Jinja2Templates(directory="templates")


# =========================
# 데이터베이스
# =========================

def get_db():
    conn = sqlite3.connect("todo.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


create_tables()


# =========================
# 로그인
# =========================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    if request.session.get("user_id"):

        return RedirectResponse(
            "/",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    conn = get_db()

    user = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE username = ?
        AND password = ?
        """,
        (username, password)
    ).fetchone()

    conn.close()

    if user:

        request.session.clear()

        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]

        return RedirectResponse(
            "/",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "아이디 또는 비밀번호가 틀렸습니다."
        }
    )


# =========================
# 회원가입
# =========================

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={}
    )


@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...)
):

    if password != password_confirm:

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "비밀번호가 서로 다릅니다."
            }
        )

    conn = get_db()

    exists = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,)
    ).fetchone()

    if exists:

        conn.close()

        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "error": "이미 존재하는 아이디입니다."
            }
        )

    conn.execute(
        """
        INSERT INTO users
        (username, password)
        VALUES (?, ?)
        """,
        (username, password)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================
# 로그아웃
# =========================

@app.get("/logout")
def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================
# 메인
# =========================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    todos = conn.execute(
        """
        SELECT id, title, done
        FROM todos
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    total = len(todos)

    completed = sum(
        1 for todo in todos
        if todo["done"] == 1
    )

    remaining = total - completed

    if total == 0:
        progress = 0
    else:
        progress = int(
            completed / total * 100
        )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "todos": todos,
            "username": request.session.get("username"),
            "total": total,
            "completed": completed,
            "remaining": remaining,
            "progress": progress
        }
    )


# =========================
# Todo 추가
# =========================

@app.post("/add")
def add_todo(
    request: Request,
    title: str = Form(...)
):

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    title = title.strip()

    if title:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO todos
            (user_id, title, done)
            VALUES (?, ?, 0)
            """,
            (user_id, title)
        )

        conn.commit()
        conn.close()

    return RedirectResponse(
        "/",
        status_code=303
    )


# =========================
# 완료 / 미완료
# =========================

@app.post("/toggle/{todo_id}")
def toggle_todo(
    request: Request,
    todo_id: int
):

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    todo = conn.execute(
        """
        SELECT done
        FROM todos
        WHERE id = ?
        AND user_id = ?
        """,
        (todo_id, user_id)
    ).fetchone()

    if todo:

        new_done = 0 if todo["done"] else 1

        conn.execute(
            """
            UPDATE todos
            SET done = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (new_done, todo_id, user_id)
        )

        conn.commit()

    conn.close()

    return RedirectResponse(
        "/",
        status_code=303
    )


# =========================
# 삭제
# =========================

@app.post("/delete/{todo_id}")
def delete_todo(
    request: Request,
    todo_id: int
):

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    conn = get_db()

    conn.execute(
        """
        DELETE FROM todos
        WHERE id = ?
        AND user_id = ?
        """,
        (todo_id, user_id)
    )

    conn.commit()
    conn.close()

    return RedirectResponse(
        "/",
        status_code=303
    )


# =========================
# 수정
# =========================

@app.post("/edit/{todo_id}")
def edit_todo(
    request: Request,
    todo_id: int,
    title: str = Form(...)
):

    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            "/login",
            status_code=303
        )

    title = title.strip()

    if title:

        conn = get_db()

        conn.execute(
            """
            UPDATE todos
            SET title = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (title, todo_id, user_id)
        )

        conn.commit()
        conn.close()

    return RedirectResponse(
        "/",
        status_code=303
    )