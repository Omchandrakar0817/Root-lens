from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.safe_http import FetchResult, safe_fetch


def analyze_html(page: FetchResult, page_url: str) -> dict:
    findings: list[dict] = []
    if not page.body or (page.status_code or 0) >= 400:
        return {
            "title": None,
            "meta_description": None,
            "h1_count": None,
            "canonical": None,
            "images_checked": 0,
            "images_missing_alt": 0,
            "forms_missing_labels": 0,
            "broken_links": [],
            "findings": [{"severity": "medium", "code": "no_html", "message": "HTML could not be analyzed because the page did not return a readable document."}],
        }
    soup = BeautifulSoup(page.body[:500_000], "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = (description_tag.get("content") or "").strip() if description_tag else ""
    h1s = soup.find_all("h1")
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical = canonical_tag.get("href") if canonical_tag else None
    images = soup.find_all("img")
    missing_alt = [img for img in images if not (img.get("alt") or "").strip()]
    missing_labels = 0
    for control in soup.find_all(["input", "select", "textarea"]):
        if control.get("type") in {"hidden", "submit", "button"}:
            continue
        control_id = control.get("id")
        labelled = False
        if control_id and soup.find("label", attrs={"for": control_id}):
            labelled = True
        if control.find_parent("label"):
            labelled = True
        if control.get("aria-label") or control.get("aria-labelledby"):
            labelled = True
        if not labelled:
            missing_labels += 1
    if not title:
        findings.append({"severity": "medium", "code": "missing_title", "message": "The page has no title element."})
    elif len(title) < 10 or len(title) > 70:
        findings.append({"severity": "low", "code": "title_length", "message": "The title length is outside the usual 10–70 character range."})
    if not description:
        findings.append({"severity": "medium", "code": "missing_description", "message": "The page has no meta description."})
    if len(h1s) == 0:
        findings.append({"severity": "medium", "code": "missing_h1", "message": "The page has no H1 heading."})
    elif len(h1s) > 1:
        findings.append({"severity": "low", "code": "multiple_h1", "message": "The page has more than one H1 heading."})
    if missing_alt:
        findings.append({"severity": "medium", "code": "missing_alt", "message": f"{len(missing_alt)} image(s) are missing alternative text."})
    if missing_labels:
        findings.append({"severity": "medium", "code": "missing_label", "message": f"{missing_labels} form control(s) have no associated label."})
    if not canonical:
        findings.append({"severity": "low", "code": "missing_canonical", "message": "No canonical link was found."})
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        findings.append({"severity": "low", "code": "missing_viewport", "message": "No viewport meta tag was found, which can hurt mobile usability."})

    broken: list[dict] = []
    origin = urlparse(page.final_url or page_url)
    checked = 0
    for anchor in soup.find_all("a", href=True):
        if checked >= 8:
            break
        href = anchor["href"].strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(page.final_url or page_url, href)
        link_host = urlparse(absolute).hostname
        if not link_host or link_host != origin.hostname:
            continue
        checked += 1
        probed = safe_fetch(absolute, method="GET")
        if probed.status_code and probed.status_code >= 400:
            broken.append({"url": absolute, "status": probed.status_code})
        elif probed.error_type in {"dns", "connection", "timeout"}:
            broken.append({"url": absolute, "status": None, "error": probed.error_type})
    if broken:
        findings.append({"severity": "medium", "code": "broken_links", "message": f"{len(broken)} same-site link(s) failed within the check limit."})
    return {
        "title": title or None,
        "meta_description": description or None,
        "h1_count": len(h1s),
        "canonical": canonical,
        "images_checked": len(images),
        "images_missing_alt": len(missing_alt),
        "forms_missing_labels": missing_labels,
        "broken_links": broken,
        "findings": findings,
    }


def check_robots_and_sitemap(site_url: str) -> dict:
    parsed = urlparse(site_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    robots = safe_fetch(root + "/robots.txt")
    robots_ok = bool(robots.status_code and robots.status_code < 400 and robots.body)
    sitemap = safe_fetch(root + "/sitemap.xml")
    sitemap_ok = bool(sitemap.status_code and sitemap.status_code < 400)
    findings = []
    if not robots_ok:
        findings.append({"severity": "low", "code": "robots", "message": "robots.txt was not available."})
    if not sitemap_ok:
        findings.append({"severity": "low", "code": "sitemap", "message": "sitemap.xml was not available at the site root."})
    return {"robots_txt_present": robots_ok, "sitemap_present": sitemap_ok, "findings": findings}
