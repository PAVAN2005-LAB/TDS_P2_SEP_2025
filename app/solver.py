import time
import re
import httpx
from playwright.async_api import async_playwright

async def get_html(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        html = await page.content()
        await browser.close()
    return html


def compute_answer(html):
    # TODO: implement your real logic
    return 1


async def submit_answer(api_url, payload):
    async with httpx.AsyncClient() as client:
        r = await client.post(api_url, json=payload)
        return r.json()


async def solve_quiz(email, secret, url, deadline):
    current = url

    while True:
        if time.time() > deadline:
            return {"error": "Timeout"}

        html = await get_html(current)

        submit_url = re.search(r'https?://[^\s"]+/submit', html)
        if not submit_url:
            raise ValueError("Submit URL not found!")
        submit_url = submit_url.group(0)

        answer = compute_answer(html)

        payload = {
            "email": email,
            "secret": secret,
            "url": current,
            "answer": answer
        }

        result = await submit_answer(submit_url, payload)

        if result.get("url"):
            current = result["url"]
        else:
            return result
