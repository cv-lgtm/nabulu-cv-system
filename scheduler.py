import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import (
    CHECK_INTERVAL_MINUTES, REPORT_DAY_OF_WEEK, REPORT_HOUR,
    REPORT_MINUTE, TIMEZONE
)
from mail_fetcher import fetch_and_process_emails
from report_generator import send_weekly_report

def setup_scheduler():
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    # 1. Görev: Her X dakikada bir gelen yeni mailleri kontrol et ve analiz et
    scheduler.add_job(
        fetch_and_process_emails,
        trigger=IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES),
        id="mail_fetcher_job",
        name="Mail Kontrolü & CV Analizi",
        replace_existing=True
    )

    # 2. Görev: Her Pazartesi saat 10:00'da (TSİ) haftalık raporu gönder
    scheduler.add_job(
        send_weekly_report,
        trigger=CronTrigger(
            day_of_week=REPORT_DAY_OF_WEEK,
            hour=REPORT_HOUR,
            minute=REPORT_MINUTE,
            timezone=TIMEZONE
        ),
        id="weekly_report_job",
        name="Pazartesi 10:00 Haftalık Rapor",
        replace_existing=True
    )

    return scheduler
