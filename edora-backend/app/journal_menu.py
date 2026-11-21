def system_pages(pages):
    slugs = {page.slug for page in pages}
    result = [("current", "Current"), ("archives", "Archives")]
    if "submissions" not in slugs:
        result.append(("submission", "Submission"))
    return [(slug, title) for slug, title in result if slug not in slugs]


def menu_order(journal, pages):
    slugs = [page.slug for page in pages] + [slug for slug, _ in system_pages(pages)]
    saved = getattr(journal, "menu_order", None) or []
    return list(dict.fromkeys([slug for slug in saved if slug in slugs] + slugs))
