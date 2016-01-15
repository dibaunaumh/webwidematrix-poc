from datetime import timedelta
from kombu import Queue

BROKER_URL = 'redis://localhost:6379/0'

CELERY_RESULT_BACKEND = 'redis://localhost/0'
CELERY_TASK_RESULT_EXPIRES = 3600
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_CREATE_MISSING_QUEUES = True

CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default',    routing_key='task.#'),
    Queue('life_events', routing_key='life.#'),
    Queue('smell_propagation', routing_key='smell.#'),
    Queue('bldg_creation', routing_key='bldg.#'),
    Queue('data_pipes', routing_key='pipe.#'),
)
CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
CELERY_DEFAULT_ROUTING_KEY = 'task.default'

DATA_PIPES_INTERVAL = 5

CELERYBEAT_SCHEDULE = {
    'invoke_data_pipes_every_few_minutes': {
        'task': 'mies.data_pipes.twitter_social_feed.pipe.invoke',
        'schedule': timedelta(minutes=DATA_PIPES_INTERVAL),

    },
    'invoke_daily_lifecycle_manager_every_hour': {
        'task': 'mies.lifecycle_managers.daily_building.manager.invoke',
        'schedule': timedelta(minutes=3),  # FIXME: should be 1 hour
    },
    'invoke_residents_life_event_every_minute': {
        'task': 'mies.lifecycle_managers.residents_life.manager.invoke',
        'schedule': timedelta(minutes=1),
    },
    'invoke_smell_propagator_every_minute': {
        'task': 'mies.senses.smell.smell_propagator.invoke',
        'schedule': timedelta(minutes=5),
    }
}
