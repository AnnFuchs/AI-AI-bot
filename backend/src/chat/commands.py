import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import EntryType
from src.core.logger import logger
from src.diary.schemas import DiaryEntryCreate
from src.diary.service import diary_service
from src.reminders.models import Reminder
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

    reminder.reminder_type = payload['reminder_type']
    reminder.med_name = payload.get('med_name')
    reminder.time = payload.get('time')
    reminder.days = payload.get('days', [])
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
