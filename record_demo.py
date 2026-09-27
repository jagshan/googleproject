import asyncio
import os
import shutil
from playwright.async_api import async_playwright

VIDEO_DIR = "/config/.gemini/antigravity/brain/6a8e3fba-e894-4af4-ba9d-fafd30d38cca"
FRONTEND_URL = "https://smart-pantry-frontend-34695136582.us-east1.run.app"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print(f"Navigating to {FRONTEND_URL}...")
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Prompt 1: Core app feature (Pantry Inventory & Expiration Check)
        prompt_1 = "What items do I have in my pantry and are any expiring soon?"
        print(f"Typing Prompt 1: '{prompt_1}'...")
        await page.type("#input", prompt_1, delay=35)
        await page.wait_for_timeout(500)
        await page.click("button[type='submit']")

        # Wait for reply bubble to finish loading
        print("Waiting for agent response 1...")
        await page.wait_for_selector(".msg.agent .bubble", timeout=30000)
        # Wait until response isn't '…'
        for _ in range(30):
            text = await page.inner_text(".msg.agent:last-child .bubble")
            if text and text != "…":
                break
            await page.wait_for_timeout(1000)

        await page.wait_for_timeout(5000)

        # Prompt 2: Richer prompt showing image tool & weather lookup
        prompt_2 = "Generate a photo of a delicious pasta dish and check the weather in Seattle"
        print(f"Typing Prompt 2: '{prompt_2}'...")
        await page.type("#input", prompt_2, delay=35)
        await page.wait_for_timeout(500)
        await page.click("button[type='submit']")

        print("Waiting for agent response 2...")
        # Wait until second agent message arrives and finishes
        for _ in range(45):
            messages = await page.query_selector_all(".msg.agent")
            if len(messages) >= 2:
                last_text = await messages[-1].inner_text()
                if last_text and "…" not in last_text:
                    break
            await page.wait_for_timeout(1000)

        await page.wait_for_timeout(6000)

        # Get video path
        video_path = await page.video.path()
        print("Recorded video saved at temp path:", video_path)

        await context.close()
        await browser.close()

        target_path = os.path.join(VIDEO_DIR, "demo_video.webm")
        shutil.copy(video_path, target_path)
        print("Final demo video copied to:", target_path)

if __name__ == "__main__":
    asyncio.run(main())
