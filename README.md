# leafytracker

A set of tools to aggregate Leafy Games' developer posts for PULSAR: Lost Colony.

## Requirements

 * Python 3 with `pip` and `virtualenv`

## Installation

```bash
$ git clone https://github.com/TomRichter/leafytracker.git
$ cd leafytracker

$ virtualenv env --python=/path/to/python3
$ . env/bin/activate  # On Windows: env\Scripts\activate
(env) $ pip install -r requirements.txt
```

## Configuration

Edit `config.json` to add Discord `webhooks` to pipe to, `app_ids` of games to watch, and `user_ids` of Steam News Commentors to filter by.

`app_ids` come from the official game ID on Steam, and can be found in many URLs (e.g., `252870` in `https://store.steampowered.com/app/252870/PULSAR_Lost_Colony/`)

`user_ids` come from the `data-miniprofile` attribute of a comment's author link, not actual Steam user IDs.  If left empty, all comments on an article will be posted.

```json
{
    "webhooks": [
        "https://discordapp.com/api/webhooks/123456/abc123"
    ],
    "app_ids": [
        1234567890
    ],
    "user_ids": [
        1234567890
    ]
}
```

## Running

```
. bin/leafytracker
```

or

```
python3 -m leafytracker
```

`leafytracker` quits after a single pass, and is best used with a periodic execution tool like `cron` to check for updates regularly:

```bash
$ crontab -e

# Every 20 minutes
*/20 * * * * /path/to/leafytracker/bin/leafytracker
```

## Important files

 * `leafytracker.log` - Info and debug log.  Always appended to, so consider log rotation to avoid large log files.
 * `steam.json` - Tracks the latest comment ID sent from each news article to each webhook.  Take care when deleting this to avoid repeat messages/spam!
