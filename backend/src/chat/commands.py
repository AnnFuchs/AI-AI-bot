import uuid
from datetime import time as dt_time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import EntryType
from src.core.logger import logger
from src.diary.schemas import DiaryEntryCreate
from src.diary.service import diary_service
from src.reminders.models import Reminder
from src.sources.models import Source
from src.users.models import User


async def handle_backend_commands(
    commands: list[dict], user: User, db: AsyncSession,
) -> None:
    """Dispatch commands coming from the AI layer."""
    for command in commands:
        command_type = command.get('command_type')
        payload = command.get('payload', {})
        try:
            if command_type == 'UPSERT_REMINDER':
                await _upsert_reminder(payload, user, db)
            elif command_type == 'SAVE_DIARY_ENTRY':
                await _save_diary_entry(payload, user, db)
            else:
                logger.warning('Unknown command type: %s', command_type)
        except Exception:
            logger.exception('Failed to handle command %s', command_type)


async def _upsert_reminder(
    payload: dict, user: User, db: AsyncSession,
) -> None:
    reminder_id = payload.get('reminder_id')
    reminder: Reminder | None = None

    if reminder_id:
        result = await db.execute(
            select(Reminder).where(
                Reminder.id == uuid.UUID(reminder_id),
                Reminder.user_id == user.id,
            ),
        )
        reminder = result.scalar_one_or_none()
        if not reminder:
            logger.warning(
                'Reminder %s not found for user %s', reminder_id, user.id,
            )
            return

    if reminder is None:
        reminder = Reminder(user_id=user.id)
        db.add(reminder)

    time_raw = payload.get('time')
    parsed_time: dt_time | None = None
    if time_raw:
        try:
            parsed_time = dt_time.fromisoformat(time_raw)
        except (ValueError, TypeError):
            logger.warning('Invalid time value from AI: %s', time_raw)

    if parsed_time is not None and parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=settings.DEFAULT_TZ)

    reminder.reminder_type = payload['reminder_type']
    reminder.med_name = payload.get('med_name')
    reminder.time = parsed_time
    reminder.days = payload.get('days') or []
    reminder.is_active = True

    await db.commit()
    logger.info(
        'Reminder upserted for user %s: %s', user.id, reminder.med_name,
    )


async def _save_diary_entry(
    payload: dict, user: User, db: AsyncSession,
) -> None:
    entry_type_raw = payload.get('entry_type')
    try:
        entry_type = EntryType(entry_type_raw)
    except ValueError:
        logger.warning('Unknown entry_type from AI: %s', entry_type_raw)
        return

    data = DiaryEntryCreate(
        entry_type=entry_type,
        entry_json=payload.get("entry_json", {}),
    )
    await diary_service.create_entry(data, user.id, db)
    logger.info('Diary entry saved for user %s: %s', user.id, entry_type)


async def get_sources(payload: dict, db: AsyncSession) -> dict:
    """Get sources for info."""
    confidence_label = payload.get('confidence_label')
    sources_raw = {s['source'] for s in payload.get('sources', [])}
    sources_formatted = []

    for file_name in sources_raw:
        db_source: Source | None = await db.scalar(
            select(Source).where(Source.source_file_name == file_name),
        )
        if db_source is None:
            logger.warning('Source not found in DB: %s', file_name)
            continue
        sources_formatted.append(
            f'{db_source.source_type} {db_source.source_name} '
            f'{db_source.source_date} {db_source.source_url} ',
        )

    return {
        'confidence_label': confidence_label, 'sources': sources_formatted,
    }
