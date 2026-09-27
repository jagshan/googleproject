const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Simple CLI args parser
function parseArgs() {
    const args = process.argv.slice(2);
    const queries = [];
    let output = 'agent_demo.webm';

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '-q' && i + 1 < args.length) {
            queries.push(args[++i]);
        } else if (args[i] === '-o' && i + 1 < args.length) {
            output = args[++i];
        }
    }

    if (queries.length === 0) {
        queries.push('What items do I have in my pantry and are any expiring soon?');
        queries.push('Generate a photo of a delicious pasta dish and check the weather in Seattle');
    }

    return { queries, output };
}

async function record() {
    const { queries, output } = parseArgs();
    const frontendUrl = process.env.FRONTEND_URL || 'https://smart-pantry-frontend-34695136582.us-east1.run.app';
    const tempVideoDir = path.join(__dirname, 'temp_video');

    if (!fs.existsSync(tempVideoDir)) {
        fs.mkdirSync(tempVideoDir, { recursive: true });
    }

    console.log(`Starting demo recording for URL: ${frontendUrl}`);
    console.log(`Prompts: ${JSON.stringify(queries)}`);

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
        recordVideo: {
            dir: tempVideoDir,
            size: { width: 1280, height: 800 }
        }
    });

    const page = await context.newPage();
    console.log(`Navigating to ${frontendUrl}...`);
    await page.goto(frontendUrl, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    for (let idx = 0; idx < queries.length; idx++) {
        const query = queries[idx];
        console.log(`[${idx + 1}/${queries.length}] Typing prompt: "${query}"...`);

        await page.type('#input', query, { delay: 35 });
        await page.waitForTimeout(500);
        await page.click("button[type='submit']");

        console.log(`[${idx + 1}/${queries.length}] Waiting for agent response...`);
        // Wait for agent bubble
        await page.waitForSelector('.msg.agent .bubble', { timeout: 45000 });

        // Wait until text is loaded and not placeholder
        for (let attempt = 0; attempt < 35; attempt++) {
            const agentMsgs = await page.$$('.msg.agent');
            if (agentMsgs.length >= idx + 1) {
                const text = await agentMsgs[agentMsgs.length - 1].innerText();
                if (text && !text.includes('…')) {
                    break;
                }
            }
            await page.waitForTimeout(1000);
        }

        await page.waitForTimeout(5000);
    }

    const video = page.video();
    let videoPath = null;
    if (video) {
        videoPath = await video.path();
    }

    await context.close();
    await browser.close();

    if (videoPath && fs.existsSync(videoPath)) {
        const targetOutput = path.resolve(process.cwd(), output);
        fs.copyFileSync(videoPath, targetOutput);
        console.log(`\n✅ Demo recording successfully saved to: ${targetOutput}`);
    } else {
        console.error('❌ Failed to locate recorded video.');
        process.exit(1);
    }
}

record().catch((err) => {
    console.error('Error during recording:', err);
    process.exit(1);
});
