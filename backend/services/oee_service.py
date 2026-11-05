"""Serviço de cálculo e consulta de OEE (Overall Equipment Effectiveness)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.config import Settings, get_settings
from database.repositories import OEERepository
from src.data.validator import VALID_CELLS
from src.oee.calculator import aggregate_oee_records, calculate_oee_from_counts
from src.simulation.event_generator import infer_shift

HISTORICAL_UNAVAILABLE_REASON = (
    "O repositório histórico contém apenas leituras de sensores (dados_sensores_vulcantech_tratados.parquet) "
    "e não possui registros reais de tempo planejado, ciclo ideal, produção total/aprovada ou paradas. "
    "Conforme as regras do projeto, percentuais de OEE não são inventados a partir de sensores isolados. "
    "Para visualizar e validar o cálculo operacional de OEE no MVP, selecione a fonte 'Simulados' ou 'Todos' "
    "e inicie o Simulador Industrial ou registre eventos operacionais."
)


class OEEService:
    """Coordena a consulta de eventos de produção/paradas e o cálculo rigoroso do OEE."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repo = OEERepository(self.settings.database_url)

    def check_status(self) -> dict[str, Any]:
        """Informa o estado do serviço OEE e a quantidade de eventos operacionais registrados."""
        events = self.repo.list_production_events(limit=500)
        sim_count = sum(1 for e in events if e.get("data_source") == "simulated")
        api_count = sum(1 for e in events if e.get("data_source") == "api")
        return {
            "service_available": True,
            "historical_production_data_available": False,
            "operational_events_count": len(events),
            "simulated_events_count": sim_count,
            "api_events_count": api_count,
            "formulas": {
                "availability": "Tempo de operação / Tempo de produção planejado",
                "performance": "(Tempo de ciclo ideal × Quantidade total produzida) / Tempo de operação",
                "quality": "Quantidade de unidades boas / Quantidade total produzida",
                "oee": "Disponibilidade × Performance × Qualidade",
            },
        }

    def record_production_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Valida e persiste um evento de produção/parada no banco SQLite."""
        data = dict(payload)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        if not data.get("timestamp"):
            data["timestamp"] = now.isoformat()
        if not data.get("shift"):
            try:
                dt = datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))
            except ValueError:
                dt = now
            data["shift"] = infer_shift(dt)

        metrics = calculate_oee_from_counts(
            planned_time_min=float(data["planned_time_min"]),
            downtime_min=float(data["downtime_min"]),
            ideal_cycle_time_min=float(data.get("ideal_cycle_time_min", 0.25)),
            total_count=int(data["total_count"]),
            good_count=int(data["good_count"]),
        )
        data["rejected_count"] = int(data["total_count"]) - int(data["good_count"])
        event_id = self.repo.insert_production_event(data)
        return {
            "event_id": event_id,
            "event": data,
            "event_oee": metrics,
        }

    def get_summary(
        self,
        equipment_id: str | None = None,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str = "historical",
    ) -> dict[str, Any]:
        """Calcula os KPIs consolidados de OEE respeitando a origem dos dados e os filtros."""
        if start_date and end_date and start_date[:10] > end_date[:10]:
            raise ValueError("Intervalo de datas inválido: start_date não pode ser posterior a end_date.")

        filters = {
            "equipment_id": equipment_id or "Todas",
            "shift": shift or "Todos",
            "start_date": start_date,
            "end_date": end_date,
            "data_source": data_source,
        }

        if data_source == "historical":
            return {
                "available": False,
                "status": "historical_source_unavailable",
                "reason": HISTORICAL_UNAVAILABLE_REASON,
                "data_source": "historical",
                "records_count": 0,
                "filters_applied": filters,
                "metrics": {
                    "availability": None,
                    "performance": None,
                    "quality": None,
                    "oee": None,
                    "planned_time_min": None,
                    "operating_time_min": None,
                    "downtime_min": None,
                    "total_count": None,
                    "good_count": None,
                    "rejected_count": None,
                },
                "last_timestamp": None,
                "notes": [
                    "Nenhum dado fictício é exibido como histórico real.",
                    "Ative o simulador ou selecione a fonte 'simulated'/'all' para inspecionar cálculos operacionais demonstrativos.",
                ],
            }

        records = self.repo.list_production_events(
            equipment_id=equipment_id,
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=1000,
        )

        agg = aggregate_oee_records(records)
        if not agg["available"]:
            reason = (
                "Não há eventos operacionais ou simulados registrados para os filtros selecionados. "
                "Use o controle de Simulação Industrial para gerar lotes operacionais identificados como simulados "
                "ou envie registros via POST /api/v1/oee/events."
                if agg["status"] == "no_production_records"
                else agg["reason"]
            )
            return {
                "available": False,
                "status": agg["status"],
                "reason": reason,
                "data_source": data_source,
                "records_count": len(records),
                "filters_applied": filters,
                "metrics": {
                    "availability": agg.get("availability"),
                    "performance": agg.get("performance"),
                    "quality": agg.get("quality"),
                    "oee": agg.get("oee"),
                    "planned_time_min": agg.get("planned_time_min"),
                    "operating_time_min": agg.get("operating_time_min"),
                    "downtime_min": agg.get("downtime_min"),
                    "total_count": agg.get("total_count"),
                    "good_count": agg.get("good_count"),
                    "rejected_count": agg.get("rejected_count"),
                },
                "last_timestamp": records[0]["timestamp"] if records else None,
                "notes": [],
            }

        sources_present = sorted({r.get("data_source", "simulated") for r in records})
        notes = ["Fórmulas oficiais: Disponibilidade × Performance × Qualidade (agregação ponderada por somas físicas)."]
        if "simulated" in sources_present:
            notes.append("ATENÇÃO: Contém registros gerados pelo Simulador Industrial (identificados como 'simulated').")

        return {
            "available": True,
            "status": "ok",
            "reason": None,
            "data_source": data_source,
            "records_count": len(records),
            "filters_applied": filters,
            "metrics": {
                "availability": agg["availability"],
                "performance": agg["performance"],
                "quality": agg["quality"],
                "oee": agg["oee"],
                "planned_time_min": agg["planned_time_min"],
                "operating_time_min": agg["operating_time_min"],
                "downtime_min": agg["downtime_min"],
                "total_count": agg["total_count"],
                "good_count": agg["good_count"],
                "rejected_count": agg["rejected_count"],
            },
            "last_timestamp": records[0]["timestamp"] if records else None,
            "notes": notes,
        }

    def get_history(
        self,
        equipment_id: str | None = None,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str = "historical",
        limit: int = 200,
    ) -> dict[str, Any]:
        """Retorna a série temporal de OEE lote a lote para construção dos gráficos."""
        if data_source == "historical":
            return {
                "available": False,
                "data_source": "historical",
                "reason": HISTORICAL_UNAVAILABLE_REASON,
                "series": [],
            }

        records = self.repo.list_production_events(
            equipment_id=equipment_id,
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=limit,
        )
        if not records:
            return {
                "available": False,
                "data_source": data_source,
                "reason": "Nenhum registro de produção encontrado para o período e fonte selecionados.",
                "series": [],
            }

        series = []
        for row in reversed(records):
            calc = calculate_oee_from_counts(
                planned_time_min=float(row["planned_time_min"]),
                downtime_min=float(row["downtime_min"]),
                ideal_cycle_time_min=float(row["ideal_cycle_time_min"]),
                total_count=int(row["total_count"]),
                good_count=int(row["good_count"]),
            )
            series.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "id_celula": row["id_celula"],
                    "liga_metalica": row["liga_metalica"],
                    "shift": row["shift"],
                    "availability": calc["availability"],
                    "performance": calc["performance"],
                    "quality": calc["quality"],
                    "oee": calc["oee"],
                    "planned_time_min": calc.get("planned_time_min"),
                    "operating_time_min": calc.get("operating_time_min"),
                    "downtime_min": calc.get("downtime_min"),
                    "total_count": calc.get("total_count"),
                    "good_count": calc.get("good_count"),
                    "rejected_count": calc.get("rejected_count"),
                    "data_source": row["data_source"],
                }
            )
        return {
            "available": True,
            "data_source": data_source,
            "reason": None,
            "series": series,
        }

    def get_by_equipment(
        self,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str = "historical",
    ) -> dict[str, Any]:
        """Calcula indicadores OEE agrupados por célula de manufatura."""
        if data_source == "historical":
            return {
                "available": False,
                "data_source": "historical",
                "reason": HISTORICAL_UNAVAILABLE_REASON,
                "equipment": [],
            }

        records = self.repo.list_production_events(
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=1000,
        )
        if not records:
            return {
                "available": False,
                "data_source": data_source,
                "reason": "Nenhum registro operacional encontrado.",
                "equipment": [],
            }

        breakdown = []
        for cell in sorted(VALID_CELLS):
            cell_rows = [r for r in records if r["id_celula"] == cell]
            agg = aggregate_oee_records(cell_rows)
            breakdown.append(
                {
                    "id_celula": cell,
                    "records_count": len(cell_rows),
                    "available": agg["available"],
                    "availability": agg["availability"],
                    "performance": agg["performance"],
                    "quality": agg["quality"],
                    "oee": agg["oee"],
                    "planned_time_min": agg["planned_time_min"],
                    "operating_time_min": agg["operating_time_min"],
                    "downtime_min": agg["downtime_min"],
                    "total_count": agg["total_count"],
                    "good_count": agg["good_count"],
                    "rejected_count": agg["rejected_count"],
                }
            )
        return {
            "available": True,
            "data_source": data_source,
            "reason": None,
            "equipment": breakdown,
        }

    def get_downtime_analysis(
        self,
        equipment_id: str | None = None,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str = "historical",
    ) -> dict[str, Any]:
        """Consolida tempos e motivos de parada registrados."""
        if data_source == "historical":
            return {
                "available": False,
                "data_source": "historical",
                "total_downtime_min": 0.0,
                "by_reason": [],
                "recent_stops": [],
            }

        records = self.repo.list_production_events(
            equipment_id=equipment_id,
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=500,
        )
        if not records:
            return {
                "available": False,
                "data_source": data_source,
                "total_downtime_min": 0.0,
                "by_reason": [],
                "recent_stops": [],
            }

        total_down = round(sum(float(r["downtime_min"]) for r in records), 2)
        reasons_map: dict[str, dict[str, Any]] = {}
        stops = []

        for r in records:
            down = float(r["downtime_min"])
            if down <= 0:
                continue
            reason = r.get("downtime_reason") or "Microparada / Ajuste operacional"
            entry = reasons_map.setdefault(reason, {"reason": reason, "downtime_min": 0.0, "occurrences": 0})
            entry["downtime_min"] = round(entry["downtime_min"] + down, 2)
            entry["occurrences"] += 1
            stops.append(
                {
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "id_celula": r["id_celula"],
                    "shift": r["shift"],
                    "downtime_min": down,
                    "downtime_reason": reason,
                    "data_source": r["data_source"],
                }
            )

        by_reason = sorted(reasons_map.values(), key=lambda x: x["downtime_min"], reverse=True)
        return {
            "available": True,
            "data_source": data_source,
            "total_downtime_min": total_down,
            "by_reason": by_reason,
            "recent_stops": stops[:50],
        }

    def get_events(
        self,
        equipment_id: str | None = None,
        shift: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_source: str = "all",
        limit: int = 100,
    ) -> dict[str, Any]:
        """Lista os eventos de produção e paradas registrados."""
        if data_source == "historical":
            return {"available": False, "data_source": "historical", "count": 0, "items": []}
        items = self.repo.list_production_events(
            equipment_id=equipment_id,
            shift=shift,
            start_date=start_date,
            end_date=end_date,
            data_source=data_source,
            limit=limit,
        )
        return {
            "available": len(items) > 0,
            "data_source": data_source,
            "count": len(items),
            "items": items,
        }

