from feedgen.feed import FeedGenerator
from leafytracker.steam import CommentsFeed


class SteamCommentsRss:
    def __init__(self, app_id):
        self.app_id = app_id
        self.steam_comments = CommentsFeed(app_id)

        self.feed = FeedGenerator()
        self.feed.id("https://steamcommunity.com/games/{app_id}/allnews/".format(app_id=self.app_id))
        self.feed.title("PULSAR: Lost Colony Developer Comments on Steam")
        self.feed.link(href="https://pulsar.wiki/leafytracker/")
        self.feed.description("Comments by leafygamesdev on PULSAR news articles.")
        self.feed.language("en")
        self.feed.generator("https://pulsar.wiki/leafytracker/") # TODO: Automate project name and version

    def append_comments(self, news_ids, user_ids):
        news_ids = set(int(x) for x in news_ids)
        user_ids = set(int(x) for x in user_ids)

        for nid in news_ids:
            for comment in self.steam_comments.get(nid, user_ids):
                entry = self.feed.add_entry()
                entry.id(str(comment.cid))
                entry.link({"href": comment.url})
                entry.title("{} commented on {}".format(comment.author.name, comment.title))
                entry.author({"name": comment.author.name})
                entry.published(comment.datetime)
                entry.content(comment.body)

    def to_atom(self, output_path, pretty=True):
        return self.feed.atom_file(output_path, pretty=pretty)

    def to_rss(self, output_path, pretty=True):
        return self.feed.rss_file(output_path, pretty=pretty)


if __name__ == "__main__":
    steam = SteamCommentsRss(252870)
    steam.append_comments(news_ids={1702811255219116398}, user_ids={257266967})
    steam.to_atom("steam.atom")

