"""
Модуль для мониторинга и анализа соединений с базой данных.
Предоставляет инструменты для сбора статистики, метрик производительности
и обнаружения "узких мест" при работе с БД в высоконагруженных сценариях.
"""

import time
from datetime import datetime
import threading
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("app.db.stats")

class ConnectionStats:
    """Класс для сбора и анализа статистики соединений с БД"""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._active_connections: Dict[int, Tuple[datetime, str]] = {}
        self._connection_times: List[float] = []
        self._long_queries: List[Tuple[float, str, datetime]] = []
        self._queries_per_second: Dict[int, int] = {}  # секунда -> количество
        self._last_cleanup = time.time()
        
    def register_connection(self, conn_id: int, query_info: str = "") -> None:
        """Регистрирует новое соединение с базой данных"""
        with self._lock:
            self._active_connections[conn_id] = (datetime.now(), query_info)
            # Обновляем статистику RPS
            current_second = int(time.time())
            self._queries_per_second[current_second] = self._queries_per_second.get(current_second, 0) + 1
            
    def release_connection(self, conn_id: int) -> Optional[float]:
        """Отмечает соединение как закрытое и возвращает длительность"""
        with self._lock:
            if conn_id in self._active_connections:
                start_time, query_info = self._active_connections.pop(conn_id)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Сохраняем длительность для расчета метрик
                self._connection_times.append(duration)
                if len(self._connection_times) > 1000:
                    self._connection_times = self._connection_times[-1000:]
                
                # Отслеживаем долгие запросы (более 0.5 секунды)
                if duration > 0.5:
                    self._long_queries.append((duration, query_info, start_time))
                    # Оставляем только последние 100 долгих запросов
                    if len(self._long_queries) > 100:
                        self._long_queries = self._long_queries[-100:]
                
                return duration
            return None
            
    def cleanup_old_data(self) -> None:
        """Очищает устаревшие данные и соединения"""
        current_time = time.time()
        # Выполняем очистку не чаще раза в 60 секунд
        if current_time - self._last_cleanup < 60:
            return
            
        with self._lock:
            # Очищаем статистику RPS старше 5 минут
            cutoff_second = int(current_time) - 300
            self._queries_per_second = {
                sec: count for sec, count in self._queries_per_second.items()
                if sec > cutoff_second
            }
            
            # Проверяем зависшие соединения (активны более 5 минут)
            now = datetime.now()
            stuck_connections = [
                conn_id for conn_id, (start_time, _) in self._active_connections.items()
                if (now - start_time).total_seconds() > 300
            ]
            
            if stuck_connections:
                logger.warning(f"Обнаружено {len(stuck_connections)} возможно зависших соединений")
                
            self._last_cleanup = current_time
            
    def get_stats(self) -> Dict:
        """Возвращает текущую статистику соединений"""
        with self._lock:
            self.cleanup_old_data()
            
            # Рассчитываем средний RPS за последние 60 секунд
            current_second = int(time.time())
            last_minute_seconds = list(range(current_second - 60, current_second))
            total_requests = sum(self._queries_per_second.get(sec, 0) for sec in last_minute_seconds)
            average_rps = total_requests / 60.0 if last_minute_seconds else 0
            
            # Рассчитываем средние времена выполнения запросов
            avg_query_time = sum(self._connection_times) / len(self._connection_times) if self._connection_times else 0
            
            # Находим 95-й перцентиль для времени выполнения запросов
            p95_query_time = 0
            if self._connection_times:
                sorted_times = sorted(self._connection_times)
                p95_index = int(len(sorted_times) * 0.95)
                p95_query_time = sorted_times[p95_index]
                
            return {
                "active_connections": len(self._active_connections),
                "average_rps": average_rps,
                "average_query_time": avg_query_time,
                "p95_query_time": p95_query_time,
                "long_queries_count": len(self._long_queries),
                "top_long_queries": sorted(self._long_queries, reverse=True)[:5]
            }

# Глобальный экземпляр для сбора статистики
db_stats = ConnectionStats()

def get_connection_stats() -> ConnectionStats:
    """Возвращает глобальный экземпляр сборщика статистики"""
    return db_stats
