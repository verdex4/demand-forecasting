import asyncio
import logging
from pathlib import Path
from sqlalchemy import text
from app.database import AsyncSessionLocal, fetch_query_to_df
from app.settings import REPORTS_DIR, REPORTS_URL

logger = logging.getLogger(__name__)

async def is_file_exists(file_path: str) -> bool:
    """Асинхронная проверка существования файла без блокировки event loop."""
    return await asyncio.to_thread(Path(file_path).is_file)

async def cleanup_reports():
    """Очищает отчёты из базы данных, файлов для которых не существует."""
    logger.info("Запуск очистки невалидных отчетов...")
    
    async with AsyncSessionLocal() as db:
        try:
            reports_df = await fetch_query_to_df("SELECT id, url FROM public.reports")
            
            if reports_df.empty:
                logger.info("База данных пуста. Очистка не требуется.")
                return
            
            reports_df["file_path"] = (
                reports_df["url"]
                .astype(str)
                .str.replace(pat=str(REPORTS_URL), repl=str(REPORTS_DIR), regex=False)
            )

            ids_to_delete = []
            for report in reports_df.to_dict(orient="records"):
                report_id = report.get("id")
                file_path = report.get("file_path")
                
                if not file_path or not await is_file_exists(file_path):
                    if report_id:
                        ids_to_delete.append(report_id)

            if ids_to_delete:
                query = text("DELETE FROM public.reports WHERE id = ANY(:ids)")
                await db.execute(query, {"ids": ids_to_delete})
                await db.commit()
                logger.info(f"Очистка завершена. Удалено записей: {len(ids_to_delete)}")
            else:
                logger.info("Очистка завершена. Невалидных записей не найдено.")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке отчетов: {e}")
            await db.rollback()