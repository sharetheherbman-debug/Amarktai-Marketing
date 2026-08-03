import express from 'express';
import { CheerioCrawler, log } from 'crawlee';

const app = express();
app.use(express.json());

// Health check
app.get('/health', (_req, res) => res.json({ status: 'ok' }));

// Scrape endpoint
app.post('/scrape', async (req, res) => {
  const { url, selector } = req.body;
  if (!url) return res.status(400).json({ error: 'url is required' });

  try {
    let content = '';
    const crawler = new CheerioCrawler({
      maxRequestsPerCrawl: 1,
      requestHandlerTimeoutSecs: 30,
      async requestHandler({ $, body }) {
        if (selector) {
          content = $(selector).text().trim();
        } else {
          // Extract main content: article, main, or body
          content = $('article').text() || $('main').text() || $('body').text();
          content = content.replace(/\s+/g, ' ').trim().substring(0, 50000);
        }
      },
      failedRequestHandler({ request }, error) {
        log.error(`Scrape failed for ${request.url}: ${error.message}`);
        content = '';
      },
    });

    await crawler.run([url]);

    if (!content) {
      return res.status(422).json({ error: 'No content extracted', url });
    }

    res.json({ url, content, scrapedAt: new Date().toISOString() });
  } catch (error: any) {
    res.status(500).json({ error: error.message, url });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Scraper API listening on port ${PORT}`));
