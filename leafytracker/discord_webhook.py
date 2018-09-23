import feedparser
import json

from DiscordHooks import Hook, Embed, EmbedAuthor, Color
from markdownify import markdownify as md
from os.path import isfile
from time import sleep

from leafytracker.steam import CommentsFeed


class SteamCommentsWebhook:
    def __init__(self, app_id, cache_path):
        self.app_id = app_id
        self.steam_comments = CommentsFeed(self.app_id)
        self.last_broadcasted = LastBroadcastedCache(cache_path)

    def _html_to_markdown(self, text):
        return md(text.replace("https://steamcommunity.com/linkfilter/?url=", "")).strip()

    def post(self, news_ids, user_ids, webhooks):
        news_ids = set(int(x) for x in news_ids)
        user_ids = set(int(x) for x in user_ids)
        webhooks = set(webhooks)

        for nid in news_ids:
            for comment in self.steam_comments.get(nid, user_ids):
                for webhook_url in webhooks:
                    last_broadcasted_id = self.last_broadcasted.get(webhook_url, nid)

                    if comment.cid > last_broadcasted_id:
                        Hook(
                            hook_url=webhook_url,
                            username="Steam Community",
                            avatar_url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Steam_icon_logo.svg/512px-Steam_icon_logo.svg.png",
                            embeds=[Embed(
                                color=Color.Blue,
                                title="re: {}".format(comment.title),
                                url=comment.url,
                                description=self._html_to_markdown(comment.body),
                                timestamp=comment.datetime,
                                author=EmbedAuthor(
                                    name=comment.author.name,
                                    icon_url=comment.author.avatar_url,
                                ),
                            )],
                        ).execute()

                        self.last_broadcasted.put(webhook_url, nid, comment.cid)
                        sleep(1/4)  # TODO: Ghetto rate limit of 4 per 1 second

        self.last_broadcasted.save()


class LastBroadcastedCache:
    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.db = self._open()

    def _initialize(self):
        with open(self.cache_path, "w") as f:
            json.dump({}, f)

    def _open(self):
        if not isfile(self.cache_path):
            self._initialize()

        with open(self.cache_path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.cache_path, "w") as f:
            json.dump(self.db, f)

    def get(self, webhook_url, news_id):
        if webhook_url in self.db:
            return int(self.db[webhook_url].get(str(news_id), 0))

        return 0

    def put(self, webhook_url, news_id, comment_id):
        if webhook_url not in self.db:
            self.db[webhook_url] = {}

        self.db[webhook_url][news_id] = comment_id


def run(app_ids, user_ids, webhooks, article_count=1):
    for aid in app_ids:
        news_listings = feedparser.parse("https://steamcommunity.com/games/{app_id}/rss/".format(app_id=aid))
        news_ids = {x.link.rsplit("/detail/", 1)[-1] for x in news_listings.entries[:article_count]}

        comment_hooker = SteamCommentsWebhook(aid, "steam.json")
        comment_hooker.post(
            news_ids=news_ids,
            user_ids=user_ids,
            webhooks=webhooks,
        )
