"""
API-калькулятор на FastAPI.
Запуск локально:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

import ast
import math
import operator
import time
from collections import deque
from threading import Lock
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Конфигурация приложения

app = FastAPI(
    title="Calculator API",
    description="Производительный API-калькулятор с поддержкой базовых операций "
                "и вычисления произвольных выражений.",
    version="1.0.0",
)

# CORS - разрешаем обращения из браузера/других сервисов 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_HISTORY_SIZE = 100
_history: deque = deque(maxlen=MAX_HISTORY_SIZE)
_history_lock = Lock()

START_TIME = time.time()

# Схемы запросов/ответов (Pydantic)

class TwoOperandRequest(BaseModel):
    a: float = Field(..., description="Первый операнд")
    b: float = Field(..., description="Второй операнд")


class OneOperandRequest(BaseModel):
    a: float = Field(..., description="Операнд")


class ExpressionRequest(BaseModel):
    expression: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Математическое выражение, например '(2 + 3) * 4 / 2'",
    )


class CalculationResult(BaseModel):
    operation: str
    result: float
    execution_time_ms: float


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float


# Вспомогательные функции

def _record_history(operation: str, result: float) -> None:
    with _history_lock:
        _history.append({
            "operation": operation,
            "result": result,
            "timestamp": time.time(),
        })


def _timed(func, *args):
    start = time.perf_counter()
    result = func(*args)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, elapsed_ms


# Безопасное вычисление произвольных выражений через ast (без eval/exec)
_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Разрешены только числовые константы")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise ValueError(f"Оператор {op_type.__name__} не разрешён")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        try:
            return _ALLOWED_BIN_OPS[op_type](left, right)
        except ZeroDivisionError:
            raise ValueError("Деление на ноль")
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise ValueError(f"Унарный оператор {op_type.__name__} не разрешён")
        return _ALLOWED_UNARY_OPS[op_type](_safe_eval(node.operand))
    raise ValueError(f"Недопустимый элемент выражения: {type(node).__name__}")


def safe_calculate_expression(expression: str) -> float:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ValueError("Синтаксическая ошибка в выражении")
    return _safe_eval(parsed)


# Эндпоинты: базовые операции

@app.post("/api/v1/add", response_model=CalculationResult, tags=["operations"])
async def add(req: TwoOperandRequest):
    result, elapsed = _timed(operator.add, req.a, req.b)
    _record_history(f"{req.a} + {req.b}", result)
    return CalculationResult(operation=f"{req.a} + {req.b}", result=result, execution_time_ms=elapsed)


@app.post("/api/v1/subtract", response_model=CalculationResult, tags=["operations"])
async def subtract(req: TwoOperandRequest):
    result, elapsed = _timed(operator.sub, req.a, req.b)
    _record_history(f"{req.a} - {req.b}", result)
    return CalculationResult(operation=f"{req.a} - {req.b}", result=result, execution_time_ms=elapsed)


@app.post("/api/v1/multiply", response_model=CalculationResult, tags=["operations"])
async def multiply(req: TwoOperandRequest):
    result, elapsed = _timed(operator.mul, req.a, req.b)
    _record_history(f"{req.a} * {req.b}", result)
    return CalculationResult(operation=f"{req.a} * {req.b}", result=result, execution_time_ms=elapsed)


@app.post("/api/v1/divide", response_model=CalculationResult, tags=["operations"])
async def divide(req: TwoOperandRequest):
    if req.b == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Деление на ноль невозможно",
        )
    result, elapsed = _timed(operator.truediv, req.a, req.b)
    _record_history(f"{req.a} / {req.b}", result)
    return CalculationResult(operation=f"{req.a} / {req.b}", result=result, execution_time_ms=elapsed)


@app.post("/api/v1/power", response_model=CalculationResult, tags=["operations"])
async def power(req: TwoOperandRequest):
    try:
        result, elapsed = _timed(operator.pow, req.a, req.b)
    except OverflowError:
        raise HTTPException(status_code=400, detail="Результат слишком велик")
    _record_history(f"{req.a} ^ {req.b}", result)
    return CalculationResult(operation=f"{req.a} ^ {req.b}", result=result, execution_time_ms=elapsed)


@app.post("/api/v1/sqrt", response_model=CalculationResult, tags=["operations"])
async def sqrt(req: OneOperandRequest):
    if req.a < 0:
        raise HTTPException(status_code=400, detail="Извлечение корня из отрицательного числа невозможно")
    result, elapsed = _timed(math.sqrt, req.a)
    _record_history(f"sqrt({req.a})", result)
    return CalculationResult(operation=f"sqrt({req.a})", result=result, execution_time_ms=elapsed)


# Эндпоинт: произвольное выражение

@app.post("/api/v1/calculate", response_model=CalculationResult, tags=["operations"])
async def calculate_expression(req: ExpressionRequest):
    try:
        result, elapsed = _timed(safe_calculate_expression, req.expression)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Деление на ноль")
    _record_history(req.expression, result)
    return CalculationResult(operation=req.expression, result=result, execution_time_ms=elapsed)


# Служебные эндпоинты

@app.get("/api/v1/history", tags=["service"])
async def get_history(limit: Optional[int] = 20):
    with _history_lock:
        items = list(_history)[-limit:]
    return {"count": len(items), "items": items}


@app.get("/health", response_model=HealthResponse, tags=["service"])
async def health():
    return HealthResponse(status="ok", uptime_seconds=time.time() - START_TIME)


@app.get("/", tags=["service"])
async def root():
    return {
        "service": "Calculator API",
        "docs": "/docs",
        "health": "/health",
    }
