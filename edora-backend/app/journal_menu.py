def system_pages(pages, inactive_slugs=()):
    slugs = {page.slug for page in pages}
    disabled = set(inactive_slugs)
    result = [("current", "Current"), ("archives", "Archives")]
    if "submissions" not in slugs and "submissions" not in disabled:
        result.append(("submission", "Submission"))
    return [(slug, title) for slug, title in result if slug not in slugs and slug not in disabled]


def menu_order(journal, pages, inactive_slugs=()):
    slugs = [page.slug for page in pages] + [slug for slug, _ in system_pages(pages,inactive_slugs)]
    saved = getattr(journal, "menu_order", None) or []
    return list(dict.fromkeys([slug for slug in saved if slug in slugs] + slugs))
