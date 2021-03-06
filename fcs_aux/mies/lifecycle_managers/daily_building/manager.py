from datetime import datetime
from celery.utils.log import get_task_logger
from mies.celery import app
from mies.data_pipes.model import update_data_pipe, STATUS_ACTIVE
from mies.lifecycle_managers.daily_building import \
    DAILY_FEED_DISPATCHER_LIFEYCLE_MANAGER
from mies.mongo_config import get_db
from mies.buildings.model import create_buildings
from mies.redis_config import get_cache

logging = get_task_logger(__name__)

DAILY_FEED = "daily-feed"


def format_date(d):
    return d.strftime('%Y-%b-%d')


def _create_bldg(target_flr, today, data_pipe):
    payload = {
        "date": today,
        "data_pipes": [data_pipe["type"]]
    }
    address = create_buildings(flr=target_flr, content_type=DAILY_FEED, heads=[dict(key=today)],
                               bodies=[dict(summary_payload=payload, raw_payload=payload,
                                            result_payload=payload)],
                               position_hints={"next_free": True},
                               is_composite=True)
    if type(address) == list:
        address = address[0]
    return address


def _update_data_pipe(address, data_pipe):
    update_data_pipe(data_pipe["_id"], {
        "connectedBldg": address
    })


def _build_user_current_bldg_cache_key(user_id):
    """
    returns a cache key for mapping a user's id to his current
    bldg address, which is also the cache key of the current bldg.
    """
    return "USER_CURRENT_ADDRESS::{user_id}"\
        .format(user_id=user_id)


def create_daily_bldg(db, today, manager):
    user_id = manager["userId"]
    # FIXME: support more than one data-pipe
    data_pipe = db.data_pipes.find_one({"_id": manager["dataPipe"]})
    if data_pipe is None or data_pipe.get("status") != STATUS_ACTIVE:
        # no need to create daily bldg if the data-pipe isn't active
        return
    user_bldg = db.buildings.find_one({"_id": manager["bldg"]})
    user_bldg_address = user_bldg["address"]
    target_flr = "{}-l0".format(user_bldg_address)
    existing_bldg = db.buildings.find_one({
        "flr": target_flr,
        "key": today
    })
    if existing_bldg is None:
        logging.info("Creating daily bldg '{today}' "
                     "inside {address}"
                     .format(today=today, address=user_bldg_address))
        address = _create_bldg(target_flr, today, data_pipe)
        _update_data_pipe(address, data_pipe)
    else:
        address = existing_bldg["address"]

    # in order to look up a user's current bldg in the cache,
    # add a cache key storing the current bldg for each user
    cache = get_cache()
    existing_bldg_in_cache = cache.get(_build_user_current_bldg_cache_key(user_id))
    if existing_bldg_in_cache is None or existing_bldg_in_cache != address:
        cache.set(_build_user_current_bldg_cache_key(user_id), address)
        # no need to delete yesterday's daily bldg, because it will expire anyway



@app.task(ignore_result=True)
def invoke():
    """
    Loops over all users and:
    * Looks up an existing bldg for the current date
    * If not found, creates one, next to the previous day
    * Connects any data-pipes for this user to the created bldg
    """
    logging.info("Invoking daily-bldg lifecycle manager...")
    today = format_date(datetime.utcnow())
    db = get_db()
    managers = db.lifecycle_managers.find(
        {"type": DAILY_FEED_DISPATCHER_LIFEYCLE_MANAGER}
    )
    # TODO read & process in batches
    for manager in managers:
        create_daily_bldg(db, today, manager)
