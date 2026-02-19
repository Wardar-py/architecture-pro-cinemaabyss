import asyncio
import json
import logging
from contextlib import asynccontextmanager

from aiokafka.errors import KafkaConnectionError
from fastapi import FastAPI, HTTPException, Request
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
CONSUMER_GROUP = "event-service-group"
RETRY_INTERVAL = 5
MAX_RETRIES = 12

TOPICS_MAP = {
    "movie": "movie-events",
    "user": "user-events",
    "payment": "payment-events"
}

async def create_producer_with_retry():
    """Запускает producer, повторяя попытки при ошибках подключения."""
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await producer.start()
            logger.info("Kafka producer connected")
            return producer
        except KafkaConnectionError as e:
            logger.warning(f"Producer connection attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(RETRY_INTERVAL)
    raise RuntimeError("Could not connect producer")

async def create_consumer_with_retry():
    """Запускает consumer, повторяя попытки при ошибках подключения."""
    consumer = AIOKafkaConsumer(
        *("movie-events", "user-events", "payment-events"),
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await consumer.start()
            logger.info("Kafka consumer connected")
            return consumer
        except KafkaConnectionError as e:
            logger.warning(f"Consumer connection attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(RETRY_INTERVAL)
    raise RuntimeError("Could not connect consumer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация с повторными попытками
    producer = await create_producer_with_retry()
    consumer = await create_consumer_with_retry()
    app.state.producer = producer
    app.state.consumer = consumer

    async def consume_loop():
        try:
            async for msg in consumer:
                value = msg.value.decode()
                logger.info(f"событие: {value}")
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
        except Exception as e:
            logger.error(f"Ошибка consumer: {e}")
        finally:
            await consumer.stop()

    task = asyncio.create_task(consume_loop())
    app.state.consumer_task = task

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await producer.stop()

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    logger.info(f"Incoming request: {request.method} {request.url} Body: {body.decode('utf-8', errors='ignore')}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.post("/api/events/payment", status_code=201)
async def send_event(payload: dict):
    topic = TOPICS_MAP["payment"]
    value = json.dumps(payload).encode("utf-8")
    await app.state.producer.send(topic, value=value)
    logger.info(f"Отправлено событие: {payload}")
    return {"status": "success"}

@app.post("/api/events/movie", status_code=201)
async def send_event(payload: dict):
    topic = TOPICS_MAP["movie"]
    value = json.dumps(payload).encode("utf-8")
    await app.state.producer.send(topic, value=value)
    logger.info(f"Отправлено событие: {payload}")
    return {"status": "success"}

@app.post("/api/events/user", status_code=201)
async def send_event(payload: dict):
    topic = TOPICS_MAP["user"]
    value = json.dumps(payload).encode("utf-8")
    await app.state.producer.send(topic, value=value)
    logger.info(f"Отправлено событие: {payload}")
    return {"status": "success"}

@app.get("/api/events/health")
async def health():
    return {"status": True}