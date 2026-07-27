"""
CareScheduler - 看護管理者タスク管理アプリ
緊急度・期日でタスクを整理し、今日やるべきことを一目で把握できるようにするWebアプリ。
"""
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, url_for

from . import db

app = Flask(__name__)
app.config["SECRET_KEY"] = "carescheduler-task-manager-dev-key"

URGENCY_ORDER = db.URGENCY_ORDER
URGENCY_LABELS = db.URGENCY_LABELS
STATUS_LABELS = db.STATUS_LABELS

REMIND_SOON_DAYS = 3  # この日数以内に迫った期日を「まもなく」として警告する


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def annotate_task(task):
    """テンプレート表示用に、期日の状態(超過/本日/まもなく)やラベルを付与する"""
    task = dict(task)
    task["urgency_label"] = URGENCY_LABELS.get(task["urgency"], task["urgency"])
    task["status_label"] = STATUS_LABELS.get(task["status"], task["status"])

    due = _parse_date(task.get("due_date"))
    task["due_state"] = "none"
    task["days_left"] = None
    if due and task["status"] != "done":
        delta = (due - date.today()).days
        task["days_left"] = delta
        if delta < 0:
            task["due_state"] = "overdue"
        elif delta == 0:
            task["due_state"] = "today"
        elif delta <= REMIND_SOON_DAYS:
            task["due_state"] = "soon"
        else:
            task["due_state"] = "later"
    return task


@app.context_processor
def inject_globals():
    return {
        "urgency_labels": URGENCY_LABELS,
        "status_labels": STATUS_LABELS,
        "today": date.today().isoformat(),
    }


@app.route("/")
def today_view():
    all_tasks = [annotate_task(t) for t in db.list_tasks(order_by="urgency")]
    open_tasks = [t for t in all_tasks if t["status"] != "done"]

    overdue = [t for t in open_tasks if t["due_state"] == "overdue"]
    due_today = [t for t in open_tasks if t["due_state"] == "today"]
    urgent_open = [
        t for t in open_tasks if t["urgency"] == "urgent" and t["due_state"] not in ("overdue", "today")
    ]
    due_soon = [t for t in open_tasks if t["due_state"] == "soon"]

    # 「今日やること」= 期限超過 + 本日期限 + 緊急度「緊急」の未完了タスク（重複除去、緊急度→期日順）
    today_ids = set()
    focus_tasks = []
    for group in (overdue, due_today, urgent_open):
        for t in group:
            if t["id"] not in today_ids:
                today_ids.add(t["id"])
                focus_tasks.append(t)
    focus_tasks.sort(key=lambda t: (URGENCY_ORDER.get(t["urgency"], 9), t["due_date"] or "9999-99-99"))

    upcoming = sorted(
        [t for t in open_tasks if t["due_state"] in ("soon", "later")],
        key=lambda t: (t["due_date"] or "9999-99-99", t["due_time"] or "99:99"),
    )[:8]

    summary = {
        "overdue_count": len(overdue),
        "due_today_count": len(due_today),
        "urgent_count": len([t for t in open_tasks if t["urgency"] == "urgent"]),
        "open_count": len(open_tasks),
    }

    return render_template(
        "today.html",
        focus_tasks=focus_tasks,
        upcoming=upcoming,
        due_soon=due_soon,
        summary=summary,
    )


@app.route("/tasks")
def task_list():
    status = request.args.get("status") or None
    urgency = request.args.get("urgency") or None
    order_by = request.args.get("sort", "urgency")

    tasks = [annotate_task(t) for t in db.list_tasks(status=status, urgency=urgency, order_by=order_by)]
    return render_template(
        "tasks.html",
        tasks=tasks,
        current_status=status or "",
        current_urgency=urgency or "",
        current_sort=order_by,
    )


@app.route("/schedule")
def schedule_view():
    tasks = [annotate_task(t) for t in db.list_tasks(order_by="due_date")]
    scheduled = [t for t in tasks if t["due_date"] and t["status"] != "done"]

    grouped = {}
    for t in scheduled:
        grouped.setdefault(t["due_date"], []).append(t)

    days = sorted(grouped.keys())
    return render_template("schedule.html", grouped=grouped, days=days)


@app.route("/tasks/new", methods=["GET", "POST"])
def task_new():
    if request.method == "POST":
        db.create_task(
            title=request.form["title"].strip(),
            description=request.form.get("description", "").strip(),
            category=request.form.get("category", "").strip(),
            urgency=request.form.get("urgency", "medium"),
            due_date=request.form.get("due_date") or None,
            due_time=request.form.get("due_time") or None,
            status=request.form.get("status", "todo"),
        )
        return redirect(url_for("task_list"))
    return render_template("task_form.html", task=None)


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def task_edit(task_id):
    task = db.get_task(task_id)
    if not task:
        return redirect(url_for("task_list"))

    if request.method == "POST":
        db.update_task(
            task_id,
            title=request.form["title"].strip(),
            description=request.form.get("description", "").strip(),
            category=request.form.get("category", "").strip(),
            urgency=request.form.get("urgency", "medium"),
            due_date=request.form.get("due_date") or None,
            due_time=request.form.get("due_time") or None,
            status=request.form.get("status", "todo"),
        )
        return redirect(url_for("task_list"))
    return render_template("task_form.html", task=task)


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def task_complete(task_id):
    db.set_task_status(task_id, "done")
    return redirect(request.referrer or url_for("today_view"))


@app.route("/tasks/<int:task_id>/reopen", methods=["POST"])
def task_reopen(task_id):
    db.set_task_status(task_id, "todo")
    return redirect(request.referrer or url_for("today_view"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def task_delete(task_id):
    db.delete_task(task_id)
    return redirect(request.referrer or url_for("task_list"))


db.init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
