from __future__ import absolute_import
from celery.utils.log import get_task_logger

from mies.celery import app
from mies.data_pipes.model import load_data_pipes
from mies.data_pipes.twitter_social_feed import web_fetcher, \
    PERSONAL_TWITTER_FEED

logging = get_task_logger(__name__)


@app.task(ignore_result=True)
def invoke():
    """
    * Reads in pages all connected & active data-pipes from the DB
    * Each read page of data-pipes is sent to the web_fetcher service
    in a REST call
    """
    logging.info("Invoking data-pipes...")
    count = 0
    criteria = {"type": PERSONAL_TWITTER_FEED}
    for page in load_data_pipes(criteria=criteria):
        count += web_fetcher.pull_from_data_pipes(page)
    return "{} posts fetched..".format(count)
