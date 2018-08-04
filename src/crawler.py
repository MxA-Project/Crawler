"""
Python + Redis Instagram usernames followers count crawler
"""
import re
import random
import time
import requests
import redis # and redis depend optionnaly on hiredis for performances (see github)
from apscheduler.schedulers.background import BackgroundScheduler


def main():
    """Main function"""
    # Connect to RedisDB
    redis_db = redis.StrictRedis(host='redis', port=6379, db=0)
    # Initialize scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    # Essential data initialization
    try:
        usernames_list = get_usernames(redis_db, "usernames")
    except ConnectionError:
        print("Error connecting to db to get usernames list")
        exit()

    headers_list = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
                    "(KHTML, like Gecko)Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
                    "Mozilla/5.0 (Windows NT 6.1; Win64; rv:59.0) Gecko/20100101 Firefox/59.0",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; rv:60.0) Gecko/20100101 Firefox/60.0"]
    proxies_list = ["127.0.0.1:10000"] # HTTPS proxies

    for i in usernames_list:
        scheduler.add_job(crawl_username_job, 'interval',
                          args=[i, headers_list, proxies_list, redis_db], seconds=3,
                          timezone="Europe/Paris", max_instances=20000)
        print("launched crawl job for " + i)
        time.sleep(2/len(usernames_list))

    # Maintain main thread alive and actualize usernames_list
    try:
        while True:
            time.sleep(100)
            usernames_list = get_usernames(redis_db, "usernames")
    except (KeyboardInterrupt, SystemExit):
        # We shutdown the scheduler
        print('shutdown, please wait for correct exit')
        scheduler.shutdown()

####################################################################
#                       Database functions                         #
####################################################################

def get_usernames(redis_db, usernames_list_redis):
    """
    To read the usernames to crawl (get all the items of the "usernames" list),
    return a list of strings
    """
    try:
        # Get a the list of usernames as bytes
        usernames = redis_db.lrange(usernames_list_redis, 0, -1)
    except ConnectionError:
        return False
    else:
        # Convert bytes to string
        for i, _ in enumerate(usernames):
            usernames[i] = usernames[i].decode("utf-8")
        return usernames

def update_followers_count(redis_db, username, count):
    """
    Update followers count of a given username,
    return 1 (True)
    """
    try:
        return redis_db.hset(username, "followcount", count)
    except ConnectionError:
        return False

####################################################################
#                       Crawling functions                         #
####################################################################

def get_followers_count(username, header_data, proxy_data):
    """
    Get the followers count number of an Instagram username
    return string
    """
    base_url = "https://instagram.com/" + username
    # Make IG request
    try:
        request = requests.get(base_url, headers=header_data, proxies=proxy_data)
        # proxies={'https': 'ip:port'})
    except ConnectionError:
        # Network or IG Downtime
        print("no network or ig downtime : may need DEBUG ")
        request = ""

    if request.status_code == 200:
        # Extract count from "edge_followed_by":{"count":71101},"followed_by_viewer"#
        try:
            followers_count = re.search('"edge_followed_by":{"count":(.+?)},"followed_by_viewer"',
                                        request.text).group(1)
        except AttributeError:
            # Before and after not found in the original string
            followers_count = None
        else:
            return followers_count
    return False


def spoofed_header(headers_list):
    """
    Generate a random spoofed header from a list
    """
    if isinstance(headers_list, list) and headers_list:
        return {"User-Agent": random.choice(headers_list)}

    return {"User-Agent":"Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 " +
                         "(KHTML, like Gecko) Chrome/66.0.3359.387 Safari/537.36"}


def random_proxy(proxies_list):
    """ Generate a random proxy """
    if isinstance(proxies_list, list) and proxies_list:
        return {"https": random.choice(proxies_list)}

    return None

def crawl_username_job(username, headers_list, proxies_list, redis_db):
    """
    Crawl and update an username' follow count
    """
    try:
        followers_count = get_followers_count(username, spoofed_header(headers_list),
                                           random_proxy(proxies_list))
    except ConnectionError:
        return "Failed to get follow count"
    if followers_count != False and followers_count != None:
        try:
            update_followers_count(redis_db, username, followers_count)
        except ConnectionError:
            return "Failed to update followers count on Redis"

    return True

if __name__ == '__main__':
    main()
