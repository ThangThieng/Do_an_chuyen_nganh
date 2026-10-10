"""
Quản lý tài khoản Dashboard (analytics.app_user). user_id = mdl_user.id để khớp teacher_ids trong bảng fact.

    python -m backend.app.cli sync-users [--password ...] [--reset-password] [--admin admin]
    python -m backend.app.cli set-password --username gv.tranminhhung [--password ...]
    python -m backend.app.cli list-users
    python -m backend.app.cli backup                      # sao lưu dữ liệu schema analytics
    python -m backend.app.cli list-backups
    python -m backend.app.cli restore --file lms_analytics_20261001_083000.zip [--yes]
    python -m backend.app.cli messaging-check [--send-test-email ban@example.com] [--save]

sync-users lấy từ Moodle: tài khoản có vai trò editingteacher/teacher trong ít nhất một môn -> TEACHER;
username trong --admin (mặc định "admin") -> ADMIN. Tài khoản Moodle bị khóa -> is_active = false;
TEACHER không còn trong Moodle -> is_active = false. Mật khẩu chỉ đặt cho tài khoản MỚI (trừ khi --reset-password).
Mật khẩu lấy từ --password, biến BACKEND_SEED_PASSWORD, hoặc nhập từ bàn phím.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

import psycopg
from psycopg import errors

from backend.app.core.security import ROLE_ADMIN, ROLE_TEACHER, hash_password
from database.config import load_db_config

MIN_PASSWORD_LENGTH = 8

MOODLE_ACCOUNTS_SQL = """
SELECT u.id, u.username, u.firstname, u.lastname, NULLIF(u.email, '') AS email, u.suspended,
       CASE WHEN u.username = ANY(%(admins)s) THEN 'ADMIN' ELSE 'TEACHER' END AS role
FROM mdl_user u
WHERE u.deleted = 0
  AND (u.username = ANY(%(admins)s)
       OR EXISTS (SELECT 1
                  FROM mdl_role_assignments ra
                  JOIN mdl_role r      ON r.id = ra.roleid AND r.shortname IN ('editingteacher', 'teacher')
                  JOIN mdl_context ctx ON ctx.id = ra.contextid AND ctx.contextlevel = 50
                  WHERE ra.userid = u.id))
ORDER BY u.id
"""


def _read_password(value: str | None, *, required: bool) -> str | None:
    password = value or os.getenv("BACKEND_SEED_PASSWORD")
    if not password and required and sys.stdin.isatty():
        password = getpass.getpass("Mật khẩu: ")
        if getpass.getpass("Nhập lại mật khẩu: ") != password:
            raise SystemExit("Hai lần nhập mật khẩu không khớp")
    if password is None:
        if required:
            raise SystemExit("Cần mật khẩu: dùng --password, biến BACKEND_SEED_PASSWORD hoặc chạy trong terminal")
        return None
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Mật khẩu phải có ít nhất {MIN_PASSWORD_LENGTH} ký tự")
    return password


def _analytics() -> psycopg.Connection:
    return psycopg.connect(**load_db_config("ANALYTICS_DB").conninfo(application_name="lms-backend-cli"))


def sync_users(password_arg: str | None, reset_password: bool, admins: list[str]) -> int:
    with psycopg.connect(**load_db_config("MOODLE_DB").conninfo(application_name="lms-backend-cli")) as moodle:
        moodle.read_only = True
        accounts = moodle.execute(MOODLE_ACCOUNTS_SQL, {"admins": admins}).fetchall()

    with _analytics() as conn:
        existing = {row[0] for row in conn.execute("SELECT user_id FROM analytics.app_user")}
        new_count = sum(1 for a in accounts if a[0] not in existing)
        password = _read_password(password_arg, required=bool(new_count) or reset_password)

        created = updated = 0
        try:
            for user_id, username, firstname, lastname, email, suspended, role in accounts:
                full_name = f"{lastname} {firstname}".strip()
                params = {"id": user_id, "username": username, "full_name": full_name, "email": email,
                          "role": role, "active": suspended == 0}
                if user_id in existing:
                    set_password = ", password_hash = %(hash)s" if reset_password else ""
                    if reset_password:
                        params["hash"] = hash_password(password)
                    conn.execute(f"""UPDATE analytics.app_user
                                     SET username = %(username)s, full_name = %(full_name)s, email = %(email)s,
                                         role = %(role)s, is_active = %(active)s{set_password}
                                     WHERE user_id = %(id)s""", params)
                    updated += 1
                else:
                    params["hash"] = hash_password(password)
                    conn.execute("""INSERT INTO analytics.app_user (user_id, username, full_name, email, role,
                                                                     password_hash, is_active)
                                    VALUES (%(id)s, %(username)s, %(full_name)s, %(email)s, %(role)s,
                                            %(hash)s, %(active)s)""", params)
                    created += 1
            deactivated = conn.execute("""
                UPDATE analytics.app_user SET is_active = FALSE
                WHERE role = %s AND is_active AND NOT (user_id = ANY(%s))""",
                (ROLE_TEACHER, [a[0] for a in accounts if a[6] == ROLE_TEACHER])).rowcount
        except errors.UniqueViolation as exc:
            conn.rollback()
            raise SystemExit(f"Trùng username với một tài khoản khác trong app_user: {exc.diag.message_detail}") from exc

    print(f"Đồng bộ xong: {created} tài khoản mới, {updated} cập nhật, {deactivated} giảng viên bị vô hiệu hóa.")
    list_users()
    return 0


def set_password(username: str, password_arg: str | None) -> int:
    password = _read_password(password_arg, required=True)
    with _analytics() as conn:
        count = conn.execute("""UPDATE analytics.app_user SET password_hash = %s, password_changed_at = now()
                                WHERE lower(username) = lower(%s)""",
                             (hash_password(password), username)).rowcount
    if not count:
        raise SystemExit(f"Không tìm thấy tài khoản {username!r}")
    print(f"Đã đặt mật khẩu mới cho {username}.")
    return 0


def list_users() -> int:
    with _analytics() as conn:
        rows = conn.execute("""SELECT user_id, username, role, is_active, full_name
                               FROM analytics.app_user ORDER BY role, user_id""").fetchall()
    print(f"{'user_id':>7}  {'username':<22} {'role':<8} {'active':<6} full_name")
    for user_id, username, role, active, full_name in rows:
        print(f"{user_id:>7}  {username:<22} {role:<8} {str(active):<6} {full_name or ''}")
    return 0


def backup() -> int:
    from backend.app.services import backup as backup_service
    info = backup_service.create_backup("cli")
    print(f"Đã tạo {info.name}: {info.total_rows} dòng, {info.size_bytes / 1_048_576:.1f} MB "
          f"(thư mục {backup_service.backup_dir()})")
    return 0


def list_backups() -> int:
    from backend.app.services import backup as backup_service
    items = backup_service.list_backups()
    if not items:
        print(f"Chưa có bản sao lưu nào trong {backup_service.backup_dir()}")
    for i in items:
        print(f"{i.name:<40} {i.created_at:<26} {i.size_bytes / 1_048_576:>7.1f} MB {i.total_rows:>9} dòng  "
              f"V{i.migration_version:03d}  {i.created_by or ''}")
    return 0


def restore(name: str, yes: bool) -> int:
    from backend.app.services import backup as backup_service
    if not yes:
        answer = input(f"Toàn bộ dữ liệu hiện tại của lms_analytics sẽ bị thay bằng {name}. Gõ 'dong y' để tiếp tục: ")
        if answer.strip().lower() not in ("dong y", "đồng ý"):
            print("Đã hủy.")
            return 1
    try:
        result = backup_service.restore_backup(name)
    except backup_service.BackupError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Đã phục hồi {result['total_rows']} dòng từ {name}.")
    return 0


def messaging_check(test_email: str | None, save: bool) -> int:
    """
    Kiểm tra kênh gửi tin (chức năng 2): in cấu hình hiện hành (đã che bí mật) và chế độ hiệu lực, thử kết nối Moodle
    Web Service và máy chủ thư; --send-test-email gửi một email thử bằng ĐÚNG đường gửi của hệ thống.
    --save ghi kết quả kiểm tra vào analytics.channel_check (điều kiện 3 của chốt chặn gửi thật).
    """
    import uuid

    from common.messaging.config import (CHANNEL_EMAIL, CHANNEL_MOODLE, MODE_FILE, MessagingConfigError,
                                         load_settings)
    from common.messaging.email import DeliveryError, check_smtp, send_email
    from common.messaging.moodle import MoodleClient
    from common.messaging.outbox import effective_modes, record_check
    from etl.db import analytics_engine

    try:
        settings = load_settings()
    except MessagingConfigError as exc:
        raise SystemExit(f"Cấu hình kênh gửi tin sai: {exc}") from exc
    print("Cấu hình (đã che bí mật):")
    for key, value in settings.describe().items():
        print(f"  {key:<24} {value}")
    engine = analytics_engine()
    results = {}

    print("\nMoodle Web Service:")
    if settings.moodle_ws_url:
        try:
            info = MoodleClient(settings).site_info()
            ok = not info["missing_functions"]
            print(f"  {'OK' if ok else 'THIẾU QUYỀN'} – {info.get('sitename')} | {info.get('release')} | "
                  f"tài khoản {info.get('username')} (id {info.get('userid')})")
            if info["missing_functions"]:
                print("  Thiếu hàm:", ", ".join(info["missing_functions"]))
            results[CHANNEL_MOODLE] = (ok, {k: info.get(k) for k in ("sitename", "release", "username", "userid")})
        except DeliveryError as exc:
            print(f"  LỖI – {exc}")
            results[CHANNEL_MOODLE] = (False, {"error": str(exc)})
    else:
        print("  chưa cấu hình MOODLE_WS_URL")

    print("\nEmail:")
    try:
        if settings.mail_transport == "smtp":
            detail = check_smtp(settings)
            print(f"  Kết nối SMTP OK – {detail.get('server', '')}")
        elif settings.mail_transport == "file":
            detail = {"transport": "file", "dir": settings.mail_file_dir}
            print(f"  Chế độ file – thư được ghi vào {settings.mail_file_dir}")
        else:
            detail = None
            print("  Kênh email đang tắt")
        if detail is not None and test_email:
            mode = MODE_FILE if settings.mail_transport == "file" else "LIVE"
            delivery = send_email(settings, mode, to=test_email, to_name="", subject="[LMS Analytics] Email thử",
                                  body="Email thử từ lệnh messaging-check của LMS Analytics.",
                                  tracking_id=f"cli-{uuid.uuid4().hex[:10]}")
            print(f"  Đã gửi email thử tới {delivery.delivered_to} – Message-ID {delivery.provider_ref}")
            detail.update(message_id=delivery.provider_ref, **delivery.meta)
        if detail is not None:
            results[CHANNEL_EMAIL] = (True, detail)
    except DeliveryError as exc:
        print(f"  LỖI – {exc}")
        results[CHANNEL_EMAIL] = (False, {"error": str(exc)})

    with engine.begin() as conn:
        if save:
            for channel, (ok, detail) in results.items():
                record_check(conn, settings, channel, ok, detail, None)
        modes = effective_modes(conn, settings)
    print("\nChế độ gửi hiệu lực:")
    for channel, (mode, warnings) in modes.items():
        print(f"  {channel:<7} {mode or 'KHÔNG DÙNG ĐƯỢC'}" + ("".join(f"\n          - {w}" for w in warnings)))
    return 0 if all(ok for ok, _ in results.values()) else 1


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Quản lý tài khoản và sao lưu dữ liệu Dashboard")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync-users", help="tạo/cập nhật tài khoản ADMIN và giảng viên từ Moodle")
    sync.add_argument("--password", help="mật khẩu ban đầu cho tài khoản mới")
    sync.add_argument("--reset-password", action="store_true", help="đặt lại mật khẩu cho mọi tài khoản đồng bộ")
    sync.add_argument("--admin", action="append", dest="admins", help="username Moodle được cấp quyền ADMIN (lặp được)")
    pwd = sub.add_parser("set-password", help="đặt mật khẩu cho một tài khoản")
    pwd.add_argument("--username", required=True)
    pwd.add_argument("--password")
    sub.add_parser("list-users", help="liệt kê tài khoản")
    sub.add_parser("backup", help="sao lưu dữ liệu CSDL phân tích ra file zip")
    sub.add_parser("list-backups", help="liệt kê các bản sao lưu")
    rst = sub.add_parser("restore", help="phục hồi dữ liệu từ một bản sao lưu")
    rst.add_argument("--file", required=True, help="tên file trong thư mục sao lưu")
    rst.add_argument("--yes", action="store_true", help="không hỏi xác nhận")
    msg = sub.add_parser("messaging-check", help="kiểm tra kênh gửi tin (Moodle Web Service, máy chủ thư)")
    msg.add_argument("--send-test-email", dest="test_email", help="gửi một email thử tới địa chỉ này")
    msg.add_argument("--save", action="store_true", help="lưu kết quả kiểm tra (điều kiện gửi thật)")
    args = parser.parse_args(argv)

    if args.command == "sync-users":
        return sync_users(args.password, args.reset_password, args.admins or ["admin"])
    if args.command == "set-password":
        return set_password(args.username, args.password)
    if args.command == "backup":
        return backup()
    if args.command == "list-backups":
        return list_backups()
    if args.command == "restore":
        return restore(args.file, args.yes)
    if args.command == "messaging-check":
        return messaging_check(args.test_email, args.save)
    return list_users()


if __name__ == "__main__":
    sys.exit(main())
