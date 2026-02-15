"""
Scraper configuration — URLs, selectors, timeouts.
"""

SCRAPER_CONFIG = {
    "base_url": "https://anc.apm.activecommunities.com/denver/activity/search",
    "search_params": {
        "onlineSiteId": "0",
        "activity_select_param": "2",
        "activity_keyword": "Carla Madison",
        "viewMode": "list",
    },
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "page_load_timeout": 60,
    "post_load_delay": 5,
    "selectors": {
        "schedule_table": "table.activity-list, table[class*='schedule']",
        "schedule_row": "tr[data-activity-id], tbody tr",
        "fallback_row": "tr",
    },
    "max_retries": 3,
    "retry_delay": 10,
}


def build_url() -> str:
    from urllib.parse import urlencode
    params = urlencode(SCRAPER_CONFIG["search_params"])
    return f"{SCRAPER_CONFIG['base_url']}?{params}"
