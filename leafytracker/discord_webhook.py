import json
from calendar import timegm as to_utc_unixtime
from datetime import datetime, timedelta, timezone
from hashlib import md5
from os.path import isfile
from time import sleep

import feedparser
from DiscordHooks import Hook, Embed, EmbedAuthor, Color
from markdownify import markdownify as md

from leafytracker.steam import CommentsFeed


def html_to_markdown(text):
    return md(text.replace("https://steamcommunity.com/linkfilter/?url=", "")).strip()


def _process_body(body, url, max_length=2048):
    body = html_to_markdown(body)

    # Discord limits message lengths to 2048 characters, so long posts need to be truncated
    if len(body) > max_length:
        footer = "\n\n[...]\n\n[Read More]({url})".format(url=url)
        # Limit body to 2048 characters - footer size, find the last clean line break, then add the footer
        body = body[:2048-len(footer)].rsplit("\n", 1)[0].strip() + footer

    return body


def rate_limit():
    sleep(1 / 4)  # TODO: Ghetto rate limit of 4 per 1 second


class SteamCommentsWebhook:
    def __init__(self, app_id, cache_path):
        self.app_id = app_id
        self.steam_comments = CommentsFeed(self.app_id)
        self.last_broadcasted = LastBroadcastedCache(cache_path)

    def post(self, news_ids, user_ids, webhooks, max_age=timedelta(days=1)):
        news_ids = set(int(x) for x in news_ids)
        user_ids = set(int(x) for x in user_ids)
        webhooks = set(webhooks)

        for nid in news_ids:
            for comment in self.steam_comments.get(nid, user_ids):
                for webhook_url in webhooks:
                    last_broadcasted_id = int(self.last_broadcasted.get(webhook_url, nid) or -1)
                    comment_age = datetime.now(timezone.utc) - comment.datetime

                    if comment.cid > last_broadcasted_id and comment_age < max_age:
                        Hook(
                            hook_url=webhook_url,
                            username="Steam Community",
                            avatar_url="https://i.imgur.com/A3dBYx9.png",
                            embeds=[Embed(
                                color=Color.Blue,
                                title="re: {}".format(comment.title),
                                url=comment.url,
                                description=html_to_markdown(comment.body),
                                timestamp=comment.datetime,
                                author=EmbedAuthor(
                                    name=comment.author.name,
                                    icon_url=comment.author.avatar_url,
                                ),
                            )],
                        ).execute()

                        self.last_broadcasted.put(webhook_url, nid, comment.cid)
                        rate_limit()

        self.last_broadcasted.save()


class FeedWebhook:
    def __init__(self, feed_url, cache_path):
        self.feed = feedparser.parse(feed_url)
        self.last_broadcasted = LastBroadcastedCache(cache_path)

    def post(self, webhooks, max_age=timedelta(days=2), force_post_count=None):
        prepped_hooks = []

        for entry in self.feed.entries[:force_post_count]:
            article_datetime = datetime.utcfromtimestamp(to_utc_unixtime(entry.published_parsed))
            article_age = datetime.now() - article_datetime

            title = entry.title
            author = entry.author
            url = entry.link
            guid = entry.id
            body = _process_body(entry.summary, url)
            entry_hash = md5(body.encode("utf-8")).hexdigest()

            for webhook_url in webhooks:
                is_modified = self._article_modified(webhook_url, guid, entry_hash)

                if not self._already_posted(webhook_url, guid) or is_modified:
                    if force_post_count or article_age < max_age or is_modified:
                        if is_modified:
                            headline = "Updated: {}".format(title)
                        else:
                            headline = "{}".format(title)

                        prepped_hooks.append(Hook(
                            hook_url=webhook_url,
                            username="Steam Community",
                            avatar_url="https://i.imgur.com/A3dBYx9.png",
                            embeds=[Embed(
                                color=Color.Blue,
                                title=headline,
                                url=url,
                                description=body,
                                timestamp=article_datetime,
                                author=EmbedAuthor(
                                    name=author,
                                ),
                            )],
                        ))
                        self.last_broadcasted.put(webhook_url, guid, entry_hash)

        for hook in reversed(prepped_hooks):
            hook.execute()
            rate_limit()

        self.last_broadcasted.save()

    def _article_modified(self, webhook_url, guid, entry_hash):
        stored_hash = self.last_broadcasted.get(webhook_url, guid)

        return stored_hash and stored_hash != entry_hash

    def _already_posted(self, webhook_url, guid):
        return self.last_broadcasted.get(webhook_url, guid) is not None


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

    def get(self, webhook_url, article_id):
        if webhook_url in self.db:
            return self.db.get(webhook_url, {}).get(str(article_id), None)

        return None

    def put(self, webhook_url, article_id, entry_id):
        if webhook_url not in self.db:
            self.db[webhook_url] = {}

        self.db[webhook_url][article_id] = str(entry_id)


def run(app_ids, user_ids, webhooks, article_count=1, max_age=timedelta(days=1)):
    rss_url = "https://steamcommunity.com/games/{app_id}/rss/"

    for aid in app_ids:
        article_hooker = FeedWebhook(rss_url.format(app_id=aid), "steam.json")
        article_hooker.post(webhooks,force_post_count=1)

        news_listings = feedparser.parse(rss_url.format(app_id=aid))
        news_ids = {x.link.rsplit("/detail/", 1)[-1] for x in news_listings.entries[:article_count]}

        comment_hooker = SteamCommentsWebhook(aid, "steam.json")
        comment_hooker.post(
            news_ids=news_ids,
            user_ids=user_ids,
            webhooks=webhooks,
            max_age=max_age,
        )
