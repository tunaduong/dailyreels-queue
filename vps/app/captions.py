"""Caption / tiêu đề / hashtag theo chuẩn từng nền tảng."""

def _tags(script, ch, n=6):
    tags = list(dict.fromkeys([*script["post"].get("hashtags", []), *ch.get("hashtags_base", [])]))
    return ["#" + t for t in tags[:n]]

def build(script, ch):
    p = script["post"]; title = p.get("title", "").strip(); cap = p.get("caption", "").strip()
    disc = ch.get("disclaimer", ""); src = p.get("sources", [])[:3]
    yt_title = (title[:90] + " #Shorts") if len(title) <= 90 else title[:88] + "… #Shorts"
    yt_desc = "\n\n".join(x for x in [cap, "Nguồn:\n" + "\n".join(src) if src else "", disc, " ".join(_tags(script, ch, 8))] if x)
    short = f"{title}\n\n{cap}\n\n{disc}\n{' '.join(_tags(script, ch, 6))}"
    return {"youtube": {"title": yt_title[:100], "description": yt_desc[:4900], "tags": [t.lstrip('#') for t in _tags(script, ch, 10)]},
            "tiktok": {"title": short[:2100]},
            "instagram": {"caption": short[:2100]},
            "facebook": {"title": title[:250], "description": short[:5000]}}
