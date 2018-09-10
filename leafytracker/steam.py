import re
import requests
import logging

from bs4 import BeautifulSoup
from datetime import datetime, timezone


logger = logging.getLogger("steam.py")

logging.basicConfig(
    filename="{}.log".format("steam"),
    format="%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


class Author:
    def __init__(self, uid, name, avatar_url):
        self.uid = uid
        self.name = name
        self.avatar_url = avatar_url

    def __eq__(self, other):
        if isisntance(other, Author):
            return self.uid == other.uid

        return False

    def __str__(self):
        return "<Author: {} ({})>".format(self.name, self.uid)


class Comment:
    def __init__(self, cid, author, datetime, body):
        self.cid = cid
        self.author = author
        self.datetime = datetime
        self.body = body

    def timestamp(self, time_format="%b %-d, %Y at %-I:%M:%S %p %Z"):
        return self.datetime.strftime(time_format)

    def __lt__(self, other):
        if isinstance(other, Comment):
            return self.datetime < other.datetime

        raise ValueError("Can't compare {} with {}".format(type(other).__name__, type(self).__name__))

    def __eq__(self, other):
        if isinstance(other, Comment):
            return self.cid == other.cid

        return False

    def __str__(self):
        return "<Comment {} by {} on {}>".format(
            self.cid,
            self.author.name,
            self.timestamp
        )

class CommentsFeed:
    RE_COMMENT_ID = re.compile(r"^comment_([0-9]+)$")
    RE_GROUP_ID = re.compile(r"steam://friends/joinchat/([0-9]+)")

    def __init__(self, app_id):
        self.app_id = app_id
        self.cached_authors = {}
        self.all_news_url = "https://steamcommunity.com/games/{app_id}/allnews/".format(app_id=self.app_id)
        self.news_article_url = "https://steamcommunity.com/games/{app_id}/announcements/detail/{post_id}".format(
            app_id=self.app_id,
            post_id="{post_id}"
        )
        self.group_id = self._find_group_id()
        self.news_comments_url = "https://steamcommunity.com/comment/ClanAnnouncement/render/{group_id}/{post_id}".format(
            group_id = self.group_id,
            post_id = "{post_id}"
        )

    def _parse_cid(self, comment):
        """Returns the comment's post ID."""
        return int(type(self).RE_COMMENT_ID.search(comment.get("id")).group(1))

    def _parse_datetime(self, comment):
        """Returns the comment's post time as a UTC datetime."""
        tag = comment.find("span", class_="commentthread_comment_timestamp")
        utc_unix_time = int(tag.get("data-timestamp"))

        return datetime.fromtimestamp(utc_unix_time, timezone.utc)

    def _parse_body(self, comment):
        """Returns the comment's body with HTML intact."""
        tag = comment.find("div", class_="commentthread_comment_text")

        return "".join(str(x) for x in tag.contents).strip().strip("<br/>")


    def _request_comments(self, post_id, start, count):
        args = {
            "start": start,
            "count": count,
        }

        # count of 0 fetches ALL comments without checking the total size beforehand
        if not count:
            args["count"] = 0

        r = requests.post(
            url=self.news_comments_url.format(post_id=post_id),
            data=args,
        )

        if r.status_code == requests.codes.ok:
            return BeautifulSoup(r.json()["comments_html"])

    def get(self, post_id, user_ids=set(), start=0, count=None):
        """Returns a list of comments for the given post, optionally filtered by user ID."""
        soup = self._request_comments(post_id, start, count)
        filtered_comments = []

        for comment in soup.find_all("div", class_="commentthread_comment"):
            # Get author's user ID
            uid = int(comment.find("a", class_="commentthread_author_link").get("data-miniprofile"))

            # Filter comments by user
            if user_ids and uid not in user_ids:
                logger.info("Skipping comment by {}".format(uid))
                continue

            # Get author from cache
            if uid not in self.cached_authors:
                self.cached_authors[uid] = Author(
                    uid=uid,
                    name=comment.find("bdi").text,
                    avatar_url=comment.find("a", attrs={"data-miniprofile": uid}).img.get("src"),
                )

            author = self.cached_authors[uid]

            # Parse and add to collection
            logger.info("Collecting comment by {}".format(author))
            logger.debug(comment.prettify())
            filtered_comments.append(Comment(
                cid=self._parse_cid(comment),
                author=author,
                datetime=self._parse_datetime(comment),
                body=self._parse_body(comment),
            ))

        filtered_comments.sort()

        return filtered_comments

    def _find_group_id(self):
        r = requests.get(self.all_news_url)

        if r.status_code == requests.codes.ok:
            return int(type(self).RE_GROUP_ID.search(r.text).group(1))
        else:
            raise LookupError('Could not find group ID in {url}'.format(url=self.all_news_url))


if __name__ == "__main__":
    start = datetime.now()
    feed = CommentsFeed(252870)
    comments = feed.get(1702811255219116398, user_ids={257266967})

    for c in comments:
        print("{} - {}".format(c.author.name, c.timestamp()))

    print("Took {}".format(datetime.now() - start))

